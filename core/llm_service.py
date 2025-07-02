"""
LLM Service for handling all API calls to OpenAI and other language models.
Provides a centralized interface for all LLM interactions.
"""

import json
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID
from openai import OpenAI
from config.settings import settings
from core.models import LLMMessage, TokenUsage
    

logger = logging.getLogger(__name__)


class LLMService:
    """Service class for handling all LLM API interactions."""
    
    def __init__(self):
        """Initialize the LLM service with OpenAI client."""
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not found in environment variables")

        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.max_tokens = settings.MAX_TOKENS
        self.temperature = settings.TEMPERATURE

        # Check if model supports structured output
        self.supports_structured_output = self._check_structured_output_support()

        # Log configuration for debugging
        logger.info(f"LLM Service initialized with model: {self.model}, max_tokens: {self.max_tokens}, temperature: {self.temperature}")
        logger.info(f"Structured output support: {self.supports_structured_output}")

    def _check_structured_output_support(self) -> bool:
        """Check if the current model supports structured output with JSON schema."""
        # Models that support structured output (as of 2024)
        supported_models = [
            "gpt-4o",
            "gpt-4o-2024-08-06",
            "gpt-4o-mini",
            "gpt-4o-mini-2024-07-18"
        ]
        return any(self.model.startswith(model) for model in supported_models)

    def _track_token_usage(
        self,
        response,
        operation_type: str,
        bot_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        conversation_number: Optional[int] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        request_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track token usage from an OpenAI API response.

        Args:
            response: OpenAI API response object
            operation_type: Type of operation (e.g., 'conversation', 'follow_up_questions')
            bot_id: Optional bot ID
            chat_id: Optional chat ID
            conversation_number: Optional conversation number
            temperature: Temperature used for the request
            max_tokens: Max tokens used for the request
            request_metadata: Additional metadata about the request
        """
        try:
            # Extract token usage from response
            usage = response.usage
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens

            # Create token usage record
            # Convert bot_id string to UUID if provided
            bot_uuid = UUID(bot_id) if bot_id else None

            token_usage = TokenUsage(
                bot_id=bot_uuid,
                chat_id=chat_id,
                conversation_number=conversation_number,
                operation_type=operation_type,
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                temperature=temperature,
                max_tokens=max_tokens,
                request_metadata=request_metadata or {}
            )

            # Import here to avoid circular imports
            from core.supabase_client import supabase_client

            # Store the usage record
            success = supabase_client.create_token_usage(token_usage)
            if success:
                logger.debug(f"Tracked token usage: {total_tokens} tokens for {operation_type}")
            else:
                logger.warning(f"Failed to track token usage for {operation_type}")

        except Exception as e:
            logger.error(f"Error tracking token usage: {e}")
            # Don't raise the exception to avoid breaking the main flow
    
    def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        operation_type: str = "completion",
        bot_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        conversation_number: Optional[int] = None
    ) -> str:
        """
        Generate a completion without structured output.

        Args:
            system_prompt: The system message to set context
            user_prompt: The user message/prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            The generated response text
        """
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature or self.temperature,
                "max_tokens": max_tokens or self.max_tokens
            }

            response = self.client.chat.completions.create(**kwargs)

            # Track token usage
            request_metadata = {
                "system_prompt_length": len(system_prompt),
                "user_prompt_length": len(user_prompt),
                "message_count": len(messages)
            }
            self._track_token_usage(
                response=response,
                operation_type=operation_type,
                bot_id=bot_id,
                chat_id=chat_id,
                conversation_number=conversation_number,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                request_metadata=request_metadata
            )

            content = response.choices[0].message.content

            # Check if content is None or empty
            if not content:
                logger.warning("Received empty response from OpenAI API")
                raise ValueError("Empty response from OpenAI API")

            return content.strip()

        except Exception as e:
            logger.error(f"Error generating completion: {e}")
            raise
    
    def generate_structured_response(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Dict[str, Any],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        operation_type: str = "structured_response",
        bot_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        conversation_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate a structured response using JSON schema validation.

        Args:
            system_prompt: The system message to set context
            user_prompt: The user message/prompt
            schema: JSON schema for response validation
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            The parsed JSON response matching the schema
        """
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature or self.temperature,
                "max_tokens": max_tokens or self.max_tokens,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "extraction_schema",
                        "strict": True,
                        "schema": schema
                    }
                }
            }

            response = self.client.chat.completions.create(**kwargs)

            # Track token usage
            request_metadata = {
                "system_prompt_length": len(system_prompt),
                "user_prompt_length": len(user_prompt),
                "message_count": len(messages),
                "schema_provided": True,
                "schema_properties_count": len(schema.get("properties", {}))
            }
            self._track_token_usage(
                response=response,
                operation_type=operation_type,
                bot_id=bot_id,
                chat_id=chat_id,
                conversation_number=conversation_number,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                request_metadata=request_metadata
            )

            content = response.choices[0].message.content

            # Check if content is None or empty
            if not content:
                logger.warning("Received empty response from OpenAI API")
                raise ValueError("Empty response from OpenAI API")

            content = content.strip()

            # Check if content is still empty after stripping
            if not content:
                logger.warning("Received whitespace-only response from OpenAI API")
                raise ValueError("Whitespace-only response from OpenAI API")

            # Parse and return the structured response
            return json.loads(content)

        except Exception as e:
            logger.error(f"Error generating structured response: {e}")
            # Fallback to regular completion with JSON instruction in prompt
            logger.info("Falling back to regular completion with JSON instruction")
            fallback_system_prompt = f"{system_prompt}\n\nIMPORTANT: Respond with valid JSON only."
            fallback_response = self.generate_completion(
                system_prompt=fallback_system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                operation_type=f"{operation_type}_fallback",
                bot_id=bot_id,
                chat_id=chat_id,
                conversation_number=conversation_number
            )
            return self.parse_json_response(fallback_response)

    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse a JSON response from the LLM.

        Args:
            response: The raw response string

        Returns:
            Parsed JSON as a dictionary
        """
        try:
            # First try to parse as-is
            return json.loads(response)
        except json.JSONDecodeError:
            # If that fails, try to extract JSON from markdown code blocks
            try:
                # Look for JSON wrapped in markdown code blocks
                import re
                json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response, re.DOTALL)
                if json_match:
                    json_content = json_match.group(1).strip()
                    return json.loads(json_content)
                else:
                    # If no markdown blocks found, try to parse the response directly
                    raise json.JSONDecodeError("No JSON found", response, 0)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON response: {e}")
                logger.error(f"Response content: {response}")
                raise ValueError(f"Invalid JSON response: {e}")

    def generate_completion_from_llm_messages(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        operation_type: str = "conversation",
        bot_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        conversation_number: Optional[int] = None
    ) -> str:
        """
        Generate a completion using LLMMessage objects.

        Args:
            messages: List of LLMMessage instances
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            The generated response text
        """
        # Convert LLMMessage objects to dictionaries for OpenAI API
        # Filter out any messages with empty content
        valid_messages = [msg for msg in messages if msg.content and msg.content.strip()]

        if not valid_messages:
            logger.error("No valid messages found after filtering empty content")
            raise ValueError("No valid messages to send to OpenAI API")

        message_dicts = [message.to_dict() for message in valid_messages]

        kwargs = {
            "model": self.model,
            "messages": message_dicts,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens
        }

        response = self.client.chat.completions.create(**kwargs)

        # Track token usage
        total_content_length = sum(len(msg.content) for msg in valid_messages)
        request_metadata = {
            "message_count": len(valid_messages),
            "total_content_length": total_content_length,
            "message_types": [msg.role for msg in valid_messages]
        }
        self._track_token_usage(
            response=response,
            operation_type=operation_type,
            bot_id=bot_id,
            chat_id=chat_id,
            conversation_number=conversation_number,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            request_metadata=request_metadata
        )

        content = response.choices[0].message.content

        # Check if content is None or empty
        if not content:
            logger.warning("Received empty response from OpenAI API")
            raise ValueError("Empty response from OpenAI API")

        return content.strip()

    def generate_structured_response_from_llm_messages(
        self,
        messages: List[LLMMessage],
        schema: Dict[str, Any],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        operation_type: str = "structured_response",
        bot_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        conversation_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate a structured response using LLMMessage objects and JSON schema validation.

        Args:
            messages: List of LLMMessage instances
            schema: JSON schema for response validation
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            The parsed JSON response matching the schema
        """
        try:
            # Convert LLMMessage objects to dictionaries for OpenAI API
            # Filter out any messages with empty content
            valid_messages = [msg for msg in messages if msg.content and msg.content.strip()]

            if not valid_messages:
                logger.error("No valid messages found after filtering empty content")
                raise ValueError("No valid messages to send to OpenAI API")

            message_dicts = [message.to_dict() for message in valid_messages]

            kwargs = {
                "model": self.model,
                "messages": message_dicts,
                "temperature": temperature or self.temperature,
                "max_tokens": max_tokens or self.max_tokens,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "extraction_schema",
                        "strict": True,
                        "schema": schema
                    }
                }
            }

            response = self.client.chat.completions.create(**kwargs)

            # Track token usage
            total_content_length = sum(len(msg.content) for msg in valid_messages)
            request_metadata = {
                "message_count": len(valid_messages),
                "total_content_length": total_content_length,
                "message_types": [msg.role for msg in valid_messages],
                "schema_provided": True,
                "schema_properties_count": len(schema.get("properties", {}))
            }
            self._track_token_usage(
                response=response,
                operation_type=operation_type,
                bot_id=bot_id,
                chat_id=chat_id,
                conversation_number=conversation_number,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                request_metadata=request_metadata
            )

            content = response.choices[0].message.content

            # Check if content is None or empty
            if not content:
                logger.warning("Received empty response from OpenAI API")
                raise ValueError("Empty response from OpenAI API")

            # Strip whitespace and check again
            content = content.strip()
            # Check if content is still empty after stripping
            if not content:
                logger.warning("Received whitespace-only response from OpenAI API")
                raise ValueError("Whitespace-only response from OpenAI API")

            # Parse and return the structured response
            return json.loads(content)

        except Exception as e:
            logger.error(f"Error generating structured response from LLM messages: {e}")
            # Fallback to regular completion with JSON instruction in prompt
            logger.info("Falling back to regular completion with JSON instruction")

            # Add JSON instruction to the last user message or create a new one
            fallback_messages = valid_messages.copy()
            if fallback_messages and fallback_messages[-1].role == "user":
                fallback_messages[-1].content += "\n\nIMPORTANT: Respond with valid JSON only."
            else:
                fallback_messages.append(LLMMessage("user", "IMPORTANT: Respond with valid JSON only."))

            fallback_response = self.generate_completion_from_llm_messages(
                messages=fallback_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                operation_type=operation_type,
                bot_id=bot_id,
                chat_id=chat_id,
                conversation_number=conversation_number
            )

            try:
                return json.loads(fallback_response)
            except json.JSONDecodeError:
                logger.error("Fallback response is not valid JSON")
                raise ValueError("Unable to generate valid structured response")

# Global LLM service instance
llm_service = LLMService()
