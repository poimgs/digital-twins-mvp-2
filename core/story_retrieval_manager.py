"""
Story Retrieval Manager - Manages long-term memory and story retrieval logic.
Handles sophisticated story filtering, ranking, and relevance scoring for
contextual story selection in conversations.
"""

import logging
from typing import Dict, List, Any, Optional
from core.llm_service import llm_service
from core.supabase_client import supabase_client

logger = logging.getLogger(__name__)


class StoryRetrievalManager:
    """
    Manages story retrieval and long-term memory functionality.
    
    Implements sophisticated story filtering, ranking, and relevance scoring
    to select the most contextually appropriate stories for conversations.
    """

    def __init__(self):
        """Initialize the story retrieval manager."""
        pass

    def filter_stories_by_metadata(self, stories: List[Dict[str, Any]], conversation_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filter stories based on structured metadata and conversation context.

        Args:
            stories: List of stories with potential analysis metadata
            conversation_context: Current conversation context

        Returns:
            Filtered list of stories that match conversation context
        """
        try:
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

    def calculate_final_story_score(self, story: Dict[str, Any], conversation_context: Dict[str, Any], repetition_penalty: float = 1.0) -> Dict[str, Any]:
        """
        Calculate the final relevance score combining multiple factors.

        Args:
            story: Story with metadata and analysis
            conversation_context: Current conversation context
            repetition_penalty: Penalty factor for story repetition

        Returns:
            Dictionary with detailed scoring breakdown
        """
        try:
            story_id = story.get("id", "unknown")

            # Get component scores
            metadata_score = story.get("metadata_relevance_score", 0.0)
            semantic_score = self.score_story_semantic_relevance(story, conversation_context)

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

    def rank_stories_by_relevance(self, stories: List[Dict[str, Any]], conversation_context: Dict[str, Any], repetition_penalties: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """
        Rank stories by comprehensive relevance scoring.

        Args:
            stories: List of stories to rank
            conversation_context: Current conversation context
            repetition_penalties: Dictionary mapping story IDs to repetition penalties

        Returns:
            List of stories ranked by relevance with scoring details
        """
        try:
            if repetition_penalties is None:
                repetition_penalties = {}

            ranked_stories = []

            for story in stories:
                story_id = story.get("id", "unknown")
                repetition_penalty = repetition_penalties.get(str(story_id), 1.0)
                
                score_details = self.calculate_final_story_score(story, conversation_context, repetition_penalty)

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

    def merge_stories_with_analyses(self, stories: List[Dict[str, Any]], analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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

    def find_relevant_stories(self, conversation_context: Dict[str, Any], repetition_penalties: Optional[Dict[str, float]] = None, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Find the most relevant stories using enhanced multi-stage filtering and ranking.

        Args:
            conversation_context: Current conversation context
            repetition_penalties: Dictionary mapping story IDs to repetition penalties
            limit: Maximum number of stories to return

        Returns:
            List of relevant stories with comprehensive scoring details
        """
        try:
            if repetition_penalties is None:
                repetition_penalties = {}

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
            stories_with_analysis = self.merge_stories_with_analyses(stories_dict, analyses_dict)

            logger.info(f"Using enhanced relevance pipeline for {len(stories_with_analysis)} stories")

            # Stage 1: Filter by metadata alignment
            filtered_stories = self.filter_stories_by_metadata(stories_with_analysis, conversation_context)

            if not filtered_stories:
                logger.warning("No stories passed metadata filtering, falling back to all stories")
                filtered_stories = stories_with_analysis

            # Stage 2: Rank by comprehensive relevance
            ranked_stories = self.rank_stories_by_relevance(filtered_stories, conversation_context, repetition_penalties)

            # Stage 3: Apply minimum threshold and select top stories
            final_stories = []
            for story in ranked_stories:
                if story["relevance_score"] > 1.0:  # Minimum relevance threshold
                    final_stories.append(story)
                if len(final_stories) >= limit:
                    break

            logger.info(f"Enhanced pipeline selected {len(final_stories)} stories from {len(filtered_stories)} filtered candidates")

            return final_stories

        except Exception as e:
            logger.error(f"Error finding relevant stories: {e}")
            return []

    def get_story_relevance_insights(self, conversation_context: Dict[str, Any], repetition_penalties: Optional[Dict[str, float]] = None, limit: int = 5) -> Dict[str, Any]:
        """
        Get insights into story relevance scoring for debugging and optimization.

        Args:
            conversation_context: Current conversation context
            repetition_penalties: Dictionary mapping story IDs to repetition penalties
            limit: Number of top stories to analyze

        Returns:
            Dictionary containing relevance insights
        """
        try:
            # Get current relevant stories with detailed scoring
            relevant_stories = self.find_relevant_stories(conversation_context, repetition_penalties, limit=limit)

            if not relevant_stories:
                return {"status": "no_relevant_stories", "insights": {}}

            insights = {
                "conversation_context": conversation_context,
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
