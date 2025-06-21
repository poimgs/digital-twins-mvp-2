"""
Personality module - Implements logic for generating comprehensive personality profiles
based on story analyses, structured extraction results, and raw story text.

Supports two approaches:
1. Structured Analysis: Uses extraction results from the two-phase story pipeline
2. Raw Text Analysis: Direct analysis of story corpus for initial personality inference
"""

import json
import logging
from typing import List, Optional
from core.llm_service import llm_service
from core.supabase_client import supabase_client
from core.utils import load_prompts
from core.models import Story, PersonalityProfile

logger = logging.getLogger(__name__)


class PersonalityProfiler:
    """Handles the generation and management of personality profiles using multiple approaches."""

    def __init__(self):
        """Initialize the personality profiler with prompts and schemas."""
        self.prompts = load_prompts()
        # Load schema from prompts.json instead of defining it locally
        self.personality_schema = self.prompts["schemas"]["personality_schema"]



    def generate_personality(
        self,
        stories: List[Story],
        user_id: str = "default"
    ) -> PersonalityProfile:
        """
        Generate personality profile directly from raw story texts using comprehensive analysis.

        This is the "Initial Phase" approach for when only raw story texts are available.

        Args:
            stories: List of Story instances
            user_id: User identifier for the profile

        Returns:
            PersonalityProfile instance containing the comprehensive personality profile
        """
        try:
            # Combine all story texts
            story_texts = []
            for story in stories:
                if story.content:
                    story_texts.append(story.content)

            if not story_texts:
                raise ValueError("No story content found for analysis")

            # Create combined corpus
            combined_corpus = "\n\n---STORY SEPARATOR---\n\n".join(story_texts)

            # Get prompts for raw text personality analysis
            system_prompt = """You are an expert in narrative psychology and personality analysis. You have been given a collection of stories. Your task is to perform a deep analysis of these texts to create a comprehensive personality profile.
            
            **Instructions:**
            Read all the provided stories and synthesize your findings to answer the following questions. Base your answers SOLELY on the content and style of the writing.
            
            1. **Core Values & Motivations:**
            - What recurring themes suggest their core values? What principles seem to drive their actions in these stories?
            - What situations or behaviors consistently trigger an action from them?
            - What are the underlying psychological drivers that motivate their behavior?
            
            2. **Communication Style & Voice:**
            - **Formality & Vocabulary:** Is the language formal or informal? Simple or complex? Technical or anecdotal?
            - **Tone:** What is the dominant emotional tone across the stories? Is it humorous, serious, reflective, optimistic, or something else?
            - **Sentence Structure:** Does the person use short, direct sentences or long, descriptive ones?
            - **Recurring Phrases/Metaphors:** Are there any unique phrases, sayings, or metaphors they use repeatedly?
            - **Emotional Expression:** How do they typically express emotions through language - directly, indirectly, through humor, etc.?
            - **Storytelling Style:** What is their approach to narrative - linear, circular, detail-oriented, big-picture focused?"""
            
            user_prompt = f"""Analyze the following collection of {len(story_texts)} personal stories and create a comprehensive personality profile:\n\n{combined_corpus}"""
            
            schema = {
                "type": "object",
                "properties": {
                    "values": {
                        "type": "array",
                        "description": "List of core values identified in the stories",
                        "items": {"type": "string"}
                    },
                    "formality_vocabulary": {
                        "type": "string",
                        "description": "Analysis of language formality and vocabulary usage"
                    },
                    "tone": {
                        "type": "string",
                        "description": "Dominant emotional tone across stories"
                    },
                    "sentence_structure": {
                        "type": "string",
                        "description": "Analysis of typical sentence construction patterns"
                    },
                    "recurring_phrases_metaphors": {
                        "type": "string",
                        "description": "Common phrases and metaphors used repeatedly"
                    },
                    "emotional_expression": {
                        "type": "string",
                        "description": "Style of emotional expression in language"
                    },
                    "storytelling_style": {
                        "type": "string",
                        "description": "Overall approach to narrative construction"
                    }
                },
                "required": [
                    "values",
                    "formality_vocabulary",
                    "tone",
                    "sentence_structure",
                    "recurring_phrases_metaphors",
                    "emotional_expression",
                    "storytelling_style"
                ],
                "additionalProperties": "false"
            }

            # Generate personality profile using structured response
            response = llm_service.generate_structured_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=schema
            )

            # Convert to PersonalityAnalysis dataclass
            personality_profile = PersonalityProfile.from_dict(response)

            logger.info(f"Successfully generated personality profile from raw text for user {user_id}")
            return personality_profile

        except Exception as e:
            logger.error(f"Error generating personality from raw text: {e}")
            raise
    
    def get_personality(self, user_id: str = "default") -> Optional[PersonalityProfile]:
        """
        Extract key personality traits from the stored profile.

        Args:
            user_id: User identifier

        Returns:
            PersonalityTraits instance containing key personality traits
        """
        try:
            personality_profile = supabase_client.get_personality_profile(user_id)

            if not personality_profile:
                logger.warning(f"No personality profile found for user {user_id}")
                return None
            
            return personality_profile

        except Exception as e:
            logger.error(f"Error extracting personality traits: {e}")
            raise
    
    def generate_personality_summary(self, user_id: str = "default") -> str:
        """
        Generate a natural language summary of the personality profile.
        
        Args:
            user_id: User identifier
        
        Returns:
            Natural language personality summary
        """
        try:
            personality = self.get_personality(user_id)
            
            if not personality:
                return ""
            
            system_prompt = """You are an expert at creating natural, engaging personality summaries. 
            Create a flowing narrative that captures the essence of this person's personality."""
            
            user_prompt = f"""Based on the following personality traits, write a natural, engaging summary 
            that captures who this person is, how they think, feel, and interact with the world:
            
            {json.dumps(personality, indent=2)}
            
            Write in a warm, insightful tone that feels like it's describing a real person you know well."""
            
            summary = llm_service.generate_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating personality summary: {e}")
            raise

# Global personality profiler instance
personality_profiler = PersonalityProfiler()
