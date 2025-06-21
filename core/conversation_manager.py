import logging
from typing import List, Optional
from datetime import datetime, timezone
from core.llm_service import llm_service
from core.supabase_client import supabase_client
from core.models import ConversationMessage, LLMMessage, ConversationState, StoryWithAnalysis
from core.story_retrieval_manager import StoryRetrievalManager

logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Enhanced conversational state management with dynamic context tracking.

    Implements a conversation-focused state that serves as the digital twin's
    short-term memory for a single user session.
    """

    def __init__(self, user_id: str = "default"):
        """Initialize conversational state for a user."""
        self.user_id = user_id
        self.story_retrieval_manager = StoryRetrievalManager()

        # Load from database or initialize with defaults
        try:
            state = supabase_client.get_conversation_state(user_id)
            if state:
                self.summary = state.summary
            else:
                # Initialize with defaults and create in database
                self.summary = ""

                # Create initial state in database
                initial_state = ConversationState(
                    user_id=user_id,
                    summary=self.summary,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                supabase_client.insert_conversation_state(initial_state)
        except Exception as e:
            logger.error(f"Error loading conversation state from database: {e}")
            # Fall back to defaults
            self.summary = ""

    def summarize_conversation(self, user_message: str, llm_response: str) -> str:
        """
        Summarize the conversation based on user input and LLM response.

        Args:
            user_message: The user's message
            llm_response: The LLM's response

        Returns:
            Updated summary
        """
        try:
            system_prompt = """You are an expert conversation summarizer. Given the previous conversation summary and new user message and LLM response, update the summary to include:
1. Updated main topics/themes based on recent context
2. Key concepts that remain relevant
3. Evolution of user's intentions throughout conversation

Consider conversation history and maintain contextual relevance."""

            user_prompt = f"""Previous summary: {self.summary}

New user message: {user_message}
LLM response: {llm_response}"""

            # Generate updated summary
            updated_summary = llm_service.generate_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )

            # Update local state
            self.summary = updated_summary

            # Persist to database
            try:
                supabase_client.update_conversation_state(
                    user_id=self.user_id,
                    summary=updated_summary
                )
            except Exception as db_error:
                logger.error(f"Error persisting summary to database: {db_error}")

            return updated_summary

        except Exception as e:
            logger.error(f"Error summarizing conversation: {e}")
            return self.summary

    def add_user_message(self, content: str):
        """
        Add a user message and update conversational state.

        Args:
            content: The user's message content
        """
        # Store message
        message = ConversationMessage(
            user_id=self.user_id,
            role="user",
            content=content,
            created_at=datetime.now(timezone.utc)
        )

        try:
            supabase_client.insert_conversation_message(message)
        except Exception as e:
            logger.error(f"Error storing user message: {e}")

    def add_assistant_message(self, content: str):
        """
        Add an assistant message and update story usage tracking.

        Args:
            content: The assistant's response content
        """
        message = ConversationMessage(
            user_id=self.user_id,
            role="assistant",
            content=content,
            created_at=datetime.now(timezone.utc)
        )

        try:
            supabase_client.insert_conversation_message(message)
        except Exception as e:
            logger.error(f"Error storing assistant message: {e}")

    def get_conversation_history_for_llm(
        self,
        max_messages: int = 10
    ) -> List[LLMMessage]:
        """
        Get conversation history formatted for LLM service with truncation.

        Args:
            max_messages: Maximum number of messages to retrieve

        Returns:
            List of message dictionaries in LLM format
        """
        try:
            # Get conversation history from database
            return supabase_client.get_conversation_history_for_llm(
                user_id=self.user_id,
                limit=max_messages
            )

        except Exception as e:
            logger.error(f"Error getting conversation history for LLM: {e}")
            return []
    
    def find_relevant_story(self, stories: List[StoryWithAnalysis]) -> Optional[StoryWithAnalysis]:
        """
        Find the most relevant stories using enhanced multi-stage filtering and ranking.

        Args:
            user_message: The user's message
            summary: Conversation summary
            user_id: User identifier
            limit: Maximum number of stories to return

        Returns:
            List of relevant stories with comprehensive scoring details
        """
        try:
            return self.story_retrieval_manager.find_relevant_story(
                stories=stories,
                conversation_summary=self.summary
            )

        except Exception as e:
            logger.error(f"Error finding relevant stories: {e}")
            return None
        
    def reset_conversation(self):
        """
        Reset the conversation state for a user.

        Args:
            user_id: User identifier

        Returns:
            True if reset was successful
        """
        try:
            supabase_client.reset_conversation(self.user_id)
            return True
        except Exception as e:
            logger.error(f"Error resetting conversation: {e}")
            return False
