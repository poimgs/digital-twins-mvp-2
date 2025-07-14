"""
Content Retrieval Manager - Manages content retrieval from multiple categories.
Handles sophisticated content filtering, ranking, and relevance scoring for
contextual content selection in conversations.
"""

import logging
import random
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from collections import defaultdict
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
        
        # Track recently used content for freshness management
        self.recently_used_content = []  # List of recently used content IDs
        self.recently_used_categories = []  # List of recently used categories

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

    def find_relevant_content(self, conversation_summary: str, latest_user_message: str = "") -> Optional[ContentItem]:
        """
        Use a balanced two-stage approach to determine the most relevant content item.
        Stage 1: Determine most relevant category with balanced representation
        Stage 2: Select best item within that category

        Args:
            conversation_summary: Summary of the conversation
            latest_user_message: The most recent user message (takes priority in evaluation)

        Returns:
            Most relevant ContentItem instance, or None if no content is relevant
        """
        content_items = self.get_all_content_items()
        if not content_items:
            return None
            
        try:
            # Use balanced content selection approach
            return self._balanced_content_selection(conversation_summary, content_items, latest_user_message)
        except Exception as e:
            logger.error(f"Error in balanced content selection: {e}")
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

    def get_random_categories_for_follow_up(self, current_category: str, count: int = 2, available_categories: Optional[List[str]] = None) -> List[str]:
        """
        Get random categories different from the current one for follow-up questions.
        Only returns categories that have actual content.

        Args:
            current_category: The current content category
            count: Number of random categories to return
            available_categories: Pre-fetched categories list

        Returns:
            List of random category type strings
        """
        # Use provided categories or fetch from database
        if available_categories is not None:
            all_categories = available_categories
        else:
            all_categories = supabase_client.get_distinct_category_types(bot_id=self.bot_id)

        # Remove current category from options
        other_categories = [cat for cat in all_categories if cat != current_category]

        # Return random selection, up to the requested count
        # Handle case where we have fewer categories than requested
        if len(other_categories) == 0:
            return []
        
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

    def _balanced_content_selection(self, conversation_summary: str, content_items: List[ContentItem], latest_user_message: str = "") -> Optional[ContentItem]:
        """
        Implement balanced content selection with two-stage relevance scoring.
        
        Args:
            conversation_summary: Summary of the conversation
            content_items: List of all available content items
            latest_user_message: The most recent user message (takes priority)
            
        Returns:
            Selected ContentItem with balanced category representation
        """
        # Group content by category
        content_by_category = self._group_content_by_category(content_items)
        
        # Stage 1: Determine most relevant category with balanced weighting
        target_category = self._select_relevant_category(conversation_summary, content_by_category, latest_user_message)
        
        if not target_category or target_category not in content_by_category:
            # Fallback to random category if category selection fails
            target_category = random.choice(list(content_by_category.keys()))
            
        # Stage 2: Select best item within the chosen category
        category_items = content_by_category[target_category]
        selected_item = self._select_best_item_in_category(conversation_summary, category_items, target_category)
        
        return selected_item

    def _group_content_by_category(self, content_items: List[ContentItem]) -> Dict[str, List[ContentItem]]:
        """
        Group content items by category type.
        
        Args:
            content_items: List of content items
            
        Returns:
            Dictionary mapping category types to lists of content items
        """
        content_by_category = defaultdict(list)
        for item in content_items:
            content_by_category[item.category_type].append(item)
        return dict(content_by_category)

    def _select_relevant_category(self, conversation_summary: str, content_by_category: Dict[str, List[ContentItem]], latest_user_message: str = "") -> Optional[str]:
        """
        Select the most relevant category using LLM judge with bias correction.
        
        Args:
            conversation_summary: Summary of the conversation
            content_by_category: Dictionary mapping categories to content items
            latest_user_message: The most recent user message (takes priority)
            
        Returns:
            Selected category name, or None if selection fails
        """
        try:
            # use LLM to determine category relevance
            llm_selected_category = self._llm_category_selection(conversation_summary, content_by_category, latest_user_message)
            return llm_selected_category
        except Exception as e:
            logger.error(f"Error selecting relevant category: {e}")
            return None

    def _llm_category_selection(self, conversation_summary: str, content_by_category: Dict[str, List[ContentItem]], latest_user_message: str = "") -> Optional[str]:
        """
        Use LLM to determine the most relevant category based on conversation context.
        
        Args:
            conversation_summary: Summary of the conversation
            content_by_category: Dictionary mapping categories to content items
            latest_user_message: The most recent user message (takes priority)
            
        Returns:
            Selected category name, or None if selection fails
        """
        try:
            # Create category overview for LLM evaluation
            category_info = []
            for category, items in content_by_category.items():
                # Get sample titles and content descriptions
                sample_items = items[:3]  # First 3 items as samples
                item_descriptions = []
                
                for item in sample_items:
                    description = item.summary if (item.summary and item.summary.strip()) else item.content
                    item_descriptions.append(f"'{item.title}': {description}")
                
                count = len(items)
                category_info.append({
                    'category': category,
                    'count': count,
                    'sample_descriptions': item_descriptions
                })
            
            # Create system prompt for category selection
            system_prompt = """You are an expert judge for determining which content category is most relevant to a conversation.

Your task is to analyze the conversation context and determine which category of content would be most appropriate to share next.

IMPORTANT PRIORITY GUIDELINES:
1. The LATEST USER MESSAGE is the most important factor - it represents what the user is asking for RIGHT NOW
2. If the user's latest message shifts the conversation in a new direction, prioritize that over the conversation history
3. The conversation summary provides context, but the latest message shows current intent

Consider in this order:
1. What the user is specifically asking for or discussing in their latest message
2. What type of content would directly address their current question or interest
3. What would be most engaging and relevant given their immediate needs
4. The overall conversation direction (secondary consideration)

You will be given:
- The user's latest message (HIGHEST PRIORITY)
- A summary of the conversation so far (for context only)
- Available content categories with sample items

Choose the category that best responds to the user's current message and intent.

Respond with a JSON object containing:
- "selected_category": the name of the most relevant category
- "reasoning": brief explanation focusing on how this addresses the user's latest message"""

            # Create user prompt with conversation context and category options
            latest_message_text = f"User's latest message: {latest_user_message}" if latest_user_message.strip() else "No specific latest message provided"
            
            user_prompt = f"""{latest_message_text}

Conversation summary (for context): {conversation_summary}

Available content categories:
"""
            
            for cat_info in category_info:
                user_prompt += f"\n**{cat_info['category']}** ({cat_info['count']} items available):\n"
                for desc in cat_info['sample_descriptions']:
                    user_prompt += f"  - {desc}\n"
            
            user_prompt += f"""\nBased PRIMARILY on the user's latest message and secondarily on the conversation context, which category would be most relevant to share content from?

Remember: The user's latest message takes priority over conversation history. If their latest message indicates a new topic or direction, select the category that best addresses their current request."""
            
            # Define schema for structured response
            schema = {
                "type": "object",
                "properties": {
                    "selected_category": {
                        "type": "string",
                        "description": "The name of the most relevant category",
                        "enum": list(content_by_category.keys())
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Brief explanation of why this category is most relevant"
                    }
                },
                "required": ["selected_category", "reasoning"],
                "additionalProperties": False
            }
            
            # Get structured response from LLM
            response = llm_service.generate_structured_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=schema,
                operation_type="category_relevance_selection",
                bot_id=str(self.bot_id),
                chat_id=str(self.chat_id),
                conversation_number=self.conversation_number
            )
            
            selected_category = response["selected_category"]
            reasoning = response["reasoning"]
            
            logger.info(f"LLM selected category: {selected_category}")
            logger.info(f"LLM reasoning: {reasoning}")
            
            return selected_category
            
        except Exception as e:
            logger.error(f"Error in LLM category selection: {e}")
            return None

    def _select_best_item_in_category(self, conversation_summary: str, category_items: List[ContentItem], category: str) -> Optional[ContentItem]:
        """
        Select the best item within a specific category.
        
        Args:
            conversation_summary: Summary of the conversation
            category_items: List of items in the selected category
            category: Name of the category
            
        Returns:
            Selected ContentItem from the category
        """
        if not category_items:
            return None
            
        if len(category_items) == 1:
            return category_items[0]
            
        try:            
            # Use LLM to select best item within the category
            system_prompt = f"""You are an expert judge for selecting the most relevant content within a specific category.

Your task is to evaluate which content item from the '{category}' category is most relevant to the current conversation context.

CONTENT CONTEXT:
- This content is from the '{category}' category
- You are evaluating {len(category_items)} items from this category

Choose the most contextually appropriate item from the provided options.

Respond with just the content ID."""

            user_prompt = f"Conversation summary: {conversation_summary}\n\nAvailable {category} content:"
            
            for item in category_items:
                content_description = item.summary if (item.summary and item.summary.strip()) else item.content
                user_prompt += f"""\n\nContent ID: {item.id}
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
                operation_type="content_item_selection",
                bot_id=str(self.bot_id),
                chat_id=str(self.chat_id),
                conversation_number=self.conversation_number
            )

            content_id = response["content_id"]
            selected_item = next((item for item in category_items if item.id == content_id), None)
            
            if selected_item is None:
                logger.warning(f"LLM selected content ID {content_id} not found in category {category}")
                # Fallback to random selection within evaluated items
                return random.choice(category_items)
                
            return selected_item
            
        except Exception as e:
            logger.error(f"Error selecting best item in category {category}: {e}")
            return random.choice(category_items)
