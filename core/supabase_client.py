"""
Supabase client for managing all database operations.
Handles connection and CRUD operations with the Supabase database.
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone
from supabase import create_client, Client
from config.settings import settings
from core.models import (
    Bot, Story, StoryAnalysis, PersonalityProfile, ConversationMessage, LLMMessage, ConversationState,
    StoryWithAnalysis, stories_from_dict_list, story_analyses_from_dict_list,
    conversation_messages_from_dict_list, conversation_messages_to_llm_format,
    bots_from_dict_list
)

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Client class for handling all Supabase database operations."""
    
    def __init__(self):
        """Initialize the Supabase client."""
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise ValueError("Supabase URL and key must be provided in environment variables")
        
        self.client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    # Bot operations
    def get_bots(self, active_only: bool = True) -> List[Bot]:
        """
        Retrieve all bots from the database.

        Args:
            active_only: If True, only return active bots

        Returns:
            List of Bot instances
        """
        try:
            query = self.client.table("bots").select("*")
            if active_only:
                query = query.eq("is_active", True)

            result = query.execute()
            return bots_from_dict_list(result.data)
        except Exception as e:
            logger.error(f"Error retrieving bots: {e}")
            raise

    def get_bot_by_id(self, bot_id: str) -> Optional[Bot]:
        """
        Retrieve a bot by its ID.

        Args:
            bot_id: The bot ID

        Returns:
            Bot instance or None if not found
        """
        try:
            result = self.client.table("bots").select("*").eq("id", bot_id).execute()
            if result.data:
                return Bot.from_dict(result.data[0])
            return None
        except Exception as e:
            logger.error(f"Error retrieving bot by ID: {e}")
            raise

    def get_bot_by_name(self, name: str) -> Optional[Bot]:
        """
        Retrieve a bot by its name.

        Args:
            name: The bot name

        Returns:
            Bot instance or None if not found
        """
        try:
            result = self.client.table("bots").select("*").eq("name", name).execute()
            if result.data:
                return Bot.from_dict(result.data[0])
            return None
        except Exception as e:
            logger.error(f"Error retrieving bot by name: {e}")
            raise

    def insert_bot(self, bot: Bot) -> Bot:
        """
        Insert a new bot.

        Args:
            bot: Bot instance to insert

        Returns:
            The inserted Bot instance
        """
        try:
            bot_dict = bot.to_dict()
            # Remove None values for insert
            bot_dict = {k: v for k, v in bot_dict.items() if v is not None}

            result = self.client.table("bots").insert(bot_dict).execute()
            if result.data:
                return Bot.from_dict(result.data[0])
            else:
                return bot
        except Exception as e:
            logger.error(f"Error inserting bot: {e}")
            raise

    def update_bot(self, bot: Bot) -> Bot:
        """
        Update an existing bot.

        Args:
            bot: Bot instance to update

        Returns:
            The updated Bot instance
        """
        try:
            bot_dict = bot.to_dict()
            bot_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
            # Remove None values for update
            bot_dict = {k: v for k, v in bot_dict.items() if v is not None}

            result = self.client.table("bots").update(bot_dict).eq("id", str(bot.id)).execute()
            if result.data:
                return Bot.from_dict(result.data[0])
            else:
                return bot
        except Exception as e:
            logger.error(f"Error updating bot: {e}")
            raise

    # Stories table operations
    def get_stories(self, bot_id: Optional[str] = None, limit: Optional[int] = None) -> List[Story]:
        """
        Retrieve stories from the database.

        Args:
            bot_id: Optional bot ID to filter stories
            limit: Optional limit on number of stories to retrieve

        Returns:
            List of Story instances
        """
        try:
            query = self.client.table("stories").select("*")
            if bot_id:
                query = query.eq("bot_id", bot_id)
            if limit:
                query = query.limit(limit)

            result = query.execute()
            return stories_from_dict_list(result.data)
        except Exception as e:
            logger.error(f"Error retrieving stories: {e}")
            raise

    def insert_story(self, story: Story) -> Story:
        """
        Insert a new story.

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

    def get_stories_with_analysis(self, bot_id: Optional[str] = None) -> List[StoryWithAnalysis]:
        """
        Retrieve stories with their analysis data.

        Args:
            bot_id: Optional bot ID to filter stories

        Returns:
            List of StoryWithAnalysis instances
        """
        try:
            # Build the JOIN query to get stories with their analysis
            query = self.client.table("stories").select("""
                id,
                bot_id,
                title,
                content,
                created_at,
                updated_at,
                story_analysis!inner(
                    id,
                    triggers,
                    emotions,
                    thoughts,
                    values,
                    created_at
                )
            """)

            if bot_id:
                query = query.eq("bot_id", bot_id)

            result = query.execute()

            # Transform the nested result into StoryWithAnalysis objects
            stories_with_analysis = []
            for row in result.data:
                # Extract story data
                story_data = {
                    'id': row['id'],
                    'bot_id': row['bot_id'],
                    'title': row['title'],
                    'content': row['content'],
                    'story_created_at': row['created_at'],
                    'story_updated_at': row['updated_at']
                }

                # Extract analysis data (should be a single item due to inner join)
                if row['story_analysis'] and len(row['story_analysis']) > 0:
                    analysis = row['story_analysis'][0]  # Take first analysis
                    story_data.update({
                        'analysis_id': analysis['id'],
                        'triggers': analysis['triggers'],
                        'emotions': analysis['emotions'],
                        'thoughts': analysis['thoughts'],
                        'values': analysis['values'],
                        'analysis_created_at': analysis['created_at']
                    })

                stories_with_analysis.append(StoryWithAnalysis.from_dict(story_data))

            logger.info(f"Retrieved {len(stories_with_analysis)} stories with analysis")
            return stories_with_analysis

        except Exception as e:
            logger.error(f"Error retrieving stories with analysis: {e}")
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

    def get_personality_profile(self, bot_id: str) -> Optional[PersonalityProfile]:
        """
        Retrieve personality profile for a bot.

        Args:
            bot_id: The bot ID

        Returns:
            The PersonalityProfile instance or None if not found
        """
        try:
            result = self.client.table("personality_profiles").select("*").eq("bot_id", bot_id).execute()
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
        chat_id: str,
        limit: int = 50
    ) -> List[ConversationMessage]:
        """
        Retrieve conversation history for a chat.

        Args:
            chat_id: The chat ID (format: bot_id_user_id)
            limit: Maximum number of messages to retrieve

        Returns:
            List of ConversationMessage instances
        """
        try:
            result = (
                self.client.table("conversation_history")
                .select("*")
                .eq("chat_id", chat_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            messages = conversation_messages_from_dict_list(result.data)
            return list(reversed(messages))  # Return in chronological order
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            raise

    def get_conversation_history_for_llm(
        self,
        chat_id: str,
        limit: int = 10
    ) -> List[LLMMessage]:
        """
        Retrieve conversation history formatted for LLM service.

        Args:
            chat_id: The chat ID (format: bot_id_user_id)
            limit: Maximum number of messages to retrieve

        Returns:
            List of message dictionaries in LLM format
        """
        try:
            query = (
                self.client.table("conversation_history")
                .select("*")
                .eq("chat_id", chat_id)
                .order("created_at", desc=True)
                .limit(limit)
            )

            result = query.execute()
            messages = conversation_messages_from_dict_list(result.data)
            messages = list(reversed(messages))  # Return in chronological order

            return conversation_messages_to_llm_format(messages)
        except Exception as e:
            logger.error(f"Error retrieving conversation history for LLM: {e}")
            raise

    # Conversation state operations
    def get_conversation_state(self, chat_id: str) -> Optional[ConversationState]:
        """
        Retrieve conversation state for a chat.

        Args:
            chat_id: The chat ID (format: bot_id_user_id)

        Returns:
            ConversationState instance or None if not found
        """
        try:
            result = (
                self.client.table("conversation_state")
                .select("*")
                .eq("chat_id", chat_id)
                .execute()
            )

            if result.data:
                return ConversationState.from_dict(result.data[0])
            return None
        except Exception as e:
            logger.error(f"Error retrieving conversation state: {e}")
            raise

    def insert_conversation_state(self, state: ConversationState) -> ConversationState:
        """
        Insert or update conversation state.

        Args:
            state: ConversationState instance to insert/update

        Returns:
            The inserted/updated ConversationState instance
        """
        try:
            state_dict = state.to_dict()
            # Remove None values for insert
            state_dict = {k: v for k, v in state_dict.items() if v is not None}

            result = self.client.table("conversation_state").upsert(state_dict).execute()
            if result.data:
                return ConversationState.from_dict(result.data[0])
            else:
                return state
        except Exception as e:
            logger.error(f"Error inserting conversation state: {e}")
            raise

    def update_conversation_state(
        self,
        chat_id: str,
        summary: Optional[str] = None,
        call_to_action_shown: Optional[bool] = None
    ) -> Optional[ConversationState]:
        """
        Update specific fields of conversation state.

        Args:
            chat_id: The chat ID (format: bot_id_user_id)
            summary: Updated summary text
            call_to_action_shown: Whether call to action has been shown

        Returns:
            The updated ConversationState instance or None if not found
        """
        try:
            # Build update dictionary with only provided fields
            update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}

            if summary is not None:
                update_data["summary"] = summary
            if call_to_action_shown is not None:
                update_data["call_to_action_shown"] = str(call_to_action_shown).lower()

            result = (
                self.client.table("conversation_state")
                .update(update_data)
                .eq("chat_id", chat_id)
                .execute()
            )

            if result.data:
                return ConversationState.from_dict(result.data[0])
            return None
        except Exception as e:
            logger.error(f"Error updating conversation state: {e}")
            raise

    def reset_conversation(self, chat_id: str) -> bool:
        """
        Reset the conversation state for a chat.

        Args:
            chat_id: Chat identifier (format: bot_id_user_id)

        Returns:
            True if reset was successful
        """
        try:
            # Delete conversation state
            self.client.table("conversation_state").delete().eq("chat_id", chat_id).execute()

            # Delete conversation history
            self.client.table("conversation_history").delete().eq("chat_id", chat_id).execute()

            return True
        except Exception as e:
            logger.error(f"Error resetting conversation: {e}")
            return False

# Global Supabase client instance
supabase_client = SupabaseClient()
