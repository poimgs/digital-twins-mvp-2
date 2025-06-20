"""
Utility functions shared across the core modules.
"""

import json
import logging
from typing import Dict, Any
from config.settings import Settings

logger = logging.getLogger(__name__)


def load_prompts() -> Dict[str, Any]:
    """
    Load prompts from the configuration file.
    
    Returns:
        Dictionary containing all prompts from the prompts.json file
        
    Raises:
        Exception: If the prompts file cannot be loaded
    """
    try:
        with open(Settings.PROMPTS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading prompts from {Settings.PROMPTS_FILE}: {e}")
        raise
