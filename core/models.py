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
    title: Optional[str] = None
    content: str = ""
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
            title=data.get('title'),
            content=data.get('content', ''),
            created_at=created_at,
            updated_at=updated_at
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Story instance to dictionary for database operations."""
        return {
            'id': str(self.id),
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


@dataclass
class StoryAnalysis:
    """Data class representing a story analysis record from the story_analysis table."""

    id: UUID = field(default_factory=uuid.uuid4)
    story_id: UUID = field(default_factory=uuid.uuid4)
    triggers: List[str] = field(default_factory=list)
    emotions: List[str] = field(default_factory=list)
    thoughts: List[str] = field(default_factory=list)
    values: List[str] = field(default_factory=list)
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
            triggers=data.get('triggers', []),
            emotions=data.get('emotions', []),
            thoughts=data.get('thoughts', []),
            values=data.get('values', []),
            created_at=created_at
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert StoryAnalysis instance to dictionary for database operations."""
        return {
            'id': str(self.id),
            'story_id': str(self.story_id),
            'triggers': self.triggers,
            'emotions': self.emotions,
            'thoughts': self.thoughts,
            'values': self.values,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }




@dataclass
class PersonalityProfile:
    """Data class representing a personality profile record from the personality_profiles table."""
    
    id: UUID = field(default_factory=uuid.uuid4)
    values: List[str] = field(default_factory=list)
    formality_vocabulary: str = ""
    tone: str = ""
    sentence_structure: str = ""
    recurring_phrases_metaphors: str = ""
    emotional_expression: str = ""
    storytelling_style: str = ""
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
        
        # Handle profile data conversion
        values = data.get('values', [])
        formality_vocabulary = data.get('formality_vocabulary', '')
        tone = data.get('tone', '')
        sentence_structure = data.get('sentence_structure', '')
        recurring_phrases_metaphors = data.get('recurring_phrases_metaphors', '')
        emotional_expression = data.get('emotional_expression', '')
        storytelling_style = data.get('storytelling_style', '')
        
        
        # Handle datetime conversion
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        
        return cls(
            id=profile_id,
            values=values,
            formality_vocabulary=formality_vocabulary,
            tone=tone,
            sentence_structure=sentence_structure,
            recurring_phrases_metaphors=recurring_phrases_metaphors,
            emotional_expression=emotional_expression,
            storytelling_style=storytelling_style,
            created_at=created_at,
            updated_at=updated_at
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert PersonalityProfile instance to dictionary for database operations."""
        return {
            'id': str(self.id),
            'values': self.values,
            'formality_vocabulary': self.formality_vocabulary,
            'tone': self.tone,
            'sentence_structure': self.sentence_structure,
            'recurring_phrases_metaphors': self.recurring_phrases_metaphors,
            'emotional_expression': self.emotional_expression,
            'storytelling_style': self.storytelling_style,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


@dataclass
class LLMMessage:
    """Data class representing a message in LLM service format."""

    role: str  # 'system', 'user', or 'assistant'
    content: str

    def __post_init__(self):
        """Validate role after initialization."""
        if self.role not in ['system', 'user', 'assistant']:
            raise ValueError("Role must be 'system', 'user', or 'assistant'")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMMessage':
        """Create an LLMMessage instance from a dictionary."""
        return cls(
            role=data.get('role', 'user'),
            content=data.get('content', '')
        )

    def to_dict(self) -> Dict[str, str]:
        """Convert LLMMessage instance to dictionary."""
        return {
            'role': self.role,
            'content': self.content
        }


@dataclass
class ConversationMessage:
    """Data class representing a conversation message record from the conversation_history table."""

    id: UUID = field(default_factory=uuid.uuid4)
    user_id: str = "default"
    role: str = "user"  # 'system', 'user', or 'assistant'
    content: str = ""
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
            created_at=created_at
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ConversationMessage instance to dictionary for database operations."""
        return {
            'id': str(self.id),
            'user_id': self.user_id,
            'role': self.role,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def to_llm_message(self) -> LLMMessage:
        """Convert ConversationMessage to LLM service message format."""
        return LLMMessage(
            role=self.role,
            content=self.content
        )


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


def conversation_messages_to_llm_format(messages: List[ConversationMessage]) -> List[LLMMessage]:
    """Convert a list of ConversationMessage instances to LLM service format."""
    return [message.to_llm_message() for message in messages]


def llm_messages_to_dict_list(messages: List[LLMMessage]) -> List[Dict[str, str]]:
    """Convert a list of LLMMessage instances to dictionary format."""
    return [message.to_dict() for message in messages]


def dict_list_to_llm_messages(data_list: List[Dict[str, str]]) -> List[LLMMessage]:
    """Convert a list of dictionaries to LLMMessage instances."""
    return [LLMMessage.from_dict(data) for data in data_list]


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