#!/usr/bin/env python3
"""
Terminal Chat Application for Narrative Digital Twin MVP - Phase 2

This script provides a command-line chat interface that:
1. Initializes the conversational engine
2. Creates a local command-line chat interface
3. Manages the main conversation loop
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from core.conversational_engine import conversational_engine
from core.personality import personality_profiler

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
    
    def display_welcome(self):
        """Display welcome message and personality summary."""
        print("\n" + "="*60)
        print("🤖 NARRATIVE DIGITAL TWIN - CHAT INTERFACE")
        print("="*60)
        
        try:
            # Get personality summary
            summary = personality_profiler.generate_personality_summary(self.user_id)
            if summary:
                print("\n📝 About your digital twin:")
                print("-" * 40)
                print(summary)
                print("-" * 40)
            else:
                print("\n⚠️  No personality profile found.")
                print("Please run the setup script first: python scripts/run_setup.py")
                
        except Exception as e:
            logger.error(f"Error displaying personality summary: {e}")
            print("\n⚠️  Could not load personality profile.")
        
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
        print("profile  - Show personality profile summary")
        print("stats    - Show conversation statistics")
        print("quit     - Exit the chat")
        print("exit     - Exit the chat")
        print("bye      - Exit the chat")
        print("="*40 + "\n")
    
    def display_profile(self):
        """Display current personality profile."""
        try:
            summary = personality_profiler.generate_personality_summary(self.user_id)
            if summary:
                print("\n" + "="*50)
                print("PERSONALITY PROFILE:")
                print("="*50)
                print(summary)
                print("="*50 + "\n")
            else:
                print("\n⚠️  No personality profile available.\n")
        except Exception as e:
            logger.error(f"Error displaying profile: {e}")
            print("\n❌ Error loading personality profile.\n")
    
    def display_stats(self):
        """Display conversation statistics."""
        try:
            state = self.engine.get_or_create_state(self.user_id)

            print("\n" + "="*40)
            print("CONVERSATION STATISTICS:")
            print("="*40)
            print(f"Turn count: {state.state['turn_count']}")
            print(f"Current topics: {', '.join(state.state['current_topics']) if state.state['current_topics'] else 'None'}")
            print(f"User ID: {state.user_id}")
            print(f"Profile loaded: {'Yes' if state.personality_profile else 'No'}")
            print(f"Stories told: {len(state.state['retrieved_story_history'])}")
            print("="*40 + "\n")

        except Exception as e:
            logger.error(f"Error displaying stats: {e}")
            print("\n❌ Error loading conversation statistics.\n")
    
    def clear_history(self):
        """Clear conversation state (local only)."""
        try:
            if self.user_id in self.engine.states:
                # Reset the conversation state
                self.engine.reset_conversation(self.user_id)
                print("\n✅ Conversation state reset.\n")
            else:
                print("\n💭 No conversation state to clear.\n")
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
        elif command == 'profile':
            self.display_profile()
            return True
        elif command == 'stats':
            self.display_stats()
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
                print("\n🤖 Thinking...")
                response = self.engine.generate_response(user_input, self.user_id)
                
                # Display response
                print(f"\nDigital Twin: {response}\n")
                
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
