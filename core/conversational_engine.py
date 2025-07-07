"""
Conversational Engine - Enhanced engine for sophisticated chat logic.
Implements conversation-focused state management with dynamic context tracking,
intelligent story repetition handling, and contextual awareness.
"""

import logging
from typing import Dict, List, Optional
import random
from core.llm_service import llm_service
from core.supabase_client import supabase_client
from core.conversation_manager import ConversationManager
from core.models import LLMMessage, ConversationResponse, StoryWithAnalysis, generate_telegram_chat_id, generate_terminal_chat_id
from core.content_retrieval_manager import ContentItem

logger = logging.getLogger(__name__)

class ConversationalEngine:
    """
    Multi-bot conversational engine with sophisticated state management.

    Implements conversation-focused state tracking, intelligent story repetition
    handling, and contextual awareness for natural dialogue flow across multiple bots.
    """

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

3. CATEGORY FOCUS EXAMPLES:
   - Stories: Personal experiences, memories, feelings
   - Daily Food Menu: Food knowledge, culinary experiences, taste preferences
   - Products: Product knowledge, brand values, coffee expertise
   - Catering: Service experience, event knowledge, hospitality insights

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
                return [
                    "What experiences shaped you most?",
                    "What matters most to you?",
                    "What would you like to share?"
                ]

            # Select one question from each available category randomly
            questions = []
            for category_type, question_list in grouped_questions.items():
                if question_list:  # Make sure the category has questions
                    selected_question = random.choice(question_list)
                    questions.append(selected_question.question)

            # If we have fewer than 3 questions, pad with available questions
            while len(questions) < 3 and any(grouped_questions.values()):
                for category_type, question_list in grouped_questions.items():
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
        Generate three follow-up questions using a dedicated LLM call with content categories.

        Args:
            user_message: The user's original message
            bot_response: The bot's response to the user
            conversation_summary: Summary of the conversation
            relevant_content: The current relevant content item
            warmth_guidance: Guidance for warmth-based questions
            conversation_history: Full conversation history for context

        Returns:
            List of exactly 3 follow-up questions
        """
        try:
            # TODO: REFACTOR - Should not retrieve content_retrieval_manager from conversation manager and run functions from there
            # Get summaries for other categories
            other_category_summaries = {}
            if relevant_content:
                # Get random categories for follow-up questions
                random_categories = conversation_manager.content_retrieval_manager.get_random_categories_for_follow_up(
                    relevant_content.category_type, count=2
                )
                for category in random_categories:
                    other_category_summaries[category] = conversation_manager.content_retrieval_manager.get_content_summaries_by_category(category)
            else:
                # If no relevant content, get summaries for all categories
                all_categories = ["stories", "daily_food_menu", "products", "catering"]
                for category in all_categories:
                    other_category_summaries[category] = conversation_manager.content_retrieval_manager.get_content_summaries_by_category(category)

            system_prompt = self._get_content_category_conversation_prompt(
                warmth_guidance, relevant_content, other_category_summaries, conversation_summary
            )

            # Build messages for LLM using conversation history instead of just current exchange
            user_message = f"""
USER MESSAGE: {user_message}
BOT RESPONSE: {bot_response}
            """
            messages = self.build_llm_messages(
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                user_message=user_message
            )
            # Add the bot's response as the final assistant message

            questions_schema = {
                "type": "object",
                "properties": {
                    "current_category_question": {
                        "type": "string",
                        "description": "Question focusing on current content category with deeper engagement"
                    },
                    "other_category_question_1": {
                        "type": "string",
                        "description": "Question focusing on a different content category"
                    },
                    "other_category_question_2": {
                        "type": "string",
                        "description": "Question focusing on another different content category"
                    }
                },
                "required": ["current_category_question", "other_category_question_1", "other_category_question_2"],
                "additionalProperties": False
            }

            questions_response = llm_service.generate_structured_response_from_llm_messages(
                messages=messages,
                schema=questions_schema,
                operation_type="follow_up_questions",
                bot_id=str(self.bot_id),
                chat_id=conversation_manager.chat_id,
                conversation_number=conversation_manager.conversation_number
            )

            # Construct the questions array for ongoing conversations
            return [
                questions_response.get("current_category_question", "Tell me more about this"),
                questions_response.get("other_category_question_1", "What about your other experiences?"),
                questions_response.get("other_category_question_2", "Tell me more")
            ]

        except Exception as e:
            logger.error(f"Error generating follow-up questions: {e}")
            # Return default questions if generation fails
            return [
                "Tell me more about this story?",
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

            system_prompt = f"""You are a digital twin with knowledge across multiple content areas.
Respond as if you are the person whose content was analyzed, maintaining their personality, communication style, and emotional patterns.
Use the conversation context to provide natural, contextually-aware responses that build on the ongoing dialogue.

You have knowledge about:
- Personal stories and experiences
- Daily food menu and culinary heritage
- Coffee products and brand values
- Catering services and hospitality

Ensure that you keep your response to the user's message brief and to the point. Focus on sharing relevant knowledge and personal insights.

CONVERSATION CONTEXT:
{conversation_manager.summary}

PERSONALITY PROFILE:
{self.bot_personality}

{content_context}
            """
            
            response = ""
            if user_message.strip().lower() == "click to discover our limited-time promotion":
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
                follow_up_questions[2] ="click to discover our limited-time promotion"

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