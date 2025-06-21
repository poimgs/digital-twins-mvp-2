"""
Conversational Engine - Enhanced engine for sophisticated chat logic.
Implements conversation-focused state management with dynamic context tracking,
intelligent story repetition handling, and contextual awareness.
"""

import logging
from typing import Dict, List, Any
from core.llm_service import llm_service
from core.supabase_client import supabase_client
from core.utils import load_prompts
from core.conversational_state import ConversationalState
from core.story_retrieval_manager import StoryRetrievalManager

logger = logging.getLogger(__name__)

class ConversationalEngine:
    """
    conversational engine with sophisticated state management.

    Implements conversation-focused state tracking, intelligent story repetition
    handling, and contextual awareness for natural dialogue flow.
    """
    personality_summary: str = ""

    def __init__(self):
        """Initialize the conversational engine."""
        self.prompts = load_prompts()
        self.states: Dict[str, ConversationalState] = {}
        self.story_retrieval_manager = StoryRetrievalManager()

        personality_profile = supabase_client.get_personality_profile()
        # Create a more structured and readable personality summary for the digital twin
        self.personality_summary = f"""
PERSONALITY PROFILE:

VALUES & MOTIVATIONS:
- Values: { ', '.join(personality_profile.values) if personality_profile else 'Not specified'}

COMMUNICATION STYLE & VOICE:
- Formality & Vocabulary: {personality_profile.formality_vocabulary if personality_profile else 'Not specified'}
- Tone: {personality_profile.tone if personality_profile else 'Not specified'}
- Sentence Structure: {personality_profile.sentence_structure if personality_profile else 'Not specified'}
- Recurring Phrases/Metaphors: {personality_profile.recurring_phrases_metaphors if personality_profile else 'Not specified'}
- Emotional Expression: {personality_profile.emotional_expression if personality_profile else 'Not specified'}
- Storytelling Style: {personality_profile.storytelling_style if personality_profile else 'Not specified'}
"""

    def get_or_create_state(self, user_id: str = "default") -> ConversationalState:
        """Get or create conversational state for a user."""
        if user_id not in self.states:
            self.states[user_id] = ConversationalState(user_id)
        return self.states[user_id]

    def find_relevant_stories(self, state: ConversationalState, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Find the most relevant stories using enhanced multi-stage filtering and ranking.

        Args:
            state: Current conversational state
            limit: Maximum number of stories to return

        Returns:
            List of relevant stories with comprehensive scoring details
        """
        try:
            conversation_context = state.get_conversation_context()

            # Create repetition penalties dictionary from state
            repetition_penalties = {}
            for story_id in state.state.get("retrieved_story_history", []):
                story_id_str = str(story_id.get("story_id", ""))
                if story_id_str:
                    repetition_penalties[story_id_str] = state.calculate_story_repetition_penalty(story_id_str)

            # Use the story retrieval manager
            return self.story_retrieval_manager.find_relevant_stories(
                conversation_context=conversation_context,
                repetition_penalties=repetition_penalties,
                limit=limit
            )

        except Exception as e:
            logger.error(f"Error finding relevant stories: {e}")
            return []



    def analyze_story_selection_performance(self, user_id: str = "default") -> Dict[str, Any]:
        """
        Analyze the performance of story selection for a user's conversation.

        Args:
            user_id: User identifier

        Returns:
            Dictionary containing story selection analytics
        """
        try:
            state = self.get_or_create_state(user_id)
            story_history = state.state["retrieved_story_history"]

            if not story_history:
                return {"status": "no_stories", "analytics": {}}

            # Analyze story selection patterns
            total_stories = len(story_history)
            unique_stories = len(set(record["story_id"] for record in story_history))
            repetition_rate = (total_stories - unique_stories) / total_stories if total_stories > 0 else 0

            # Analyze turn gaps between story repetitions
            story_gaps = {}
            for record in story_history:
                story_id = record["story_id"]
                turn = record["told_at_turn"]

                if story_id in story_gaps:
                    last_turn = story_gaps[story_id][-1]
                    gap = turn - last_turn
                    story_gaps[story_id].append(turn)
                else:
                    story_gaps[story_id] = [turn]

            # Calculate average gaps for repeated stories
            repeated_story_gaps = []
            for story_id, turns in story_gaps.items():
                if len(turns) > 1:
                    for i in range(1, len(turns)):
                        gap = turns[i] - turns[i-1]
                        repeated_story_gaps.append(gap)

            avg_repetition_gap = sum(repeated_story_gaps) / len(repeated_story_gaps) if repeated_story_gaps else 0

            analytics = {
                "total_stories_told": total_stories,
                "unique_stories": unique_stories,
                "repetition_rate": repetition_rate,
                "average_repetition_gap": avg_repetition_gap,
                "story_distribution": dict(story_gaps),
                "conversation_turns": state.state["turn_count"],
                "stories_per_turn_ratio": total_stories / max(1, state.state["turn_count"])
            }

            return {"status": "success", "analytics": analytics}

        except Exception as e:
            logger.error(f"Error analyzing story selection performance: {e}")
            return {"status": "error", "error": str(e)}

    def get_story_relevance_insights(self, user_id: str = "default", limit: int = 5) -> Dict[str, Any]:
        """
        Get insights into story relevance scoring for debugging and optimization.

        Args:
            user_id: User identifier
            limit: Number of top stories to analyze

        Returns:
            Dictionary containing relevance insights
        """
        try:
            state = self.get_or_create_state(user_id)
            conversation_context = state.get_conversation_context()

            # Create repetition penalties dictionary from state
            repetition_penalties = {}
            for story_id in state.state.get("retrieved_story_history", []):
                story_id_str = str(story_id.get("story_id", ""))
                if story_id_str:
                    repetition_penalties[story_id_str] = state.calculate_story_repetition_penalty(story_id_str)

            # Use the story retrieval manager
            return self.story_retrieval_manager.get_story_relevance_insights(
                conversation_context=conversation_context,
                repetition_penalties=repetition_penalties,
                limit=limit
            )

        except Exception as e:
            logger.error(f"Error getting story relevance insights: {e}")
            return {"status": "error", "error": str(e)}

    def generate_response(self, user_message: str, user_id: str = "default") -> Dict[str, Any]:
        """
        Generate a response to a user message

        Args:
            user_message: The user's message
            user_id: User identifier

        Returns:
            Dictionary containing response and conversation metadata
        """
        try:
            # Get conversational state
            state = self.get_or_create_state(user_id)

            # Process user message and update state
            state.add_user_message(user_message)

            # Find relevant stories using enhanced context
            relevant_stories = self.find_relevant_stories(state)

            # Prepare enhanced context for response generation
            conversation_context = state.get_conversation_context()

            stories_context = ""
            used_story_ids = []
            if relevant_stories:
                stories_context = "\n\n".join([
                    f"Story (relevance: {story['relevance_score']:.1f}): {story.get('content', story.get('text', ''))[:500]}..."
                    for story in relevant_stories
                ])
                used_story_ids = [str(s.get("id")) for s in relevant_stories if s.get("id") is not None]

            # Enhanced context information
            context_info = f"""
            Conversation Context:
            - Turn: {conversation_context['turn_count']}
            - Topics: {', '.join(conversation_context['current_topics'])}
            - Dominant Theme: {conversation_context['dominant_theme']}
            - Recent Intents: {', '.join(conversation_context['recent_intents'])}
            - Key Concepts: {', '.join(conversation_context['key_concepts'][:5])}
            - Conversation Stage: {conversation_context['conversation_maturity']}
            """

            # Get conversation history for better context
            conversation_history = state.get_conversation_history_for_llm(max_messages=10)

            # If we have conversation history, use it for better context
            if conversation_history:
                # Build messages for conversation completion using LLMMessage objects
                messages = llm_service.build_llm_messages(
                    system_prompt=self.prompts["conversation"]["system_prompt"],
                    conversation_history=conversation_history[:-1],  # Exclude the last user message
                    user_message=self.prompts["conversation"]["response_prompt"].format(
                        personality=self.personality_summary,
                        relevant_stories=stories_context,
                        conversation_history=context_info,
                        user_message=user_message
                    )
                )

                response = llm_service.generate_completion_from_llm_messages(messages)
            else:
                # Fallback to original method if no history
                system_prompt = self.prompts["conversation"]["system_prompt"]
                user_prompt = self.prompts["conversation"]["response_prompt"].format(
                    personality=self.personality_summary,
                    relevant_stories=stories_context,
                    conversation_history=context_info,
                    user_message=user_message
                )

                response = llm_service.generate_completion(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt
                )

            # Record assistant response and story usage
            state.add_assistant_message(
                content=response,
                used_stories=used_story_ids
            )

            # Return comprehensive response data
            return {
                "response": response,
                "conversation_context": conversation_context,
                "used_stories": used_story_ids,
                "stories_considered": len(relevant_stories),
                "state_summary": state.get_state_summary()
            }

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "response": "I'm sorry, I'm having trouble responding right now. Could you try again?",
                "error": str(e),
                "conversation_context": {},
                "used_stories": [],
                "stories_considered": 0
            }

    def get_conversation_summary(self, user_id: str = "default") -> Dict[str, Any]:
        """
        Get a summary of the conversation state for a user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary containing conversation summary
        """
        try:
            state = self.get_or_create_state(user_id)
            return state.get_state_summary()
        except Exception as e:
            logger.error(f"Error getting conversation summary: {e}")
            return {}

    def reset_conversation(self, user_id: str = "default") -> bool:
        """
        Reset the conversation state for a user.

        Args:
            user_id: User identifier

        Returns:
            True if reset was successful
        """
        try:
            if user_id in self.states:
                del self.states[user_id]
            logger.info(f"Reset conversation state for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error resetting conversation: {e}")
            return False

    def get_active_topics(self, user_id: str = "default") -> List[str]:
        """
        Get the currently active topics for a user's conversation.

        Args:
            user_id: User identifier

        Returns:
            List of active topics
        """
        try:
            state = self.get_or_create_state(user_id)
            return state.state["current_topics"]
        except Exception as e:
            logger.error(f"Error getting active topics: {e}")
            return []

    def get_story_usage_stats(self, user_id: str = "default") -> Dict[str, Any]:
        """
        Get statistics about story usage in the conversation.

        Args:
            user_id: User identifier

        Returns:
            Dictionary containing story usage statistics
        """
        try:
            state = self.get_or_create_state(user_id)
            story_history = state.state["retrieved_story_history"]

            if not story_history:
                return {"total_stories_told": 0, "unique_stories": 0, "repeated_stories": 0}

            story_ids = [record["story_id"] for record in story_history]
            unique_stories = set(story_ids)

            return {
                "total_stories_told": len(story_history),
                "unique_stories": len(unique_stories),
                "repeated_stories": len(story_ids) - len(unique_stories),
                "most_recent_stories": story_ids[-5:] if len(story_ids) >= 5 else story_ids
            }
        except Exception as e:
            logger.error(f"Error getting story usage stats: {e}")
            return {"total_stories_told": 0, "unique_stories": 0, "repeated_stories": 0}


# Global conversational engine instance
conversational_engine = ConversationalEngine()
