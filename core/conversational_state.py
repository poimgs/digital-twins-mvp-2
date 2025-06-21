import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from core.llm_service import llm_service
from core.supabase_client import supabase_client
from core.utils import load_prompts
from core.models import PersonalityProfile, ConversationMessage, UserInputAnalysis, LLMMessage

logger = logging.getLogger(__name__)

class ConversationalState:
    """
    Enhanced conversational state management with dynamic context tracking.

    Implements a conversation-focused state that serves as the digital twin's
    short-term memory for a single user session.
    """

    def __init__(self, user_id: str = "default"):
        """Initialize conversational state for a user."""
        self.user_id = user_id
        # TODO: Load from database
        self.summary = ""
        self.context = {
            "triggers" : [],
            "emotions": [],
            "thoughts": [],
            "values": []
        }

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

            # TODO: Generate updated summary using schema. For now, storing string will suffice
            return llm_service.generate_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )

        except Exception as e:
            logger.error(f"Error summarizing conversation: {e}")
            return ""
        
    def update_context(self, user_message: str):
        """
        Update the conversation context based on user input and LLM response.

        Args:
            user_message: The user's message
        """
        try:
            system_prompt = """You are an expert conversation context manager. Given the previous conversation context and new user message , update the context to include:
            1. Updated triggers based on recent context
            2. Updated emotions based on recent context
            3. Updated thoughts based on recent context
            4. Updated values based on recent context        

            Consider conversation history and maintain contextual relevance."""

            user_prompt = f"""Previous context: {self.context}

            New user message: {user_message}"""

            # TODO: Generate updated context using schema. For now, storing string will suffice
            return llm_service.generate_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )

        except Exception as e:
            logger.error(f"Error updating conversation context: {e}")
            return {}

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

    def add_assistant_message(self, content: str, used_stories: Optional[List[str]] = None):
        """
        Add an assistant message and update story usage tracking.

        Args:
            content: The assistant's response content
            used_stories: List of story IDs that were used in the response
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