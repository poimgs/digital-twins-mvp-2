"""
Conversational Engine - Enhanced engine for sophisticated chat logic.
Implements conversation-focused state management with dynamic context tracking,
intelligent story repetition handling, and contextual awareness.
"""

import logging
import random
from enum import Enum
from typing import Dict, List, Optional, Any
from core.llm_service import llm_service
from core.supabase_client import supabase_client
from core.conversation_manager import ConversationManager
from core.models import LLMMessage, ConversationResponse, StoryWithAnalysis, generate_telegram_chat_id, generate_terminal_chat_id
from core.content_retrieval_manager import ContentItem

logger = logging.getLogger(__name__)


class CategoryStrategy(Enum):
    """Enum for different category-based question generation strategies."""
    STORIES_ONLY = "stories_only"
    LIMITED_CATEGORIES = "limited_categories"  # 2-3 categories
    MANY_CATEGORIES = "many_categories"  # 4+ categories


class ConversationalEngine:
    """
    Multi-bot conversational engine with sophisticated state management.

    Implements conversation-focused state tracking, intelligent story repetition
    handling, and contextual awareness for natural dialogue flow across multiple bots.
    """
    cta_prompt = "click to discover our limited-time promotion"

    def __init__(self, bot_id: str):
        """Initialize the conversational engine."""
        self.bot_id = bot_id
        self.conversations: Dict[str, ConversationManager] = {}  # chat_id -> ConversationManager
        self.bot_personality: str = self.get_bot_personality_summary()
        
        # Get bot call to action and keyword
        bot = supabase_client.get_bot_by_id(bot_id)
        if not bot:
            raise ValueError(f"Bot with ID {bot_id} not found")
        self.call_to_action = bot.call_to_action
        self.call_to_action_keyword = bot.call_to_action_keyword
        
        # Cache category information for efficient question generation
        self.available_categories = supabase_client.get_distinct_category_types(bot_id=self.bot_id)
        self.category_count = len(self.available_categories)
        self.category_strategy = self._determine_category_strategy()

    def _determine_category_strategy(self) -> CategoryStrategy:
        """Determine the appropriate category strategy based on available categories."""
        if self.category_count == 1 and self.available_categories == ["stories"]:
            return CategoryStrategy.STORIES_ONLY
        elif self.category_count <= 3:
            return CategoryStrategy.LIMITED_CATEGORIES
        else:
            return CategoryStrategy.MANY_CATEGORIES

    def get_bot_personality_summary(self) -> str:
        """Get or create personality summary for a bot."""
        personality_profile = supabase_client.get_personality_profile(self.bot_id)
        # Create a more structured and readable personality summary for the digital twin
        return f"""
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

    def _get_category_specific_system_prompt(self, relevant_content: Optional[ContentItem], conversation_manager, content_context: str) -> str:
        """
        Generate system prompt based on content category.
        Uses different prompts for 'stories' vs other categories.
        """
        # Check if we have relevant content and what category it is
        if relevant_content and relevant_content.category_type == "stories":
            # Use storytelling-focused prompt for stories category
            return f"""You are a digital twin.
Respond as if you are the person whose content was analyzed, maintaining their personality, communication style, and emotional patterns.
Use the conversation context to provide natural, contextually-aware responses that build on the ongoing dialogue.

Ensure that you keep your response to the user's message brief and to the point. Focus on sharing relevant knowledge and personal insights.

CONVERSATION CONTEXT:
{conversation_manager.summary}

PERSONALITY PROFILE:
{self.bot_personality}

{content_context}
            """
        else:
            # Use informational prompt for other categories (products, catering, daily_food_menu, etc.)
            return f"""You are a helpful digital assistant representing this business/service. Your role is to provide detailed, accurate information about our offerings and services.

COMMUNICATION STYLE:
- Be informative and professional yet warm
- Focus on practical details like pricing, ingredients, availability, and specifications
- Provide clear, actionable information
- Use bullet points and structured formatting when helpful
- Be concise but comprehensive

CONTENT FOCUS:
- Share specific details about products, menus, and services
- Include pricing, portions, ingredients, and availability when relevant
- Help users understand what we offer and how to access it
- Answer questions about specifications, customization options, and logistics

When users ask questions, prioritize sharing relevant content details over storytelling. Focus on being a knowledgeable resource about our offerings.

CONVERSATION CONTEXT:
{conversation_manager.summary}

{content_context}
            """

    def _get_category_specific_conversation_question_prompt(
        self,
        relevant_content: Optional[ContentItem],
        conversation_summary: str,
        relevant_content_prompt: str,
        warmth_guidance_prompt: str
    ) -> str:
        """
        Generate category-specific system prompt for conversation follow-up questions.
        """
        if relevant_content and relevant_content.category_type == "stories":
            # Stories category: Focus on personal experiences and emotional depth
            return f"""You are an expert at generating conversation-focused follow-up questions.

Your task is to generate exactly 1 follow-up question that builds naturally on the current dialogue exchange.

DIGITAL TWIN PERSONALITY PROFILE:
{self.bot_personality}

CONVERSATION SUMMARY:
{conversation_summary}

{relevant_content_prompt}

{warmth_guidance_prompt}

🚨 CRITICAL REQUIREMENTS FOR CONVERSATION-FOCUSED QUESTIONS:

1. FOCUS ON CURRENT DIALOGUE:
   - Build directly on what was just discussed in the user message and bot response
   - Help deepen the current conversation topic
   - Encourage the user to share more about their current interest

2. NATURAL CONVERSATION FLOW:
   - Should feel like a natural follow-up to what was just said
   - Focus on the digital twin's perspective on the current topic
   - Encourage deeper exploration of the current subject

3. ABOUT THE DIGITAL TWIN:
   - Always focus on the digital twin's experiences, feelings, and perspectives
   - Never ask about other people mentioned in the conversation
   - Ask about how things affected the digital twin

Generate 1 engaging question (up to 7 words) that naturally continues the current conversation."""
        else:
            # Other categories: Focus on practical information and service details
            return f"""You are an expert at generating conversation-focused follow-up questions for business/service content.

Your task is to generate exactly 1 follow-up question that builds naturally on the current dialogue exchange.

CONVERSATION SUMMARY:
{conversation_summary}

{relevant_content_prompt}

🚨 CRITICAL REQUIREMENTS FOR CONVERSATION-FOCUSED QUESTIONS:

1. FOCUS ON CURRENT DIALOGUE:
   - Build directly on what was just discussed in the user message and bot response
   - Help deepen understanding of the current topic
   - Encourage the user to learn more about the current subject

2. NATURAL CONVERSATION FLOW:
   - Should feel like a natural follow-up to what was just said
   - Focus on practical aspects of the topic being discussed
   - Encourage deeper exploration of details, options, or specifications

3. ABOUT THE OFFERINGS:
   - Focus on products, services, pricing, availability, or customization options
   - Ask about specific details that might interest the user
   - Help the user understand what's available and how to access it

Generate 1 engaging question (up to 7 words) that naturally continues the current conversation."""

    def _get_category_specific_category_questions_prompt(
        self,
        content_context: str,
        conversation_summary: str,
        other_category_summaries: dict
    ) -> str:
        """
        Generate category-specific system prompt for category exploration questions.
        """
        # Check if any of the categories are stories
        has_stories = any(category == "stories" for category in other_category_summaries.keys())
        
        if has_stories:
            # If stories category is present, use personality-focused approach
            return f"""You are an expert at generating category-exploration follow-up questions.

Your task is to generate exactly 2 follow-up questions that explore different content categories.

DIGITAL TWIN PERSONALITY PROFILE:
{self.bot_personality}

{content_context}

CONVERSATION SUMMARY:
{conversation_summary}

🚨 CRITICAL REQUIREMENTS FOR CATEGORY QUESTIONS:

1. EXPLORE DIFFERENT CATEGORIES:
   - Each question should focus on a different content category
   - Help the user discover new aspects of the digital twin's knowledge
   - Encourage exploration beyond the current conversation topic

2. ABOUT THE DIGITAL TWIN:
   - Always focus on the digital twin's experiences, knowledge, and perspectives
   - Never ask about other people
   - Ask about the digital twin's relationship to each category

Generate 2 engaging questions (up to 7 words each) that explore different categories."""
        else:
            # If no stories category, use service/business-focused approach
            return f"""You are an expert at generating category-exploration follow-up questions for business/service content.

Your task is to generate exactly 2 follow-up questions that explore different content categories.

{content_context}

CONVERSATION SUMMARY:
{conversation_summary}

🚨 CRITICAL REQUIREMENTS FOR CATEGORY QUESTIONS:

1. EXPLORE DIFFERENT CATEGORIES:
   - Each question should focus on a different content category
   - Help the user discover new aspects of what we offer
   - Encourage exploration beyond the current conversation topic

2. ABOUT THE OFFERINGS:
   - Focus on products, services, pricing, availability, or features
   - Ask about specific details that might interest the user
   - Help the user understand what's available and how to access it
   - Encourage questions about customization, ordering, or specifications

Generate 2 engaging questions (up to 7 words each) that explore different categories."""

    def get_or_create_conversation_manager(self, chat_id: str, bot_id: str) -> ConversationManager:
        """Get or create conversation manager for a chat."""
        if chat_id not in self.conversations:
            self.conversations[chat_id] = ConversationManager(chat_id, bot_id)
        return self.conversations[chat_id]

    def build_llm_messages(
        self,
        system_prompt: str,
        conversation_history: List[LLMMessage],
        user_message: str
    ) -> List[LLMMessage]:
        """
        Build a complete conversation message list using LLMMessage objects.

        Args:
            system_prompt: Optional system prompt to start the conversation
            conversation_history: Optional list of previous LLMMessage objects
            user_message: Optional new user message to append

        Returns:
            Complete list of LLMMessage objects
        """
        messages = []
        messages.append(LLMMessage("system", system_prompt))
        messages.extend(conversation_history)
        messages.append(LLMMessage("user", user_message))

        return messages

    def _get_initial_conversation_prompt(self) -> str:
        """
        Generate system prompt for initial conversations with broad, exploratory questions.
        """
        return f"""You are an expert at generating follow-up questions for the user to ask the digital twin.

Your task is to generate exactly 3 BROAD and EXPLORATORY follow-up questions for an initial conversation.

DIGITAL TWIN PERSONALITY PROFILE:
{self.bot_personality}

🚨 CRITICAL REQUIREMENTS FOR INITIAL CONVERSATIONS:

1. ALL QUESTIONS MUST BE ABOUT THE DIGITAL TWIN:
   - Never ask about other people mentioned in stories
   - Always focus on the digital twin's experiences, feelings, and perspectives

2. QUESTIONS MUST BE BROAD AND WELCOMING:
   - Use general, open-ended questions
   - Help the user discover what they want to explore
   - Avoid overly specific details
   - Focus on general topics and experiences
   - Keep questions welcoming and exploratory

Generate 3 broad questions following this strategy:

1. GENERAL EXPERIENCE QUESTION: Ask about a broad area of the digital twin's life or experiences
   - Should be open-ended and exploratory
   - Help the user discover interesting topics
   - Example: "What experiences shaped you most?"

2. PERSONALITY/VALUES QUESTION: Ask about the digital twin's personality, values, or perspectives
   - Should be broad and inviting
   - Help understand the digital twin as a person
   - Example: "What matters most to you?"

3. OPEN EXPLORATION QUESTION: Your choice that invites broad exploration
   - Should be engaging and open-ended
   - Help the user feel comfortable exploring
   - Example: "What would you like to share?"

Each question should be up to 7 words long and welcoming."""

    def _get_ongoing_conversation_prompt(
        self,
        warmth_guidance: str,
        relevant_story: Optional[StoryWithAnalysis],
        other_story_summaries: str,
        conversation_summary: str
    ) -> str:
        """
        Generate system prompt for ongoing conversations with specific, contextual questions.
        """
        
        # Create story context
        if relevant_story:
            story_context = f"""
CURRENT RELEVANT STORY:
{relevant_story.content}

OTHER AVAILABLE STORIES:
{other_story_summaries if other_story_summaries else "No other stories available"}
"""
        else:
            story_context = f"""
OTHER AVAILABLE STORIES:
{other_story_summaries if other_story_summaries else "No other stories available"}             
"""
        

        return f"""You are an expert at generating follow-up questions for the user to ask the digital twin.

Your task is to generate exactly 3 follow-up questions based on the established conversation context.

DIGITAL TWIN PERSONALITY PROFILE:
{self.bot_personality}

WARMTH GUIDANCE FOR CURRENT STORY QUESTIONS:
{warmth_guidance}

{story_context}

CONVERSATION SUMMARY:
{conversation_summary}

🚨 CRITICAL REQUIREMENTS FOR ONGOING CONVERSATIONS:

1. ALL QUESTIONS MUST BE ABOUT THE DIGITAL TWIN:
   - Never ask about other people mentioned in stories
   - Always focus on the digital twin's experiences, feelings, and perspectives
   - If a story mentions other people, ask about how the digital twin felt or what they learned
   - Example: Instead of "What did your friend think?" ask "How did that experience affect you?"

2. QUESTIONS CAN BE SPECIFIC AND DETAILED:
   - Build on established conversation context
   - Dive deeper into topics already discussed
   - Use specific details from the conversation

Generate 3 questions following this strategy:

1. CURRENT STORY QUESTION: 🚨 MANDATORY PROGRESSION - You MUST move UP the question ladder!
   - REQUIRED: Follow the EXACT structure specified in the warmth guidance above
   - The warmth guidance tells you the REQUIRED next level - you MUST use that structure
   - Focus on the current relevant story about the DIGITAL TWIN
   - This question MUST progress to the next warmth level - NO EXCEPTIONS
   - MUST be about the digital twin, not other people in the story

2. OTHER STORY QUESTION: Ask about exploring a different story from the available stories
   - Can use any appropriate question structure
   - Should nudge toward exploring different experiences of the DIGITAL TWIN
   - MUST be about the digital twin's experiences

3. LLM CHOICE QUESTION: Your choice that fits conversation flow and personality
   - Can use any appropriate question structure
   - Should be engaging and relevant to the DIGITAL TWIN
   - MUST be about the digital twin

Each question should be up to 7 words long and engaging.

🚨 CRITICAL REQUIREMENT FOR QUESTION #1:
- The warmth guidance above specifies the EXACT question structure you MUST use
- You MUST progress up the ladder - if current level is "can", you MUST ask "will" questions
- If current level is "will", you MUST ask "would" questions, etc.
- NO EXCEPTIONS - the first question MUST move to the next warmth level
- Failure to follow this progression breaks the conversation flow"""

    def _get_content_category_conversation_prompt(
        self,
        warmth_guidance: str,
        relevant_content: Optional[ContentItem],
        other_category_summaries: Dict[str, str],
        conversation_summary: str
    ) -> str:
        """
        Generate system prompt for conversations with content categories.
        """

        # Create content context
        if relevant_content:
            content_context = f"""
CURRENT RELEVANT CONTENT ({relevant_content.category_type.upper()}):
{relevant_content.content}

OTHER AVAILABLE CATEGORIES:
"""
            for category_type, summaries in other_category_summaries.items():
                if category_type != relevant_content.category_type:
                    content_context += f"\n{category_type.upper()}:\n{summaries}\n"
        else:
            content_context = """
OTHER AVAILABLE CATEGORIES:
"""
            for category_type, summaries in other_category_summaries.items():
                content_context += f"\n{category_type.upper()}:\n{summaries}\n"

        return f"""You are an expert at generating follow-up questions for the user to ask the digital twin.

Your task is to generate exactly 3 follow-up questions based on content categories.

DIGITAL TWIN PERSONALITY PROFILE:
{self.bot_personality}

WARMTH GUIDANCE FOR CURRENT CATEGORY QUESTIONS:
{warmth_guidance}

{content_context}

CONVERSATION SUMMARY:
{conversation_summary}

🚨 CRITICAL REQUIREMENTS FOR CONTENT CATEGORY CONVERSATIONS:

1. ALL QUESTIONS MUST BE ABOUT THE DIGITAL TWIN:
   - Never ask about other people mentioned in content
   - Always focus on the digital twin's experiences, knowledge, and perspectives
   - If content mentions other people, ask about how the digital twin relates to it

2. QUESTION STRUCTURE:
   - 1st question: Focus on the CURRENT CATEGORY using warmth guidance
   - 2nd question: Focus on a DIFFERENT CATEGORY from available categories
   - 3rd question: Focus on another DIFFERENT CATEGORY from available categories

Each question should be up to 7 words long and engaging.

- For the 1st question: {warmth_guidance}
- For 2nd and 3rd questions: Use any appropriate question structure that fits the category"""

    # Get initial category questions and save into database
    # This is so that the telegram bot can use this function to get initial category questions, and ensure that when user clicks on one, the correct question is picked up
    def get_initial_category_questions(self, bot_id: str, chat_id: Optional[str] = None, telegram_chat_id: Optional[int] = None) -> List[str]:
        """
        Get initial category questions and save them into database.
        """
        initial_questions = self._get_initial_category_questions()
        
        # Determine chat_id based on input
        if chat_id:
            final_chat_id = chat_id
        elif telegram_chat_id is not None:
            final_chat_id = generate_telegram_chat_id(bot_id, telegram_chat_id)
        else:
            final_chat_id = generate_terminal_chat_id(bot_id)

        conversation_manager = self.get_or_create_conversation_manager(final_chat_id, bot_id)
        conversation_manager.store_follow_up_questions(initial_questions)
            
        return initial_questions

    def _get_initial_category_questions(self) -> List[str]:
        """
        Get initial questions from database based on content categories.
        Returns 3 questions, each focusing on a different category.
        """
        import random

        try:
            # Get all initial questions for this bot grouped by category
            grouped_questions = supabase_client.get_initial_questions_by_bot(self.bot_id)

            if not grouped_questions:
                # Fallback to default questions if none found in database
                logger.warning(f"No initial questions found for bot {self.bot_id}, using defaults")
                return ["Tell me more about yourself"]

            # Select one question from each available category randomly
            questions = []
            for _, question_list in grouped_questions.items():
                if question_list:  # Make sure the category has questions
                    selected_question = random.choice(question_list)
                    questions.append(selected_question.question)

            # If we have fewer than 3 questions, pad with available questions
            while len(questions) < 3 and any(grouped_questions.values()):
                for _, question_list in grouped_questions.items():
                    if len(questions) >= 3:
                        break
                    if question_list:
                        # Pick a random question that we haven't used yet
                        available_questions = [q.question for q in question_list if q.question not in questions]
                        if available_questions:
                            questions.append(random.choice(available_questions))

            # Shuffle the order of questions so they don't always appear in the same sequence
            random.shuffle(questions)

            # Ensure we return exactly 3 questions
            return questions[:3] if len(questions) >= 3 else questions

        except Exception as e:
            logger.error(f"Error retrieving initial questions from database: {e}")
            # Fallback to default questions
            return [
                "What experiences shaped you most?",
                "What matters most to you?",
                "What would you like to share?"
            ]

    def _generate_conversation_question(
        self,
        user_message: str,
        bot_response: str,
        relevant_content: Optional[ContentItem],
        warmth_guidance: str,
        conversation_summary: str,
        conversation_history: List[LLMMessage],
        conversation_manager
    ) -> str:
        """
        Generate a single conversation-focused follow-up question based on current dialogue context.

        Args:
            user_message: The user's original message
            bot_response: The bot's response to the user
            conversation_summary: Summary of the conversation
            conversation_history: Full conversation history for context
            conversation_manager: Conversation manager instance

        Returns:
            A single conversation-focused follow-up question
        """
        relevant_content_prompt = ""
        if relevant_content:
            relevant_content_prompt = f"""
RELEVANT CONTENT ({relevant_content.category_type.upper()}):
{relevant_content.content}
"""

        warmth_guidance_prompt = f"""
WARMTH GUIDANCE FOR CURRENT CONVERSATION QUESTION:
{warmth_guidance}
"""

        try:
            system_prompt = self._get_category_specific_conversation_question_prompt(
                relevant_content=relevant_content,
                conversation_summary=conversation_summary,
                relevant_content_prompt=relevant_content_prompt,
                warmth_guidance_prompt=warmth_guidance_prompt
            )

            user_message_context = f"""
USER MESSAGE: {user_message}
BOT RESPONSE: {bot_response}
            """
            
            messages = self.build_llm_messages(
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                user_message=user_message_context
            )

            conversation_question_schema = {
                "type": "object",
                "properties": {
                    "conversation_question": {
                        "type": "string",
                        "description": "A follow-up question that builds naturally on the current dialogue"
                    }
                },
                "required": ["conversation_question"],
                "additionalProperties": False
            }

            response = llm_service.generate_structured_response_from_llm_messages(
                messages=messages,
                schema=conversation_question_schema,
                operation_type="conversation_follow_up",
                bot_id=str(self.bot_id),
                chat_id=conversation_manager.chat_id,
                conversation_number=conversation_manager.conversation_number
            )

            return response.get("conversation_question", "Tell me more about that")

        except Exception as e:
            logger.error(f"Error generating conversation question: {e}")
            return "Tell me more about that"

    def _build_category_summaries(self, categories: List[str], conversation_manager) -> Dict[str, str]:
        """Build category summaries for the given categories."""
        category_summaries = {}
        for category in categories:
            category_summaries[category] = conversation_manager.content_retrieval_manager.get_content_summaries_by_category(category)
        return category_summaries

    def _get_question_schema(self) -> Dict[str, Any]:
        """Get the standard schema for category questions."""
        return {
            "type": "object",
            "properties": {
                "category_question_1": {
                    "type": "string",
                    "description": "Question focusing on first content category"
                },
                "category_question_2": {
                    "type": "string",
                    "description": "Question focusing on second content category"
                }
            },
            "required": ["category_question_1", "category_question_2"],
            "additionalProperties": False
        }

    def _generate_category_questions_with_llm(
        self,
        system_prompt: str,
        conversation_history: List[LLMMessage],
        conversation_manager,
        operation_type: str = "category_follow_up"
    ) -> List[str]:
        """Generate category questions using LLM with common logic."""
        try:
            messages = self.build_llm_messages(
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                user_message="Generate category exploration questions based on available content."
            )

            response = llm_service.generate_structured_response_from_llm_messages(
                messages=messages,
                schema=self._get_question_schema(),
                operation_type=operation_type,
                bot_id=str(self.bot_id),
                chat_id=conversation_manager.chat_id,
                conversation_number=conversation_manager.conversation_number
            )

            return [
                response.get("category_question_1", "What about your experiences?"),
                response.get("category_question_2", "Tell me about your knowledge")
            ]

        except Exception as e:
            logger.error(f"Error generating category questions with LLM: {e}")
            return [
                "What about your experiences?",
                "Tell me about your knowledge"
            ]

    def _generate_stories_only_questions(
        self,
        conversation_summary: str,
        conversation_history: List[LLMMessage],
        conversation_manager
    ) -> List[str]:
        """
        Generate follow-up questions for digital twins with only stories category.
        Focuses on different aspects of storytelling and personal experiences.
        """
        try:
            system_prompt = f"""You are an expert at generating story-focused follow-up questions.

Your task is to generate exactly 2 follow-up questions that explore different aspects of the digital twin's stories and experiences.

DIGITAL TWIN PERSONALITY PROFILE:
{self.bot_personality}

CONVERSATION SUMMARY:
{conversation_summary}

🚨 CRITICAL REQUIREMENTS FOR STORIES-ONLY QUESTIONS:

1. EXPLORE DIFFERENT STORY ASPECTS:
   - Focus on different themes, emotions, or life experiences
   - Help the user discover varied aspects of the digital twin's journey
   - Encourage exploration of different story elements

2. ABOUT THE DIGITAL TWIN:
   - Always focus on the digital twin's experiences, feelings, and perspectives
   - Never ask about other people mentioned in stories
   - Ask about personal growth, lessons learned, or emotional responses

3. STORY EXPLORATION STRATEGIES:
   - Ask about themes (resilience, relationships, growth, challenges)
   - Ask about emotional aspects (feelings, reactions, transformations)
   - Ask about life lessons or insights gained
   - Ask about different time periods or life stages

Generate 2 engaging questions (up to 7 words each) that explore different aspects of the digital twin's stories."""

            messages = self.build_llm_messages(
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                user_message="Generate story-focused exploration questions for a stories-only digital twin."
            )

            stories_questions_schema = {
                "type": "object",
                "properties": {
                    "story_question_1": {
                        "type": "string",
                        "description": "Question focusing on first story aspect or theme"
                    },
                    "story_question_2": {
                        "type": "string",
                        "description": "Question focusing on second story aspect or theme"
                    }
                },
                "required": ["story_question_1", "story_question_2"],
                "additionalProperties": False
            }

            response = llm_service.generate_structured_response_from_llm_messages(
                messages=messages,
                schema=stories_questions_schema,
                operation_type="stories_only_follow_up",
                bot_id=str(self.bot_id),
                chat_id=conversation_manager.chat_id,
                conversation_number=conversation_manager.conversation_number
            )

            return [
                response.get("story_question_1", "What experiences shaped you most?"),
                response.get("story_question_2", "How did challenges change you?")
            ]

        except Exception as e:
            logger.error(f"Error generating stories-only questions: {e}")
            return [
                "What experiences shaped you most?",
                "How did challenges change you?"
            ]

    def _generate_limited_categories_questions(
        self,
        conversation_summary: str,
        conversation_history: List[LLMMessage],
        conversation_manager
    ) -> List[str]:
        """
        Generate follow-up questions for digital twins with limited categories (2-3).
        Uses all available categories for exploration.
        """
        category_summaries = self._build_category_summaries(self.available_categories, conversation_manager)
        
        # Create content context for categories
        content_context = "AVAILABLE CATEGORIES FOR EXPLORATION:\n"
        for category_type, summaries in category_summaries.items():
            content_context += f"\n{category_type.upper()}:\n{summaries}\n"

        system_prompt = self._get_category_specific_category_questions_prompt(
            content_context=content_context,
            conversation_summary=conversation_summary,
            other_category_summaries=category_summaries
        )

        return self._generate_category_questions_with_llm(
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            conversation_manager=conversation_manager,
            operation_type="limited_category_follow_up"
        )

    def _generate_many_categories_questions(
        self,
        conversation_summary: str,
        relevant_content: Optional[ContentItem],
        conversation_history: List[LLMMessage],
        conversation_manager
    ) -> List[str]:
        """
        Generate follow-up questions for digital twins with many categories (4+).
        Randomly selects 2 categories for exploration.
        """
        # Get random categories for follow-up questions
        if relevant_content:
            random_categories = conversation_manager.content_retrieval_manager.get_random_categories_for_follow_up(
                relevant_content.category_type, count=2, available_categories=self.available_categories
            )
        else:
            # If no relevant content, randomly select 2 categories from available categories
            random_categories = random.sample(self.available_categories, min(2, len(self.available_categories)))

        category_summaries = self._build_category_summaries(random_categories, conversation_manager)

        # Create content context for categories
        content_context = "AVAILABLE CATEGORIES FOR EXPLORATION:\n"
        for category_type, summaries in category_summaries.items():
            content_context += f"\n{category_type.upper()}:\n{summaries}\n"

        system_prompt = self._get_category_specific_category_questions_prompt(
            content_context=content_context,
            conversation_summary=conversation_summary,
            other_category_summaries=category_summaries
        )

        return self._generate_category_questions_with_llm(
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            conversation_manager=conversation_manager,
            operation_type="category_follow_up"
        )

    def _generate_category_questions(
        self,
        conversation_summary: str,
        relevant_content: Optional[ContentItem],
        conversation_history: List[LLMMessage],
        conversation_manager
    ) -> List[str]:
        """
        Generate two category-based follow-up questions from different content categories.
        Uses cached category information to handle different scenarios efficiently.

        Args:
            conversation_summary: Summary of the conversation
            relevant_content: The current relevant content item
            conversation_history: Full conversation history for context
            conversation_manager: Conversation manager instance

        Returns:
            List of 2 category-based follow-up questions
        """
        try:
            # Route to appropriate strategy based on category scenario
            if self.category_strategy == CategoryStrategy.STORIES_ONLY:
                return self._generate_stories_only_questions(
                    conversation_summary=conversation_summary,
                    conversation_history=conversation_history,
                    conversation_manager=conversation_manager
                )
            elif self.category_strategy == CategoryStrategy.LIMITED_CATEGORIES:
                return self._generate_limited_categories_questions(
                    conversation_summary=conversation_summary,
                    conversation_history=conversation_history,
                    conversation_manager=conversation_manager
                )
            else:  # MANY_CATEGORIES
                return self._generate_many_categories_questions(
                    conversation_summary=conversation_summary,
                    relevant_content=relevant_content,
                    conversation_history=conversation_history,
                    conversation_manager=conversation_manager
                )

        except Exception as e:
            logger.error(f"Error generating category questions: {e}")
            # Return appropriate fallback questions based on category scenario
            if self.category_strategy == CategoryStrategy.STORIES_ONLY:
                return [
                    "What experiences shaped you most?",
                    "How did challenges change you?"
                ]
            else:
                return [
                    "What about your other experiences?",
                    "Tell me about your knowledge"
                ]

    def _generate_follow_up_questions(
        self,
        user_message: str,
        bot_response: str,
        conversation_summary: str,
        relevant_content: Optional[ContentItem],
        warmth_guidance: str,
        conversation_history: List[LLMMessage],
        conversation_manager
    ) -> List[str]:
        """
        Generate three follow-up questions using separate conversation and category-focused approaches.

        Args:
            user_message: The user's original message
            bot_response: The bot's response to the user
            conversation_summary: Summary of the conversation
            relevant_content: The current relevant content item
            warmth_guidance: Guidance for warmth-based questions (deprecated in favor of conversation flow)
            conversation_history: Full conversation history for context
            conversation_manager: Conversation manager instance

        Returns:
            List of exactly 3 follow-up questions:
            - Question 1: Conversation-focused (based on current dialogue)
            - Questions 2-3: Category-focused (based on different content categories)
        """
        try:
            # Generate conversation-focused question (Question 1)
            conversation_question = self._generate_conversation_question(
                user_message=user_message,
                bot_response=bot_response,
                relevant_content=relevant_content,
                warmth_guidance=warmth_guidance,
                conversation_summary=conversation_summary,
                conversation_history=conversation_history,
                conversation_manager=conversation_manager
            )

            # Generate category-focused questions (Questions 2-3)
            category_questions = self._generate_category_questions(
                conversation_summary=conversation_summary,
                relevant_content=relevant_content,
                conversation_history=conversation_history,
                conversation_manager=conversation_manager
            )

            # Combine questions: 1 conversation + 2 category
            return [conversation_question] + category_questions

        except Exception as e:
            logger.error(f"Error generating follow-up questions: {e}")
            # Return default questions if generation fails
            return [
                "Tell me more about that",
                "What about your other experiences?",
                "How did that make you feel?"
            ]

    def generate_response(self, user_message: str, bot_id: str, chat_id: Optional[str] = None, telegram_chat_id: Optional[int] = None) -> ConversationResponse:
        """
        Generate a response to a user message for a specific bot

        Args:
            user_message: The user's message
            bot_id: Bot identifier
            chat_id: Direct chat_id (if provided, takes precedence)
            telegram_chat_id: Telegram chat ID (for Telegram bots)

        Returns:
            ConversationResponse containing response and conversation metadata
        """
        try:
            # Determine chat_id based on input
            if chat_id:
                final_chat_id = chat_id
            elif telegram_chat_id is not None:
                final_chat_id = generate_telegram_chat_id(bot_id, telegram_chat_id)
            else:
                final_chat_id = generate_terminal_chat_id(bot_id)

            conversation_manager = self.get_or_create_conversation_manager(final_chat_id, bot_id)
            conversation_manager.add_user_message(user_message)

            # Get relevant content from all categories
            relevant_content = conversation_manager.find_relevant_content()
            conversation_history = conversation_manager.get_conversation_history_for_llm()

            # Get guidance for question warmth level
            warmth_guidance = conversation_manager.get_next_question_guidance()

            # content context
            if relevant_content:
                content_context = f"""
RELEVANT CONTENT ({relevant_content.category_type.upper()}):
{relevant_content.content}
"""
            else:
                content_context = """
No specific content selected for this conversation.
"""

            # Generate category-specific system prompt
            system_prompt = self._get_category_specific_system_prompt(
                relevant_content=relevant_content,
                conversation_manager=conversation_manager,
                content_context=content_context
            )
            
            response = ""
            if user_message == self.cta_prompt:
                response = self.call_to_action
            else:  
                messages = self.build_llm_messages(
                    system_prompt=system_prompt,
                    conversation_history=conversation_history,
                    user_message=user_message
                )
                response = llm_service.generate_completion_from_llm_messages(
                    messages,
                    operation_type="conversation",
                    bot_id=str(self.bot_id),
                    chat_id=conversation_manager.chat_id,
                    conversation_number=conversation_manager.conversation_number
                )

            # Second LLM: Generate follow-up questions based on the response and content categories
            follow_up_questions = self._generate_follow_up_questions(
                user_message=user_message,
                bot_response=response,
                conversation_summary=conversation_manager.summary,
                relevant_content=relevant_content,
                warmth_guidance=warmth_guidance,
                conversation_history=conversation_history,
                conversation_manager=conversation_manager
            )
            
            if conversation_manager.ready_for_call_to_action():
                follow_up_questions[2] = self.cta_prompt

            conversation_response = ConversationResponse(response, follow_up_questions)

            conversation_manager.add_assistant_message(conversation_response.response)
            conversation_manager.summarize_conversation(user_message, conversation_response.response)
            conversation_manager.store_follow_up_questions(follow_up_questions)

            # Return comprehensive response data
            return conversation_response

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return ConversationResponse("I'm sorry, I'm having trouble responding right now. Could you try again?", [])

    def reset_conversation(self, bot_id: str, chat_id: Optional[str] = None, telegram_chat_id: Optional[int] = None) -> bool:
        """
        Reset the conversation state for a chat.

        Args:
            bot_id: Bot identifier
            chat_id: Direct chat_id (if provided, takes precedence)
            telegram_chat_id: Telegram chat ID (for Telegram bots)

        Returns:
            True if reset was successful
        """
        try:
            # Determine chat_id based on input
            if chat_id:
                final_chat_id = chat_id
            elif telegram_chat_id is not None:
                final_chat_id = generate_telegram_chat_id(bot_id, telegram_chat_id)

            conversation_manager = self.get_or_create_conversation_manager(final_chat_id, bot_id)
            if final_chat_id in self.conversations:
                del self.conversations[final_chat_id]
            logger.info(f"Reset conversation state for chat {final_chat_id}")
            conversation_manager.reset_conversation()
            return True
        except Exception as e:
            logger.error(f"Error resetting conversation: {e}")
            return False