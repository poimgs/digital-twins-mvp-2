"""
Configuration settings for the Narrative Digital Twin MVP.
Loads environment variables and provides centralized access to configuration.
"""

import os
from typing import Dict
from dotenv import load_dotenv

# Load environment variables from .env file (override existing env vars)
load_dotenv(override=True)


class Settings:
    """Central configuration class for the application."""
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "2000"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    # Application Settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Data Paths
    STORIES_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "stories")
    PROMPTS_FILE: str = os.path.join(os.path.dirname(__file__), "prompts.json")
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required settings are present."""
        required_settings = [
            cls.OPENAI_API_KEY,
            cls.SUPABASE_URL,
            cls.SUPABASE_KEY
        ]
        
        missing = [name for name, value in zip(
            ["OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"],
            required_settings
        ) if not value]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return True


# Global settings instance
settings = Settings()
