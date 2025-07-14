"""
Content Retrieval Manager - Manages content retrieval from multiple categories.
Handles sophisticated content filtering, ranking, and relevance scoring for
contextual content selection in conversations.
"""

import logging
import random
from dataclasses import dataclass
from typing import List, Optional
from core.llm_service import llm_service
from core.models import ContentItem
from core.supabase_client import supabase_client

logger = logging.getLogger(__name__)




class ContentRetrievalManager:
    """
    Manages content retrieval and selection from multiple content categories.
    
    Implements sophisticated content filtering, ranking, and relevance scoring
    to select the most contextually appropriate content for conversations.
    """

    def __init__(self, chat_id: str, bot_id: str, conversation_number: int):
        """Initialize the content retrieval manager."""
        self.chat_id = chat_id
        self.bot_id = bot_id
        self.conversation_number = conversation_number

    def get_all_content_items(self) -> List[ContentItem]:
        """
        Get all content items from the unified stories table for the bot.
        
        Returns:
            List of ContentItem instances
        """
        content_items = []
        
        try:
            # Get all stories (all content types) with optional analysis
            stories = supabase_client.get_stories_with_analysis(self.bot_id)
            for story in stories:
                content_items.append(ContentItem.from_story(story))
            
            logger.info(f"Retrieved {len(content_items)} total content items for bot {self.bot_id}")
            return content_items
            
        except Exception as e:
            logger.error(f"Error retrieving content items: {e}")
            return []

    def find_relevant_content(self, conversation_summary: str) -> Optional[ContentItem]:
        """
        Use a judge LLM to determine the most relevant content item.

        Args:
            conversation_summary: Summary of the conversation

        Returns:
            Most relevant ContentItem instance, or None if no content is relevant
        """
        content_items = self.get_all_content_items()
        if not content_items:
            return None
            
        try:
            # Get available categories for dynamic system prompt
            active_categories = supabase_client.get_distinct_category_types(bot_id=self.bot_id)
            
            system_prompt = f"""You are an expert judge for determining content relevance in digital twin conversations.

Your task is to evaluate which content should be shared in the current conversation context. You will be given a summary of the conversation and a list of content items from different categories.

Available categories: {', '.join(active_categories)}

Choose the most relevant content item based on the conversation context.

Respond with just the content ID."""

            user_prompt = f"Conversation summary: {conversation_summary}"
            
            for item in content_items:
                # Use summary if available and non-empty, otherwise use truncated content
                content_description = item.summary if (item.summary and item.summary.strip()) else item.content
                
                user_prompt += f"""\n\nContent ID: {item.id}
Category: {item.category_type}
Title: {item.title}
Content: {content_description}
"""

            # Define schema for structured response
            schema = {
                "type": "object",
                "properties": {
                    "content_id": {
                        "type": "string",
                        "description": "ID of the content item to be shared"
                    }
                },
                "required": ["content_id"],
                "additionalProperties": False
            }

            # Get structured response from judge LLM
            response = llm_service.generate_structured_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=schema,
                operation_type="content_relevance_judgement",
                bot_id=str(self.bot_id),
                chat_id=str(self.chat_id),
                conversation_number=self.conversation_number
            )

            # Return content item with matching id
            content_id = response["content_id"]
            selected_content = next((item for item in content_items if item.id == content_id), None)

            if selected_content is None:
                logger.warning(f"LLM selected content ID {content_id} which was not found in provided content items")
                # Fallback to first content item if available
                return content_items[0] if content_items else None

            return selected_content

        except Exception as e:
            logger.error(f"Error in content relevance assessment: {e}")
            return None

    def get_content_items_by_category(self, category_type: str) -> List[ContentItem]:
        """
        Get content items filtered by category type.

        Args:
            category_type: The category type to filter by

        Returns:
            List of ContentItem instances for the specified category
        """
        try:
            # Get stories filtered by category type with optional analysis
            stories = supabase_client.get_stories_with_analysis(self.bot_id, category_type=category_type)
            content_items = []
            for story in stories:
                content_items.append(ContentItem.from_story(story))
            
            logger.info(f"Retrieved {len(content_items)} content items for category {category_type} for bot {self.bot_id}")
            return content_items
            
        except Exception as e:
            logger.error(f"Error retrieving content items by category {category_type}: {e}")
            return []

    def get_random_categories_for_follow_up(self, current_category: str, count: int = 2) -> List[str]:
        """
        Get random categories different from the current one for follow-up questions.
        Only returns categories that have actual content.

        Args:
            current_category: The current content category
            count: Number of random categories to return

        Returns:
            List of random category type strings
        """
        # Get categories that have actual content for user-facing follow-up questions
        all_categories = supabase_client.get_distinct_category_types(bot_id=self.bot_id)

        # Remove current category from options
        other_categories = [cat for cat in all_categories if cat != current_category]

        # Return random selection, up to the requested count
        return random.sample(other_categories, min(count, len(other_categories)))

    def get_content_summaries_by_category(self, category_type: str) -> str:
        """
        Get summaries of content items for a specific category.
        
        Args:
            category_type: The category type to get summaries for
            
        Returns:
            String containing summaries of content items in the category
        """
        content_items = self.get_content_items_by_category(category_type)
        summaries = []
        
        for item in content_items:
            # Use summary if available and non-empty, otherwise use content
            description = item.summary if (item.summary and item.summary.strip()) else item.content
            summaries.append(f"- {description}")
        
        return "\n".join(summaries) if summaries else f"No {category_type} content available"
