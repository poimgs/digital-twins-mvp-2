"""
Setup Script for Narrative Digital Twin MVP - Multi-Bot Support

This script handles the complete setup process for all bots:
1. Retrieves all bots from the database
2. For each bot, reads their stories from database
3. Runs the deconstruction and personality generation pipelines per bot
4. Populates the 'story_analysis' and 'personality_profiles' tables with bot-specific data
"""

import sys
import logging
from pathlib import Path
from typing import List

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from core.supabase_client import supabase_client
from core.story_deconstructor import story_deconstructor
from core.personality import personality_profiler
from core.models import Story, StoryAnalysis

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_story_analysis_for_bot(bot_id: str, stories: List[Story]) -> List[StoryAnalysis]:
    """
    Run story analysis for a specific bot's stories.

    Args:
        bot_id: Bot ID for filtering existing analyses
        stories: List of Story instances from database for this bot

    Returns:
        List of StoryAnalysis instances for this bot
    """
    logger.info(f"Starting story analysis pipeline for bot {bot_id}...")

    try:
        # Check if analyses already exist for this bot's stories
        existing_analyses = supabase_client.get_story_analyses()
        bot_story_ids = [str(story.id) for story in stories]
        existing_bot_analyses = [
            a for a in existing_analyses
            if str(a.story_id) in bot_story_ids
        ]
        analyzed_story_ids = [str(a.story_id) for a in existing_bot_analyses]

        # Filter out already analyzed stories
        stories_to_analyze = [
            story for story in stories
            if str(story.id) not in analyzed_story_ids
        ]

        if not stories_to_analyze:
            logger.info(f"All stories for bot {bot_id} already analyzed")
            return existing_bot_analyses

        # Analyze new stories (returns StoryAnalysis objects)
        new_analyses = story_deconstructor.analyze_multiple_stories(stories_to_analyze)

        # Combine with existing analyses for this bot
        all_bot_analyses = existing_bot_analyses + new_analyses

        logger.info(f"Completed analysis of {len(new_analyses)} new stories for bot {bot_id}")
        return all_bot_analyses
    except Exception as e:
        logger.error(f"Error in story analysis pipeline for bot {bot_id}: {e}")
        raise

def main():
    """Main setup function."""
    logger.info("Starting Narrative Digital Twin setup for all bots...")
    try:
        # Validate configuration
        settings.validate()
        logger.info("Configuration validated successfully")

        # Step 1: Get all bots from database
        bots = supabase_client.get_all_bots()
        if not bots:
            logger.warning("No bots found in database")
            print("No bots found in database. Please create bots first using scripts/bot_manager.py")
            return False

        logger.info(f"Found {len(bots)} bots to process")

        total_stories_processed = 0
        total_analyses_created = 0
        profiles_created = 0

        # Process each bot individually
        for bot in bots:
            logger.info(f"Processing bot: {bot.name} (ID: {bot.id})")

            # Step 2: Get stories for this bot
            bot_stories = supabase_client.get_stories(bot_id=str(bot.id))
            if not bot_stories:
                logger.info(f"No stories found for bot {bot.name}, skipping...")
                continue

            logger.info(f"Found {len(bot_stories)} stories for bot {bot.name}")

            # Filter stories to only include "stories" category for analysis
            stories_to_analyze = [story for story in bot_stories if story.category_type == "stories"]
            
            if not stories_to_analyze:
                logger.info(f"No 'stories' category content found for bot {bot.name}, skipping story analysis...")
                continue

            logger.info(f"Found {len(stories_to_analyze)} stories (category: 'stories') for analysis for bot {bot.name}")

            # Step 3: Run story analysis for this bot (stories category only)
            logger.info(f"Running story analysis for bot {bot.name}...")
            bot_analyses = run_story_analysis_for_bot(str(bot.id), stories_to_analyze)

            # Step 4: Generate personality profile for this bot (stories category only)
            logger.info(f"Generating personality profile for bot {bot.name}...")
            try:
                # Check if profile already exists
                existing_profile = supabase_client.get_personality_profile(str(bot.id))
                if existing_profile:
                    logger.info(f"Personality profile already exists for bot {bot.name}")
                    profile = existing_profile
                else:
                    # Generate new profile using only stories category content
                    profile = personality_profiler.generate_personality(stories_to_analyze, str(bot.id))
                    # Set the correct bot_id
                    profile.bot_id = bot.id
                    # Store the profile
                    stored_profile = supabase_client.insert_personality_profile(profile)
                    profile = stored_profile
                    logger.info(f"Created new personality profile for bot {bot.name}")

                profiles_created += 1
            except Exception as e:
                logger.error(f"Failed to generate personality profile for bot {bot.name}: {e}")
                profile = None

            # Update totals
            total_stories_processed += len(bot_stories)
            total_analyses_created += len([a for a in bot_analyses if a])

            logger.info(f"Completed processing bot {bot.name}")

        # Summary
        logger.info("Setup completed successfully!")
        logger.info(f"- Bots processed: {len(bots)}")
        logger.info(f"- Stories processed: {total_stories_processed}")
        logger.info(f"- Analyses created: {total_analyses_created}")
        logger.info(f"- Personality profiles: {profiles_created}")

        print("\n" + "="*50)
        print("SETUP COMPLETE!")
        print("="*50)
        print(f"✓ Processed {len(bots)} bots")
        print(f"✓ Processed {total_stories_processed} stories")
        print(f"✓ Created {profiles_created} personality profiles")
        print("\nYou can now run the chat application:")
        print("python terminal_app/chat.py")
        print("="*50)

        return True

    except Exception as e:
        logger.error(f"Setup failed: {e}")
        print(f"\nSetup failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
