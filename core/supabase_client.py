"""
Supabase client for managing all database operations.
Handles connection and CRUD operations with the Supabase database.
"""

import logging
from typing import List, Optional
from supabase import create_client, Client
from config.settings import settings
from core.models import (
    Story, StoryAnalysis, PersonalityProfile, ConversationMessage,
    stories_from_dict_list, story_analyses_from_dict_list,
    conversation_messages_from_dict_list
)

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Client class for handling all Supabase database operations."""
    
    def __init__(self):
        """Initialize the Supabase client."""
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise ValueError("Supabase URL and key must be provided in environment variables")
        
        self.client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    
    # Stories table operations
    def insert_story(self, story: Story) -> Story:
        """
        Insert a new story into the stories table.

        Args:
            story: Story instance to insert

        Returns:
            The inserted Story instance
        """
        try:
            story_dict = story.to_dict()
            # Remove None values for insert
            story_dict = {k: v for k, v in story_dict.items() if v is not None}

            result = self.client.table("stories").insert(story_dict).execute()
            if result.data:
                return Story.from_dict(result.data[0])
            else:
                return story
        except Exception as e:
            logger.error(f"Error inserting story: {e}")
            raise

    def get_stories(self, limit: Optional[int] = None) -> List[Story]:
        """
        Retrieve all stories from the database.

        Args:
            limit: Optional limit on number of stories to retrieve

        Returns:
            List of Story instances
        """
        try:
            query = self.client.table("stories").select("*")
            if limit:
                query = query.limit(limit)

            result = query.execute()
            return stories_from_dict_list(result.data)
        except Exception as e:
            logger.error(f"Error retrieving stories: {e}")
            raise

    def get_story_by_id(self, story_id: str) -> Optional[Story]:
        """
        Retrieve a specific story by ID.

        Args:
            story_id: The ID of the story to retrieve

        Returns:
            The Story instance or None if not found
        """
        try:
            result = self.client.table("stories").select("*").eq("id", story_id).execute()
            if result.data:
                return Story.from_dict(result.data[0])
            return None
        except Exception as e:
            logger.error(f"Error retrieving story {story_id}: {e}")
            raise
    
    # Story analysis table operations
    def insert_story_analysis(self, analysis: StoryAnalysis) -> StoryAnalysis:
        """
        Insert story analysis data.

        Args:
            analysis: StoryAnalysis instance to insert

        Returns:
            The inserted StoryAnalysis instance
        """
        try:
            analysis_dict = analysis.to_dict()
            # Remove None values for insert
            analysis_dict = {k: v for k, v in analysis_dict.items() if v is not None}

            result = self.client.table("story_analysis").insert(analysis_dict).execute()
            if result.data:
                return StoryAnalysis.from_dict(result.data[0])
            else:
                return analysis
        except Exception as e:
            logger.error(f"Error inserting story analysis: {e}")
            raise

    def get_story_analyses(self) -> List[StoryAnalysis]:
        """
        Retrieve all story analyses.

        Returns:
            List of StoryAnalysis instances
        """
        try:
            result = self.client.table("story_analysis").select("*").execute()
            return story_analyses_from_dict_list(result.data)
        except Exception as e:
            logger.error(f"Error retrieving story analyses: {e}")
            raise
    
    # Personality profiles table operations
    def insert_personality_profile(self, profile: PersonalityProfile) -> PersonalityProfile:
        """
        Insert or update personality profile.

        Args:
            profile: PersonalityProfile instance to insert/update

        Returns:
            The inserted/updated PersonalityProfile instance
        """
        try:
            profile_dict = profile.to_dict()
            # Remove None values for insert
            profile_dict = {k: v for k, v in profile_dict.items() if v is not None}

            result = self.client.table("personality_profiles").upsert(profile_dict).execute()
            if result.data:
                return PersonalityProfile.from_dict(result.data[0])
            else:
                return profile
        except Exception as e:
            logger.error(f"Error inserting personality profile: {e}")
            raise

    def get_personality_profile(self, user_id: str = "default") -> Optional[PersonalityProfile]:
        """
        Retrieve personality profile for a user.

        Args:
            user_id: The user ID (defaults to "default" for MVP)

        Returns:
            The PersonalityProfile instance or None if not found
        """
        try:
            result = self.client.table("personality_profiles").select("*").eq("user_id", user_id).execute()
            if result.data:
                return PersonalityProfile.from_dict(result.data[0])
            return None
        except Exception as e:
            logger.error(f"Error retrieving personality profile: {e}")
            raise
    
    # Conversation history operations
    def insert_conversation_message(self, message: ConversationMessage) -> ConversationMessage:
        """
        Insert a conversation message.

        Args:
            message: ConversationMessage instance to insert

        Returns:
            The inserted ConversationMessage instance
        """
        try:
            message_dict = message.to_dict()
            # Remove None values for insert
            message_dict = {k: v for k, v in message_dict.items() if v is not None}

            result = self.client.table("conversation_history").insert(message_dict).execute()
            if result.data:
                return ConversationMessage.from_dict(result.data[0])
            else:
                return message
        except Exception as e:
            logger.error(f"Error inserting conversation message: {e}")
            raise

    def get_conversation_history(
        self,
        user_id: str = "default",
        limit: int = 50
    ) -> List[ConversationMessage]:
        """
        Retrieve conversation history for a user.

        Args:
            user_id: The user ID
            limit: Maximum number of messages to retrieve

        Returns:
            List of ConversationMessage instances
        """
        try:
            result = (
                self.client.table("conversation_history")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            messages = conversation_messages_from_dict_list(result.data)
            return list(reversed(messages))  # Return in chronological order
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            raise

    # Backward compatibility methods for existing code that expects dictionaries
    def insert_story_dict(self, story_data: dict) -> dict:
        """Backward compatibility method for inserting story from dictionary."""
        story = Story.from_dict(story_data)
        result = self.insert_story(story)
        return result.to_dict()

    def insert_story_analysis_dict(self, analysis_data: dict) -> dict:
        """Backward compatibility method for inserting analysis from dictionary."""
        analysis = StoryAnalysis.from_dict(analysis_data)
        result = self.insert_story_analysis(analysis)
        return result.to_dict()

    def insert_personality_profile_dict(self, profile_data: dict) -> dict:
        """Backward compatibility method for inserting profile from dictionary."""
        profile = PersonalityProfile.from_dict(profile_data)
        result = self.insert_personality_profile(profile)
        return result.to_dict()

    def insert_conversation_message_dict(self, message_data: dict) -> dict:
        """Backward compatibility method for inserting message from dictionary."""
        message = ConversationMessage.from_dict(message_data)
        result = self.insert_conversation_message(message)
        return result.to_dict()


# Global Supabase client instance
supabase_client = SupabaseClient()
