import logging
from typing import List, Optional
from datetime import datetime, timezone
from core.llm_service import llm_service
from core.supabase_client import supabase_client
from uuid import UUID
from core.models import ConversationMessage, LLMMessage, ConversationState, StoryWithAnalysis, WarmthLevel
from core.story_retrieval_manager import StoryRetrievalManager
from core.content_retrieval_manager import ContentRetrievalManager, ContentItem

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

        # Get current conversation number
        self.conversation_number = supabase_client.get_current_conversation_number(chat_id)
        
        self.story_retrieval_manager = StoryRetrievalManager(chat_id, bot_id, self.conversation_number)
        self.content_retrieval_manager = ContentRetrievalManager(chat_id, bot_id, self.conversation_number)

        # Load from database or initialize with defaults
        try:
            state = supabase_client.get_conversation_state(chat_id, self.conversation_number)
            if state:
                self.summary = state.summary
                self.current_warmth_level = WarmthLevel(state.current_warmth_level)
                self.max_warmth_achieved = WarmthLevel(state.max_warmth_achieved)
            else:
                # Initialize with defaults - state will be created when first message is sent
                self.summary = ""
                self.current_warmth_level = WarmthLevel.IS
                self.max_warmth_achieved = WarmthLevel.IS
                self._state_needs_creation = True  # Flag to create state on first message
        except Exception as e:
            logger.error(f"Error loading conversation state from database: {e}")
            # Fall back to defaults
            self.summary = ""
            self.current_warmth_level = WarmthLevel.IS
            self.max_warmth_achieved = WarmthLevel.IS
            self._state_needs_creation = True

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
                user_prompt=user_prompt,
                operation_type="conversation_summary",
                bot_id=str(self.bot_id),
                chat_id=self.chat_id,
                conversation_number=self.conversation_number
            )

            # Persist to database first, then update local state
            try:
                supabase_client.update_conversation_state(
                    chat_id=self.chat_id,
                    summary=updated_summary,
                    conversation_number=self.conversation_number
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
        # Create conversation state if this is the first message in a new conversation
        if hasattr(self, '_state_needs_creation') and self._state_needs_creation:
            try:
                from core.models import ConversationState
                initial_state = ConversationState(
                    chat_id=self.chat_id,
                    bot_id=self.bot_id,
                    conversation_number=self.conversation_number,
                    summary=self.summary,
                    current_warmth_level=self.current_warmth_level.value,
                    max_warmth_achieved=self.max_warmth_achieved.value,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                supabase_client.insert_conversation_state(initial_state)
                self._state_needs_creation = False
                logger.info(f"Created conversation state for conversation {self.conversation_number}")
            except Exception as e:
                logger.error(f"Error creating conversation state: {e}")

        # Store message
        message = ConversationMessage(
            chat_id=self.chat_id,
            bot_id=self.bot_id,
            conversation_number=self.conversation_number,
            role="user",
            content=content,
            created_at=datetime.now(timezone.utc)
        )

        try:
            supabase_client.insert_conversation_message(message)
            self.log_warmth_progression(content)  # Log before updating
            self.update_warmth_level(message)
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
            conversation_number=self.conversation_number,
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
                limit=max_messages,
                conversation_number=self.conversation_number
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

    def find_relevant_content(self) -> Optional[ContentItem]:
        """
        Find the most relevant content item using the content retrieval manager.

        Returns:
            Most relevant ContentItem instance, or None if no content is relevant
        """
        try:
            return self.content_retrieval_manager.find_relevant_content(
                conversation_summary=self.summary
            )

        except Exception as e:
            logger.error(f"Error finding relevant content: {e}")
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

    def update_warmth_level(self, message: ConversationMessage):
        """
        Update the conversation warmth level based on recent conversation context.
        """
        try:
            # Analyze message
            new_warmth_level = WarmthLevel(self.analyze_message_warmth_regex(message.content))

            # Update warmth tracking
            self.current_warmth_level = new_warmth_level

            # Update max warmth achieved if this is higher
            if new_warmth_level.value > self.max_warmth_achieved.value:
                self.max_warmth_achieved = new_warmth_level

            # Persist to database
            supabase_client.update_conversation_state(
                chat_id=self.chat_id,
                current_warmth_level=self.current_warmth_level.value,
                max_warmth_achieved=self.max_warmth_achieved.value,
                conversation_number=self.conversation_number
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

    def _is_fibonacci_number(self, n: int) -> bool:
        """
        Check if a number is in the Fibonacci sequence.

        Args:
            n: Number to check

        Returns:
            True if n is a Fibonacci number, False otherwise
        """
        if n <= 0:
            return False

        # Generate Fibonacci numbers up to n
        a, b = 1, 1
        while a < n:
            a, b = b, a + b

        return a == n

    def ready_for_call_to_action(self) -> bool:
        """
        Check if the conversation is ready for call to action based on Fibonacci sequence.
        CTA is shown when user message count reaches 5, 8, 13, 21, 34, ... (Fibonacci numbers).

        Returns:
            True if ready for call to action, False otherwise
        """
        try:
            user_message_count = supabase_client.get_user_message_count(
                self.chat_id,
                self.conversation_number
            )

            # Check if current user message count is a Fibonacci number >= 5
            is_fibonacci_trigger = (
                user_message_count >= 5 and
                self._is_fibonacci_number(user_message_count)
            )

            logger.info(f"CTA Check - User messages: {user_message_count}, Is Fibonacci >= 5: {is_fibonacci_trigger}")
            return is_fibonacci_trigger

        except Exception as e:
            logger.error(f"Error checking CTA readiness: {e}")
            # Fallback to warmth-based logic if there's an error
            return self.max_warmth_achieved.value >= WarmthLevel.MIGHT.value

    def get_next_question_guidance(self) -> str:
        """
        Get guidance for the LLM on what type of question to ask next based on current warmth level.

        Returns:
            String guidance for the LLM
        """
        current_level = self.current_warmth_level.value

        # ALWAYS move up the question ladder - next question MUST be higher than current level
        target_level = min(current_level + 1, 6)  # Always progress to the next level

        # If we're already at max level (6), stay there
        if current_level >= 6:
            target_level = 6

        warmth_level = WarmthLevel(target_level)

        # Get specific guidance for the target warmth level
        specific_guidance = self._get_specific_question_guidance(warmth_level)

        guidance = f"""🚨 MANDATORY PROGRESSION: You MUST ask a {warmth_level.get_question_type()} question using '{warmth_level.name.lower()}' structure.

CURRENT WARMTH: {current_level}/6 ({WarmthLevel(current_level).name})
REQUIRED NEXT LEVEL: {target_level}/6 ({warmth_level.name}) - {warmth_level.get_question_type()}

⚠️  CRITICAL: The next question MUST move UP the ladder from level {current_level} to level {target_level}.
    DO NOT ask another {WarmthLevel(current_level).name.lower()} question - you MUST ask a {warmth_level.name.lower()} question.

{specific_guidance}

📊 QUESTION LADDER PROGRESSION (MUST FOLLOW IN ORDER):
1. 'is' questions (Level 1): Factual verification - "Is this important to you?"
2. 'did' questions (Level 2): Historical exploration - "Did you experience this before?"
3. 'can' questions (Level 3): Capability assessment - "Can you imagine doing this?"
4. 'will' questions (Level 4): Future intention - "Will you consider this approach?"
5. 'would' questions (Level 5): Hypothetical scenarios - "Would you be open to exploring this?"
6. 'might' questions (Level 6): Speculative possibilities - "Might there be other perspectives on this?"
"""

        return guidance

    def _get_specific_question_guidance(self, warmth_level: WarmthLevel) -> str:
        """
        Get specific guidance for asking questions at a particular warmth level.

        Args:
            warmth_level: The target warmth level

        Returns:
            Specific guidance for that warmth level
        """
        if warmth_level == WarmthLevel.IS:
            return """STRUCTURE: Start with "Is..." or "Are..."
FOCUS: Ask about facts, current states, or simple verification
EXAMPLES: "Is this something you value?", "Are you familiar with this concept?"
PURPOSE: Establish basic facts and current understanding"""

        elif warmth_level == WarmthLevel.DID:
            return """STRUCTURE: Start with "Did..." or "Have you..."
FOCUS: Explore past experiences, historical events, or previous encounters
EXAMPLES: "Did you face similar challenges before?", "Have you experienced this feeling?"
PURPOSE: Connect current situation to past experiences"""

        elif warmth_level == WarmthLevel.CAN:
            return """STRUCTURE: Start with "Can..." or "Are you able to..."
FOCUS: Assess capabilities, possibilities, or potential actions
EXAMPLES: "Can you see yourself in this situation?", "Can you imagine a different outcome?"
PURPOSE: Explore what's possible and assess readiness"""

        elif warmth_level == WarmthLevel.WILL:
            return """STRUCTURE: Start with "Will..." or "Are you going to..."
FOCUS: Future intentions, commitments, or planned actions
EXAMPLES: "Will you take steps toward this?", "Will you consider this path?"
PURPOSE: Gauge commitment and future-oriented thinking"""

        elif warmth_level == WarmthLevel.WOULD:
            return """STRUCTURE: Start with "Would..." or "If you could..."
FOCUS: Hypothetical scenarios, preferences, or conditional situations
EXAMPLES: "Would you be interested in exploring this?", "Would this approach work for you?"
PURPOSE: Explore preferences and hypothetical engagement"""

        elif warmth_level == WarmthLevel.MIGHT:
            return """STRUCTURE: Start with "Might..." or "Could it be that..."
FOCUS: Speculative possibilities, alternative perspectives, or deeper insights
EXAMPLES: "Might there be other ways to view this?", "Might this connect to something deeper?"
PURPOSE: Encourage reflection on possibilities and deeper meaning"""

        else:
            return "Ask an engaging question that fits the conversation flow."

    def log_warmth_progression(self, user_message: str):
        """
        Log warmth progression for debugging and monitoring.

        Args:
            user_message: The user's message to analyze
        """
        try:
            # Analyze the current message
            message_warmth = self.analyze_message_warmth_regex(user_message)
            next_target = min(self.current_warmth_level.value + 1, 6)

            # Get user message count for Fibonacci CTA logic
            user_message_count = supabase_client.get_user_message_count(
                self.chat_id,
                self.conversation_number
            )

            logger.info(f"🎯 Conversation Progression - Chat: {self.chat_id}")
            logger.info(f"  📝 Message: '{user_message[:50]}...' -> Detected Warmth: {message_warmth}")
            logger.info(f"  📊 Current Level: {self.current_warmth_level.value}/6 ({self.current_warmth_level.name})")
            logger.info(f"  🏆 Max Achieved: {self.max_warmth_achieved.value}/6 ({self.max_warmth_achieved.name})")
            logger.info(f"  ⬆️  Next Required: {next_target}/6 ({WarmthLevel(next_target).name if next_target <= 6 else 'MAX'})")
            logger.info(f"  💬 User Messages: {user_message_count}")
            logger.info(f"  🎯 Ready for CTA (Fibonacci): {self.ready_for_call_to_action()}")

        except Exception as e:
            logger.error(f"Error logging conversation progression: {e}")

    def reset_conversation(self):
        """
        Reset the conversation state for a chat by incrementing conversation number.
        This preserves conversation history for analytics while starting fresh.

        Returns:
            True if reset was successful
        """
        try:
            # Call the supabase reset (which just logs the reset)
            supabase_client.reset_conversation(self.chat_id)

            # Increment conversation number for new conversation
            self.conversation_number = supabase_client.get_current_conversation_number(self.chat_id) + 1

            # Reset local state
            self.summary = ""
            self.current_warmth_level = WarmthLevel.IS
            self.max_warmth_achieved = WarmthLevel.IS

            # Create initial state for new conversation number to ensure it exists
            # This is important so that get_current_conversation_number returns the correct value
            try:
                from core.models import ConversationState
                initial_state = ConversationState(
                    chat_id=self.chat_id,
                    bot_id=self.bot_id,
                    conversation_number=self.conversation_number,
                    summary=self.summary,
                    current_warmth_level=self.current_warmth_level.value,
                    max_warmth_achieved=self.max_warmth_achieved.value,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                supabase_client.insert_conversation_state(initial_state)
                logger.info(f"Created conversation state for new conversation {self.conversation_number}")
            except Exception as e:
                logger.error(f"Error creating conversation state for reset: {e}")
                # Set flag to create state later if immediate creation fails
                self._state_needs_creation = True

            logger.info(f"Reset conversation {self.chat_id} to conversation number {self.conversation_number}")
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
                follow_up_questions=questions,
                conversation_number=self.conversation_number
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
            state = supabase_client.get_conversation_state(self.chat_id, self.conversation_number)
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
                follow_up_questions=[],
                conversation_number=self.conversation_number
            )
            return True
        except Exception as e:
            logger.error(f"Error clearing follow-up questions: {e}")
            return False
