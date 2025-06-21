"""
Conversational Engine - Enhanced engine for sophisticated chat logic.
Implements conversation-focused state management with dynamic context tracking,
intelligent story repetition handling, and contextual awareness.
"""

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


class ConversationalEngine:
    """
    Enhanced conversational engine with sophisticated state management.

    Implements conversation-focused state tracking, intelligent story repetition
    handling, and contextual awareness for natural dialogue flow.
    """

    def __init__(self):
        """Initialize the enhanced conversational engine."""
        self.prompts = load_prompts()
        self.states: Dict[str, ConversationalState] = {}

    def get_or_create_state(self, user_id: str = "default") -> ConversationalState:
        """Get or create enhanced conversational state for a user."""
        if user_id not in self.states:
            self.states[user_id] = ConversationalState(user_id)
        return self.states[user_id]

    def filter_stories_by_metadata(self, stories: List[Dict[str, Any]], state: ConversationalState) -> List[Dict[str, Any]]:
        """
        Filter stories based on structured metadata and conversation context.

        Args:
            stories: List of stories with potential analysis metadata
            state: Current conversational state

        Returns:
            Filtered list of stories that match conversation context
        """
        try:
            conversation_context = state.get_conversation_context()
            current_topics = conversation_context.get("current_topics", [])
            recent_intents = conversation_context.get("recent_intents", [])
            key_concepts = conversation_context.get("key_concepts", [])

            filtered_stories = []

            for story in stories:
                story_analysis = story.get("analysis", {})
                extraction_results = story_analysis.get("extraction_results", {})

                # Calculate metadata-based relevance score
                metadata_score = 0.0

                # Check trigger category alignment
                trigger = extraction_results.get("trigger")
                if trigger and current_topics:
                    trigger_category = trigger.get("category", "")
                    trigger_description = trigger.get("description", "")

                    # Score based on trigger category relevance
                    for topic in current_topics:
                        if any(keyword in trigger_description.lower() for keyword in topic.lower().split()):
                            metadata_score += 2.0
                        if trigger_category in ["Social Interaction", "Stressor"] and "work" in topic.lower():
                            metadata_score += 1.5

                # Check emotional alignment
                feelings = extraction_results.get("feelings", {})
                emotions = feelings.get("emotions", [])

                # Score based on emotional context (if we can infer user's emotional state)
                if emotions and recent_intents:
                    if "seek_advice" in recent_intents and any(emotion in ["frustrated", "angry", "stressed"] for emotion in emotions):
                        metadata_score += 2.0
                    if "request_story" in recent_intents:
                        metadata_score += 1.0

                # Check value alignment
                value_analysis = extraction_results.get("value_analysis")
                if value_analysis and key_concepts:
                    violated_value = value_analysis.get("violated_value", "").lower()
                    confidence = value_analysis.get("confidence_score", 0)

                    # Higher score for high-confidence value matches
                    for concept in key_concepts:
                        if concept.lower() in violated_value:
                            metadata_score += confidence * 0.5

                # Check thought pattern alignment
                thought = extraction_results.get("thought")
                if thought and key_concepts:
                    internal_monologue = thought.get("internal_monologue", "").lower()
                    for concept in key_concepts:
                        if concept.lower() in internal_monologue:
                            metadata_score += 1.0

                # Only include stories with some metadata relevance
                if metadata_score > 0.5:
                    story_with_metadata_score = {
                        **story,
                        "metadata_relevance_score": metadata_score
                    }
                    filtered_stories.append(story_with_metadata_score)

            logger.info(f"Filtered {len(filtered_stories)} stories from {len(stories)} based on metadata")
            return filtered_stories

        except Exception as e:
            logger.error(f"Error filtering stories by metadata: {e}")
            return stories  # Return all stories if filtering fails

    def score_story_semantic_relevance(self, story: Dict[str, Any], conversation_context: Dict[str, Any]) -> float:
        """
        Score story relevance using semantic similarity and LLM judgment.

        Args:
            story: Story data with content and analysis
            conversation_context: Current conversation context

        Returns:
            Semantic relevance score between 0 and 10
        """
        try:
            story_content = story.get("content", story.get("text", ""))
            story_analysis = story.get("analysis", {})
            extraction_results = story_analysis.get("extraction_results", {})

            # Prepare context for LLM judge
            current_topics = conversation_context.get("current_topics", [])
            dominant_theme = conversation_context.get("dominant_theme", "")
            recent_intents = conversation_context.get("recent_intents", [])
            key_concepts = conversation_context.get("key_concepts", [])

            # Create rich context description
            context_description = f"""
            Current Topics: {', '.join(current_topics)}
            Dominant Theme: {dominant_theme}
            Recent User Intents: {', '.join(recent_intents)}
            Key Concepts: {', '.join(key_concepts)}
            Conversation Maturity: {conversation_context.get('conversation_maturity', 'unknown')}
            """

            # Prepare story summary with analysis
            story_summary = f"""
            Story Content: {story_content[:800]}

            Analysis:
            - Trigger: {extraction_results.get('trigger', {}).get('description', 'N/A')}
            - Emotions: {', '.join(extraction_results.get('feelings', {}).get('emotions', []))}
            - Internal Thought: {extraction_results.get('thought', {}).get('internal_monologue', 'N/A')[:200]}
            - Violated Value: {extraction_results.get('value_analysis', {}).get('violated_value', 'N/A')}
            """

            # Use enhanced LLM judge for semantic relevance
            system_prompt = """You are an expert at determining story relevance for conversations.
            You will be given a conversation context and a story with its psychological analysis.
            Score how relevant this story is to the current conversation context on a scale of 0-10.

            Consider:
            1. Topic alignment between conversation and story
            2. Emotional resonance with current conversation tone
            3. Value alignment and psychological relevance
            4. Appropriateness for current user intent
            5. Potential to advance or enrich the conversation

            Respond with just a number between 0-10 followed by a brief explanation."""

            user_prompt = f"""Rate the relevance of this story to the current conversation context:

            CONVERSATION CONTEXT:
            {context_description}

            STORY WITH ANALYSIS:
            {story_summary}

            Provide a relevance score (0-10) and brief explanation."""

            response = llm_service.generate_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=150
            )

            # Extract numeric score
            score_text = response.strip().split()[0]
            try:
                semantic_score = float(score_text)
                semantic_score = max(0, min(10, semantic_score))

                logger.debug(f"Story semantic score: {semantic_score:.2f} - {response[:100]}")
                return semantic_score

            except ValueError:
                logger.warning(f"Could not parse semantic score from response: {response}")
                return 5.0  # Default middle score

        except Exception as e:
            logger.error(f"Error scoring semantic relevance: {e}")
            return 0.0

    def calculate_final_story_score(self, story: Dict[str, Any], state: ConversationalState) -> Dict[str, Any]:
        """
        Calculate the final relevance score combining multiple factors.

        Args:
            story: Story with metadata and analysis
            state: Current conversational state

        Returns:
            Dictionary with detailed scoring breakdown
        """
        try:
            story_id = story.get("id", "unknown")
            conversation_context = state.get_conversation_context()

            # Get component scores
            metadata_score = story.get("metadata_relevance_score", 0.0)
            semantic_score = self.score_story_semantic_relevance(story, conversation_context)
            repetition_penalty = state.calculate_story_repetition_penalty(story_id)

            # Weighted combination of scores
            weights = {
                "metadata": 0.3,      # 30% weight for metadata alignment
                "semantic": 0.7       # 70% weight for semantic relevance
            }

            base_score = (weights["metadata"] * metadata_score +
                         weights["semantic"] * semantic_score)

            # Apply repetition penalty
            final_score = base_score / repetition_penalty

            # Bonus for high-confidence value analysis
            extraction_results = story.get("analysis", {}).get("extraction_results", {})
            value_analysis = extraction_results.get("value_analysis", {})
            confidence = value_analysis.get("confidence_score", 0)

            if confidence >= 4:  # High confidence bonus
                final_score *= 1.1

            return {
                "story_id": story_id,
                "final_score": max(0, final_score),
                "component_scores": {
                    "metadata_score": metadata_score,
                    "semantic_score": semantic_score,
                    "base_score": base_score,
                    "repetition_penalty": repetition_penalty,
                    "confidence_bonus": confidence >= 4
                },
                "reasoning": f"Metadata: {metadata_score:.1f}, Semantic: {semantic_score:.1f}, Penalty: {repetition_penalty:.1f}x"
            }

        except Exception as e:
            logger.error(f"Error calculating final story score: {e}")
            return {
                "story_id": story.get("id", "unknown"),
                "final_score": 0.0,
                "component_scores": {},
                "reasoning": f"Error: {str(e)}"
            }

    def rank_stories_by_relevance(self, stories: List[Dict[str, Any]], state: ConversationalState) -> List[Dict[str, Any]]:
        """
        Rank stories by comprehensive relevance scoring.

        Args:
            stories: List of stories to rank
            state: Current conversational state

        Returns:
            List of stories ranked by relevance with scoring details
        """
        try:
            ranked_stories = []

            for story in stories:
                score_details = self.calculate_final_story_score(story, state)

                ranked_story = {
                    **story,
                    "relevance_score": score_details["final_score"],
                    "score_breakdown": score_details["component_scores"],
                    "selection_reasoning": score_details["reasoning"]
                }

                ranked_stories.append(ranked_story)

            # Sort by final relevance score
            ranked_stories.sort(key=lambda x: x["relevance_score"], reverse=True)

            logger.info(f"Ranked {len(ranked_stories)} stories by comprehensive relevance")

            # Log top stories for debugging
            for i, story in enumerate(ranked_stories[:3]):
                logger.debug(f"Rank {i+1}: Story {story.get('id')} - Score: {story['relevance_score']:.2f} - {story['selection_reasoning']}")

            return ranked_stories

        except Exception as e:
            logger.error(f"Error ranking stories: {e}")
            return stories

    def find_relevant_stories(self, state: ConversationalState, limit: int = 3, use_enhanced_relevance: bool = True) -> List[Dict[str, Any]]:
        """
        Find the most relevant stories using enhanced multi-stage filtering and ranking.

        Args:
            state: Current conversational state
            limit: Maximum number of stories to return
            use_enhanced_relevance: Whether to use the enhanced relevance pipeline

        Returns:
            List of relevant stories with comprehensive scoring details
        """
        try:
            # Get all stories with their analyses (now returns model objects)
            stories = supabase_client.get_stories()
            story_analyses = supabase_client.get_story_analyses()

            if not stories:
                logger.warning("No stories found in database")
                return []

            # Convert to dictionaries for backward compatibility with existing logic
            stories_dict = [story.to_dict() for story in stories]
            analyses_dict = [analysis.to_dict() for analysis in story_analyses]

            # Merge stories with their analyses
            stories_with_analysis = self._merge_stories_with_analyses(stories_dict, analyses_dict)

            conversation_context = state.get_conversation_context()
            current_topics = conversation_context.get("current_topics", [])

            if not current_topics and use_enhanced_relevance:
                logger.info("No current topics, using basic story selection")
                use_enhanced_relevance = False

            if use_enhanced_relevance:
                logger.info(f"Using enhanced relevance pipeline for {len(stories_with_analysis)} stories")

                # Stage 1: Filter by metadata alignment
                filtered_stories = self.filter_stories_by_metadata(stories_with_analysis, state)

                if not filtered_stories:
                    logger.warning("No stories passed metadata filtering, falling back to all stories")
                    filtered_stories = stories_with_analysis

                # Stage 2: Rank by comprehensive relevance
                ranked_stories = self.rank_stories_by_relevance(filtered_stories, state)

                # Stage 3: Apply minimum threshold and select top stories
                final_stories = []
                for story in ranked_stories:
                    if story["relevance_score"] > 1.0:  # Minimum relevance threshold
                        final_stories.append(story)
                    if len(final_stories) >= limit:
                        break

                logger.info(f"Enhanced pipeline selected {len(final_stories)} stories from {len(filtered_stories)} filtered candidates")

                return final_stories

            else:
                # Fallback to basic relevance scoring
                logger.info("Using basic relevance scoring")
                return self._find_relevant_stories_basic(stories_with_analysis, state, limit)

        except Exception as e:
            logger.error(f"Error finding relevant stories: {e}")
            return []

    def _merge_stories_with_analyses(self, stories: List[Dict[str, Any]], analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge stories with their corresponding analyses.

        Args:
            stories: List of story records
            analyses: List of story analysis records (from new column structure)

        Returns:
            List of stories with merged analysis data in expected format
        """
        try:
            # Create lookup for analyses by story_id
            analysis_lookup = {}
            for analysis in analyses:
                story_id = analysis.get("story_id")
                if story_id:
                    # Convert column-based analysis to expected nested format
                    extraction_results = {
                        "trigger": {
                            "title": analysis.get("trigger_title"),
                            "description": analysis.get("trigger_description"),
                            "category": analysis.get("trigger_category")
                        } if analysis.get("trigger_title") else None,
                        "feelings": {"emotions": analysis.get("emotions", [])},
                        "thought": {
                            "internal_monologue": analysis.get("internal_monologue")
                        } if analysis.get("internal_monologue") else None,
                        "value_analysis": {
                            "violated_value": analysis.get("violated_value"),
                            "reasoning": analysis.get("value_reasoning"),
                            "confidence_score": analysis.get("confidence_score")
                        } if analysis.get("violated_value") else None
                    }

                    analysis_lookup[story_id] = {
                        "extraction_results": extraction_results
                    }

            # Merge stories with analyses
            merged_stories = []
            for story in stories:
                story_id = story.get("id")
                merged_story = {**story}

                if story_id in analysis_lookup:
                    merged_story["analysis"] = analysis_lookup[story_id]

                merged_stories.append(merged_story)

            logger.debug(f"Merged {len(merged_stories)} stories with analyses ({len(analysis_lookup)} analyses available)")
            return merged_stories

        except Exception as e:
            logger.error(f"Error merging stories with analyses: {e}")
            return stories

    def _find_relevant_stories_basic(self, stories: List[Dict[str, Any]], state: ConversationalState, limit: int) -> List[Dict[str, Any]]:
        """
        Basic story relevance scoring for fallback scenarios.

        Args:
            stories: List of stories to score
            state: Current conversational state
            limit: Maximum stories to return

        Returns:
            List of relevant stories with basic scoring
        """
        try:
            conversation_context = state.get_conversation_context()
            topics = conversation_context.get("current_topics", [])

            if not topics:
                # If no topics, return random selection
                import random
                return random.sample(stories, min(limit, len(stories)))

            scored_stories = []

            for story in stories:
                story_content = story.get("content", story.get("text", ""))
                story_id = story.get("id", "unknown")

                # Simple keyword matching score
                basic_score = 0.0
                for topic in topics:
                    if topic.lower() in story_content.lower():
                        basic_score += 2.0

                # Apply repetition penalty
                repetition_penalty = state.calculate_story_repetition_penalty(story_id)
                final_score = basic_score / repetition_penalty

                if final_score > 0.5:
                    scored_stories.append({
                        **story,
                        "relevance_score": final_score,
                        "selection_reasoning": f"Basic keyword match: {basic_score:.1f}, Penalty: {repetition_penalty:.1f}x"
                    })

            # Sort and return top stories
            scored_stories.sort(key=lambda x: x["relevance_score"], reverse=True)
            return scored_stories[:limit]

        except Exception as e:
            logger.error(f"Error in basic story relevance: {e}")
            return stories[:limit]

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

            # Get current relevant stories with detailed scoring
            relevant_stories = self.find_relevant_stories(state, limit=limit, use_enhanced_relevance=True)

            if not relevant_stories:
                return {"status": "no_relevant_stories", "insights": {}}

            insights = {
                "conversation_context": state.get_conversation_context(),
                "top_stories": [],
                "scoring_summary": {
                    "total_candidates": len(relevant_stories),
                    "score_range": {
                        "highest": max(story["relevance_score"] for story in relevant_stories),
                        "lowest": min(story["relevance_score"] for story in relevant_stories)
                    }
                }
            }

            # Detailed breakdown for top stories
            for i, story in enumerate(relevant_stories[:limit]):
                story_insight = {
                    "rank": i + 1,
                    "story_id": story.get("id"),
                    "title": story.get("title", "Untitled")[:50],
                    "relevance_score": story["relevance_score"],
                    "score_breakdown": story.get("score_breakdown", {}),
                    "selection_reasoning": story.get("selection_reasoning", ""),
                    "has_analysis": "analysis" in story
                }
                insights["top_stories"].append(story_insight)

            return {"status": "success", "insights": insights}

        except Exception as e:
            logger.error(f"Error getting story relevance insights: {e}")
            return {"status": "error", "error": str(e)}

    def generate_response(self, user_message: str, user_id: str = "default") -> Dict[str, Any]:
        """
        Generate a response to a user message using enhanced state management.

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

            personality_summary = ""
            if state.personality_profile:
                # Create a more structured and readable personality summary for the digital twin
                profile = state.personality_profile.profile
                core_values = profile.get("core_values_motivations", {})
                communication = profile.get("communication_style_voice", {})
                cognitive = profile.get("cognitive_style_worldview", {})

                personality_summary = f"""
PERSONALITY PROFILE:

CORE VALUES & MOTIVATIONS:
- Core Values: {core_values.get('core_values', 'Not specified')}
- Anti-Values: {core_values.get('anti_values', 'Not specified')}
- Motivational Drivers: {core_values.get('motivational_drivers', 'Not specified')}
- Value Conflicts: {core_values.get('value_conflicts', 'Not specified')}

COMMUNICATION STYLE & VOICE:
- Formality & Vocabulary: {communication.get('formality_vocabulary', 'Not specified')}
- Tone: {communication.get('tone', 'Not specified')}
- Sentence Structure: {communication.get('sentence_structure', 'Not specified')}
- Recurring Phrases/Metaphors: {communication.get('recurring_phrases_metaphors', 'Not specified')}
- Emotional Expression: {communication.get('emotional_expression', 'Not specified')}
- Storytelling Style: {communication.get('storytelling_style', 'Not specified')}

COGNITIVE STYLE & WORLDVIEW:
- Thinking Process: {cognitive.get('thinking_process', 'Not specified')}
- Outlook: {cognitive.get('outlook', 'Not specified')}
- Focus: {cognitive.get('focus', 'Not specified')}
- Learning Style: {cognitive.get('learning_style', 'Not specified')}
- Decision Making: {cognitive.get('decision_making', 'Not specified')}
- Stress Response: {cognitive.get('stress_response', 'Not specified')}
"""

            stories_context = ""
            used_story_ids = []
            if relevant_stories:
                stories_context = "\n\n".join([
                    f"Story (relevance: {story['relevance_score']:.1f}): {story.get('content', story.get('text', ''))[:500]}..."
                    for story in relevant_stories
                ])
                used_story_ids = [s.get("id") for s in relevant_stories]

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

            # Generate response with enhanced context
            system_prompt = self.prompts["conversation"]["system_prompt"]
            user_prompt = self.prompts["conversation"]["response_prompt"].format(
                personality=personality_summary,
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
                used_stories=used_story_ids,
                metadata={
                    "conversation_context": conversation_context,
                    "stories_considered": len(relevant_stories)
                }
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
