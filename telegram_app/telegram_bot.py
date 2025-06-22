"""
Telegram Bot Integration for Digital Twin MVP

This script creates a Telegram bot that integrates with the conversational engine.
Each bot corresponds to a specific digital twin with its own personality and stories.

Usage:
    python telegram_app/telegram_bot.py <bot_id> <telegram_bot_token>

Example:
    python telegram_app/telegram_bot.py 123e4567-e89b-12d3-a456-426614174000 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
"""

import sys
import logging
from pathlib import Path
from typing import Optional

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from config.settings import settings
from core.conversational_engine import conversational_engine
from core.supabase_client import supabase_client
from core.models import Bot

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TelegramDigitalTwin:
    """Telegram bot wrapper for a digital twin."""
    
    def __init__(self, bot_id: str, telegram_token: str):
        """Initialize the Telegram bot for a specific digital twin."""
        self.bot_id = bot_id
        self.telegram_token = telegram_token
        self.engine = conversational_engine
        self.bot_info: Optional[Bot] = None

        # Store follow-up questions temporarily (in production, use Redis or database)
        self.follow_up_questions = {}

        # Load bot information
        self._load_bot_info()

        # Create Telegram application
        self.application = Application.builder().token(telegram_token).build()

        # Add handlers
        self._setup_handlers()
    
    def _load_bot_info(self):
        """Load bot information from database."""
        try:
            self.bot_info = supabase_client.get_bot_by_id(self.bot_id)
            if not self.bot_info:
                raise ValueError(f"Bot with ID {self.bot_id} not found")
            logger.info(f"Loaded bot: {self.bot_info.name}")
        except Exception as e:
            logger.error(f"Error loading bot information: {e}")
            raise
    
    def _setup_handlers(self):
        """Set up Telegram bot handlers."""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("reset", self.reset_command))
        
        # Message handler for regular text
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Callback query handler for inline keyboard buttons
        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        if not self.bot_info:
            await update.message.reply_text("❌ Bot configuration error. Please contact support.")
            return
        
        welcome_text = f"🤖 **{self.bot_info.name}**\n\n{self.bot_info.welcome_message}"
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = """
🤖 **Digital Twin Bot Commands**

/start - Get welcome message and introduction
/help - Show this help message
/reset - Reset conversation history

Just send me a message to start chatting! I'll respond based on my personality and experiences.
        """
        await update.message.reply_text(help_text.strip(), parse_mode='Markdown')
    
    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reset command."""
        try:
            telegram_chat_id = update.effective_chat.id
            success = self.engine.reset_conversation(self.bot_id, telegram_chat_id=telegram_chat_id)
            
            if success:
                await update.message.reply_text("✅ Conversation history has been reset!")
            else:
                await update.message.reply_text("❌ Failed to reset conversation history.")
        except Exception as e:
            logger.error(f"Error resetting conversation: {e}")
            await update.message.reply_text("❌ An error occurred while resetting the conversation.")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages."""
        try:
            user_message = update.message.text
            telegram_chat_id = update.effective_chat.id
            
            # Show typing indicator
            await context.bot.send_chat_action(chat_id=telegram_chat_id, action="typing")
            
            # Generate response
            response = self.engine.generate_response(
                user_message=user_message,
                bot_id=self.bot_id,
                telegram_chat_id=telegram_chat_id
            )
            
            # Send the main response
            await update.message.reply_text(response.response)
            
            # Send follow-up questions as inline keyboard if available
            if response.follow_up_questions:
                await self._send_follow_up_questions(update, response.follow_up_questions)
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text("❌ Sorry, I encountered an error. Please try again.")
    
    async def _send_follow_up_questions(self, update: Update, questions: list):
        """Send follow-up questions as inline keyboard buttons."""
        if not questions:
            return

        chat_id = update.effective_chat.id

        # Create inline keyboard with follow-up questions
        keyboard = []
        for i, question in enumerate(questions[:3]):  # Limit to 3 questions
            callback_data = f"followup_{chat_id}_{i}"
            keyboard.append([InlineKeyboardButton(question, callback_data=callback_data)])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "💡 You might also ask:",
            reply_markup=reply_markup
        )

        # Store questions for callback handling
        self.follow_up_questions[chat_id] = questions
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboard buttons."""
        try:
            query = update.callback_query
            await query.answer()

            # Parse callback data
            if query.data.startswith("followup_"):
                parts = query.data.split("_")
                if len(parts) >= 3:
                    chat_id = int(parts[1])
                    question_index = int(parts[2])

                    # Get stored questions
                    if chat_id in self.follow_up_questions:
                        questions = self.follow_up_questions[chat_id]
                        if 0 <= question_index < len(questions):
                            selected_question = questions[question_index]

                            # Remove the inline keyboard
                            await query.edit_message_text("💡 You asked: " + selected_question)

                            # Show typing indicator
                            await context.bot.send_chat_action(chat_id=chat_id, action="typing")

                            # Generate response for the selected question
                            response = self.engine.generate_response(
                                user_message=selected_question,
                                bot_id=self.bot_id,
                                telegram_chat_id=chat_id
                            )

                            # Send the response
                            await context.bot.send_message(chat_id=chat_id, text=response.response)

                            # Send new follow-up questions if available
                            if response.follow_up_questions:
                                # Create a mock update object for follow-up questions
                                mock_message = type('MockMessage', (), {
                                    'reply_text': lambda text, reply_markup=None: context.bot.send_message(
                                        chat_id=chat_id, text=text, reply_markup=reply_markup
                                    )
                                })()
                                mock_update = type('MockUpdate', (), {
                                    'effective_chat': type('MockChat', (), {'id': chat_id})(),
                                    'message': mock_message
                                })()
                                await self._send_follow_up_questions(mock_update, response.follow_up_questions)

                            # Clean up stored questions
                            del self.follow_up_questions[chat_id]

        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
            await query.message.reply_text("❌ Sorry, I encountered an error.")
    
    def run(self):
        """Start the Telegram bot."""
        logger.info(f"Starting Telegram bot for {self.bot_info.name if self.bot_info else 'Unknown Bot'}")
        self.application.run_polling()


def main():
    """Main function to start the Telegram bot."""
    if len(sys.argv) != 3:
        print("Usage: python telegram_app/telegram_bot.py <bot_id> <telegram_bot_token>")
        print("Example: python telegram_app/telegram_bot.py 123e4567-e89b-12d3-a456-426614174000 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
        sys.exit(1)
    
    bot_id = sys.argv[1]
    telegram_token = sys.argv[2]
    
    try:
        # Validate configuration
        settings.validate()
        
        # Create and run the Telegram bot
        telegram_bot = TelegramDigitalTwin(bot_id, telegram_token)
        telegram_bot.run()
        
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("Please check your bot ID and ensure the bot exists and is active.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error starting Telegram bot: {e}")
        print(f"❌ Error starting Telegram bot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
