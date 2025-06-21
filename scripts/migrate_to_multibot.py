"""
Setup Script for Multi-Bot System

This script sets up the multi-bot system by creating a sample bot for testing.
Since backward compatibility is not required, this simply creates a fresh setup.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timezone


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


def create_sample_bot():
    """Create a sample bot for testing the multi-bot system."""
    try:
        print("🔄 Creating sample bot...")

        # Create sample bot
        sample_bot = Bot(
            name="Sample Digital Twin",
            description="A sample digital twin for testing the multi-bot system",
            welcome_message="Hello! I'm a sample digital twin. I'm here to chat with you and share stories from my experiences.",
            call_to_action="Feel free to ask me about my experiences, values, or anything else you'd like to know!",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        # Insert bot
        created_bot = supabase_client.insert_bot(sample_bot)
        print(f"✅ Created sample bot: {created_bot.name} (ID: {created_bot.id})")

        # Create personality profile for the bot
        personality_profile = PersonalityProfile(
            bot_id=created_bot.id,
            values=["authenticity", "curiosity", "empathy", "growth"],
            formality_vocabulary="Casual and approachable, using everyday language",
            tone="Warm, friendly, and conversational",
            sentence_structure="Mix of short and medium sentences, occasionally longer for storytelling",
            recurring_phrases_metaphors="Uses metaphors from nature and everyday life",
            emotional_expression="Open and genuine, comfortable sharing feelings",
            storytelling_style="Narrative-driven with personal anecdotes and reflections",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        created_personality = supabase_client.insert_personality_profile(personality_profile)
        print(f"✅ Created personality profile for bot")

        # Update bot with personality profile ID
        created_bot.personality_profile_id = created_personality.id
        updated_bot = supabase_client.update_bot(created_bot)

        return updated_bot

    except Exception as e:
        logger.error(f"Error creating sample bot: {e}")
        raise





def main():
    """Main setup function."""
    try:
        # Validate configuration
        settings.validate()

        print("\n" + "="*60)
        print("🔄 MULTI-BOT SETUP UTILITY")
        print("="*60)
        print("This script will set up the multi-bot system with a sample bot.")
        print("="*60)

        # Check if setup is needed
        try:
            bots = supabase_client.get_bots(active_only=False)
            if bots:
                print("\n✅ Multi-bot system already set up!")
                print(f"Found {len(bots)} bot(s) in the system.")
                for bot in bots:
                    status = "Active" if bot.is_active else "Inactive"
                    print(f"  - {bot.name} ({status})")
                return True
        except Exception:
            # Expected if bots table doesn't exist yet
            pass

        confirm = input("\nProceed with setup? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Setup cancelled.")
            return True

        print("\n🚀 Starting setup...")

        # Create sample bot
        sample_bot = create_sample_bot()

        print("\n" + "="*60)
        print("✅ SETUP COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"Sample bot created: {sample_bot.name}")
        print(f"Bot ID: {sample_bot.id}")
        print("\nYou can now:")
        print("1. Run the chat application to test the sample bot")
        print("2. Use scripts/bot_manager.py to create additional bots")
        print("3. Update the sample bot's configuration as needed")
        print("="*60)

        return True

    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("Please check your .env file and ensure all required variables are set.")
        return False
    except Exception as e:
        logger.error(f"Error during setup: {e}")
        print(f"\n❌ Setup failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
