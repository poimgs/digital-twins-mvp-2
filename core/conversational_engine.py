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
from core.story_retrieval_manager import StoryRetrievalManager
from core.models import LLMMessage, ConversationResponse, StoryWithAnalysis, generate_telegram_chat_id, generate_terminal_chat_id

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
        self.story_retrieval_manager = StoryRetrievalManager()
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

    def _generate_follow_up_questions(
        self,
        user_message: str,
        bot_response: str,
        conversation_summary: str,
        relevant_story: Optional[StoryWithAnalysis],
        other_story_summaries: str,
        warmth_guidance: str
    ) -> List[str]:
        """
        Generate three follow-up questions using a dedicated LLM call.

        Args:
            user_message: The user's original message
            bot_response: The bot's response to the user
            conversation_summary: Summary of the conversation
            relevant_story: The current relevant story
            other_story_summaries: Summaries of other available stories
            warmth_guidance: Guidance for warmth-based questions

        Returns:
            List of exactly 3 follow-up questions
        """
        try:
            system_prompt = f"""You are an expert at generating follow-up questions for the user to ask the digital twin.

Your task is to generate exactly 3 follow-up questions based on the conversation context.

DIGITAL TWIN PERSONALITY PROFILE:
{self.bot_personality}

WARMTH GUIDANCE FOR CURRENT STORY QUESTIONS:
{warmth_guidance}

CURRENT RELEVANT STORY:
{relevant_story.summary if relevant_story else 'No relevant story found'}

OTHER AVAILABLE STORIES:
{other_story_summaries if other_story_summaries else "No other stories available"}

CONVERSATION SUMMARY:
{conversation_summary}

Generate 3 questions following this strategy:

1. CURRENT STORY QUESTION: 🚨 MANDATORY PROGRESSION - You MUST move UP the question ladder!
   - REQUIRED: Follow the EXACT structure specified in the warmth guidance above
   - The warmth guidance tells you the REQUIRED next level - you MUST use that structure
   - Focus on the current relevant story
   - This question MUST progress to the next warmth level - NO EXCEPTIONS

2. OTHER STORY QUESTION: Ask about exploring a different story from the available stories
   - Can use any appropriate question structure
   - Should nudge toward exploring different experiences

3. LLM CHOICE QUESTION: Your choice that fits conversation flow and personality
   - Can use any appropriate question structure
   - Should be engaging and relevant

Each question should be up to 7 words long and engaging.

🚨 CRITICAL REQUIREMENT FOR QUESTION #1:
- The warmth guidance above specifies the EXACT question structure you MUST use
- You MUST progress up the ladder - if current level is "can", you MUST ask "will" questions
- If current level is "will", you MUST ask "would" questions, etc.
- NO EXCEPTIONS - the first question MUST move to the next warmth level
- Failure to follow this progression breaks the conversation flow"""

            user_prompt = f"""Conversation exchange: 
User: {user_message}
Bot: {bot_response}
"""

            # Schema for the follow-up questions
            questions_schema = {
                "type": "object",
                "properties": {
                    "current_story_question": {
                        "type": "string",
                        "description": "Question focusing on current story with deeper engagement"
                    },
                    "other_story_question": {
                        "type": "string",
                        "description": "Question nudging toward a different story"
                    },
                    "llm_choice_question": {
                        "type": "string",
                        "description": "Any engaging question fitting conversation flow"
                    }
                },
                "required": ["current_story_question", "other_story_question", "llm_choice_question"],
                "additionalProperties": False
            }

            questions_response = llm_service.generate_structured_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=questions_schema
            )

            # Construct the questions array
            follow_up_questions = [
                questions_response.get("current_story_question", "Tell me more about this story?"),
                questions_response.get("other_story_question", "What about your other experiences?"),
                questions_response.get("llm_choice_question", "How did that make you feel?")
            ]

            return follow_up_questions

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

            # Check if call to action has already been shown - if so, end conversation
            if conversation_manager.call_to_action_shown:
                reset_message = ("Thank you for our conversation! I've shared what I wanted to share with you. "
                               "If you'd like to start a new conversation, please use the reset command (/reset)")
                return ConversationResponse(reset_message, [])

            conversation_manager.add_user_message(user_message)

            # Get bot-specific stories
            stories = supabase_client.get_stories_with_analysis(bot_id)
            relevant_story = conversation_manager.find_relevant_story(stories)
            conversation_history = conversation_manager.get_conversation_history_for_llm()

            # Get guidance for question warmth level
            warmth_guidance = conversation_manager.get_next_question_guidance()

            # Prepare call to action context based on warmth level
            cta_context = ""
            if not conversation_manager.call_to_action_shown and conversation_manager.ready_for_call_to_action():
                cta_context = f"""
CALL TO ACTION GUIDANCE - MANDATORY:

You MUST incorporate this call to action into your response and end the conversation:
{self.call_to_action}

IMPORTANT REQUIREMENTS:
- Include the call to action naturally in your response
- Make it clear this is the end of our conversation
- Express gratitude for the engaging dialogue
- Do NOT ask follow-up questions or invite further conversation
- End with a sense of closure and completion

The user has demonstrated deep engagement and is ready for the next step. This is your opportunity to share what you wanted to share and gracefully conclude our interaction."""

            system_prompt = f"""You are a digital twin created from personal stories and experiences.
Respond as if you are the person whose stories were analyzed, maintaining their personality, communication style, and emotional patterns.
Use the conversation context to provide natural, contextually-aware responses that build on the ongoing dialogue.

Ensure that you keep your response to the user's message brief and to the point. Focus on sharing stories and personal insights.

If the conversation is moving away from stories and experiences, guide the conversation back to share stories and insights.
Do not deviate away from personal stories and experiences.

{cta_context}

CONVERSATION CONTEXT:
{conversation_manager.summary}

PERSONALITY PROFILE:
{self.bot_personality}
            """
            
            messages = self.build_llm_messages(
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                user_message=user_message
            )
            response = llm_service.generate_completion_from_llm_messages(messages)

            # Second LLM: Generate follow-up questions based on the response and context
            other_stories = [story for story in stories if story != relevant_story] if relevant_story else stories
            other_story_summaries = ""
            if other_stories:
                # Randomly select up to 3 other stories for variety
                selected_stories = random.sample(other_stories, min(3, len(other_stories)))
                for story in selected_stories:
                    other_story_summaries += f"- {story.summary}\n"
                    
            follow_up_questions = self._generate_follow_up_questions(
                user_message=user_message,
                bot_response=response,
                conversation_summary=conversation_manager.summary,
                relevant_story=relevant_story,
                other_story_summaries=other_story_summaries,
                warmth_guidance=warmth_guidance
            )

            # Check if the LLM naturally included the call to action in the response
            # If so, mark it as shown to prevent future prompting
            cta_detected = False
            if not conversation_manager.call_to_action_shown:
                response_lower = response.lower()
                cta_mentioned = False

                # Check if the specific keyword is mentioned in the response
                cta_mentioned = self.call_to_action_keyword.lower() in response_lower
                logger.info(f"Checking for CTA keyword '{self.call_to_action_keyword}' in response: {cta_mentioned}")

                if cta_mentioned:
                    try:
                        supabase_client.update_conversation_state(
                            chat_id=final_chat_id,
                            call_to_action_shown=True
                        )
                        conversation_manager.call_to_action_shown = True
                        cta_detected = True
                        logger.info(f"CTA detected in response and marked as shown")
                    except Exception as e:
                        logger.error(f"Error updating call_to_action_shown state: {e}")

            # If call to action was just detected, don't provide follow-up questions
            # as this marks the end of the conversation
            final_follow_up_questions = [] if cta_detected else follow_up_questions
            conversation_response = ConversationResponse(response, final_follow_up_questions)

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
            else:
                final_chat_id = generate_terminal_chat_id(bot_id)

            conversation_manager = self.get_or_create_conversation_manager(final_chat_id, bot_id)
            if final_chat_id in self.conversations:
                del self.conversations[final_chat_id]
            logger.info(f"Reset conversation state for chat {final_chat_id}")
            conversation_manager.reset_conversation()
            return True
        except Exception as e:
            logger.error(f"Error resetting conversation: {e}")
            return False