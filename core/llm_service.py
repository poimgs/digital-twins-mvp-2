"""
LLM Service for handling all API calls to OpenAI and other language models.
Provides a centralized interface for all LLM interactions.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from openai import OpenAI
from config.settings import settings
from core.models import LLMMessage
    

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
    
    def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
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
        max_tokens: Optional[int] = None
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
                max_tokens=max_tokens
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
        max_tokens: Optional[int] = None
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
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate a structured response using LLMMessage objects.

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

            logger.debug(f"Making OpenAI API call with {len(message_dicts)} messages")
            response = self.client.chat.completions.create(**kwargs)
            logger.debug(f"Received response with {len(response.choices)} choices")
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
            logger.error(f"Error generating conversation structured response: {e}")
            logger.error(f"Error type: {type(e).__name__}")

            # Log additional context for debugging
            logger.error(f"Full error details: {str(e)}")

            # Fallback to regular completion with JSON instruction in prompt
            logger.info("Falling back to regular completion with JSON instruction")
            try:
                fallback_system_prompt = f"{messages[0].content}\n\nIMPORTANT: Respond with valid JSON only. The JSON must include 'response' and 'follow_up_questions' fields."
                fallback_user_prompt = messages[-1].content if len(messages) > 1 else ""
                fallback_response = self.generate_completion(
                    system_prompt=fallback_system_prompt,
                    user_prompt=fallback_user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                logger.info(f"Fallback response received: {len(fallback_response)} characters")
                return self.parse_json_response(fallback_response)
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                logger.error(f"Fallback error type: {type(fallback_error).__name__}")
                # Return a safe default response that matches the expected schema
                logger.info("Returning safe default response")
                return {
                    "response": "I'm sorry, I'm having trouble responding right now. Could you try again?",
                    "follow_up_questions": []
                }

# Global LLM service instance
llm_service = LLMService()
