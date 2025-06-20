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
        self.prompts = load_prompts()
        # Load schemas from prompts.json instead of defining them locally
        self.trigger_schema = self.prompts["schemas"]["trigger_schema"]
        self.feelings_schema = self.prompts["schemas"]["feelings_schema"]
        self.thought_schema = self.prompts["schemas"]["thought_schema"]
        self.value_analysis_schema = self.prompts["schemas"]["value_analysis_schema"]
        self.theme_extraction_schema = self.prompts["schemas"]["theme_extraction_schema"]





    def _extract_trigger(self, story_text: str) -> Optional[TriggerExtraction]:
        """
        Phase 1: Extract the trigger event from the story using structured schema.

        Args:
            story_text: The raw story text to analyze

        Returns:
            TriggerExtraction instance containing trigger information or None
        """
        try:
            system_prompt = self.prompts["trigger_extraction"]["system_prompt"]
            user_prompt = self.prompts["trigger_extraction"]["user_prompt"].format(
                story_text=story_text
            )

            # Use structured response with trigger schema
            response = llm_service.generate_structured_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=self.trigger_schema
            )

            if response:
                return TriggerExtraction.from_dict(response)
            return None

        except Exception as e:
            logger.error(f"Error extracting trigger: {e}")
            return None

    def _extract_feelings(self, story_text: str) -> FeelingsExtraction:
        """
        Phase 1: Extract explicitly mentioned emotions from the story using structured schema.

        Args:
            story_text: The raw story text to analyze

        Returns:
            FeelingsExtraction instance containing emotions list
        """
        try:
            system_prompt = self.prompts["feeling_extraction"]["system_prompt"]
            user_prompt = self.prompts["feeling_extraction"]["user_prompt"].format(
                story_text=story_text
            )

            # Use structured response with feelings schema
            response = llm_service.generate_structured_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=self.feelings_schema
            )

            if response:
                return FeelingsExtraction.from_dict(response)
            return FeelingsExtraction()

        except Exception as e:
            logger.error(f"Error extracting feelings: {e}")
            return FeelingsExtraction()

    def _extract_thought(self, story_text: str) -> Optional[ThoughtExtraction]:
        """
        Phase 1: Extract internal thoughts/monologue from the story using structured schema.

        Args:
            story_text: The raw story text to analyze

        Returns:
            ThoughtExtraction instance containing internal monologue or None
        """
        try:
            system_prompt = self.prompts["thought_extraction"]["system_prompt"]
            user_prompt = self.prompts["thought_extraction"]["user_prompt"].format(
                story_text=story_text
            )

            # Use structured response with thought schema
            response = llm_service.generate_structured_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=self.thought_schema
            )

            if response:
                return ThoughtExtraction.from_dict(response)
            return None

        except Exception as e:
            logger.error(f"Error extracting thought: {e}")
            return None

    def _extract_violated_value(self, story_text: str, trigger: Optional[TriggerExtraction],
                               feelings: FeelingsExtraction, thought: Optional[ThoughtExtraction]) -> Optional[ValueAnalysisExtraction]:
        """
        Phase 2: Extract violated values using context from Phase 1 with structured schema.

        Args:
            story_text: The raw story text
            trigger: Trigger extraction results
            feelings: Feelings extraction results
            thought: Thought extraction results

        Returns:
            ValueAnalysisExtraction instance containing value analysis or None
        """
        try:
            system_prompt = self.prompts["value_extraction"]["system_prompt"]

            context = {
                "story": story_text,
                "trigger": trigger.to_dict() if trigger else None,
                "feelings": feelings.to_dict(),
                "thought": thought.to_dict() if thought else None
            }

            user_prompt = self.prompts["value_extraction"]["user_prompt"].format(
                context=json.dumps(context, indent=2)
            )

            # Use structured response with value analysis schema
            response = llm_service.generate_structured_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=self.value_analysis_schema
            )

            if response:
                return ValueAnalysisExtraction.from_dict(response)
            return None

        except Exception as e:
            logger.error(f"Error extracting violated value: {e}")
            return None

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
            trigger = self._extract_trigger(story_text)
            feelings = self._extract_feelings(story_text)
            thought = self._extract_thought(story_text)

            logger.debug(f"Phase 1 complete for story {story_id}")

            # Phase 2: Context-aware enrichment
            logger.debug(f"Phase 2: Extracting violated values for story {story_id}")

            value_analysis = self._extract_violated_value(
                story_text, trigger, feelings, thought
            )

            logger.debug(f"Phase 2 complete for story {story_id}")

            # Create StoryAnalysis instance with individual fields
            story_analysis = StoryAnalysis(
                story_id=story_id,
                # Trigger fields
                trigger_title=trigger.title if trigger else None,
                trigger_description=trigger.description if trigger else None,
                trigger_category=trigger.category if trigger else None,
                # Emotions
                emotions=feelings.emotions,
                # Internal monologue
                internal_monologue=thought.internal_monologue if thought else None,
                # Value analysis
                violated_value=value_analysis.violated_value if value_analysis else None,
                value_reasoning=value_analysis.reasoning if value_analysis else None,
                confidence_score=value_analysis.confidence_score if value_analysis else None,
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
    
    def extract_key_themes(self, analyses: List[StoryAnalysis]) -> ThemeExtraction:
        """
        Extract overarching themes from multiple story analyses using the new column structure.

        Args:
            analyses: List of StoryAnalysis instances from the two-phase pipeline

        Returns:
            ThemeExtraction instance containing key themes and patterns
        """
        try:
            # Convert StoryAnalysis instances to structured extraction format for theme analysis
            extraction_results = []
            for analysis in analyses:
                # Create dataclass instances from the analysis data
                trigger = None
                if analysis.trigger_title:
                    trigger = TriggerExtraction(
                        title=analysis.trigger_title,
                        description=analysis.trigger_description or "",
                        category=analysis.trigger_category or ""
                    )

                feelings = FeelingsExtraction(emotions=analysis.emotions)

                thought = None
                if analysis.internal_monologue:
                    thought = ThoughtExtraction(internal_monologue=analysis.internal_monologue)

                value_analysis = None
                if analysis.violated_value:
                    value_analysis = ValueAnalysisExtraction(
                        violated_value=analysis.violated_value,
                        reasoning=analysis.value_reasoning or "",
                        confidence_score=analysis.confidence_score or 1
                    )

                # Convert to dictionary format for LLM processing
                extraction_result = {
                    "trigger": trigger.to_dict() if trigger else None,
                    "feelings": feelings.to_dict(),
                    "thought": thought.to_dict() if thought else None,
                    "value_analysis": value_analysis.to_dict() if value_analysis else None
                }
                extraction_results.append(extraction_result)

            combined_analyses = {
                "total_stories": len(analyses),
                "extraction_results": extraction_results
            }

            system_prompt = """You are an expert at identifying patterns and themes across multiple story analyses.
            Extract overarching themes, recurring patterns, and key insights from the structured extraction results."""

            user_prompt = f"""Based on the following story extraction results, identify:
            1. Recurring trigger patterns and categories
            2. Common emotional responses and patterns
            3. Frequent internal thought patterns and cognitive styles
            4. Most commonly violated values and their themes
            5. Relationships between triggers, emotions, thoughts, and values
            6. Overall psychological patterns and coping mechanisms

            Focus on:
            - Trigger categories that appear most frequently
            - Emotional patterns that repeat across stories
            - Common cognitive responses and thought patterns
            - Core values that are consistently important to this person
            - How different triggers relate to different violated values

            Extraction Results: {json.dumps(combined_analyses, indent=2)}

            Provide a comprehensive analysis with specific insights about this person's psychological patterns."""

            # Use structured response with theme extraction schema
            themes_response = llm_service.generate_structured_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=self.theme_extraction_schema
            )

            logger.info("Successfully extracted key themes from two-phase analyses")
            return ThemeExtraction.from_dict(themes_response)

        except Exception as e:
            logger.error(f"Error extracting themes: {e}")
            raise
    
    def process_all_stories(self) -> StoryProcessingResult:
        """
        Process all stories in the database through the complete analysis pipeline.

        Returns:
            StoryProcessingResult instance containing the processing results
        """
        try:
            # Get all stories from database (now returns List[Story])
            stories = supabase_client.get_stories()

            if not stories:
                logger.warning("No stories found in database")
                return StoryProcessingResult(
                    status="no_stories",
                    total_stories=0,
                    processed_stories=0,
                    key_themes=ThemeExtraction()
                )

            # Analyze all stories (now works with Story objects)
            analyses = self.analyze_multiple_stories(stories)

            # Extract key themes (now works with StoryAnalysis objects)
            themes = self.extract_key_themes(analyses)

            result = StoryProcessingResult(
                status="success",
                total_stories=len(stories),
                processed_stories=len(analyses),
                key_themes=themes
            )

            logger.info(f"Story processing complete: {result.status} - {result.processed_stories}/{result.total_stories} stories")
            return result

        except Exception as e:
            logger.error(f"Error in story processing pipeline: {e}")
            raise


# Global story deconstructor instance
story_deconstructor = StoryDeconstructor()
