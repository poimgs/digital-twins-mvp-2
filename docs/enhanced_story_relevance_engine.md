# Enhanced Story Relevance Engine

## Overview

The Enhanced Story Relevance Engine implements a sophisticated multi-stage pipeline for intelligent story selection that leverages both conversational context and structured story analysis metadata. It combines metadata-based filtering, semantic relevance scoring, and intelligent repetition handling to deliver the most appropriate stories for any conversation context.

## Architecture

### Multi-Stage Pipeline

The engine operates through three distinct stages:

1. **Stage 1: Metadata-Based Filtering**
   - Filters stories using structured analysis data
   - Aligns trigger categories with conversation topics
   - Matches emotional context and violated values
   - Reduces candidate pool to most contextually relevant stories

2. **Stage 2: Semantic Relevance Scoring**
   - Uses LLM judge for deep semantic analysis
   - Considers conversation context and story content
   - Evaluates psychological alignment and appropriateness
   - Provides nuanced relevance scoring (0-10)

3. **Stage 3: Comprehensive Ranking & Selection**
   - Combines metadata and semantic scores with weighted formula
   - Applies dynamic repetition penalties
   - Adds confidence bonuses for high-quality analysis
   - Selects top stories above minimum threshold

## Key Components

### 1. Metadata-Based Filtering

**Trigger Category Alignment:**
```python
# Matches conversation topics with story trigger categories
if trigger_category in ["Social Interaction", "Stressor"] and "work" in topic.lower():
    metadata_score += 1.5
```

**Emotional Context Matching:**
```python
# Aligns user intent with story emotions
if "seek_advice" in recent_intents and any(emotion in ["frustrated", "angry"] for emotion in emotions):
    metadata_score += 2.0
```

**Value Alignment Scoring:**
```python
# Matches conversation concepts with violated values
for concept in key_concepts:
    if concept.lower() in violated_value:
        metadata_score += confidence * 0.5
```

### 2. Semantic Relevance Scoring

**LLM Judge System:**
- Analyzes conversation context vs story content
- Considers psychological appropriateness
- Evaluates potential to advance conversation
- Provides detailed reasoning for scores

**Context-Rich Analysis:**
```python
context_description = f"""
Current Topics: {current_topics}
Dominant Theme: {dominant_theme}
Recent User Intents: {recent_intents}
Key Concepts: {key_concepts}
Conversation Maturity: {conversation_maturity}
"""
```

### 3. Comprehensive Scoring Formula

**Weighted Combination:**
```python
weights = {
    "metadata": 0.3,      # 30% weight for metadata alignment
    "semantic": 0.7       # 70% weight for semantic relevance
}

base_score = (weights["metadata"] * metadata_score + 
             weights["semantic"] * semantic_score)
```

**Dynamic Penalties & Bonuses:**
- Repetition penalties based on recency
- Confidence bonuses for high-quality analysis
- Minimum threshold filtering

## Enhanced Features

### Intelligent Repetition Handling

**Dynamic Penalty System:**
- **Very Recent** (≤2 turns): 3x penalty multiplier
- **Recent** (≤5 turns): 2x penalty multiplier
- **Somewhat Recent** (≤10 turns): 1.5x penalty multiplier
- **Old** (>10 turns): 1x penalty multiplier

**Smart Selection Logic:**
- Highly relevant stories can overcome repetition penalties
- Balances freshness with relevance
- Prevents boring repetition while allowing important re-sharing

### Context-Aware Analysis

**Multi-Dimensional Context:**
- Current conversation topics
- Dominant themes and stability
- Recent user intents and goals
- Key concepts and entities mentioned
- Conversation maturity level

**Psychological Alignment:**
- Trigger category matching
- Emotional resonance analysis
- Value system alignment
- Thought pattern compatibility

### Performance Analytics

**Story Selection Metrics:**
```python
analytics = {
    "total_stories_told": total_stories,
    "unique_stories": unique_stories,
    "repetition_rate": repetition_rate,
    "average_repetition_gap": avg_repetition_gap,
    "stories_per_turn_ratio": stories_per_turn_ratio
}
```

**Relevance Insights:**
- Detailed score breakdowns
- Selection reasoning
- Performance comparisons
- Optimization recommendations

## Usage Examples

### Basic Enhanced Story Selection

```python
from core.conversational_engine import conversational_engine

# Get conversational state
state = conversational_engine.get_or_create_state("user_001")

# Find relevant stories using enhanced pipeline
relevant_stories = conversational_engine.find_relevant_stories(
    state=state,
    limit=3,
    use_enhanced_relevance=True
)

# Access detailed scoring information
for story in relevant_stories:
    print(f"Story: {story['id']}")
    print(f"Score: {story['relevance_score']:.2f}")
    print(f"Reasoning: {story['selection_reasoning']}")
    print(f"Breakdown: {story['score_breakdown']}")
```

### Performance Analysis

```python
# Analyze story selection performance
performance = conversational_engine.analyze_story_selection_performance("user_001")

if performance["status"] == "success":
    analytics = performance["analytics"]
    print(f"Repetition rate: {analytics['repetition_rate']:.1%}")
    print(f"Average gap: {analytics['average_repetition_gap']:.1f} turns")

# Get detailed relevance insights
insights = conversational_engine.get_story_relevance_insights("user_001", limit=5)

if insights["status"] == "success":
    for story in insights["insights"]["top_stories"]:
        print(f"Rank {story['rank']}: {story['story_id']} - {story['relevance_score']:.2f}")
```

### Fallback Mechanisms

```python
# Enhanced pipeline with automatic fallback
relevant_stories = conversational_engine.find_relevant_stories(
    state=state,
    limit=3,
    use_enhanced_relevance=True  # Falls back to basic if enhanced fails
)

# Explicit basic relevance (for comparison)
basic_stories = conversational_engine.find_relevant_stories(
    state=state,
    limit=3,
    use_enhanced_relevance=False
)
```

## Configuration & Tuning

### Scoring Weights

Adjust the balance between metadata and semantic scoring:

```python
weights = {
    "metadata": 0.3,      # Increase for more metadata influence
    "semantic": 0.7       # Increase for more semantic influence
}
```

### Repetition Penalties

Configure penalty multipliers for different recency levels:

```python
"context_decay": {
    "story_repetition_penalty_base": 2.0,  # Base penalty multiplier
    "topic_decay_threshold": 3,            # Turns before topic decay
    "concept_decay_threshold": 5           # Turns before concept removal
}
```

### Relevance Thresholds

Set minimum scores for story inclusion:

```python
if story["relevance_score"] > 1.0:  # Minimum relevance threshold
    final_stories.append(story)
```

## Integration Points

### With Story Extraction Pipeline
- **Structured Metadata**: Uses trigger, emotion, thought, and value data
- **Confidence Scores**: Leverages analysis confidence for bonuses
- **Psychological Insights**: Aligns story psychology with conversation context

### With Conversational State
- **Dynamic Context**: Real-time conversation topic and intent tracking
- **Repetition History**: Complete story usage tracking with turn-level precision
- **Concept Tracking**: Key concept frequency and recency analysis

### With Personality Profiler
- **Value Alignment**: Matches story values with personality profile
- **Communication Style**: Considers personality in story appropriateness
- **Behavioral Patterns**: Aligns story selection with personality traits

## Benefits

### 1. Intelligent Context Awareness
- **Multi-dimensional Analysis**: Considers topics, emotions, values, and intent
- **Dynamic Adaptation**: Responds to conversation evolution in real-time
- **Psychological Alignment**: Matches stories to user's current emotional state

### 2. Sophisticated Repetition Management
- **Dynamic Penalties**: Prevents boring repetition while allowing relevant re-sharing
- **Turn-level Tracking**: Precise repetition gap analysis
- **Smart Overrides**: Highly relevant stories can overcome repetition penalties

### 3. Comprehensive Scoring System
- **Multi-factor Analysis**: Combines metadata, semantic, and contextual factors
- **Weighted Optimization**: Balances different relevance dimensions
- **Confidence Integration**: Leverages analysis quality for better selection

### 4. Production-Ready Performance
- **Fallback Mechanisms**: Graceful degradation when enhanced features fail
- **Performance Analytics**: Detailed insights for optimization
- **Scalable Architecture**: Efficient processing for large story corpora

## Testing

Run the comprehensive test suite:

```bash
python scripts/test_enhanced_story_relevance.py
```

This demonstrates:
- ✅ **Metadata-based filtering** with conversation context
- 🧠 **Semantic relevance scoring** using LLM judge
- 🔄 **Intelligent repetition handling** with dynamic penalties
- ⚡ **Performance comparison** between enhanced and basic approaches
- 📊 **Analytics and insights** for optimization

## Future Enhancements

- **Machine Learning Integration**: Train models on story selection success
- **User Feedback Loop**: Incorporate user ratings for story relevance
- **Emotional State Detection**: Real-time emotion analysis for better matching
- **Cross-conversation Learning**: Learn patterns across multiple users
- **A/B Testing Framework**: Compare different scoring approaches
- **Real-time Optimization**: Dynamic weight adjustment based on performance

The Enhanced Story Relevance Engine transforms story selection from simple keyword matching into sophisticated, context-aware intelligence that delivers the right story at the right moment in every conversation.
