"""
Personality module - Implements logic for generating comprehensive personality profiles
based on story analyses, structured extraction results, and raw story text.

Supports two approaches:
1. Structured Analysis: Uses extraction results from the two-phase story pipeline
2. Raw Text Analysis: Direct analysis of story corpus for initial personality inference
"""

import json
import logging
from typing import Dict, List, Any, Optional
from core.llm_service import llm_service
from core.supabase_client import supabase_client
from core.utils import load_prompts
from core.models import (
    Story, PersonalityProfile, PersonalityAnalysis,
    PersonalityTraits, PersonalityPipelineResult
)

logger = logging.getLogger(__name__)


class PersonalityProfiler:
    """Handles the generation and management of personality profiles using multiple approaches."""

    def __init__(self):
        """Initialize the personality profiler with prompts and schemas."""
        self.prompts = load_prompts()
        # Load schema from prompts.json instead of defining it locally
        self.personality_schema = self.prompts["schemas"]["personality_schema"]



    def generate_personality_from_raw_text(
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
            system_prompt = self.prompts["raw_text_personality"]["system_prompt"]
            user_prompt = self.prompts["raw_text_personality"]["analysis_prompt"].format(
                story_corpus=combined_corpus,
                story_count=len(story_texts)
            )

            # Generate personality profile using structured response
            profile_response = llm_service.generate_structured_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=self.personality_schema
            )

            # Convert to PersonalityAnalysis dataclass
            personality_analysis = PersonalityAnalysis.from_dict(profile_response)
            raw_response = json.dumps(profile_response)

            # Create PersonalityProfile instance
            personality_profile = PersonalityProfile(
                user_id=user_id,
                profile={
                    **personality_analysis.to_dict(),
                    "analysis_type": "raw_text_analysis",
                    "source_stories_count": len(story_texts),
                    "generation_method": "comprehensive_text_analysis"
                },
                source_analyses_count=len(story_texts),
                raw_response=raw_response,
                profile_version="2.0"
            )

            logger.info(f"Successfully generated personality profile from raw text for user {user_id}")
            return personality_profile

        except Exception as e:
            logger.error(f"Error generating personality from raw text: {e}")
            raise

    def generate_personality_from_structured_data(
        self,
        extraction_results: List[Dict[str, Any]],
        user_id: str = "default"
    ) -> PersonalityProfile:
        """
        Generate personality profile from structured extraction results.

        Uses the results from the two-phase story extraction pipeline.

        Args:
            extraction_results: List of structured extraction results
            user_id: User identifier for the profile

        Returns:
            PersonalityProfile instance containing the personality profile
        """
        try:
            # Prepare structured data for analysis
            structured_data = {
                "total_stories": len(extraction_results),
                "extraction_results": extraction_results
            }

            # Get prompts for structured data personality analysis
            system_prompt = self.prompts["structured_personality"]["system_prompt"]
            user_prompt = self.prompts["structured_personality"]["analysis_prompt"].format(
                structured_data=json.dumps(structured_data, indent=2)
            )

            # Generate personality profile using structured response
            profile_response = llm_service.generate_structured_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=self.personality_schema
            )

            # Convert to PersonalityAnalysis dataclass
            personality_analysis = PersonalityAnalysis.from_dict(profile_response)
            raw_response = json.dumps(profile_response)

            # Create PersonalityProfile instance
            personality_profile = PersonalityProfile(
                user_id=user_id,
                profile={
                    **personality_analysis.to_dict(),
                    "analysis_type": "structured_extraction_analysis",
                    "source_extractions_count": len(extraction_results),
                    "generation_method": "structured_data_synthesis"
                },
                source_analyses_count=len(extraction_results),
                raw_response=raw_response,
                profile_version="2.0"
            )

            logger.info(f"Successfully generated personality profile from structured data for user {user_id}")
            return personality_profile

        except Exception as e:
            logger.error(f"Error generating personality from structured data: {e}")
            raise

    def generate_persona_document(
        self,
        personality_profile: PersonalityProfile,
        user_name: str = "Individual"
    ) -> str:
        """
        Generate a Persona.md document from personality profile data.

        This creates the human-readable persona file used to instruct the digital twin.

        Args:
            personality_profile: PersonalityProfile instance
            user_name: Name to use in the persona document

        Returns:
            Formatted persona document as markdown string
        """
        try:
            profile = personality_profile.profile
            analysis_type = profile.get("analysis_type", "unknown")

            # Get profile components
            core_values = profile.get("core_values_motivations", {})
            communication = profile.get("communication_style_voice", {})
            cognitive = profile.get("cognitive_style_worldview", {})

            # Generate the persona document
            system_prompt = self.prompts["persona_generation"]["system_prompt"]
            user_prompt = self.prompts["persona_generation"]["document_prompt"].format(
                user_name=user_name,
                analysis_type=analysis_type,
                core_values=json.dumps(core_values, indent=2),
                communication_style=json.dumps(communication, indent=2),
                cognitive_style=json.dumps(cognitive, indent=2)
            )

            persona_document = llm_service.generate_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )

            logger.info(f"Generated persona document for {user_name}")
            return persona_document

        except Exception as e:
            logger.error(f"Error generating persona document: {e}")
            raise

    def create_complete_personality_pipeline(
        self,
        stories: List[Dict[str, Any]],
        user_id: str = "default",
        user_name: str = "Individual",
        use_structured_extraction: bool = True
    ) -> Dict[str, Any]:
        """
        Complete pipeline to create personality profile and persona document.

        Args:
            stories: List of story dictionaries
            user_id: User identifier
            user_name: Name for the persona document
            use_structured_extraction: Whether to use structured extraction first

        Returns:
            Complete personality data including profile and persona document
        """
        try:
            if use_structured_extraction:
                # First, try to get structured extraction results
                from core.story_deconstructor import story_deconstructor

                logger.info("Running structured extraction on stories...")
                extraction_results = []

                for story in stories:
                    story_id = story.get("id", f"story_{len(extraction_results)}")
                    story_content = story.get("content", story.get("text", ""))

                    if story_content:
                        try:
                            result = story_deconstructor.analyze_story(story_content, story_id)
                            extraction_results.append(result.get("extraction_results", {}))
                        except Exception as e:
                            logger.warning(f"Failed to extract from story {story_id}: {e}")
                            continue

                if extraction_results:
                    logger.info(f"Using structured extraction results from {len(extraction_results)} stories")
                    profile_data = self.generate_personality_from_structured_data(
                        extraction_results, user_id
                    )
                else:
                    logger.info("No structured extraction results, falling back to raw text analysis")
                    profile_data = self.generate_personality_from_raw_text(stories, user_id)
            else:
                # Use raw text analysis directly
                logger.info("Using raw text analysis for personality generation")
                profile_data = self.generate_personality_from_raw_text(stories, user_id)

            # Generate persona document
            persona_document = self.generate_persona_document(profile_data, user_name)

            # Create complete result
            complete_result = {
                "user_id": user_id,
                "user_name": user_name,
                "profile_data": profile_data,
                "persona_document": persona_document,
                "source_stories_count": len(stories),
                "analysis_method": profile_data.get("analysis_type", "unknown")
            }

            # Store in database
            supabase_client.insert_personality_profile(profile_data)

            logger.info(f"Created complete personality pipeline for user {user_id}")
            return complete_result

        except Exception as e:
            logger.error(f"Error in complete personality pipeline: {e}")
            raise
    
    def generate_personality_profile(
        self,
        analyses: List[Dict[str, Any]],
        user_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive personality profile based on story analyses.

        This method maintains backward compatibility while supporting new extraction formats.

        Args:
            analyses: List of story analysis results (old or new format)
            user_id: User identifier for the profile

        Returns:
            Dictionary containing the personality profile
        """
        try:
            # Check if we have new structured extraction results
            has_structured_data = any(
                "extraction_results" in analysis for analysis in analyses
            )

            if has_structured_data:
                # Use structured data approach
                extraction_results = []
                for analysis in analyses:
                    if "extraction_results" in analysis:
                        extraction_results.append(analysis["extraction_results"])

                return self.generate_personality_from_structured_data(
                    extraction_results, user_id
                )
            else:
                # Use legacy approach for backward compatibility
                analyses_text = json.dumps([
                    analysis.get("analysis", analysis) for analysis in analyses
                ], indent=2)

                # Get prompts for personality generation
                system_prompt = self.prompts["personality_generation"]["system_prompt"]
                user_prompt = self.prompts["personality_generation"]["profile_prompt"].format(
                    analyses=analyses_text
                )

                # Generate personality profile using structured response
                profile_response = llm_service.generate_structured_response(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema=self.personality_schema
                )

                # Convert to PersonalityAnalysis dataclass
                personality_analysis = PersonalityAnalysis.from_dict(profile_response)
                response = json.dumps(profile_response)

                # Create complete profile data
                profile_data = {
                    "user_id": user_id,
                    "profile": personality_analysis.to_dict(),
                    "analysis_type": "legacy_analysis",
                    "source_analyses_count": len(analyses),
                    "raw_response": response
                }

                logger.info(f"Successfully generated personality profile (legacy) for user {user_id}")
                return profile_data

        except Exception as e:
            logger.error(f"Error generating personality profile: {e}")
            raise
    
    def update_personality_profile(
        self, 
        user_id: str = "default", 
        new_analyses: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Update an existing personality profile with new story analyses.
        
        Args:
            user_id: User identifier for the profile
            new_analyses: Optional new analyses to incorporate
        
        Returns:
            Updated personality profile
        """
        try:
            # Get existing profile
            existing_profile = supabase_client.get_personality_profile(user_id)
            
            # Get all analyses if new ones not provided
            if new_analyses is None:
                new_analyses = supabase_client.get_story_analyses()
            
            # Generate new profile
            updated_profile = self.generate_personality_profile(new_analyses, user_id)
            
            # If there's an existing profile, note the update
            if existing_profile:
                updated_profile["previous_version"] = existing_profile.get("created_at")
                updated_profile["update_reason"] = "new_analyses_added"
            
            # Store updated profile
            supabase_client.insert_personality_profile(updated_profile)
            
            logger.info(f"Updated personality profile for user {user_id}")
            return updated_profile
            
        except Exception as e:
            logger.error(f"Error updating personality profile: {e}")
            raise
    
    def get_personality_traits(self, user_id: str = "default") -> PersonalityTraits:
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
                return PersonalityTraits()

            profile = personality_profile.profile

            # Extract key traits for easy access
            return PersonalityTraits(
                core_traits=profile.get("core_personality_traits", []),
                communication_style=profile.get("communication_style", {}),
                emotional_patterns=profile.get("emotional_patterns", {}),
                values=profile.get("values_and_motivations", []),
                behavioral_tendencies=profile.get("behavioral_tendencies", []),
                relationship_approach=profile.get("relationship_approach", {}),
                decision_making=profile.get("decision_making_style", {})
            )

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
            traits = self.get_personality_traits(user_id)
            
            if not traits:
                return "No personality profile available."
            
            system_prompt = """You are an expert at creating natural, engaging personality summaries. 
            Create a flowing narrative that captures the essence of this person's personality."""
            
            user_prompt = f"""Based on the following personality traits, write a natural, engaging summary 
            that captures who this person is, how they think, feel, and interact with the world:
            
            {json.dumps(traits, indent=2)}
            
            Write in a warm, insightful tone that feels like it's describing a real person you know well."""
            
            summary = llm_service.generate_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating personality summary: {e}")
            raise
    
    def create_profile_from_stories(self, user_id: str = "default") -> PersonalityPipelineResult:
        """
        Complete pipeline to create a personality profile from all available story analyses.

        Args:
            user_id: User identifier

        Returns:
            PersonalityPipelineResult instance containing complete personality profile data
        """
        try:
            # Get all story analyses (now returns StoryAnalysis objects)
            analyses = supabase_client.get_story_analyses()

            if not analyses:
                logger.warning("No story analyses found for personality profile generation")
                return PersonalityPipelineResult(
                    status="no_analyses",
                    profile=PersonalityProfile(),
                    summary="No analyses available for profile generation",
                    source_analyses=0
                )

            # Convert StoryAnalysis objects to the expected format for personality generation
            analyses_dict = []
            for analysis in analyses:
                # Convert to extraction format for personality generation
                extraction_result = {
                    "trigger": {
                        "title": analysis.trigger_title,
                        "description": analysis.trigger_description,
                        "category": analysis.trigger_category
                    } if analysis.trigger_title else None,
                    "feelings": {"emotions": analysis.emotions},
                    "thought": {
                        "internal_monologue": analysis.internal_monologue
                    } if analysis.internal_monologue else None,
                    "value_analysis": {
                        "violated_value": analysis.violated_value,
                        "reasoning": analysis.value_reasoning,
                        "confidence_score": analysis.confidence_score
                    } if analysis.violated_value else None
                }
                analyses_dict.append({"extraction_results": extraction_result})

            # Generate personality profile
            profile_data = self.generate_personality_profile(analyses_dict, user_id)

            # Store in database (convert to PersonalityProfile if needed)
            if isinstance(profile_data, dict):
                personality_profile = PersonalityProfile.from_dict(profile_data)
            else:
                personality_profile = profile_data

            stored_profile = supabase_client.insert_personality_profile(personality_profile)

            # Generate summary
            summary = self.generate_personality_summary(user_id)

            result = PersonalityPipelineResult(
                status="success",
                profile=stored_profile,
                summary=summary,
                source_analyses=len(analyses)
            )

            logger.info(f"Created complete personality profile for user {user_id}")
            return result

        except Exception as e:
            logger.error(f"Error creating personality profile: {e}")
            raise


# Global personality profiler instance
personality_profiler = PersonalityProfiler()
