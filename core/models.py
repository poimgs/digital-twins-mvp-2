"""
Database Models - Data classes representing database table structures.
Provides type-safe data structures for all database operations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID
import uuid


@dataclass
class Story:
    """Data class representing a story record from the stories table."""
    
    id: UUID = field(default_factory=uuid.uuid4)
    filename: Optional[str] = None
    title: Optional[str] = None
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Story':
        """Create a Story instance from a dictionary (e.g., from database)."""
        # Handle UUID conversion
        story_id = data.get('id')
        if isinstance(story_id, str):
            story_id = UUID(story_id)
        elif story_id is None:
            story_id = uuid.uuid4()
        
        # Handle datetime conversion
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        
        return cls(
            id=story_id,
            filename=data.get('filename'),
            title=data.get('title'),
            content=data.get('content', ''),
            metadata=data.get('metadata', {}),
            created_at=created_at,
            updated_at=updated_at
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Story instance to dictionary for database operations."""
        return {
            'id': str(self.id),
            'filename': self.filename,
            'title': self.title,
            'content': self.content,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


@dataclass
class StoryAnalysis:
    """Data class representing a story analysis record from the story_analysis table."""

    id: UUID = field(default_factory=uuid.uuid4)
    story_id: UUID = field(default_factory=uuid.uuid4)
    # Trigger information
    trigger_title: Optional[str] = None
    trigger_description: Optional[str] = None
    trigger_category: Optional[str] = None
    # Feelings/emotions
    emotions: List[str] = field(default_factory=list)
    # Thought/internal monologue
    internal_monologue: Optional[str] = None
    # Value analysis
    violated_value: Optional[str] = None
    value_reasoning: Optional[str] = None
    confidence_score: Optional[int] = None
    # Keep raw response for debugging/audit
    raw_response: Optional[str] = None
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StoryAnalysis':
        """Create a StoryAnalysis instance from a dictionary."""
        # Handle UUID conversion
        analysis_id = data.get('id')
        if isinstance(analysis_id, str):
            analysis_id = UUID(analysis_id)
        elif analysis_id is None:
            analysis_id = uuid.uuid4()

        story_id = data.get('story_id')
        if isinstance(story_id, str):
            story_id = UUID(story_id)
        elif story_id is None:
            story_id = uuid.uuid4()

        # Handle datetime conversion
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

        return cls(
            id=analysis_id,
            story_id=story_id,
            trigger_title=data.get('trigger_title'),
            trigger_description=data.get('trigger_description'),
            trigger_category=data.get('trigger_category'),
            emotions=data.get('emotions', []),
            internal_monologue=data.get('internal_monologue'),
            violated_value=data.get('violated_value'),
            value_reasoning=data.get('value_reasoning'),
            confidence_score=data.get('confidence_score'),
            raw_response=data.get('raw_response'),
            created_at=created_at
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert StoryAnalysis instance to dictionary for database operations."""
        return {
            'id': str(self.id),
            'story_id': str(self.story_id),
            'trigger_title': self.trigger_title,
            'trigger_description': self.trigger_description,
            'trigger_category': self.trigger_category,
            'emotions': self.emotions,
            'internal_monologue': self.internal_monologue,
            'violated_value': self.violated_value,
            'value_reasoning': self.value_reasoning,
            'confidence_score': self.confidence_score,
            'raw_response': self.raw_response,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }




@dataclass
class PersonalityProfile:
    """Data class representing a personality profile record from the personality_profiles table."""
    
    id: UUID = field(default_factory=uuid.uuid4)
    user_id: str = "default"
    profile: Dict[str, Any] = field(default_factory=dict)
    source_analyses_count: int = 0
    raw_response: Optional[str] = None
    profile_version: str = "1.0"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PersonalityProfile':
        """Create a PersonalityProfile instance from a dictionary."""
        # Handle UUID conversion
        profile_id = data.get('id')
        if isinstance(profile_id, str):
            profile_id = UUID(profile_id)
        elif profile_id is None:
            profile_id = uuid.uuid4()
        
        # Handle datetime conversion
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        
        return cls(
            id=profile_id,
            user_id=data.get('user_id', 'default'),
            profile=data.get('profile', {}),
            source_analyses_count=data.get('source_analyses_count', 0),
            raw_response=data.get('raw_response'),
            profile_version=data.get('profile_version', '1.0'),
            created_at=created_at,
            updated_at=updated_at
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert PersonalityProfile instance to dictionary for database operations."""
        return {
            'id': str(self.id),
            'user_id': self.user_id,
            'profile': self.profile,
            'source_analyses_count': self.source_analyses_count,
            'raw_response': self.raw_response,
            'profile_version': self.profile_version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


@dataclass
class ConversationMessage:
    """Data class representing a conversation message record from the conversation_history table."""
    
    id: UUID = field(default_factory=uuid.uuid4)
    user_id: str = "default"
    role: str = "user"  # 'user' or 'assistant'
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        """Create a ConversationMessage instance from a dictionary."""
        # Handle UUID conversion
        message_id = data.get('id')
        if isinstance(message_id, str):
            message_id = UUID(message_id)
        elif message_id is None:
            message_id = uuid.uuid4()
        
        # Handle datetime conversion
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        return cls(
            id=message_id,
            user_id=data.get('user_id', 'default'),
            role=data.get('role', 'user'),
            content=data.get('content', ''),
            metadata=data.get('metadata', {}),
            created_at=created_at
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ConversationMessage instance to dictionary for database operations."""
        return {
            'id': str(self.id),
            'user_id': self.user_id,
            'role': self.role,
            'content': self.content,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# Utility functions for working with models
def stories_from_dict_list(data_list: List[Dict[str, Any]]) -> List[Story]:
    """Convert a list of dictionaries to a list of Story instances."""
    return [Story.from_dict(data) for data in data_list]


def story_analyses_from_dict_list(data_list: List[Dict[str, Any]]) -> List[StoryAnalysis]:
    """Convert a list of dictionaries to a list of StoryAnalysis instances."""
    return [StoryAnalysis.from_dict(data) for data in data_list]


def conversation_messages_from_dict_list(data_list: List[Dict[str, Any]]) -> List[ConversationMessage]:
    """Convert a list of dictionaries to a list of ConversationMessage instances."""
    return [ConversationMessage.from_dict(data) for data in data_list]


# Schema-based dataclasses for structured responses
@dataclass
class TriggerExtraction:
    """Data class for trigger extraction results."""

    title: str
    description: str
    category: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TriggerExtraction':
        """Create a TriggerExtraction instance from a dictionary."""
        return cls(
            title=data.get('title', ''),
            description=data.get('description', ''),
            category=data.get('category', '')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert TriggerExtraction instance to dictionary."""
        return {
            'title': self.title,
            'description': self.description,
            'category': self.category
        }


@dataclass
class FeelingsExtraction:
    """Data class for feelings extraction results."""

    emotions: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeelingsExtraction':
        """Create a FeelingsExtraction instance from a dictionary."""
        return cls(
            emotions=data.get('emotions', [])
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert FeelingsExtraction instance to dictionary."""
        return {
            'emotions': self.emotions
        }


@dataclass
class ThoughtExtraction:
    """Data class for thought extraction results."""

    internal_monologue: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThoughtExtraction':
        """Create a ThoughtExtraction instance from a dictionary."""
        return cls(
            internal_monologue=data.get('internal_monologue', '')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert ThoughtExtraction instance to dictionary."""
        return {
            'internal_monologue': self.internal_monologue
        }


@dataclass
class ValueAnalysisExtraction:
    """Data class for value analysis extraction results."""

    violated_value: str
    reasoning: str
    confidence_score: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValueAnalysisExtraction':
        """Create a ValueAnalysisExtraction instance from a dictionary."""
        return cls(
            violated_value=data.get('violated_value', ''),
            reasoning=data.get('reasoning', ''),
            confidence_score=data.get('confidence_score', 1)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert ValueAnalysisExtraction instance to dictionary."""
        return {
            'violated_value': self.violated_value,
            'reasoning': self.reasoning,
            'confidence_score': self.confidence_score
        }


@dataclass
class UserInputAnalysis:
    """Data class for user input analysis results."""

    topics: List[str] = field(default_factory=list)
    concepts: List[str] = field(default_factory=list)
    intent: str = "general_conversation"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserInputAnalysis':
        """Create a UserInputAnalysis instance from a dictionary."""
        return cls(
            topics=data.get('topics', []),
            concepts=data.get('concepts', []),
            intent=data.get('intent', 'general_conversation')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert UserInputAnalysis instance to dictionary."""
        return {
            'topics': self.topics,
            'concepts': self.concepts,
            'intent': self.intent
        }


@dataclass
class TriggerPatterns:
    """Data class for trigger pattern analysis."""

    most_common_categories: List[str] = field(default_factory=list)
    recurring_themes: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TriggerPatterns':
        """Create a TriggerPatterns instance from a dictionary."""
        return cls(
            most_common_categories=data.get('most_common_categories', []),
            recurring_themes=data.get('recurring_themes', [])
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert TriggerPatterns instance to dictionary."""
        return {
            'most_common_categories': self.most_common_categories,
            'recurring_themes': self.recurring_themes
        }


@dataclass
class EmotionalPatterns:
    """Data class for emotional pattern analysis."""

    dominant_emotions: List[str] = field(default_factory=list)
    emotional_clusters: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmotionalPatterns':
        """Create an EmotionalPatterns instance from a dictionary."""
        return cls(
            dominant_emotions=data.get('dominant_emotions', []),
            emotional_clusters=data.get('emotional_clusters', [])
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert EmotionalPatterns instance to dictionary."""
        return {
            'dominant_emotions': self.dominant_emotions,
            'emotional_clusters': self.emotional_clusters
        }


@dataclass
class CognitivePatterns:
    """Data class for cognitive pattern analysis."""

    thinking_styles: List[str] = field(default_factory=list)
    recurring_concerns: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CognitivePatterns':
        """Create a CognitivePatterns instance from a dictionary."""
        return cls(
            thinking_styles=data.get('thinking_styles', []),
            recurring_concerns=data.get('recurring_concerns', [])
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert CognitivePatterns instance to dictionary."""
        return {
            'thinking_styles': self.thinking_styles,
            'recurring_concerns': self.recurring_concerns
        }


@dataclass
class ValuePatterns:
    """Data class for value pattern analysis."""

    core_values: List[str] = field(default_factory=list)
    trigger_value_relationships: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValuePatterns':
        """Create a ValuePatterns instance from a dictionary."""
        return cls(
            core_values=data.get('core_values', []),
            trigger_value_relationships=data.get('trigger_value_relationships', [])
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert ValuePatterns instance to dictionary."""
        return {
            'core_values': self.core_values,
            'trigger_value_relationships': self.trigger_value_relationships
        }


@dataclass
class PsychologicalInsights:
    """Data class for psychological insights analysis."""

    personality_traits: List[str] = field(default_factory=list)
    coping_mechanisms: List[str] = field(default_factory=list)
    growth_areas: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PsychologicalInsights':
        """Create a PsychologicalInsights instance from a dictionary."""
        return cls(
            personality_traits=data.get('personality_traits', []),
            coping_mechanisms=data.get('coping_mechanisms', []),
            growth_areas=data.get('growth_areas', [])
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert PsychologicalInsights instance to dictionary."""
        return {
            'personality_traits': self.personality_traits,
            'coping_mechanisms': self.coping_mechanisms,
            'growth_areas': self.growth_areas
        }


@dataclass
class ThemeExtraction:
    """Data class for theme extraction results."""

    trigger_patterns: TriggerPatterns = field(default_factory=TriggerPatterns)
    emotional_patterns: EmotionalPatterns = field(default_factory=EmotionalPatterns)
    cognitive_patterns: CognitivePatterns = field(default_factory=CognitivePatterns)
    value_patterns: ValuePatterns = field(default_factory=ValuePatterns)
    psychological_insights: PsychologicalInsights = field(default_factory=PsychologicalInsights)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThemeExtraction':
        """Create a ThemeExtraction instance from a dictionary."""
        return cls(
            trigger_patterns=TriggerPatterns.from_dict(data.get('trigger_patterns', {})),
            emotional_patterns=EmotionalPatterns.from_dict(data.get('emotional_patterns', {})),
            cognitive_patterns=CognitivePatterns.from_dict(data.get('cognitive_patterns', {})),
            value_patterns=ValuePatterns.from_dict(data.get('value_patterns', {})),
            psychological_insights=PsychologicalInsights.from_dict(data.get('psychological_insights', {}))
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert ThemeExtraction instance to dictionary."""
        return {
            'trigger_patterns': self.trigger_patterns.to_dict(),
            'emotional_patterns': self.emotional_patterns.to_dict(),
            'cognitive_patterns': self.cognitive_patterns.to_dict(),
            'value_patterns': self.value_patterns.to_dict(),
            'psychological_insights': self.psychological_insights.to_dict()
        }


@dataclass
class CoreValuesMotivations:
    """Data class for core values and motivations analysis."""

    core_values: str = ""
    anti_values: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CoreValuesMotivations':
        """Create a CoreValuesMotivations instance from a dictionary."""
        return cls(
            core_values=data.get('core_values', ''),
            anti_values=data.get('anti_values', '')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert CoreValuesMotivations instance to dictionary."""
        return {
            'core_values': self.core_values,
            'anti_values': self.anti_values
        }


@dataclass
class CommunicationStyleVoice:
    """Data class for communication style and voice analysis."""

    formality_vocabulary: str = ""
    tone: str = ""
    sentence_structure: str = ""
    recurring_phrases_metaphors: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommunicationStyleVoice':
        """Create a CommunicationStyleVoice instance from a dictionary."""
        return cls(
            formality_vocabulary=data.get('formality_vocabulary', ''),
            tone=data.get('tone', ''),
            sentence_structure=data.get('sentence_structure', ''),
            recurring_phrases_metaphors=data.get('recurring_phrases_metaphors', '')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert CommunicationStyleVoice instance to dictionary."""
        return {
            'formality_vocabulary': self.formality_vocabulary,
            'tone': self.tone,
            'sentence_structure': self.sentence_structure,
            'recurring_phrases_metaphors': self.recurring_phrases_metaphors
        }


@dataclass
class CognitiveStyleWorldview:
    """Data class for cognitive style and worldview analysis."""

    thinking_process: str = ""
    outlook: str = ""
    focus: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CognitiveStyleWorldview':
        """Create a CognitiveStyleWorldview instance from a dictionary."""
        return cls(
            thinking_process=data.get('thinking_process', ''),
            outlook=data.get('outlook', ''),
            focus=data.get('focus', '')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert CognitiveStyleWorldview instance to dictionary."""
        return {
            'thinking_process': self.thinking_process,
            'outlook': self.outlook,
            'focus': self.focus
        }


@dataclass
class PersonalityAnalysis:
    """Data class for personality analysis results."""

    core_values_motivations: CoreValuesMotivations = field(default_factory=CoreValuesMotivations)
    communication_style_voice: CommunicationStyleVoice = field(default_factory=CommunicationStyleVoice)
    cognitive_style_worldview: CognitiveStyleWorldview = field(default_factory=CognitiveStyleWorldview)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PersonalityAnalysis':
        """Create a PersonalityAnalysis instance from a dictionary."""
        return cls(
            core_values_motivations=CoreValuesMotivations.from_dict(data.get('core_values_motivations', {})),
            communication_style_voice=CommunicationStyleVoice.from_dict(data.get('communication_style_voice', {})),
            cognitive_style_worldview=CognitiveStyleWorldview.from_dict(data.get('cognitive_style_worldview', {}))
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert PersonalityAnalysis instance to dictionary."""
        return {
            'core_values_motivations': self.core_values_motivations.to_dict(),
            'communication_style_voice': self.communication_style_voice.to_dict(),
            'cognitive_style_worldview': self.cognitive_style_worldview.to_dict()
        }


@dataclass
class StoryProcessingResult:
    """Data class for story processing pipeline results."""

    status: str
    total_stories: int
    processed_stories: int
    key_themes: ThemeExtraction

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StoryProcessingResult':
        """Create a StoryProcessingResult instance from a dictionary."""
        return cls(
            status=data.get('status', 'unknown'),
            total_stories=data.get('total_stories', 0),
            processed_stories=data.get('processed_stories', 0),
            key_themes=ThemeExtraction.from_dict(data.get('key_themes', {}))
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert StoryProcessingResult instance to dictionary."""
        return {
            'status': self.status,
            'total_stories': self.total_stories,
            'processed_stories': self.processed_stories,
            'key_themes': self.key_themes.to_dict()
        }


@dataclass
class PersonalityTraits:
    """Data class for extracted personality traits."""

    core_traits: List[str] = field(default_factory=list)
    communication_style: Dict[str, Any] = field(default_factory=dict)
    emotional_patterns: Dict[str, Any] = field(default_factory=dict)
    values: List[str] = field(default_factory=list)
    behavioral_tendencies: List[str] = field(default_factory=list)
    relationship_approach: Dict[str, Any] = field(default_factory=dict)
    decision_making: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PersonalityTraits':
        """Create a PersonalityTraits instance from a dictionary."""
        return cls(
            core_traits=data.get('core_traits', []),
            communication_style=data.get('communication_style', {}),
            emotional_patterns=data.get('emotional_patterns', {}),
            values=data.get('values', []),
            behavioral_tendencies=data.get('behavioral_tendencies', []),
            relationship_approach=data.get('relationship_approach', {}),
            decision_making=data.get('decision_making', {})
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert PersonalityTraits instance to dictionary."""
        return {
            'core_traits': self.core_traits,
            'communication_style': self.communication_style,
            'emotional_patterns': self.emotional_patterns,
            'values': self.values,
            'behavioral_tendencies': self.behavioral_tendencies,
            'relationship_approach': self.relationship_approach,
            'decision_making': self.decision_making
        }


@dataclass
class PersonalityPipelineResult:
    """Data class for complete personality pipeline results."""

    status: str
    profile: PersonalityProfile
    summary: str
    source_analyses: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PersonalityPipelineResult':
        """Create a PersonalityPipelineResult instance from a dictionary."""
        return cls(
            status=data.get('status', 'unknown'),
            profile=PersonalityProfile.from_dict(data.get('profile', {})),
            summary=data.get('summary', ''),
            source_analyses=data.get('source_analyses', 0)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert PersonalityPipelineResult instance to dictionary."""
        return {
            'status': self.status,
            'profile': self.profile.to_dict(),
            'summary': self.summary,
            'source_analyses': self.source_analyses
        }
