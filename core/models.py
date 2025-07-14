"""
Database Models - Data classes representing database table structures.
Provides type-safe data structures for all database operations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, Any, Optional, List
from uuid import UUID
import uuid
import re

def normalize_timestamp(timestamp_str: str) -> str:
    """
    Normalize Supabase timestamp strings to handle variable microsecond precision.
    
    Supabase can return timestamps like:
    - 2025-07-14 15:59:00.17095+00
    - 2025-07-14 15:59:00.1+00
    - 2025-07-14 15:59:00.123456+00
    
    This function ensures microseconds are padded to 6 digits or removed if all zeros.
    """
    # Replace 'Z' with '+00:00' for timezone handling
    timestamp_str = timestamp_str.replace('Z', '+00:00')
    
    # Pattern to match timestamps with optional microseconds (handles both space and T separators)
    pattern = r'(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?(\+\d{2}:?\d{2}|Z)$'
    match = re.match(pattern, timestamp_str)
    
    if not match:
        # If no match, return as-is and let fromisoformat handle it
        return timestamp_str
    
    base_time, microseconds, timezone = match.groups()
    
    if microseconds:
        # Pad microseconds to 6 digits or truncate if longer
        microseconds = microseconds.ljust(6, '0')[:6]
        # Remove trailing zeros for cleaner format
        microseconds = microseconds.rstrip('0')
        if microseconds:
            return f"{base_time}.{microseconds}{timezone}"
    
    return f"{base_time}{timezone}"

@dataclass
class Bot:
    """Data class representing a bot record from the bots table."""

    id: UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    description: Optional[str] = None
    welcome_message: str = ""
    call_to_action: str = ""
    call_to_action_keyword: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Bot':
        """Create a Bot instance from a dictionary (e.g., from database)."""
        # Handle UUID conversion
        bot_id = data.get('id')
        if isinstance(bot_id, str):
            bot_id = UUID(bot_id)
        elif bot_id is None:
            bot_id = uuid.uuid4()

        # Handle datetime conversion
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(normalize_timestamp(created_at))

        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(normalize_timestamp(updated_at))

        return cls(
            id=bot_id,
            name=data.get('name', ''),
            description=data.get('description'),
            welcome_message=data.get('welcome_message', ''),
            call_to_action=data.get('call_to_action', ''),
            call_to_action_keyword=data.get('call_to_action_keyword', 'NO CTA PROVIDED FOR BOT'),
            created_at=created_at,
            updated_at=updated_at
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Bot instance to dictionary for database operations."""
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'welcome_message': self.welcome_message,
            'call_to_action': self.call_to_action,
            'call_to_action_keyword': self.call_to_action_keyword,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


@dataclass
class Story:
    """Data class representing a story record from the stories table."""

    id: UUID = field(default_factory=uuid.uuid4)
    bot_id: UUID = field(default_factory=uuid.uuid4)
    category_type: str = "stories"
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

        bot_id = data.get('bot_id')
        if isinstance(bot_id, str):
            bot_id = UUID(bot_id)
        elif bot_id is None:
            bot_id = uuid.uuid4()

        # Handle datetime conversion
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(normalize_timestamp(created_at))

        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(normalize_timestamp(updated_at))

        return cls(
            id=story_id,
            bot_id=bot_id,
            category_type=data.get('category_type', 'stories'),
            title=data.get('title'),
            content=data.get('content', ''),
            created_at=created_at,
            updated_at=updated_at
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Story instance to dictionary for database operations."""
        return {
            'id': str(self.id),
            'bot_id': str(self.bot_id),
            'category_type': self.category_type,
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
    summary: str = field(default_factory=str)
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
            created_at = datetime.fromisoformat(normalize_timestamp(created_at))

        return cls(
            id=analysis_id,
            story_id=story_id,
            summary=data.get('summary', ''),
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
            'summary': self.summary,
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
    bot_id: UUID = field(default_factory=uuid.uuid4)
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

        bot_id = data.get('bot_id')
        if isinstance(bot_id, str):
            bot_id = UUID(bot_id)
        elif bot_id is None:
            bot_id = uuid.uuid4()

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
            created_at = datetime.fromisoformat(normalize_timestamp(created_at))

        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(normalize_timestamp(updated_at))

        return cls(
            id=profile_id,
            bot_id=bot_id,
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
            'bot_id': str(self.bot_id),
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
class InitialQuestion:
    """Data class representing an initial question record from the initial_questions table."""

    id: UUID = field(default_factory=uuid.uuid4)
    bot_id: UUID = field(default_factory=uuid.uuid4)
    category_type: str = "stories"
    question: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InitialQuestion':
        """Create an InitialQuestion instance from a dictionary (e.g., from database)."""
        # Handle UUID conversion
        question_id = data.get('id')
        if isinstance(question_id, str):
            question_id = UUID(question_id)
        elif question_id is None:
            question_id = uuid.uuid4()

        bot_id = data.get('bot_id')
        if isinstance(bot_id, str):
            bot_id = UUID(bot_id)
        elif bot_id is None:
            bot_id = uuid.uuid4()

        category_type = data.get('category_type', 'stories')

        # Handle datetime conversion
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(normalize_timestamp(created_at))

        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(normalize_timestamp(updated_at))

        return cls(
            id=question_id,
            bot_id=bot_id,
            category_type=category_type,
            question=data.get('question', ''),
            created_at=created_at,
            updated_at=updated_at
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert InitialQuestion instance to dictionary for database operations."""
        return {
            'id': str(self.id),
            'bot_id': str(self.bot_id),
            'category_type': self.category_type,
            'question': self.question,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


@dataclass
class LLMMessage:
    """Data class representing a message in LLM service format."""

    role: str  # 'system', 'user', or 'assistant'
    content: str

    def __post_init__(self):
        """Validate role and content after initialization."""
        if self.role not in ['system', 'user', 'assistant']:
            raise ValueError("Role must be 'system', 'user', or 'assistant'")

        # Ensure content is not None and is a string
        if self.content is None:
            self.content = ""
        elif not isinstance(self.content, str):
            self.content = str(self.content)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMMessage':
        """Create an LLMMessage instance from a dictionary."""
        content = data.get('content', '')
        # Handle None content from database
        if content is None:
            content = ''
        return cls(
            role=data.get('role', 'user'),
            content=content
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
    chat_id: str = ""
    bot_id: UUID = field(default_factory=uuid.uuid4)
    conversation_number: int = 1
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

        bot_id = data.get('bot_id')
        if isinstance(bot_id, str):
            bot_id = UUID(bot_id)
        elif bot_id is None:
            bot_id = uuid.uuid4()

        # Handle datetime conversion
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(normalize_timestamp(created_at))

        return cls(
            id=message_id,
            chat_id=data.get('chat_id', ''),
            bot_id=bot_id,
            conversation_number=data.get('conversation_number', 1),
            role=data.get('role', 'user'),
            content=data.get('content', ''),
            created_at=created_at
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert ConversationMessage instance to dictionary for database operations."""
        return {
            'id': str(self.id),
            'chat_id': self.chat_id,
            'bot_id': str(self.bot_id),
            'conversation_number': self.conversation_number,
            'role': self.role,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def to_llm_message(self) -> LLMMessage:
        """Convert ConversationMessage to LLM service message format."""
        # Ensure content is not empty
        content = self.content if self.content else ""
        return LLMMessage(
            role=self.role,
            content=content
        )


# Utility functions for working with models
def stories_from_dict_list(data_list: List[Dict[str, Any]]) -> List[Story]:
    """Convert a list of dictionaries to a list of Story instances."""
    return [Story.from_dict(data) for data in data_list]


def story_analyses_from_dict_list(data_list: List[Dict[str, Any]]) -> List[StoryAnalysis]:
    """Convert a list of dictionaries to a list of StoryAnalysis instances."""
    return [StoryAnalysis.from_dict(data) for data in data_list]




def initial_questions_from_dict_list(data_list: List[Dict[str, Any]]) -> List[InitialQuestion]:
    """Convert a list of dictionaries to a list of InitialQuestion instances."""
    return [InitialQuestion.from_dict(data) for data in data_list]


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

class WarmthLevel(Enum):
    IS = 1
    DID = 2
    CAN = 3
    WILL = 4
    WOULD = 5
    MIGHT = 6

    @classmethod
    def from_warmth_level(cls, warmth_level: int) -> 'WarmthLevel':
        """Get the warmth level for a given warmth level."""
        return cls(warmth_level)

    @classmethod
    def get_warmth_level(cls, warmth_level: int) -> int:
        """Get the warmth level for a given warmth level."""
        return cls.from_warmth_level(warmth_level).value
    
    def get_question_type(self):
        """Get the question type for a given warmth level."""
        if self.value == 1:
            return 'Factual'
        elif self.value == 2:
            return 'Historical Factual'
        elif self.value == 3:
            return 'Capability'
        elif self.value == 4:
            return 'Intention'
        elif self.value == 5:
            return 'Hypothetical'
        elif self.value == 6:
            return 'Speculative'
        else:
            raise ValueError(f"Invalid warmth level: {self.value}")

@dataclass
class ConversationState:
    """Data class representing a conversation state record from the conversation_state table."""

    id: UUID = field(default_factory=uuid.uuid4)
    chat_id: str = ""
    bot_id: UUID = field(default_factory=uuid.uuid4)
    conversation_number: int = 1
    summary: str = ""
    current_warmth_level: int = WarmthLevel.IS.value
    max_warmth_achieved: int = WarmthLevel.IS.value
    follow_up_questions: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationState':
        """Create a ConversationState instance from a dictionary."""
        # Handle UUID conversion
        state_id = data.get('id')
        if isinstance(state_id, str):
            state_id = UUID(state_id)
        elif state_id is None:
            state_id = uuid.uuid4()

        bot_id = data.get('bot_id')
        if isinstance(bot_id, str):
            bot_id = UUID(bot_id)
        elif bot_id is None:
            bot_id = uuid.uuid4()

        # Handle datetime conversion
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(normalize_timestamp(created_at))

        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(normalize_timestamp(updated_at))

        return cls(
            id=state_id,
            chat_id=data.get('chat_id', ''),
            bot_id=bot_id,
            conversation_number=data.get('conversation_number', 1),
            summary=data.get('summary', ''),
            current_warmth_level=data.get('current_warmth_level', WarmthLevel.IS.value),
            max_warmth_achieved=data.get('max_warmth_achieved', WarmthLevel.IS.value),
            follow_up_questions=data.get('follow_up_questions', []),
            created_at=created_at,
            updated_at=updated_at
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert ConversationState instance to dictionary for database operations."""
        return {
            'id': str(self.id),
            'chat_id': self.chat_id,
            'bot_id': str(self.bot_id),
            'conversation_number': self.conversation_number,
            'summary': self.summary,
            'current_warmth_level': self.current_warmth_level,
            'max_warmth_achieved': self.max_warmth_achieved,
            'follow_up_questions': self.follow_up_questions,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


@dataclass
class StoryWithAnalysis:
    """Data class representing a story with its corresponding analysis."""

    # Story fields
    id: UUID = field(default_factory=uuid.uuid4)
    bot_id: UUID = field(default_factory=uuid.uuid4)
    category_type: str = "stories"
    title: Optional[str] = None
    content: str = ""
    story_created_at: Optional[datetime] = None
    story_updated_at: Optional[datetime] = None

    # Analysis fields (optional)
    analysis_id: Optional[UUID] = None
    summary: Optional[str] = None
    triggers: List[str] = field(default_factory=list)
    emotions: List[str] = field(default_factory=list)
    thoughts: List[str] = field(default_factory=list)
    values: List[str] = field(default_factory=list)
    analysis_created_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StoryWithAnalysis':
        """Create a StoryWithAnalysis instance from a dictionary (typically from a JOIN query)."""
        # Handle UUID conversion for story ID
        story_id = data.get('id')
        if isinstance(story_id, str):
            story_id = UUID(story_id)
        elif story_id is None:
            story_id = uuid.uuid4()

        # Handle UUID conversion for bot ID
        bot_id = data.get('bot_id')
        if isinstance(bot_id, str):
            bot_id = UUID(bot_id)
        elif bot_id is None:
            bot_id = uuid.uuid4()

        # Handle UUID conversion for analysis ID
        analysis_id = data.get('analysis_id')
        if isinstance(analysis_id, str):
            analysis_id = UUID(analysis_id)
        elif analysis_id is None:
            analysis_id = None

        # Handle datetime conversion for story timestamps
        story_created_at = data.get('created_at') or data.get('story_created_at')
        if isinstance(story_created_at, str):
            story_created_at = datetime.fromisoformat(normalize_timestamp(story_created_at))

        story_updated_at = data.get('updated_at') or data.get('story_updated_at')
        if isinstance(story_updated_at, str):
            story_updated_at = datetime.fromisoformat(normalize_timestamp(story_updated_at))

        # Handle datetime conversion for analysis timestamp
        analysis_created_at = data.get('analysis_created_at')
        if isinstance(analysis_created_at, str):
            analysis_created_at = datetime.fromisoformat(normalize_timestamp(analysis_created_at))

        return cls(
            id=story_id,
            bot_id=bot_id,
            category_type=data.get('category_type', 'stories'),
            title=data.get('title'),
            content=data.get('content', ''),
            story_created_at=story_created_at,
            story_updated_at=story_updated_at,
            analysis_id=analysis_id,
            summary=data.get('summary'),
            triggers=data.get('triggers', []),
            emotions=data.get('emotions', []),
            thoughts=data.get('thoughts', []),
            values=data.get('values', []),
            analysis_created_at=analysis_created_at
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert StoryWithAnalysis instance to dictionary for API responses."""
        return {
            'id': str(self.id),
            'bot_id': str(self.bot_id),
            'category_type': self.category_type,
            'title': self.title,
            'content': self.content,
            'story_created_at': self.story_created_at.isoformat() if self.story_created_at else None,
            'story_updated_at': self.story_updated_at.isoformat() if self.story_updated_at else None,
            'analysis_id': str(self.analysis_id) if self.analysis_id else None,
            'summary': self.summary,
            'triggers': self.triggers,
            'emotions': self.emotions,
            'thoughts': self.thoughts,
            'values': self.values,
            'analysis_created_at': self.analysis_created_at.isoformat() if self.analysis_created_at else None
        }

    def has_analysis(self) -> bool:
        """Check if this story has analysis data."""
        return self.analysis_id is not None

    def get_analysis_dict(self) -> Dict[str, Any]:
        """Get analysis data as a dictionary for compatibility with existing code."""
        return {
            'summary': self.summary,
            'triggers': self.triggers,
            'emotions': self.emotions,
            'thoughts': self.thoughts,
            'values': self.values
        }


def stories_with_analysis_from_dict_list(data_list: List[Dict[str, Any]]) -> List[StoryWithAnalysis]:
    """Convert a list of dictionaries to StoryWithAnalysis instances."""
    return [StoryWithAnalysis.from_dict(data) for data in data_list]


@dataclass
class TokenUsage:
    """Data class representing token usage tracking for LLM API calls."""

    id: UUID = field(default_factory=uuid.uuid4)
    bot_id: Optional[UUID] = None
    chat_id: Optional[str] = None
    conversation_number: Optional[int] = None
    operation_type: str = ""  # 'conversation', 'follow_up_questions', 'story_analysis', etc.
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    request_metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TokenUsage':
        """Create a TokenUsage instance from a dictionary."""
        # Handle UUID conversion
        usage_id = data.get('id')
        if isinstance(usage_id, str):
            usage_id = UUID(usage_id)
        elif usage_id is None:
            usage_id = uuid.uuid4()

        bot_id = data.get('bot_id')
        if isinstance(bot_id, str):
            bot_id = UUID(bot_id)

        # Handle datetime conversion
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(normalize_timestamp(created_at))

        return cls(
            id=usage_id,
            bot_id=bot_id,
            chat_id=data.get('chat_id'),
            conversation_number=data.get('conversation_number'),
            operation_type=data.get('operation_type', ''),
            model=data.get('model', ''),
            prompt_tokens=data.get('prompt_tokens', 0),
            completion_tokens=data.get('completion_tokens', 0),
            total_tokens=data.get('total_tokens', 0),
            temperature=data.get('temperature'),
            max_tokens=data.get('max_tokens'),
            request_metadata=data.get('request_metadata', {}),
            created_at=created_at
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert TokenUsage instance to dictionary for database operations."""
        return {
            'id': str(self.id),
            'bot_id': str(self.bot_id) if self.bot_id else None,
            'chat_id': self.chat_id,
            'conversation_number': self.conversation_number,
            'operation_type': self.operation_type,
            'model': self.model,
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'total_tokens': self.total_tokens,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'request_metadata': self.request_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


def token_usage_from_dict_list(data_list: List[Dict[str, Any]]) -> List[TokenUsage]:
    """Convert a list of dictionaries to a list of TokenUsage instances."""
    return [TokenUsage.from_dict(data) for data in data_list]


def bots_from_dict_list(data_list: List[Dict[str, Any]]) -> List[Bot]:
    """Convert a list of dictionaries to a list of Bot instances."""
    return [Bot.from_dict(data) for data in data_list]


def generate_chat_id(bot_id: str, user_id: str) -> str:
    """
    Generate a chat_id from bot_id and user_id.
    For Telegram, user_id will be the Telegram chat_id.
    """
    return f"{bot_id}_{user_id}"


def parse_chat_id(chat_id: str) -> tuple[str, str]:
    """
    Parse a chat_id to extract bot_id and user_id.
    Returns (bot_id, user_id) where user_id could be a Telegram chat_id or 'default'.
    """
    parts = chat_id.split('_', 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid chat_id format: {chat_id}. Expected format: bot_id_user_id")
    return parts[0], parts[1]


def generate_telegram_chat_id(bot_id: str, telegram_chat_id: int) -> str:
    """Generate a chat_id for Telegram using numeric chat_id."""
    return f"{bot_id}_{telegram_chat_id}"


def generate_terminal_chat_id(bot_id: str, user_id: str = "default") -> str:
    """Generate a chat_id for terminal app using default or custom user_id."""
    return f"{bot_id}_{user_id}"


@dataclass
class ConversationResponse:
    """Data class representing a conversation response."""

    response: str
    follow_up_questions: List[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationResponse':
        """Create a ConversationResponse instance from a dictionary."""
        return cls(
            response=data.get('response', ''),
            follow_up_questions=data.get('follow_up_questions', [])
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert ConversationResponse instance to dictionary for API responses."""
        return {
            'response': self.response,
            'follow_up_questions': self.follow_up_questions
        }
        
@dataclass
class ContentItem:
    """Unified content item that can represent either a story or content category."""

    id: str
    category_type: str
    title: Optional[str]
    content: str
    summary: Optional[str]

    @classmethod
    def from_story(cls, story: StoryWithAnalysis) -> 'ContentItem':
        """Create ContentItem from StoryWithAnalysis (unified content structure)."""
        return cls(
            id=str(story.id),
            category_type=story.category_type,
            title=story.title,
            content=story.content,
            summary=story.summary
        )
