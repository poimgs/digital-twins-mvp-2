"""
Bot Management Utility Script

This script provides utilities for creating and managing bots in the multi-bot system.
It includes functions for creating bots, setting up personality profiles, and managing bot configurations.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from core.supabase_client import supabase_client
from core.models import Bot, PersonalityProfile

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_bot(
    name: str,
    description: str,
    welcome_message: str,
    call_to_action: str,
    personality_values: list = None,
    formality_vocabulary: str = "",
    tone: str = "",
    sentence_structure: str = "",
    recurring_phrases_metaphors: str = "",
    emotional_expression: str = "",
    storytelling_style: str = ""
) -> Bot:
    """
    Create a new bot with personality profile.
    
    Args:
        name: Bot name
        description: Bot description
        welcome_message: Welcome message for users
        call_to_action: Call to action message
        personality_values: List of personality values
        formality_vocabulary: Formality and vocabulary style
        tone: Communication tone
        sentence_structure: Sentence structure preferences
        recurring_phrases_metaphors: Recurring phrases and metaphors
        emotional_expression: Emotional expression style
        storytelling_style: Storytelling style
    
    Returns:
        Created Bot instance
    """
    try:
        # Create personality profile first
        personality_profile = PersonalityProfile(
            bot_id=uuid4(),  # Temporary, will be updated after bot creation
            values=personality_values or [],
            formality_vocabulary=formality_vocabulary,
            tone=tone,
            sentence_structure=sentence_structure,
            recurring_phrases_metaphors=recurring_phrases_metaphors,
            emotional_expression=emotional_expression,
            storytelling_style=storytelling_style,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Create bot
        bot = Bot(
            name=name,
            description=description,
            welcome_message=welcome_message,
            call_to_action=call_to_action,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Insert bot first
        created_bot = supabase_client.insert_bot(bot)
        
        # Update personality profile with correct bot_id
        personality_profile.bot_id = created_bot.id
        created_personality = supabase_client.insert_personality_profile(personality_profile)
        
        # Update bot with personality profile ID
        created_bot.personality_profile_id = created_personality.id
        updated_bot = supabase_client.update_bot(created_bot)
        
        logger.info(f"Successfully created bot: {updated_bot.name}")
        return updated_bot
        
    except Exception as e:
        logger.error(f"Error creating bot: {e}")
        raise


def list_bots():
    """List all bots in the system."""
    try:
        bots = supabase_client.get_bots(active_only=False)
        
        print("\n" + "="*60)
        print("🤖 ALL BOTS IN SYSTEM")
        print("="*60)
        
        if not bots:
            print("No bots found.")
            return
        
        for bot in bots:
            status = "✅ Active" if bot.is_active else "❌ Inactive"
            print(f"\nBot ID: {bot.id}")
            print(f"Name: {bot.name}")
            print(f"Description: {bot.description or 'No description'}")
            print(f"Status: {status}")
            print(f"Created: {bot.created_at}")
            print("-" * 40)
            
    except Exception as e:
        logger.error(f"Error listing bots: {e}")
        print(f"❌ Error listing bots: {e}")


def create_sample_bot():
    """Create a sample bot for testing."""
    try:
        sample_bot = create_bot(
            name="Sample Digital Twin",
            description="A sample digital twin for testing the multi-bot system",
            welcome_message="Hello! I'm a sample digital twin. I'm here to chat with you and share stories from my experiences.",
            call_to_action="Feel free to ask me about my experiences, values, or anything else you'd like to know!",
            personality_values=["authenticity", "curiosity", "empathy", "growth"],
            formality_vocabulary="Casual and approachable, using everyday language",
            tone="Warm, friendly, and conversational",
            sentence_structure="Mix of short and medium sentences, occasionally longer for storytelling",
            recurring_phrases_metaphors="Uses metaphors from nature and everyday life",
            emotional_expression="Open and genuine, comfortable sharing feelings",
            storytelling_style="Narrative-driven with personal anecdotes and reflections"
        )
        
        print(f"\n✅ Successfully created sample bot: {sample_bot.name}")
        print(f"Bot ID: {sample_bot.id}")
        
    except Exception as e:
        logger.error(f"Error creating sample bot: {e}")
        print(f"❌ Error creating sample bot: {e}")


def main():
    """Main function for bot management."""
    try:
        # Validate configuration
        settings.validate()
        
        print("\n" + "="*60)
        print("🤖 BOT MANAGEMENT UTILITY")
        print("="*60)
        print("1. List all bots")
        print("2. Create sample bot")
        print("3. Exit")
        print("="*60)
        
        while True:
            choice = input("\nSelect an option (1-3): ").strip()
            
            if choice == "1":
                list_bots()
            elif choice == "2":
                create_sample_bot()
            elif choice == "3":
                print("\n👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please select 1, 2, or 3.")
                
    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("Please check your .env file and ensure all required variables are set.")
        return False
    except Exception as e:
        logger.error(f"Error in bot management: {e}")
        print(f"\n❌ Error: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
