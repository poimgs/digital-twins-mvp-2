"""
Supabase client for managing all database operations.
Handles connection and CRUD operations with the Supabase database.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from supabase import create_client, Client
from config.settings import settings
from core.models import (
    Bot, Story, StoryAnalysis, PersonalityProfile, ConversationMessage, LLMMessage, ConversationState,
    StoryWithAnalysis, TokenUsage, InitialQuestion,
    stories_from_dict_list, story_analyses_from_dict_list,
    initial_questions_from_dict_list, conversation_messages_from_dict_list, conversation_messages_to_llm_format,
    bots_from_dict_list, token_usage_from_dict_list
)

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Client class for handling all Supabase database operations."""
    
    def __init__(self):
        """Initialize the Supabase client."""
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise ValueError("Supabase URL and key must be provided in environment variables")
        
        self.client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

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

    def get_all_bots(self) -> List[Bot]:
        """
        Retrieve all bots from the database.

        Returns:
            List of Bot instances
        """
        try:
            result = self.client.table("bots").select("*").order("created_at", desc=True).execute()
            return bots_from_dict_list(result.data)
        except Exception as e:
            logger.error(f"Error retrieving all bots: {e}")
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
    def get_stories(self, bot_id: Optional[str] = None, category_type: Optional[str] = None, limit: Optional[int] = None) -> List[Story]:
        """
        Retrieve stories from the database.

        Args:
            bot_id: Optional bot ID to filter stories
            category_type: Optional category type to filter stories
            limit: Optional limit on number of stories to retrieve

        Returns:
            List of Story instances
        """
        try:
            query = self.client.table("stories").select("*")
            if bot_id:
                query = query.eq("bot_id", bot_id)
            if category_type:
                query = query.eq("category_type", category_type)
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

    def get_stories_with_analysis(self, bot_id: Optional[str] = None, category_type: Optional[str] = None) -> List[StoryWithAnalysis]:
        """
        Retrieve stories with their analysis data (analysis is optional).

        Args:
            bot_id: Optional bot ID to filter stories
            category_type: Optional category type to filter stories

        Returns:
            List of StoryWithAnalysis instances
        """
        try:
            # Build the LEFT JOIN query to get stories with optional analysis
            query = self.client.table("stories").select("""
                id,
                bot_id,
                category_type,
                title,
                content,
                created_at,
                updated_at,
                story_analysis(
                    id,
                    summary,
                    triggers,
                    emotions,
                    thoughts,
                    values,
                    created_at
                )
            """)

            if bot_id:
                query = query.eq("bot_id", bot_id)
            if category_type:
                query = query.eq("category_type", category_type)

            result = query.execute()

            # Transform the nested result into StoryWithAnalysis objects
            stories_with_analysis = []
            for row in result.data:
                # Extract story data
                story_data = {
                    'id': row['id'],
                    'bot_id': row['bot_id'],
                    'category_type': row.get('category_type', 'stories'),
                    'title': row['title'],
                    'content': row['content'],
                    'story_created_at': row['created_at'],
                    'story_updated_at': row['updated_at']
                }

                # Extract analysis data (optional - may be None or empty)
                analysis_data = row.get('story_analysis')
                if analysis_data and len(analysis_data) > 0:
                    analysis = analysis_data[0]  # Take first analysis
                    story_data.update({
                        'analysis_id': analysis['id'],
                        'summary': analysis['summary'],
                        'triggers': analysis['triggers'],
                        'emotions': analysis['emotions'],
                        'thoughts': analysis['thoughts'],
                        'values': analysis['values'],
                        'analysis_created_at': analysis['created_at']
                    })
                else:
                    # No analysis data - use defaults
                    story_data.update({
                        'analysis_id': None,
                        'summary': '',
                        'triggers': [],
                        'emotions': [],
                        'thoughts': [],
                        'values': [],
                        'analysis_created_at': None
                    })

                stories_with_analysis.append(StoryWithAnalysis.from_dict(story_data))

            logger.info(f"Retrieved {len(stories_with_analysis)} stories with optional analysis")
            return stories_with_analysis

        except Exception as e:
            logger.error(f"Error retrieving stories with analysis: {e}")
            raise

    def get_distinct_category_types(self, bot_id: Optional[str] = None) -> List[str]:
        """
        Retrieve distinct category types from stories table.
        Shows all categories that have actual content.

        Args:
            bot_id: Optional bot ID to filter stories

        Returns:
            List of distinct category type strings
        """
        try:
            query = self.client.table("stories").select("category_type")
            if bot_id:
                query = query.eq("bot_id", bot_id)

            result = query.execute()
            
            # Extract unique category types
            category_types = set()
            for row in result.data:
                if row.get("category_type"):
                    category_types.add(row["category_type"])
            
            return sorted(list(category_types)) if category_types else ["stories"]
        except Exception as e:
            logger.error(f"Error retrieving distinct category types: {e}")
            # Return fallback categories if database query fails
            return ["stories"]

    # Initial questions table operations
    def insert_initial_question(self, initial_question: InitialQuestion) -> InitialQuestion:
        """
        Insert an initial question into the database.

        Args:
            initial_question: InitialQuestion instance to insert

        Returns:
            The inserted InitialQuestion instance
        """
        try:
            question_dict = initial_question.to_dict()
            # Remove None values for insert
            question_dict = {k: v for k, v in question_dict.items() if v is not None}

            result = self.client.table("initial_questions").insert(question_dict).execute()
            if result.data:
                return InitialQuestion.from_dict(result.data[0])
            else:
                return initial_question
        except Exception as e:
            logger.error(f"Error inserting initial question: {e}")
            raise

    def get_initial_questions(self, bot_id: Optional[str] = None, category_type: Optional[str] = None) -> List[InitialQuestion]:
        """
        Retrieve initial questions from the database.

        Args:
            bot_id: Optional bot ID to filter initial questions
            category_type: Optional category type to filter initial questions

        Returns:
            List of InitialQuestion instances
        """
        try:
            query = self.client.table("initial_questions").select("*")
            if bot_id:
                query = query.eq("bot_id", bot_id)
            if category_type:
                query = query.eq("category_type", category_type)

            result = query.execute()
            return initial_questions_from_dict_list(result.data)
        except Exception as e:
            logger.error(f"Error retrieving initial questions: {e}")
            raise

    def get_initial_questions_by_bot(self, bot_id: str) -> Dict[str, List[InitialQuestion]]:
        """
        Retrieve initial questions grouped by category type for a specific bot.

        Args:
            bot_id: The bot ID

        Returns:
            Dictionary mapping category types to lists of initial questions
        """
        try:
            questions = self.get_initial_questions(bot_id=bot_id)
            grouped_questions = {}

            for question in questions:
                if question.category_type not in grouped_questions:
                    grouped_questions[question.category_type] = []
                grouped_questions[question.category_type].append(question)

            return grouped_questions
        except Exception as e:
            logger.error(f"Error retrieving grouped initial questions: {e}")
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
        limit: int = 50,
        conversation_number: Optional[int] = None
    ) -> List[ConversationMessage]:
        """
        Retrieve conversation history for a chat.

        Args:
            chat_id: The chat ID (format: bot_id_user_id)
            limit: Maximum number of messages to retrieve
            conversation_number: Specific conversation number (defaults to current/latest)

        Returns:
            List of ConversationMessage instances
        """
        try:
            if conversation_number is None:
                conversation_number = self.get_current_conversation_number(chat_id)

            result = (
                self.client.table("conversation_history")
                .select("*")
                .eq("chat_id", chat_id)
                .eq("conversation_number", conversation_number)
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
        limit: int = 10,
        conversation_number: Optional[int] = None
    ) -> List[LLMMessage]:
        """
        Retrieve conversation history formatted for LLM service.

        Args:
            chat_id: The chat ID (format: bot_id_user_id)
            limit: Maximum number of messages to retrieve
            conversation_number: Specific conversation number (defaults to current/latest)

        Returns:
            List of message dictionaries in LLM format
        """
        try:
            if conversation_number is None:
                conversation_number = self.get_current_conversation_number(chat_id)

            query = (
                self.client.table("conversation_history")
                .select("*")
                .eq("chat_id", chat_id)
                .eq("conversation_number", conversation_number)
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

    def get_user_message_count(
        self,
        chat_id: str,
        conversation_number: Optional[int] = None
    ) -> int:
        """
        Get the count of user messages in the current conversation.

        Args:
            chat_id: The chat ID (format: bot_id_user_id)
            conversation_number: Specific conversation number (defaults to current/latest)

        Returns:
            Number of user messages in the conversation
        """
        try:
            if conversation_number is None:
                conversation_number = self.get_current_conversation_number(chat_id)

            result = (
                self.client.table("conversation_history")
                .select("*")
                .eq("chat_id", chat_id)
                .eq("conversation_number", conversation_number)
                .eq("role", "user")
                .execute()
            )

            return len(result.data) if result.data else 0
        except Exception as e:
            logger.error(f"Error getting user message count: {e}")
            return 0

    # Conversation state operations
    def get_current_conversation_number(self, chat_id: str) -> int:
        """
        Get the current conversation number for a chat.

        Args:
            chat_id: The chat ID (format: bot_id_user_id)

        Returns:
            Current conversation number (defaults to 1 if no conversations exist)
        """
        try:
            result = (
                self.client.table("conversation_state")
                .select("conversation_number")
                .eq("chat_id", chat_id)
                .order("conversation_number", desc=True)
                .limit(1)
                .execute()
            )

            if result.data:
                return result.data[0]['conversation_number']
            return 1
        except Exception as e:
            logger.error(f"Error retrieving current conversation number: {e}")
            return 1

    def get_conversation_state(self, chat_id: str, conversation_number: Optional[int] = None) -> Optional[ConversationState]:
        """
        Retrieve conversation state for a chat.

        Args:
            chat_id: The chat ID (format: bot_id_user_id)
            conversation_number: Specific conversation number (defaults to current/latest)

        Returns:
            ConversationState instance or None if not found
        """
        try:
            if conversation_number is None:
                conversation_number = self.get_current_conversation_number(chat_id)

            result = (
                self.client.table("conversation_state")
                .select("*")
                .eq("chat_id", chat_id)
                .eq("conversation_number", conversation_number)
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
        current_warmth_level: Optional[int] = None,
        max_warmth_achieved: Optional[int] = None,
        follow_up_questions: Optional[List[str]] = None,
        conversation_number: Optional[int] = None
    ) -> Optional[ConversationState]:
        """
        Update specific fields of conversation state.

        Args:
            chat_id: The chat ID (format: bot_id_user_id)
            summary: Updated summary text
            current_warmth_level: Current warmth level (1-6)
            max_warmth_achieved: Maximum warmth level achieved (1-6)
            follow_up_questions: List of follow-up questions
            conversation_number: Specific conversation number (defaults to current/latest)

        Returns:
            The updated ConversationState instance or None if not found
        """
        try:
            if conversation_number is None:
                conversation_number = self.get_current_conversation_number(chat_id)

            # Build update dictionary with only provided fields
            update_data: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}

            if summary is not None:
                update_data["summary"] = summary
            if current_warmth_level is not None:
                update_data["current_warmth_level"] = str(current_warmth_level)
            if max_warmth_achieved is not None:
                update_data["max_warmth_achieved"] = str(max_warmth_achieved)
            if follow_up_questions is not None:
                update_data["follow_up_questions"] = follow_up_questions

            result = (
                self.client.table("conversation_state")
                .update(update_data)
                .eq("chat_id", chat_id)
                .eq("conversation_number", conversation_number)
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
        Reset the conversation state for a chat by incrementing conversation number.
        This preserves conversation history for analytics while starting fresh.

        Args:
            chat_id: Chat identifier (format: bot_id_user_id)

        Returns:
            True if reset was successful
        """
        try:
            # Get current conversation number and increment it
            current_number = self.get_current_conversation_number(chat_id)
            new_conversation_number = current_number + 1

            logger.info(f"Reset conversation {chat_id}: incrementing from conversation {current_number} to {new_conversation_number}")

            # The conversation manager will create new state for the new conversation number
            # when it's next accessed, so we don't need to create it here
            return True
        except Exception as e:
            logger.error(f"Error resetting conversation: {e}")
            return False

    def create_token_usage(self, token_usage: TokenUsage) -> bool:
        """
        Create a new token usage record.

        Args:
            token_usage: TokenUsage instance to create

        Returns:
            True if creation was successful
        """
        try:
            data = token_usage.to_dict()
            data["created_at"] = datetime.now(timezone.utc).isoformat()
            result = self.client.table("token_usage").insert(data).execute()
            logger.debug(f"Created token usage record: {result.data}")
            return True
        except Exception as e:
            logger.error(f"Error creating token usage record: {e}")
            return False

# Global Supabase client instance
supabase_client = SupabaseClient()
