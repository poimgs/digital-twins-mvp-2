"""
LLM Service for handling all API calls to OpenAI and other language models.
Provides a centralized interface for all LLM interactions.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from openai import OpenAI
from config.settings import settings

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

            return response.choices[0].message.content.strip()

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
            content = response.choices[0].message.content.strip()

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
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {e}")
            logger.error(f"Response content: {response}")
            raise ValueError(f"Invalid JSON response: {e}")


# Global LLM service instance
llm_service = LLMService()
