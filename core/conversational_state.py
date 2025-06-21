import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from core.llm_service import llm_service
from core.supabase_client import supabase_client
from core.utils import load_prompts
from core.models import PersonalityProfile, ConversationMessage, UserInputAnalysis, LLMMessage, ConversationState

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

        # Load from database or initialize with defaults
        try:
            state = supabase_client.get_conversation_state(user_id)
            if state:
                self.summary = state.summary
                self.triggers = state.triggers
                self.emotions = state.emotions
                self.thoughts = state.thoughts
                self.values = state.values
            else:
                # Initialize with defaults and create in database
                self.summary = ""
                self.triggers = []
                self.emotions = []
                self.thoughts = []
                self.values = []

                # Create initial state in database
                initial_state = ConversationState(
                    user_id=user_id,
                    summary=self.summary,
                    triggers=self.triggers,
                    emotions=self.emotions,
                    thoughts=self.thoughts,
                    values=self.values,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                supabase_client.insert_conversation_state(initial_state)
        except Exception as e:
            logger.error(f"Error loading conversation state from database: {e}")
            # Fall back to defaults
            self.summary = ""
            self.triggers = []
            self.emotions = []
            self.thoughts = []
            self.values = []

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
        
    def update_context(self, user_message: str) -> Dict[str, List[str]]:
        """
        Update the conversation context based on user input and LLM response.

        Args:
            user_message: The user's message

        Returns:
            Updated context dictionary
        """
        try:
            system_prompt = """You are an expert conversation context manager. Given the previous conversation context and new user message, update the context to include:
            1. Updated triggers based on recent context
            2. Updated emotions based on recent context
            3. Updated thoughts based on recent context
            4. Updated values based on recent context

            Consider conversation history and maintain contextual relevance."""

            user_prompt = f"""Previous context: {self.get_context()}

            New user message: {user_message}"""
            
            schema = {
                "type": "object",
                "properties": {
                    "triggers": {
                        "type": "array",
                        "description": "Updated triggers based on recent context",
                        "items": {"type": "string"}
                    },
                    "emotions": {
                        "type": "array",
                        "description": "Updated emotions based on recent context",
                        "items": {"type": "string"}
                    },
                    "thoughts": {
                        "type": "array",
                        "description": "Updated thoughts based on recent context",
                        "items": {"type": "string"}
                    },
                    "values": {
                        "type": "array",
                        "description": "Updated values based on recent context",
                        "items": {"type": "string"}
                    }
                },
                "required": [
                    "triggers",
                    "emotions",
                    "thoughts",
                    "values"
                ],
                "additionalProperties": "false"
            }

            # Generate updated context
            context_response = llm_service.generate_structured_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=schema
            )
            
            # Update local state
            self.triggers = context_response["triggers"]
            self.emotions = context_response["emotions"]
            self.thoughts = context_response["thoughts"]
            self.values = context_response["values"]

            # Persist to database
            try:
                supabase_client.update_conversation_state(
                    user_id=self.user_id,
                    triggers=self.triggers,
                    emotions=self.emotions,
                    thoughts=self.thoughts,
                    values=self.values
                )
            except Exception as db_error:
                logger.error(f"Error persisting context to database: {db_error}")

            return context_response

        except Exception as e:
            logger.error(f"Error updating conversation context: {e}")
            return self.get_context()

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

    def get_context(self) -> Dict[str, Any]:
        """Get the current conversational context."""
        return {
            "summary": self.summary,
            "context": {
                "triggers": self.triggers,
                "emotions": self.emotions,
                "thoughts": self.thoughts,
                "values": self.values
            }
        }