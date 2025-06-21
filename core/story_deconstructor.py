"""
Story Deconstructor - Implements the "Internal State Extraction" pipeline.
Analyzes stories to extract internal states, emotions, and psychological patterns.

This module implements a robust, two-phase pipeline:
Phase 1: Parallel Foundational Extraction (Trigger, Feeling, Thought)
Phase 2: Sequential Context-Aware Enrichment (Violated Value)
"""

import json
import logging
from typing import List, Optional
from core.llm_service import llm_service
from core.supabase_client import supabase_client
from core.utils import load_prompts
from core.models import (
    Story, StoryAnalysis, TriggerExtraction, FeelingsExtraction,
    ThoughtExtraction, ValueAnalysisExtraction, ThemeExtraction, StoryProcessingResult
)

logger = logging.getLogger(__name__)


class StoryDeconstructor:
    """Handles the analysis and deconstruction of personal stories using a two-phase pipeline."""

    def __init__(self):
        """Initialize the story deconstructor with prompts and schemas."""
        self.theme_extraction_schema = self.prompts["schemas"]["theme_extraction_schema"]

    def _extract_triggers(self, story_text: str) -> List[str]:
        """
        Extract the trigger events from the story using structured schema.

        Args:
            story_text: The raw story text to analyze

        Returns:
            List of trigger events
        """
        try:
            system_prompt = "You are a data extraction specialist. Your task is to analyze the provided story and identify the primary external events that acted as the trigger for the narrator's emotional response and/or actions."
            user_prompt = f"Analyze the following story and identify the trigger event: {story_text}"
            schema = {
                "type": "object",
                "properties": {
                    "triggers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Primary external events that acted as the trigger for the narrator's emotional response and/or actions."
                    }
                },
                "required": [
                    "triggers"
                ],
                "additionalProperties": "false"
            }

            # Use structured response with trigger schema
            response = llm_service.generate_structured_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=schema
            )

            if response:
                return response.get("triggers", [])
            return []

        except Exception as e:
            logger.error(f"Error extracting trigger: {e}")
            return []

    def _extract_emotions(self, story_text: str) -> List[str]:
        """
        Phase 1: Extract explicitly mentioned emotions from the story using structured schema.

        Args:
            story_text: The raw story text to analyze

        Returns:
            List of emotions
        """
        try:
            system_prompt = "You are an emotion detection specialist. Your task is to read the provided story and derive the emotions"
            user_prompt = f"Analyze the following story: {story_text}"
            schema = {
                "type": "object",
                "properties": {
                    "emotions": {
                        "type": "array",
                        "description": "List of emotions felt.",
                        "items": {"type": "string"}
                    }
                },
                "required": [
                    "emotions"
                ],
                "additionalProperties": "false"
            }

            # Use structured response with feelings schema
            response = llm_service.generate_structured_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=schema
            )

            if response:
                return response.get("emotions", [])
            return []

        except Exception as e:
            logger.error(f"Error extracting feelings: {e}")
            return []

    def _extract_thoughts(self, story_text: str) -> List[str]:
        """
        Extract internal thoughts/monologue from the story using structured schema.

        Args:
            story_text: The raw story text to analyze

        Returns:
            List of thoughts
        """
        try:
            system_prompt = "You are a cognitive analysis specialist. Your task is to identify and extract the narrator's immediate internal thoughts or the story they told themselves. Capture the core thought, quoting directly from the text if possible."
            user_prompt = f"Analyze the following story: {story_text}"
            schema = {
                "type": "object",
                "properties": {
                    "thoughts": {
                        "type": "array",
                        "description": "internal thoughts.",
                        "items": {"type": "string"}
                    }
                },
                "required": ["thoughts"],
                "additionalProperties": "false"
            }

            # Use structured response with thought schema
            response = llm_service.generate_structured_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=schema
            )

            if response:
                return response.get("thoughts", [])
            return []

        except Exception as e:
            logger.error(f"Error extracting thoughts: {e}")
            return []

    def _extract_values(self, story_text: str, triggers: List[str], emotions: List[str], thoughts: List[str]) -> List[str]:
        """
        Phase 2: Extract violated values using context from Phase 1 with structured schema.

        Args:
            story_text: The raw story text
            triggers: triggers
            emotions: emotions
            thoughts: thoughts

        Returns:
            List of values
        """
        try:
            system_prompt = "You are an expert in human psychology and values. Your task is to analyze a story and its pre-processed components to determine the core values."

            context = {
                "story": story_text,
                "triggers": triggers,
                "emotions": emotions,
                "thoughts": thoughts
            }

            user_prompt = f"Analyze the following context to determine core values: {context}"
            schema = {
                "type": "object",
                "properties": {
                    "values": {
                        "type": "array",
                        "description": "core values",
                        "items": {"type": "string"}
                    }
                },
                "required": ["values"],
                "additionalProperties": "false"
            }

            # Use structured response with value analysis schema
            response = llm_service.generate_structured_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=schema
            )

            if response:
                return response.get("values", [])
            return []

        except Exception as e:
            logger.error(f"Error extracting violated value: {e}")
            return []

    def analyze_story(self, story_text: str, story_id: str) -> StoryAnalysis:
        """
        Analyze a single story using the two-phase extraction pipeline.

        Phase 1: Parallel extraction of trigger, feelings, and thoughts
        Phase 2: Context-aware extraction of violated values

        Args:
            story_text: The raw story text to analyze
            story_id: The ID of the story being analyzed

        Returns:
            StoryAnalysis instance containing the complete analysis results
        """
        try:
            logger.info(f"Starting two-phase analysis for story {story_id}")

            # Phase 1: Parallel foundational extraction
            logger.debug(f"Phase 1: Extracting foundational elements for story {story_id}")

            # Extract trigger, feelings, and thoughts in parallel
            # For now, we'll do them sequentially but this could be parallelized
            triggers = self._extract_triggers(story_text)
            emotions = self._extract_emotions(story_text)
            thoughts = self._extract_thoughts(story_text)

            logger.debug(f"Phase 1 complete for story {story_id}")

            # Phase 2: Context-aware enrichment
            logger.debug(f"Phase 2: Extracting violated values for story {story_id}")

            values = self._extract_values(story_text, triggers, emotions, thoughts)

            logger.debug(f"Phase 2 complete for story {story_id}")

            # Create StoryAnalysis instance with individual fields
            story_analysis = StoryAnalysis(
                story_id=story_id,
                triggers=triggers,
                emotions=emotions,
                thoughts=thoughts,
                values=values,
            )

            logger.info(f"Successfully completed two-phase analysis for story {story_id}")
            return story_analysis

        except Exception as e:
            logger.error(f"Error in two-phase analysis for story {story_id}: {e}")
            raise
    
    def analyze_multiple_stories(self, stories: List[Story]) -> List[StoryAnalysis]:
        """
        Analyze multiple stories in batch using the two-phase pipeline.

        Args:
            stories: List of Story instances to analyze

        Returns:
            List of StoryAnalysis instances
        """
        analyses = []

        for story in stories:
            try:
                story_id = str(story.id)
                story_content = story.content

                if not story_content:
                    logger.warning(f"Empty content for story {story_id}")
                    continue

                analysis = self.analyze_story(story_content, story_id)
                analyses.append(analysis)

                # Store analysis in database
                supabase_client.insert_story_analysis(analysis)

            except Exception as e:
                logger.error(f"Error processing story {story.id}: {e}")
                continue

        logger.info(f"Completed two-phase analysis of {len(analyses)} stories")
        return analyses


# Global story deconstructor instance
story_deconstructor = StoryDeconstructor()
