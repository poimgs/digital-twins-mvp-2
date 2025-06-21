"""
Story Retrieval Manager - Manages long-term memory and story retrieval logic.
Handles sophisticated story filtering, ranking, and relevance scoring for
contextual story selection in conversations.
"""

import logging
from typing import List, Optional
from core.llm_service import llm_service
from core.models import StoryWithAnalysis



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

    def find_relevant_story(self, stories: List[StoryWithAnalysis], conversation_summary: str) -> Optional[StoryWithAnalysis]:
        """
        Use a judge LLM to determine the most relevant story.

        Args:
            stories: List of StoryWithAnalysis instances
            conversation_summary: Summary of the conversation

        Returns:
            Most relevant StoryWithAnalysis instance, or None if no stories are relevant
        """
        if not stories:
            return None
        try:
            system_prompt = """You are an expert judge for determining story relevance in digital twin conversations.

Your task is to evaluate whether a story should be shared in the current conversation context. You will be given a summary of the conversation and a list of stories.

Respond with just the story ID.
"""

            user_prompt = f"Conversation summary: {conversation_summary}"
            
            for story in stories:
                user_prompt += f"""\n\nStory ID: {story.id}
Title: {story.title}
Summary: {story.summary}
Triggers: {story.triggers}
Emotions: {story.emotions}
Thoughts: {story.thoughts}
Values: {story.values}
"""

            # Define schema for structured response
            schema = {
                "type": "object",
                "properties": {
                    "story_id": {
                        "type": "string",
                        "description": "ID of the story to be shared"
                    }
                },
                "required": ["story_id"],
                "additionalProperties": False
            }

            # Get structured response from judge LLM
            response = llm_service.generate_structured_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=schema
            )
            
            # Return story with id
            return next((story for story in stories if story.id == response["story_id"]), None)

        except Exception as e:
            logger.error(f"Error in judge LLM assessment: {e}")
            return None