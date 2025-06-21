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

    def __init__(self):
        """Initialize the conversational engine."""
        self.conversations: Dict[str, ConversationManager] = {}  # chat_id -> ConversationManager
        self.story_retrieval_manager = StoryRetrievalManager()
        self.bot_personalities: Dict[str, str] = {}  # bot_id -> personality_summary

    def get_bot_personality_summary(self, bot_id: str) -> str:
        """Get or create personality summary for a bot."""
        if bot_id not in self.bot_personalities:
            personality_profile = supabase_client.get_personality_profile(bot_id)
            # Create a more structured and readable personality summary for the digital twin
            self.bot_personalities[bot_id] = f"""
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
        return self.bot_personalities[bot_id]

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

            # Get bot-specific stories and personality
            stories = supabase_client.get_stories_with_analysis(bot_id)
            relevant_story = conversation_manager.find_relevant_story(stories)
            story_summaries = ""
            for story in stories:
                story_summaries += f"{story.summary}\n\n"

            conversation_history = conversation_manager.get_conversation_history_for_llm()
            personality_summary = self.get_bot_personality_summary(bot_id)

            # Note: Bot information can be used for welcome message and call to action logic

            system_prompt = f"""You are a digital twin created from personal stories and experiences.
Respond as if you are the person whose stories were analyzed, maintaining their personality, communication style, and emotional patterns.
Use the conversation context to provide natural, contextually-aware responses that build on the ongoing dialogue.

From the story summaries provided, also provide recommended questions for users to ask.

CONVERSATION CONTEXT:
{conversation_manager.summary}

PERSONALITY PROFILE:
{personality_summary}

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
                "additionalProperties": "false"
            }

            response = llm_service.generate_structured_response_from_llm_messages(
                messages=messages,
                schema=schema
            )
            
            conversation_response = ConversationResponse(response["response"], response["follow_up_questions"])

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

            if final_chat_id in self.conversations:
                del self.conversations[final_chat_id]

            conversation_manager = self.get_or_create_conversation_manager(final_chat_id, bot_id)
            logger.info(f"Reset conversation state for chat {final_chat_id}")
            conversation_manager.reset_conversation()
            return True
        except Exception as e:
            logger.error(f"Error resetting conversation: {e}")
            return False


# Global conversational engine instance
conversational_engine = ConversationalEngine()
