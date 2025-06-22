"""
Conversational Engine - Enhanced engine for sophisticated chat logic.
Implements conversation-focused state management with dynamic context tracking,
intelligent story repetition handling, and contextual awareness.
"""

import logging
from typing import Dict, List, Optional
from core.llm_service import llm_service
from core.supabase_client import supabase_client
from core.conversation_manager import ConversationManager
from core.story_retrieval_manager import StoryRetrievalManager
from core.models import LLMMessage, ConversationResponse, generate_telegram_chat_id, generate_terminal_chat_id

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
        
        # Get bot call to action
        bot = supabase_client.get_bot_by_id(bot_id)
        if not bot:
            raise ValueError(f"Bot with ID {bot_id} not found")
        self.call_to_action = bot.call_to_action

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

            # Get bot-specific stories
            stories = supabase_client.get_stories_with_analysis(bot_id)
            relevant_story = conversation_manager.find_relevant_story(stories)
            story_summaries = ""
            for story in stories:
                story_summaries += f"{story.summary}\n\n"

            conversation_history = conversation_manager.get_conversation_history_for_llm()

            # Prepare call to action context for natural integration after 5 turns
            cta_context = ""
            if not conversation_manager.call_to_action_shown and len(conversation_history) >= 10:
                cta_context = f"""
CALL TO ACTION GUIDANCE:
You have a call to action available: "{self.call_to_action}"

You may naturally incorporate this call to action into your response if the conversation feels right for it. Consider:
- Has enough rapport and trust been built?
- Is the user engaged and showing genuine interest?
- Would mentioning this feel natural and valuable, not forced or sales-y?
- Have you shared meaningful insights that connect to this call to action?

If the timing feels right, weave it naturally into your response. If not, simply respond normally without it.
The call to action doesn't need to be word-for-word - adapt it to fit naturally into your response style."""

            system_prompt = f"""You are a digital twin created from personal stories and experiences.
Respond as if you are the person whose stories were analyzed, maintaining their personality, communication style, and emotional patterns.
Use the conversation context to provide natural, contextually-aware responses that build on the ongoing dialogue.

Ensure that you keep your response to the user's message brief and to the point. Do not ask a question back to the user, and focus on sharing stories.

If the conversation is moving away from stories and experiences, guide the conversation back to share stories and insights.
Do not deviate away from personal stories and experiences.

From the story summaries provided, also provide recommended questions for users to ask.

{cta_context}

CONVERSATION CONTEXT:
{conversation_manager.summary}

PERSONALITY PROFILE:
{self.bot_personality}

RELEVANT STORY:
{relevant_story.summary if relevant_story else 'No relevant story found'}

SUMMARY OF ALL STORIES:
{story_summaries}
            """
            
            messages = self.build_llm_messages(
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                user_message=user_message
            )
            
            # Schema to ensure that LLM returns natural response as well as 3 recommended questions for users to ask
            schema = {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "string",
                        "description": "Natural response to the user's message"
                    },
                    "follow_up_questions": {
                        "type": "array",
                        "description": "3 recommended questions for users to ask. Each question should only be up to 7 words long.",
                        "items": {"type": "string"}
                    }
                },
                "required": ["response", "follow_up_questions"],
                "additionalProperties": False
            }

            response = llm_service.generate_structured_response_from_llm_messages(
                messages=messages,
                schema=schema
            )

            # Ensure response has required fields with defaults
            response_text = response.get("response", "I'm sorry, I'm having trouble responding right now. Could you try again?")
            follow_up_questions = response.get("follow_up_questions", [])

            # Check if the LLM naturally included the call to action in the response
            # If so, mark it as shown to prevent future prompting
            if not conversation_manager.call_to_action_shown:
                # Simple heuristic: if the response contains key terms from the CTA, consider it shown
                cta_keywords = self.call_to_action.lower().split()
                response_lower = response_text.lower()

                # Check if response contains significant CTA content (more sophisticated detection could be added)
                cta_mentioned = any(keyword in response_lower for keyword in cta_keywords if len(keyword) > 3)

                if cta_mentioned:
                    try:
                        supabase_client.update_conversation_state(
                            chat_id=final_chat_id,
                            call_to_action_shown=True
                        )
                        conversation_manager.call_to_action_shown = True
                        logger.info(f"CTA detected in response and marked as shown")
                    except Exception as e:
                        logger.error(f"Error updating call_to_action_shown state: {e}")

            conversation_response = ConversationResponse(response_text, follow_up_questions)

            conversation_manager.add_assistant_message(conversation_response.response)
            conversation_manager.summarize_conversation(user_message, conversation_response.response)

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