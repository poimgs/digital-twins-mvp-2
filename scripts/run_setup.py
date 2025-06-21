"""
Setup Script for Narrative Digital Twin MVP - Phase 1

This script handles the complete setup process:
1. Reads stories from database
2. Runs the deconstruction and personality generation pipelines
3. Populates the 'story_analysis' and 'personality_profiles' tables
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

def run_story_analysis(stories: List[Story]) -> List[StoryAnalysis]:
    """
    Run story analysis on all stories.

    Args:
        stories: List of Story instances from database

    Returns:
        List of StoryAnalysis instances
    """
    logger.info("Starting story analysis pipeline...")

    try:
        # Check if analyses already exist
        existing_analyses = supabase_client.get_story_analyses()
        analyzed_story_ids = [str(a.story_id) for a in existing_analyses]

        # Filter out already analyzed stories
        stories_to_analyze = [
            story for story in stories
            if str(story.id) not in analyzed_story_ids
        ]

        if not stories_to_analyze:
            logger.info("All stories already analyzed")
            return existing_analyses

        # Analyze new stories (returns StoryAnalysis objects)
        new_analyses = story_deconstructor.analyze_multiple_stories(stories_to_analyze)

        # Combine with existing analyses
        all_analyses = existing_analyses + new_analyses

        logger.info(f"Completed analysis of {len(new_analyses)} new stories")
        return all_analyses
    except Exception as e:
        logger.error(f"Error in story analysis pipeline: {e}")
        raise

def main():
    """Main setup function."""
    logger.info("Starting Narrative Digital Twin setup...")
    try:
        # Validate configuration
        settings.validate()
        logger.info("Configuration validated successfully")

        # Step 1: Get stories from database
        stories = supabase_client.get_stories()
        
        # Step 2: Run story analysis
        logger.info("Step 3: Running story analysis...")
        analyses = run_story_analysis(stories)
        
        # Step 3: Generate personality profile
        # Create dictionary 
        logger.info("Step 4: Generating personality profile...")
        profile = personality_profiler.generate_personality(stories)
        
        # Summary
        logger.info("Setup completed successfully!")
        logger.info(f"- Stories processed: {len(stories)}")
        logger.info(f"- Analyses created: {len(analyses)}")
        logger.info(f"- Personality profile: {'Created' if profile else 'Failed'}")

        print("\n" + "="*50)
        print("SETUP COMPLETE!")
        print("="*50)
        print(f"✓ Processed {len(stories)} stories")
        print(f"✓ Created personality profile")
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
