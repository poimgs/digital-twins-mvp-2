import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from core.llm_service import llm_service
from core.supabase_client import supabase_client
from core.utils import load_prompts
from core.models import PersonalityProfile, ConversationMessage, UserInputAnalysis

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
        self.state = self._create_initial_state()
        self.personality_profile: Optional[PersonalityProfile] = None
        # Load schema from prompts.json instead of defining it locally
        prompts = load_prompts()
        self.user_input_analysis_schema = prompts["schemas"]["user_input_analysis_schema"]
        self.load_state()

    def _create_initial_state(self) -> Dict[str, Any]:
        """Create the initial conversation-focused state structure."""
        return {
            "session_id": str(uuid.uuid4()),
            "last_updated_timestamp": datetime.now(timezone.utc).isoformat(),
            "turn_count": 0,
            "current_topics": [],
            "user_intent_history": [],
            "retrieved_story_history": [],
            "mentioned_concepts": {},
            "conversation_flow": {
                "dominant_theme": None,
                "theme_stability_count": 0,
                "last_topic_shift_turn": 0
            },
            "context_decay": {
                "topic_decay_threshold": 3,
                "concept_decay_threshold": 5,
                "story_repetition_penalty_base": 2.0
            }
        }



    def load_state(self):
        """Load existing conversation state and personality profile."""
        try:
            # Load personality profile (now returns PersonalityProfile object)
            self.personality_profile = supabase_client.get_personality_profile(self.user_id)

            logger.info(f"Loaded conversational state for user {self.user_id}")

        except Exception as e:
            logger.error(f"Error loading conversational state: {e}")
            # Continue with empty state

    def update_timestamp(self):
        """Update the last updated timestamp."""
        self.state["last_updated_timestamp"] = datetime.now(timezone.utc).isoformat()

    def increment_turn(self):
        """Increment the turn counter and update timestamp."""
        self.state["turn_count"] += 1
        self.update_timestamp()

    def analyze_user_input(self, user_message: str) -> UserInputAnalysis:
        """
        Analyze user input to extract topics, concepts, and intent.

        Args:
            user_message: The user's message

        Returns:
            UserInputAnalysis instance containing analysis results
        """
        try:
            system_prompt = """You are an expert conversation analyst. Analyze the user's message to extract:
            1. Main topics/themes (2-4 words each)
            2. Key concepts mentioned
            3. User intent (what they're trying to accomplish)

            Respond with structured JSON containing topics, concepts, and intent."""

            user_prompt = f"""Analyze this message:

            "{user_message}"

            Extract:
            - topics: List of 1-3 main topics (2-4 words each)
            - concepts: List of key concepts, names, or ideas mentioned
            - intent: Single phrase describing what the user wants (choose from: request_story, ask_opinion, seek_advice, ask_clarification_question, share_experience, general_conversation, express_emotion, ask_question)"""

            # Use structured response with user input analysis schema
            analysis = llm_service.generate_structured_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=self.user_input_analysis_schema
            )

            return UserInputAnalysis.from_dict(analysis)

        except Exception as e:
            logger.error(f"Error analyzing user input: {e}")
            return UserInputAnalysis()

    def update_state_with_analysis(self, analysis: UserInputAnalysis):
        """
        Update the conversational state with analysis results.

        Args:
            analysis: UserInputAnalysis instance from analyze_user_input
        """
        # Update topics
        new_topics = analysis.topics
        current_topics = self.state["current_topics"]

        # Add new topics and maintain recency
        for topic in new_topics:
            if topic not in current_topics:
                current_topics.append(topic)

        # Keep only the most recent topics (max 5)
        self.state["current_topics"] = current_topics[-5:]

        # Update intent history
        intent = analysis.intent
        intent_history = self.state["user_intent_history"]
        intent_history.append(intent)

        # Keep only recent intents (max 5)
        self.state["user_intent_history"] = intent_history[-5:]

        # Update mentioned concepts
        concepts = analysis.concepts
        mentioned_concepts = self.state["mentioned_concepts"]

        for concept in concepts:
            if concept in mentioned_concepts:
                mentioned_concepts[concept]["count"] += 1
                mentioned_concepts[concept]["last_mentioned_turn"] = self.state["turn_count"]
            else:
                mentioned_concepts[concept] = {
                    "count": 1,
                    "first_mentioned_turn": self.state["turn_count"],
                    "last_mentioned_turn": self.state["turn_count"]
                }

        # Update conversation flow
        self._update_conversation_flow(new_topics)

        # Apply context decay
        self._apply_context_decay()

    def _update_conversation_flow(self, new_topics: List[str]):
        """Update conversation flow tracking."""
        flow = self.state["conversation_flow"]

        if not new_topics:
            return

        # Determine dominant theme from current topics
        current_dominant = self._get_dominant_theme()

        if flow["dominant_theme"] == current_dominant:
            flow["theme_stability_count"] += 1
        else:
            flow["last_topic_shift_turn"] = self.state["turn_count"]
            flow["dominant_theme"] = current_dominant
            flow["theme_stability_count"] = 1

    def _get_dominant_theme(self) -> Optional[str]:
        """Get the most frequently mentioned topic as dominant theme."""
        topics = self.state["current_topics"]
        if not topics:
            return None

        # For simplicity, return the most recent topic
        # In a more sophisticated implementation, this could analyze frequency
        return topics[-1] if topics else None

    def _apply_context_decay(self):
        """Apply context decay logic to prevent stale information."""
        current_turn = self.state["turn_count"]
        decay_config = self.state["context_decay"]

        # Decay old concepts
        concepts_to_remove = []
        for concept, data in self.state["mentioned_concepts"].items():
            turns_since_mention = current_turn - data["last_mentioned_turn"]
            if turns_since_mention > decay_config["concept_decay_threshold"]:
                concepts_to_remove.append(concept)

        for concept in concepts_to_remove:
            del self.state["mentioned_concepts"][concept]

        # Topic decay is handled by the conversation flow logic

    def calculate_story_repetition_penalty(self, story_id: str) -> float:
        """
        Calculate repetition penalty for a story based on when it was last told.

        Args:
            story_id: ID of the story to check

        Returns:
            Penalty multiplier (higher = more penalty)
        """
        current_turn = self.state["turn_count"]

        for story_record in self.state["retrieved_story_history"]:
            if story_record["story_id"] == story_id:
                turns_since_told = current_turn - story_record["told_at_turn"]

                # Dynamic penalty: higher penalty for recently told stories
                base_penalty = self.state["context_decay"]["story_repetition_penalty_base"]

                if turns_since_told <= 2:
                    return base_penalty * 3.0  # Heavy penalty for very recent
                elif turns_since_told <= 5:
                    return base_penalty * 2.0  # Moderate penalty for recent
                elif turns_since_told <= 10:
                    return base_penalty * 1.5  # Light penalty for somewhat recent
                else:
                    return base_penalty * 1.0  # Minimal penalty for old stories

        return 1.0  # No penalty for never-told stories

    def record_story_usage(self, story_id: str):
        """
        Record that a story was told in this conversation.

        Args:
            story_id: ID of the story that was told
        """
        story_record = {
            "story_id": story_id,
            "told_at_turn": self.state["turn_count"]
        }

        self.state["retrieved_story_history"].append(story_record)

        # Keep history manageable (last 20 stories)
        if len(self.state["retrieved_story_history"]) > 20:
            self.state["retrieved_story_history"] = self.state["retrieved_story_history"][-20:]

    def get_conversation_context(self) -> Dict[str, Any]:
        """
        Get current conversation context for response generation.

        Returns:
            Dictionary containing conversation context
        """
        return {
            "session_id": self.state["session_id"],
            "turn_count": self.state["turn_count"],
            "current_topics": self.state["current_topics"],
            "dominant_theme": self.state["conversation_flow"]["dominant_theme"],
            "recent_intents": self.state["user_intent_history"][-3:],
            "key_concepts": list(self.state["mentioned_concepts"].keys()),
            "conversation_maturity": "established" if self.state["turn_count"] > 5 else "new"
        }

    def should_context_reset(self) -> bool:
        """
        Determine if conversation context should be reset due to inactivity or topic shift.

        Returns:
            True if context should be reset
        """
        # Check for long inactivity (would need timestamp comparison in real implementation)
        # For now, just check for very long conversations
        if self.state["turn_count"] > 50:
            return True

        # Check for major topic shifts
        flow = self.state["conversation_flow"]
        if flow["theme_stability_count"] == 1 and self.state["turn_count"] > 10:
            # New theme after established conversation might indicate reset needed
            return False  # For now, don't auto-reset

        return False

    def add_user_message(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Add a user message and update conversational state.

        Args:
            content: The user's message content
            metadata: Optional metadata for the message
        """
        # Increment turn counter
        self.increment_turn()

        # Analyze user input
        analysis = self.analyze_user_input(content)

        # Update state with analysis
        self.update_state_with_analysis(analysis)

        # Store message (optional - for persistence)
        message = ConversationMessage(
            user_id=self.user_id,
            role="user",
            content=content,
            metadata={
                **(metadata or {}),
                "analysis": analysis.to_dict(),
                "turn_count": self.state["turn_count"]
            },
            created_at=datetime.now(timezone.utc)
        )

        try:
            supabase_client.insert_conversation_message(message)
        except Exception as e:
            logger.error(f"Error storing user message: {e}")

    def add_assistant_message(self, content: str, used_stories: List[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """
        Add an assistant message and update story usage tracking.

        Args:
            content: The assistant's response content
            used_stories: List of story IDs that were used in the response
            metadata: Optional metadata for the message
        """
        # Record story usage
        if used_stories:
            for story_id in used_stories:
                self.record_story_usage(story_id)

        # Store message (optional - for persistence)
        message = ConversationMessage(
            user_id=self.user_id,
            role="assistant",
            content=content,
            metadata={
                **(metadata or {}),
                "used_stories": used_stories or [],
                "turn_count": self.state["turn_count"],
                "conversation_context": self.get_conversation_context()
            },
            created_at=datetime.now(timezone.utc)
        )

        try:
            supabase_client.insert_conversation_message(message)
        except Exception as e:
            logger.error(f"Error storing assistant message: {e}")

    def get_state_summary(self) -> Dict[str, Any]:
        """Get a summary of the current conversational state."""
        return {
            "session_id": self.state["session_id"],
            "user_id": self.user_id,
            "turn_count": self.state["turn_count"],
            "current_topics": self.state["current_topics"],
            "dominant_theme": self.state["conversation_flow"]["dominant_theme"],
            "stories_told_count": len(self.state["retrieved_story_history"]),
            "key_concepts_count": len(self.state["mentioned_concepts"]),
            "last_updated": self.state["last_updated_timestamp"]
        }