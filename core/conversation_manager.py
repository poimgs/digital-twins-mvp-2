import logging
from typing import List, Optional
from datetime import datetime, timezone
from core.llm_service import llm_service
from core.supabase_client import supabase_client
from uuid import UUID
from core.models import ConversationMessage, LLMMessage, ConversationState, StoryWithAnalysis, WarmthLevel
from core.story_retrieval_manager import StoryRetrievalManager

logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Enhanced conversational state management with dynamic context tracking.

    Implements a conversation-focused state that serves as the digital twin's
    short-term memory for a single chat session.
    """

    def __init__(self, chat_id: str, bot_id: str):
        """Initialize conversational state for a chat."""
        self.chat_id = chat_id
        self.bot_id = UUID(bot_id)
        self.story_retrieval_manager = StoryRetrievalManager()

        # Load from database or initialize with defaults
        try:
            state = supabase_client.get_conversation_state(chat_id)
            if state:
                self.summary = state.summary
                self.call_to_action_shown = state.call_to_action_shown
                self.current_warmth_level = WarmthLevel(state.current_warmth_level)
                self.max_warmth_achieved = WarmthLevel(state.max_warmth_achieved)
            else:
                # Initialize with defaults and create in database
                self.summary = ""
                self.call_to_action_shown = False
                self.current_warmth_level = WarmthLevel.IS
                self.max_warmth_achieved = WarmthLevel.IS

                # Create initial state in database
                initial_state = ConversationState(
                    chat_id=chat_id,
                    bot_id=self.bot_id,
                    summary=self.summary,
                    call_to_action_shown=self.call_to_action_shown,
                    current_warmth_level=self.current_warmth_level.value,
                    max_warmth_achieved=self.max_warmth_achieved.value,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                supabase_client.insert_conversation_state(initial_state)
        except Exception as e:
            logger.error(f"Error loading conversation state from database: {e}")
            # Fall back to defaults
            self.summary = ""
            self.call_to_action_shown = False
            self.current_warmth_level = WarmthLevel.IS
            self.max_warmth_achieved = WarmthLevel.IS

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

            # Persist to database first, then update local state
            try:
                supabase_client.update_conversation_state(
                    chat_id=self.chat_id,
                    summary=updated_summary
                )
                # Only update local state if database update succeeds
                self.summary = updated_summary
            except Exception as db_error:
                logger.error(f"Error persisting summary to database: {db_error}")
                # Keep the old summary if database update fails

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
            chat_id=self.chat_id,
            bot_id=self.bot_id,
            role="user",
            content=content,
            created_at=datetime.now(timezone.utc)
        )

        try:
            supabase_client.insert_conversation_message(message)
            self.update_warmth_level()
        except Exception as e:
            logger.error(f"Error storing user message: {e}")

    def add_assistant_message(self, content: str):
        """
        Add an assistant message and update story usage tracking.

        Args:
            content: The assistant's response content
        """
        message = ConversationMessage(
            chat_id=self.chat_id,
            bot_id=self.bot_id,
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
                chat_id=self.chat_id,
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
        
    def analyze_message_warmth_regex(self, message: str) -> int:
        """
        Analyze a message using regex patterns to determine warmth level for warmth measurement.
        This is faster and more reliable than LLM analysis for basic patterns.

        Args:
            message: The message to analyze

        Returns:
            Warmth level
        """
        import re

        message_lower = message.lower().strip()
        complexity = 1

        # Pattern matching for warmth levels (ordered from most to least specific)
        if re.search(r'\bmight\b.*\?|\bmight\s+\w+.*\?|might.*be.*possible', message_lower):
            complexity = 6
        elif re.search(r'\bwould\b.*\?|\bwould\s+you.*\?|would.*consider|would.*think', message_lower):
            complexity = 5
        elif re.search(r'\bwill\b.*\?|\bwill\s+you.*\?|will.*happen|will.*do', message_lower):
            complexity = 4
        elif re.search(r'\bcan\b.*\?|\bcan\s+you.*\?|can.*help|can.*tell|able to', message_lower):
            complexity = 3
        elif re.search(r'\bdid\b.*\?|\bdid\s+you.*\?|did.*happen|did.*feel|have you', message_lower):
            complexity = 2
        elif re.search(r'\bis\b.*\?|\bis\s+this.*\?|is.*true|are you|are there', message_lower):
            complexity = 1
        # For non-questions, analyze engagement level
        elif any(word in message_lower for word in ['tell me more', 'explain', 'describe', 'share']):
            complexity = 3  # Requesting capability
        elif any(word in message_lower for word in ['think', 'feel', 'believe', 'opinion']):
            complexity = 5  # Hypothetical/opinion seeking
        elif any(word in message_lower for word in ['interesting', 'fascinating', 'wow', 'amazing']):
            complexity = 2  # Engaging with past content

        return complexity

    def analyze_conversation_warmth(self, recent_messages_limit: int = 3) -> int:
        """
        Analyze the warmth level based on the last X messages

        Args:
            recent_messages_limit: Number of recent messages to analyze

        Returns:
            Warmth level
        """
        try:
            # Get recent conversation history
            recent_messages = supabase_client.get_conversation_history(
                chat_id=self.chat_id,
                limit=recent_messages_limit
            )

            # Filter for user messages only
            user_messages = [msg for msg in recent_messages if msg.role == 'user']

            if not user_messages:
                return 1
            # Analyze each message and calculate weighted average
            total_warmth_level = 0
            total_weight = 0

            for i, message in enumerate(reversed(user_messages)):  # Most recent first
                weight = recent_messages_limit - i  # More recent messages have higher weight
                warmth_level = self.analyze_message_warmth_regex(message.content)
                total_warmth_level += warmth_level * weight
                total_weight += weight

            # Calculate weighted average warmth level
            weighted_warmth = total_warmth_level / total_weight
            return round(weighted_warmth)

        except Exception as e:
            logger.error(f"Error analyzing conversation warmth: {e}")
            return 1

    def update_warmth_level(self):
        """
        Update the conversation warmth level based on recent conversation context.
        """
        try:
            # Analyze recent conversation context
            new_warmth_level = WarmthLevel(self.analyze_conversation_warmth(recent_messages_limit=5))

            # Update warmth tracking
            self.current_warmth_level = new_warmth_level

            # Update max warmth achieved if this is higher
            if new_warmth_level.value > self.max_warmth_achieved.value:
                self.max_warmth_achieved = new_warmth_level

            # Persist to database
            supabase_client.update_conversation_state(
                chat_id=self.chat_id,
                current_warmth_level=self.current_warmth_level.value,
                max_warmth_achieved=self.max_warmth_achieved.value
            )

            logger.info(f"Updated warmth level to {new_warmth_level} (max: {self.max_warmth_achieved})")

        except Exception as e:
            logger.error(f"Error updating warmth level: {e}")

    def get_current_warmth_level(self) -> WarmthLevel:
        """
        Get the current warmth level for the conversation.

        Returns:
            Current warmth level
        """
        return self.current_warmth_level

    def ready_for_call_to_action(self) -> bool:
        """
        Check if the conversation is ready for call to action based on current warmth level.

        Returns:
            True if ready for call to action, False otherwise
        """
        return self.max_warmth_achieved.value >= WarmthLevel.WILL.value  # Will/Would/Might level questions

    def get_next_question_guidance(self) -> str:
        """
        Get guidance for the LLM on what type of question to ask next based on current warmth level.

        Returns:
            String guidance for the LLM
        """
        current_level = self.current_warmth_level.value
        max_level = self.max_warmth_achieved.value

        # Determine the next appropriate warmth level
        if max_level < WarmthLevel.WILL.value:  # Haven't reached maximum warmth yet
            target_level = min(max_level + 1, 6)  # Try to increase warmth gradually
        else:
            target_level = max(4, current_level)  # Stay at higher levels once achieved

        warmth_level = WarmthLevel(target_level)

        guidance = f"""Based on the current conversation warmth level ({current_level}/6, max achieved: {max_level}/6),
consider asking a {warmth_level.get_question_type()} question using '{warmth_level.name}' structure.

Question warmth levels (from simple to complex):
- 'is' questions: Factual (warmth level 1) - "Is this important to you?"
- 'did' questions: Historical Factual (warmth level 2) - "Did you experience this before?"
- 'can' questions: Capability (warmth level 3) - "Can you imagine doing this?"
- 'will' questions: Intention (warmth level 4) - "Will you consider this approach?"
- 'would' questions: Hypothetical (warmth level 5) - "Would you be open to exploring this?"
- 'might' questions: Speculative (warmth level 6) - "Might there be other perspectives on this?"

{f'Ready for call to action - user has shown high engagement!' if max_level >= 4 else 'Continue building warmth before call to action.'}"""

        return guidance

    def reset_conversation(self):
        """
        Reset the conversation state for a chat.

        Returns:
            True if reset was successful
        """
        try:
            supabase_client.reset_conversation(self.chat_id)
            # Reset local state
            self.summary = ""
            self.call_to_action_shown = False
            self.current_warmth_level = WarmthLevel.IS
            self.max_warmth_achieved = WarmthLevel.IS
            return True
        except Exception as e:
            logger.error(f"Error resetting conversation: {e}")
            return False

    def store_follow_up_questions(self, questions: List[str]) -> bool:
        """
        Store follow-up questions for the current conversation.

        Args:
            questions: List of follow-up questions to store

        Returns:
            True if storage was successful
        """
        try:
            # Update the conversation state with the new follow-up questions
            supabase_client.update_conversation_state(
                chat_id=self.chat_id,
                follow_up_questions=questions
            )
            logger.info(f"Stored {len(questions)} follow-up questions for chat {self.chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error storing follow-up questions: {e}")
            return False

    def get_follow_up_questions(self) -> List[str]:
        """
        Retrieve follow-up questions for the current conversation.

        Returns:
            List of follow-up questions, empty list if none found
        """
        try:
            # Get the conversation state which now includes follow-up questions
            state = supabase_client.get_conversation_state(self.chat_id)
            if state and state.follow_up_questions:
                return state.follow_up_questions
            return []
        except Exception as e:
            logger.error(f"Error retrieving follow-up questions: {e}")
            return []

    def clear_follow_up_questions(self) -> bool:
        """
        Clear follow-up questions for the current conversation.

        Returns:
            True if clearing was successful
        """
        try:
            # Clear follow-up questions by setting them to empty list
            supabase_client.update_conversation_state(
                chat_id=self.chat_id,
                follow_up_questions=[]
            )
            return True
        except Exception as e:
            logger.error(f"Error clearing follow-up questions: {e}")
            return False
