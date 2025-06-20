# Enhanced Conversational Engine

## Overview

The Enhanced Conversational Engine implements sophisticated conversation-focused state management that serves as the digital twin's short-term memory for user sessions. It provides dynamic context tracking, intelligent story repetition handling, and contextual awareness for natural dialogue flow.

## Core Architecture

### Conversation-Focused State Structure

The engine maintains a dynamic JSON state object that tracks the flow, context, and key concepts of conversations in real-time:

```json
{
  "session_id": "uuid-for-this-specific-conversation",
  "last_updated_timestamp": "2025-06-19T15:08:00Z",
  "turn_count": 5,
  "current_topics": ["Team Conflict", "Handling Deadlines"],
  "user_intent_history": ["request_story", "ask_clarification_question", "ask_opinion"],
  "retrieved_story_history": [
    {"story_id": "story_about_phoenix_conflict", "told_at_turn": 2},
    {"story_id": "story_about_early_career_failure", "told_at_turn": 4}
  ],
  "mentioned_concepts": {
    "deadline": {"count": 3, "first_mentioned_turn": 1, "last_mentioned_turn": 4},
    "team": {"count": 2, "first_mentioned_turn": 1, "last_mentioned_turn": 3}
  },
  "conversation_flow": {
    "dominant_theme": "Work Challenges",
    "theme_stability_count": 3,
    "last_topic_shift_turn": 2
  },
  "context_decay": {
    "topic_decay_threshold": 3,
    "concept_decay_threshold": 5,
    "story_repetition_penalty_base": 2.0
  }
}
```

## Key Features

### 1. Dynamic Context Tracking

**Real-time Analysis**: Every user message is analyzed to extract:
- Main topics and themes
- Key concepts and entities mentioned
- User intent (request_story, ask_opinion, seek_advice, etc.)

**State Updates**: The conversation state is continuously updated with:
- Current active topics (max 5 most recent)
- User intent history (last 5 intents)
- Mentioned concepts with frequency and recency tracking
- Conversation flow patterns

### 2. Intelligent Story Repetition Handling

**Dynamic Penalty System**: Stories receive repetition penalties based on recency:
- **Very Recent** (≤2 turns): 3x penalty multiplier
- **Recent** (≤5 turns): 2x penalty multiplier  
- **Somewhat Recent** (≤10 turns): 1.5x penalty multiplier
- **Old** (>10 turns): 1x penalty multiplier

**Smart Selection**: The system:
- Calculates base relevance scores for all stories
- Applies repetition penalties to previously told stories
- Selects stories with highest final scores
- Allows highly relevant stories to overcome repetition penalties

### 3. Context Decay Mechanisms

**Concept Decay**: Old concepts are automatically removed when:
- They haven't been mentioned for more than 5 turns
- New topics dominate the conversation for 3+ consecutive turns

**Topic Evolution**: The system tracks:
- Dominant themes and their stability
- Topic shift patterns
- Conversation maturity (new vs established)

### 4. Comprehensive Analytics

**Conversation Metrics**:
- Turn count and session duration
- Topic diversity and stability
- Story usage patterns and repetition rates
- Concept frequency and recency

**Real-time Insights**:
- Current conversation context
- Story selection rationale
- Repetition penalty calculations
- Context decay status

## Usage Examples

### Basic Conversation Flow

```python
from core.conversational_engine import conversational_engine

# Generate response with enhanced state management
result = conversational_engine.generate_response(
    user_message="I'm having trouble with my team at work",
    user_id="user_001"
)

# Access comprehensive response data
response = result["response"]
context = result["conversation_context"]
used_stories = result["used_stories"]
stories_considered = result["stories_considered"]

print(f"Response: {response}")
print(f"Turn: {context['turn_count']}")
print(f"Topics: {context['current_topics']}")
print(f"Theme: {context['dominant_theme']}")
```

### Conversation Analytics

```python
# Get conversation summary
summary = conversational_engine.get_conversation_summary("user_001")
print(f"Session: {summary['session_id']}")
print(f"Turns: {summary['turn_count']}")
print(f"Topics: {summary['current_topics']}")

# Get story usage statistics
stats = conversational_engine.get_story_usage_stats("user_001")
print(f"Stories told: {stats['total_stories_told']}")
print(f"Unique stories: {stats['unique_stories']}")
print(f"Repeated stories: {stats['repeated_stories']}")

# Get active topics
topics = conversational_engine.get_active_topics("user_001")
print(f"Active topics: {topics}")
```

### Conversation Management

```python
# Reset conversation state
success = conversational_engine.reset_conversation("user_001")
print(f"Reset successful: {success}")

# Check if context should reset (automatic)
state = conversational_engine.get_or_create_state("user_001")
should_reset = state.should_context_reset()
```

## State Update Loop

### On Each User Turn

1. **Increment Turn Counter**: Track conversation progress
2. **Analyze Input**: Extract topics, concepts, and intent
3. **Update State**: Refresh topics, intents, and concepts
4. **Apply Decay**: Remove stale concepts and topics
5. **Find Stories**: Score stories with repetition penalties
6. **Generate Response**: Use enhanced context for natural dialogue
7. **Record Usage**: Track story usage for future penalty calculations

### Story Selection Process

1. **Get Candidates**: Retrieve all available stories
2. **Calculate Base Scores**: Score relevance to current topics
3. **Apply Penalties**: Reduce scores for recently told stories
4. **Rank and Select**: Choose top stories after penalties
5. **Record Usage**: Track selected stories for future reference

## Advanced Features

### Context-Aware Response Generation

The engine provides rich context to the LLM for response generation:

```python
context_info = f"""
Conversation Context:
- Turn: {turn_count}
- Topics: {current_topics}
- Dominant Theme: {dominant_theme}
- Recent Intents: {recent_intents}
- Key Concepts: {key_concepts}
- Conversation Stage: {maturity_level}
"""
```

### Intelligent Topic Tracking

- **Multi-topic Support**: Tracks multiple concurrent topics
- **Topic Evolution**: Monitors how topics change over time
- **Theme Stability**: Measures conversation focus consistency
- **Shift Detection**: Identifies when conversations change direction

### Flexible Decay Configuration

```python
"context_decay": {
    "topic_decay_threshold": 3,        # Turns before topic decay
    "concept_decay_threshold": 5,      # Turns before concept removal
    "story_repetition_penalty_base": 2.0  # Base penalty multiplier
}
```

## Integration Points

### With Story Extraction Pipeline
- Uses structured extraction results for enhanced story selection
- Leverages psychological insights for contextual relevance
- Integrates trigger/emotion/value patterns into conversation flow

### With Personality Profiler
- Incorporates personality profiles into response generation
- Maintains character consistency across conversations
- Adapts communication style based on personality traits

### With Database Layer
- Persists conversation messages for continuity
- Stores conversation state for session recovery
- Tracks long-term conversation patterns

## Benefits

### 1. Natural Dialogue Flow
- **Context Continuity**: Maintains conversation thread across turns
- **Topic Awareness**: Responds appropriately to topic shifts
- **Intent Recognition**: Understands what users are trying to accomplish

### 2. Intelligent Story Management
- **Repetition Prevention**: Avoids boring users with repeated stories
- **Relevance Optimization**: Selects most appropriate stories for context
- **Dynamic Penalties**: Balances freshness with relevance

### 3. Sophisticated State Tracking
- **Real-time Updates**: Continuously adapts to conversation evolution
- **Comprehensive Analytics**: Provides insights into conversation patterns
- **Flexible Configuration**: Allows tuning of decay and penalty parameters

### 4. Production Readiness
- **Error Handling**: Graceful degradation when components fail
- **Performance Optimization**: Efficient state management and storage
- **Scalability**: Supports multiple concurrent conversations

## Testing

Run the comprehensive test suite:

```bash
python scripts/test_enhanced_conversation.py
```

This demonstrates:
- ✅ Conversation state tracking across multiple turns
- 🔄 Story repetition penalty system in action
- ⏰ Context decay and topic evolution
- 🛠️ Conversation utility methods
- 📊 Real-time analytics and insights

## Future Enhancements

- **Emotion Tracking**: Monitor emotional state throughout conversations
- **Personality Adaptation**: Adjust responses based on user personality
- **Multi-session Memory**: Connect conversations across sessions
- **Advanced Analytics**: Machine learning insights into conversation patterns
- **Real-time Optimization**: Dynamic parameter tuning based on conversation success
