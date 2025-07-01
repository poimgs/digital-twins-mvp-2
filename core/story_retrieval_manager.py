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

    def __init__(self, chat_id: str, bot_id: str, conversation_number: int):
        """Initialize the story retrieval manager."""
        self.chat_id = chat_id
        self.bot_id = bot_id
        self.conversation_number = conversation_number

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
                schema=schema,
                operation_type="story_relevance_judgement",
                bot_id=str(self.bot_id),
                chat_id=str(self.chat_id),
                conversation_number=self.conversation_number
            )

            # Return story with id (convert UUID to string for comparison)
            story_id = response["story_id"]
            selected_story = next((story for story in stories if str(story.id) == story_id), None)

            if selected_story is None:
                logger.warning(f"LLM selected story ID {story_id} which was not found in provided stories")
                # Fallback to first story if available
                return stories[0] if stories else None

            return selected_story

        except Exception as e:
            logger.error(f"Error in judge LLM assessment: {e}")
            return None