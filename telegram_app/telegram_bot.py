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
import signal
import asyncio
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from config.settings import settings
from core.conversational_engine import ConversationalEngine
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
        self.engine = ConversationalEngine(bot_id)
        self.bot_info: Bot = self._load_bot_info()

        # Create shutdown event for graceful exit
        self._shutdown_event = asyncio.Event()
        self._is_shutting_down = False

        # Track active message processing tasks
        self._active_tasks = set()
        self._task_lock = asyncio.Lock()

        # Create Telegram application
        self.application = Application.builder().token(telegram_token).build()

        # Add handlers
        self._setup_handlers()

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
    
    def _load_bot_info(self):
        """Load bot information from database."""
        try:
            bot_info = supabase_client.get_bot_by_id(self.bot_id)
            if not bot_info:
                raise ValueError(f"Bot with ID {self.bot_id} not found")
            logger.info(f"Loaded bot: {bot_info.name}")
            return bot_info
        except Exception as e:
            logger.error(f"Error loading bot information: {e}")
            raise

    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum} ({signal.Signals(signum).name}), initiating graceful shutdown...")
            # Create a task to handle shutdown in the event loop
            # We need to schedule the shutdown in the event loop
            # This will be handled by the run method
            self._shutdown_event.set()

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
        logger.info("Signal handlers registered for graceful shutdown")

    async def _add_active_task(self, task):
        """Add a task to the active tasks set."""
        async with self._task_lock:
            self._active_tasks.add(task)

    async def _remove_active_task(self, task):
        """Remove a task from the active tasks set."""
        async with self._task_lock:
            self._active_tasks.discard(task)

    async def _wait_for_active_tasks(self, timeout: float = 60.0):
        """Wait for all active tasks to complete with a timeout."""
        if not self._active_tasks:
            return

        logger.info(f"Waiting for {len(self._active_tasks)} active tasks to complete...")

        try:
            # Wait for all active tasks to complete, with timeout
            await asyncio.wait_for(
                asyncio.gather(*self._active_tasks, return_exceptions=True),
                timeout=timeout
            )
            logger.info("All active tasks completed successfully")
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for tasks to complete after {timeout}s")
            # Cancel remaining tasks
            for task in self._active_tasks:
                if not task.done():
                    task.cancel()
            logger.info("Cancelled remaining active tasks")
        except Exception as e:
            logger.error(f"Error waiting for active tasks: {e}")

    async def _shutdown(self):
        """Perform graceful shutdown of the bot."""
        if self._is_shutting_down:
            logger.info("Shutdown already in progress...")
            return

        self._is_shutting_down = True
        logger.info("Starting graceful shutdown...")

        try:
            # First, wait for all active message processing tasks to complete
            logger.info("Waiting for active message processing tasks to complete...")
            await self._wait_for_active_tasks(timeout=60.0)

            # Stop accepting new updates by stopping the updater
            updater = self.application.updater
            if updater:
                logger.info("Stopping updater (no new messages will be processed)...")
                await updater.stop()

            # Give a brief moment for any final operations to complete
            await asyncio.sleep(1.0)

            # Stop the application gracefully
            logger.info("Stopping Telegram application...")
            await self.application.stop()

            # Shutdown the application
            logger.info("Shutting down Telegram application...")
            await self.application.shutdown()

            # Perform any additional cleanup here if needed
            # For example, close database connections, save state, etc.
            logger.info("Performing cleanup...")

            logger.info("Graceful shutdown completed successfully")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

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
        if not update.message:
            logger.warning("Received start command without message")
            return

        if not self.bot_info:
            await update.message.reply_text("❌ Bot configuration error. Please contact support.")
            return
        
        if not update.effective_chat:
            logger.warning("Received start command without effective_chat")
            await update.message.reply_text("❌ Unable to identify chat.")
            return
        
        telegram_chat_id = update.effective_chat.id

        welcome_text = f"{self.bot_info.welcome_message}"
        await update.message.reply_text(welcome_text)

        # Send and pin the instruction message
        await self._send_and_pin_instruction_message(update, context)

        follow_up_questions = self.engine.get_initial_category_questions(bot_id=self.bot_id, telegram_chat_id=telegram_chat_id)
        await self._send_follow_up_questions(update, follow_up_questions)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        if not update.message:
            logger.warning("Received help command without message")
            return

        help_text = f"""
/start - Get welcome message and introduction
/help - Show this help message
/reset - Reset conversation history
"""
        await update.message.reply_text(help_text.strip())
    
    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reset command."""
        if not update.message:
            logger.warning("Received reset command without message")
            return

        if not update.effective_chat:
            logger.warning("Received reset command without effective_chat")
            await update.message.reply_text("❌ Unable to identify chat.")
            return

        try:
            telegram_chat_id = update.effective_chat.id
            success = self.engine.reset_conversation(self.bot_id, telegram_chat_id=telegram_chat_id)

            if success:
                await update.message.reply_text("✅ Conversation history has been reset!")
                welcome_text = f"{self.bot_info.welcome_message}"
                await update.message.reply_text(welcome_text)

                # Send and pin the instruction message
                await self._send_and_pin_instruction_message(update, context)
                
                follow_up_questions = self.engine.get_initial_category_questions(bot_id=self.bot_id, telegram_chat_id=telegram_chat_id)
                await self._send_follow_up_questions(update, follow_up_questions)
            else:
                await update.message.reply_text("❌ Failed to reset conversation history.")
        except Exception as e:
            logger.error(f"Error resetting conversation: {e}")
            await update.message.reply_text("❌ An error occurred while resetting the conversation.")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages with task tracking for graceful shutdown."""
        if self._is_shutting_down:
            if update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Sorry, I'm currently unavailable. Please try again later."
                )
            return

        # Create a task for this message processing
        task = asyncio.current_task()
        if task:
            await self._add_active_task(task)

        try:
            await self._handle_message_impl(update, context)
        finally:
            # Always remove the task when done
            if task:
                await self._remove_active_task(task)

    async def _handle_message_impl(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Implementation of message handling."""
        if not update.message:
            logger.warning("Received message handler call without message")
            return

        if not update.effective_chat:
            logger.warning("Received message without effective_chat")
            await update.message.reply_text("❌ Unable to identify chat.")
            return

        try:
            user_message = update.message.text
            if not user_message:
                logger.warning("Received message without text content")
                await update.message.reply_text("❌ I can only process text messages.")
                return

            telegram_chat_id = update.effective_chat.id

            # Show typing indicator
            await context.bot.send_chat_action(chat_id=telegram_chat_id, action="typing")

            # Generate response (this is the main processing that could take time)
            logger.debug(f"Processing message from chat {telegram_chat_id}")
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

        if not update.message:
            logger.warning("Cannot send follow-up questions without message")
            return

        if not update.effective_chat:
            logger.warning("Cannot send follow-up questions without effective_chat")
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

    async def _send_follow_up_questions_direct(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, questions: list):
        """Send follow-up questions directly using context.bot when we don't have an update.message."""
        if not questions:
            return

        # Create inline keyboard with follow-up questions
        keyboard = []
        for i, question in enumerate(questions[:3]):  # Limit to 3 questions
            callback_data = f"followup_{chat_id}_{i}"
            keyboard.append([InlineKeyboardButton(question, callback_data=callback_data)])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=chat_id,
            text="💡 You might also ask:",
            reply_markup=reply_markup
        )

    async def _send_and_pin_instruction_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send and pin the instruction message."""
        # TODO: Unpin all previously pinned messages (if any)
        if not update.effective_chat:
            logger.warning("Cannot send and pin instruction message without effective_chat")
            return

        try:
            chat_id = update.effective_chat.id           
            instruction_text = "Feel free to ask your own question to me on the chat"
            message = await context.bot.send_message(
                chat_id=chat_id,
                text=instruction_text
            )

            # Pin the message
            await context.bot.pin_chat_message(
                chat_id=chat_id,
                message_id=message.message_id,
                disable_notification=True  # Don't notify users about the pin
            )

            logger.info(f"Pinned instruction message in chat {chat_id}")

        except Exception as e:
            logger.error(f"Error sending and pinning instruction message: {e}")
            # Don't raise the exception as this is not critical functionality

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboard buttons with task tracking."""
        # Create a task for this callback processing
        if self._is_shutting_down:
            if update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Sorry, I'm currently unavailable. Please try again later."
                )
            return

        task = asyncio.current_task()
        if task:
            await self._add_active_task(task)

        try:
            await self._handle_callback_query_impl(update, context)
        finally:
            # Always remove the task when done
            if task:
                await self._remove_active_task(task)

    async def _handle_callback_query_impl(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Implementation of callback query handling."""
        try:
            query = update.callback_query
            if not query:
                logger.warning("Received callback query handler call without callback query")
                return

            # Parse callback data
            if query.data and query.data.startswith("followup_"):
                parts = query.data.split("_")
                if len(parts) >= 3:
                    chat_id = int(parts[1])
                    question_index = int(parts[2])

                    # Get stored questions from conversation manager
                    from core.conversation_manager import ConversationManager
                    from core.models import generate_telegram_chat_id

                    conversation_chat_id = generate_telegram_chat_id(self.bot_id, chat_id)
                    conversation_manager = ConversationManager(conversation_chat_id, self.bot_id)
                    questions = conversation_manager.get_follow_up_questions()

                    if questions and 0 <= question_index < len(questions):
                        if conversation_manager.ready_for_call_to_action():
                            questions[2] = "click to discover our limited-time promotion"
                        selected_question = questions[question_index]

                        # Answer the callback query first
                        await query.answer()

                        # Remove the inline keyboard
                        await query.edit_message_text("💡 You asked: " + selected_question)

                        # Show typing indicator
                        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

                        # Generate response for the selected question
                        logger.debug(f"Processing callback query from chat {chat_id}")
                        response = self.engine.generate_response(
                            user_message=selected_question,
                            bot_id=self.bot_id,
                            telegram_chat_id=chat_id
                        )

                        # Send the response (which may naturally include call to action)
                        await context.bot.send_message(chat_id=chat_id, text=response.response)

                        # Send new follow-up questions if available
                        if response.follow_up_questions:
                            await self._send_follow_up_questions_direct(
                                context, chat_id, response.follow_up_questions
                            )
                    else:
                        # Invalid question index or no questions available
                        await query.answer("⚠️ This question is no longer available.")
                else:
                    # Invalid callback data format (old format or malformed)
                    await query.answer("⚠️ This question has already been processed.")
            else:
                # Unknown callback data
                await query.answer("❌ Unknown action.")

        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
            # Answer the callback query to prevent loading state
            try:
                if query:
                    await query.answer("❌ Sorry, I encountered an error.")
            except:
                pass
            # Use context.bot.send_message instead of query.message.reply_text for safety
            if update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Sorry, I encountered an error."
                )
    
    def run(self):
        """Start the Telegram bot with graceful shutdown support."""
        logger.info(f"Starting Telegram bot for {self.bot_info.name if self.bot_info else 'Unknown Bot'}")

        # Run the async version
        asyncio.run(self.run_async())

    async def run_async(self):
        """Async version of run method for more control over shutdown."""
        logger.info(f"Starting Telegram bot for {self.bot_info.name if self.bot_info else 'Unknown Bot'}")

        try:
            # Initialize the application
            await self.application.initialize()
            await self.application.start()

            # Start polling
            updater = self.application.updater
            if updater:
                await updater.start_polling()
            else:
                logger.error("Updater is None, cannot start polling")
                return

            # Wait for shutdown signal
            logger.info("Bot is running. Press Ctrl+C to stop gracefully.")
            await self._shutdown_event.wait()

            logger.info("Shutdown signal received, stopping bot...")

        except Exception as e:
            logger.error(f"Error running bot: {e}")
            raise
        finally:
            # Ensure cleanup happens
            try:
                await self._shutdown()
            except Exception as e:
                logger.error(f"Error during final cleanup: {e}")
            logger.info("Bot has stopped running")


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
