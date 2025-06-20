"""
Setup Script for Narrative Digital Twin MVP - Phase 1

This script handles the complete setup process:
1. Reads stories from the /data/stories directory
2. Ingests them into Supabase
3. Runs the deconstruction and personality generation pipelines
4. Populates the 'story_analysis' and 'personality_profiles' tables
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
from core.models import Story, StoryAnalysis, PersonalityProfile

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def read_story_files() -> List[Story]:
    """
    Read all story files from the data/stories directory.

    Returns:
        List of Story instances with filename and content
    """
    stories = []
    stories_dir = Path(settings.STORIES_DIR)

    if not stories_dir.exists():
        logger.error(f"Stories directory not found: {stories_dir}")
        return stories

    # Read all .txt files in the stories directory
    for story_file in stories_dir.glob("*.txt"):
        try:
            with open(story_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            if content:
                story = Story(
                    filename=story_file.name,
                    title=story_file.stem.replace('_', ' ').title(),
                    content=content
                )
                stories.append(story)
                logger.info(f"Read story: {story_file.name}")
            else:
                logger.warning(f"Empty story file: {story_file.name}")

        except Exception as e:
            logger.error(f"Error reading story file {story_file.name}: {e}")

    logger.info(f"Read {len(stories)} stories from {stories_dir}")
    return stories


def ingest_stories(stories: List[Story]) -> List[Story]:
    """
    Ingest stories into the Supabase database.

    Args:
        stories: List of Story instances

    Returns:
        List of inserted Story instances
    """
    inserted_stories = []

    for story in stories:
        try:
            # Check if story already exists (by filename)
            existing_stories = supabase_client.get_stories()
            existing_filenames = [s.filename for s in existing_stories]

            if story.filename in existing_filenames:
                logger.info(f"Story already exists, skipping: {story.filename}")
                # Find the existing story and add to our list
                existing_story = next(s for s in existing_stories if s.filename == story.filename)
                inserted_stories.append(existing_story)
                continue

            # Insert the Story instance
            inserted_story = supabase_client.insert_story(story)
            inserted_stories.append(inserted_story)
            logger.info(f"Inserted story: {story.filename}")

        except Exception as e:
            logger.error(f"Error inserting story {story.filename}: {e}")

    logger.info(f"Ingested {len(inserted_stories)} stories into database")
    return inserted_stories


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


def generate_personality_profile(analyses: List[StoryAnalysis]) -> PersonalityProfile:
    """
    Generate personality profile from story analyses.

    Args:
        analyses: List of StoryAnalysis instances

    Returns:
        PersonalityProfile instance
    """
    logger.info("Generating personality profile...")

    try:
        # Check if profile already exists
        existing_profile = supabase_client.get_personality_profile()

        if existing_profile and len(analyses) <= existing_profile.source_analyses_count:
            logger.info("Personality profile already up to date")
            return existing_profile

        # Generate new or updated profile
        profile_result = personality_profiler.create_profile_from_stories()

        if profile_result["status"] == "success":
            logger.info("Successfully generated personality profile")
            # The profile_result["profile"] should be a PersonalityProfile instance
            # but create_profile_from_stories returns a dict, so we need to handle this
            profile_data = profile_result["profile"]
            if isinstance(profile_data, PersonalityProfile):
                return profile_data
            else:
                # Convert dict to PersonalityProfile if needed
                return PersonalityProfile.from_dict(profile_data)
        else:
            logger.warning(f"Profile generation status: {profile_result['status']}")
            # Return a default empty profile
            return PersonalityProfile()

    except Exception as e:
        logger.error(f"Error generating personality profile: {e}")
        raise


def main():
    """Main setup function."""
    logger.info("Starting Narrative Digital Twin setup...")
    try:
        # Validate configuration
        settings.validate()
        logger.info("Configuration validated successfully")

        # Step 1: Read story files
        logger.info("Step 1: Reading story files...")
        stories = read_story_files()
        
        if not stories:
            logger.error("No stories found. Please add .txt files to the data/stories directory.")
            return False
        
        # Step 2: Ingest stories into database
        logger.info("Step 2: Ingesting stories into database...")
        inserted_stories = ingest_stories(stories)
        
        # Step 3: Run story analysis
        logger.info("Step 3: Running story analysis...")
        analyses = run_story_analysis(inserted_stories)
        
        # Step 4: Generate personality profile
        logger.info("Step 4: Generating personality profile...")
        profile = generate_personality_profile(analyses)
        
        # Summary
        logger.info("Setup completed successfully!")
        logger.info(f"- Stories processed: {len(inserted_stories)}")
        logger.info(f"- Analyses created: {len(analyses)}")
        logger.info(f"- Personality profile: {'Created' if profile and profile.profile else 'Failed'}")

        print("\n" + "="*50)
        print("SETUP COMPLETE!")
        print("="*50)
        print(f"✓ Processed {len(inserted_stories)} stories")
        print(f"✓ Generated {len(analyses)} analyses")
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
