"""
Terminal Chat Application for Narrative Digital Twin MVP - Phase 2

This script provides a command-line chat interface that:
1. Initializes the conversational engine
2. Creates a local command-line chat interface
3. Manages the main conversation loop
"""

import sys
import logging
from pathlib import Path
from typing import Optional
from core.models import Bot, generate_terminal_chat_id

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from core.conversational_engine import conversational_engine
from core.supabase_client import supabase_client

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChatInterface:
    """Command-line chat interface for the digital twin."""

    def __init__(self, user_id: str = "default"):
        """Initialize the chat interface."""
        self.user_id = user_id
        self.engine = conversational_engine
        self.running = False
        self.selected_bot: Optional[Bot] = None

    def select_bot(self):
        """Allow user to select a bot to chat with."""
        try:
            bots = supabase_client.get_bots(active_only=True)
            if not bots:
                print("\n❌ No active bots found. Please create a bot first.")
                return False

            print("\n" + "="*60)
            print("🤖 SELECT A DIGITAL TWIN TO CHAT WITH")
            print("="*60)

            for i, bot in enumerate(bots, 1):
                print(f"{i}. {bot.name}")
                if bot.description:
                    print(f"   {bot.description}")
                print()

            while True:
                try:
                    choice = input("Select a bot (enter number): ").strip()
                    if choice.lower() in ['quit', 'exit', 'bye']:
                        return False

                    bot_index = int(choice) - 1
                    if 0 <= bot_index < len(bots):
                        self.selected_bot = bots[bot_index]
                        return True
                    else:
                        print("❌ Invalid selection. Please try again.")
                except ValueError:
                    print("❌ Please enter a valid number.")
                except KeyboardInterrupt:
                    return False

        except Exception as e:
            logger.error(f"Error selecting bot: {e}")
            print("\n❌ Error loading bots.")
            return False

    def display_welcome(self):
        """Display welcome message and personality summary."""
        if not self.selected_bot:
            return

        print("\n" + "="*60)
        print(f"🤖 CHATTING WITH: {self.selected_bot.name.upper()}")
        print("="*60)

        # Display bot's welcome message
        print(f"\n{self.selected_bot.welcome_message}")

        try:
            # Get personality summary for the selected bot
            personality_profile = supabase_client.get_personality_profile(str(self.selected_bot.id))
            if personality_profile:
                print("\n📝 About this digital twin:")
                print("-" * 40)
                print(f"Values: {', '.join(personality_profile.values)}")
                print(f"Communication Style: {personality_profile.tone}")
                print("-" * 40)

        except Exception as e:
            logger.error(f"Error displaying personality summary: {e}")

        print("\n💬 Start chatting! Type 'quit', 'exit', or 'bye' to end the conversation.")
        print("Type 'help' for available commands.")
        print("="*60 + "\n")

    def display_help(self):
        """Display help information."""
        print("\n" + "="*40)
        print("AVAILABLE COMMANDS:")
        print("="*40)
        print("help     - Show this help message")
        print("clear    - Clear conversation history")
        print("quit     - Exit the chat")
        print("exit     - Exit the chat")
        print("bye      - Exit the chat")
        print("="*40 + "\n")

    def clear_history(self):
        """Clear conversation state (local only)."""
        if not self.selected_bot:
            print("\n❌ No bot selected.\n")
            return

        try:
            # Reset the conversation state using terminal chat_id
            chat_id = generate_terminal_chat_id(str(self.selected_bot.id))
            self.engine.reset_conversation(str(self.selected_bot.id), chat_id=chat_id)
            print("\n✅ Conversation state reset.\n")
        except Exception as e:
            logger.error(f"Error clearing history: {e}")
            print("\n❌ Error clearing conversation state.\n")

    def process_command(self, user_input: str) -> bool:
        """
        Process special commands.
        
        Args:
            user_input: The user's input
        
        Returns:
            True if it was a command, False if it's a regular message
        """
        command = user_input.lower().strip()

        if command in ['quit', 'exit', 'bye']:
            print("\n👋 Goodbye! Thanks for chatting with your digital twin.")
            return True
        elif command == 'help':
            self.display_help()
            return True
        elif command == 'clear':
            self.clear_history()
            return True

        return False

    def get_user_input(self) -> Optional[str]:
        """Get user input with proper handling."""
        try:
            user_input = input("You: ").strip()
            return user_input if user_input else None
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            return None
        except EOFError:
            print("\n\n👋 Goodbye!")
            return None

    def run(self):
        """Run the main chat loop."""
        self.running = True

        # First, select a bot
        if not self.select_bot():
            print("\n👋 Goodbye!")
            return

        self.display_welcome()

        while self.running:
            try:
                # Get user input
                user_input = self.get_user_input()

                if user_input is None:
                    break

                # Check for commands
                if self.process_command(user_input):
                    if user_input.lower() in ['quit', 'exit', 'bye']:
                        break
                    continue

                # Generate response
                if not self.selected_bot:
                    print("\n❌ No bot selected.")
                    continue

                print("\n🤖 Thinking...")
                # Use terminal chat_id for terminal app
                chat_id = generate_terminal_chat_id(str(self.selected_bot.id))
                response = self.engine.generate_response(user_input, str(self.selected_bot.id), chat_id=chat_id)

                # Display response
                print(f"\n{self.selected_bot.name}: {response.response}")

                # Display follow-up questions if available
                if response.follow_up_questions:
                    print("\n💡 You might also ask:")
                    for i, question in enumerate(response.follow_up_questions, 1):
                        print(f"   {i}. {question}")
                print()

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error in chat loop: {e}")
                print(f"\n❌ Sorry, I encountered an error: {e}\n")

        self.running = False


def main():
    """Main function to start the chat application."""
    try:
        # Validate configuration
        settings.validate()
        
        # Create and run chat interface
        chat = ChatInterface()
        chat.run()
        
    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("Please check your .env file and ensure all required variables are set.")
        return False
    except Exception as e:
        logger.error(f"Error starting chat application: {e}")
        print(f"\n❌ Error starting chat: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
