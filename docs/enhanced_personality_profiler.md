# Enhanced Personality Profiler

## Overview

The Enhanced Personality Profiler implements a comprehensive system for generating personality profiles from personal narratives using two distinct approaches:

1. **Raw Text Analysis**: Direct analysis of story corpus for initial personality inference
2. **Structured Data Analysis**: Uses results from the two-phase story extraction pipeline

This dual approach ensures personality profiles can be generated from day one with raw stories, while also leveraging deeper structured insights when available.

## Architecture

### Approach 1: Raw Text Analysis (Initial Phase)

When only raw story texts are available, the system performs holistic analysis of the entire story corpus using a specialized "digital psychologist" prompt.

**Process:**
1. **Combine Stories**: Merge all story texts into a comprehensive corpus
2. **Deep Analysis**: Use specialized LLM prompts to extract personality traits
3. **Structured Output**: Generate personality profile following strict JSON schema
4. **Persona Generation**: Create human-readable Persona.md document

**Key Features:**
- Works from day one with raw stories
- Authentic foundation based entirely on individual's own words
- Comprehensive analysis of values, communication style, and cognitive patterns

### Approach 2: Structured Data Analysis

Uses structured extraction results from the two-phase story pipeline to generate personality profiles.

**Process:**
1. **Pattern Analysis**: Identify patterns across trigger categories, emotions, thoughts, and values
2. **Synthesis**: Combine patterns into cohesive personality traits
3. **Profile Generation**: Create comprehensive personality profile
4. **Persona Document**: Generate instructional persona for digital twin

**Key Features:**
- Leverages deep psychological insights from structured extraction
- Identifies patterns across multiple psychological dimensions
- Higher precision through structured data analysis

## JSON Schema Structure

Both approaches generate personality profiles following this schema:

```json
{
  "core_values_motivations": {
    "core_values": "Summary of recurring themes suggesting core values",
    "anti_values": "Situations/behaviors that trigger negative reactions"
  },
  "communication_style_voice": {
    "formality_and_vocabulary": "Description of language formality and complexity",
    "dominant_tone": "Primary emotional tone across stories",
    "sentence_structure": "Analysis of typical sentence construction",
    "recurring_phrases_or_metaphors": "Unique expressions and metaphors"
  },
  "cognitive_style_worldview": {
    "thinking_process": "Typical mode of thinking (analytical, intuitive, etc.)",
    "outlook": "Optimistic or pessimistic worldview tendency",
    "focus": "Temporal focus (past, present, future)"
  }
}
```

## Key Components

### 1. Raw Text Personality Analysis

```python
profile_data = personality_profiler.generate_personality_from_raw_text(
    stories=story_list,
    user_id="user_001"
)
```

**Features:**
- Analyzes entire story corpus holistically
- Extracts values, communication patterns, and cognitive style
- Returns structured personality profile
- Works with minimal story data

### 2. Structured Data Analysis

```python
profile_data = personality_profiler.generate_personality_from_structured_data(
    extraction_results=structured_results,
    user_id="user_001"
)
```

**Features:**
- Uses structured extraction results (triggers, emotions, thoughts, values)
- Identifies patterns across psychological dimensions
- Higher precision through structured analysis
- Builds on two-phase extraction pipeline

### 3. Persona Document Generation

```python
persona_doc = personality_profiler.generate_persona_document(
    profile_data=profile_data,
    user_name="Alex"
)
```

**Features:**
- Converts personality profile into human-readable format
- Creates instructional document for digital twin
- Includes behavioral guidelines and communication style
- Ready for use in conversational AI systems

### 4. Complete Pipeline

```python
result = personality_profiler.create_complete_personality_pipeline(
    stories=stories,
    user_id="user_001",
    user_name="Alex",
    use_structured_extraction=True
)
```

**Features:**
- End-to-end personality profile generation
- Automatic fallback between approaches
- Generates both profile data and persona document
- Stores results in database

## Usage Examples

### Basic Raw Text Analysis

```python
from core.personality import personality_profiler

stories = [
    {"id": "001", "content": "Story text here..."},
    {"id": "002", "content": "Another story..."}
]

# Generate personality from raw text
profile_data = personality_profiler.generate_personality_from_raw_text(
    stories=stories,
    user_id="alex_001"
)

# Access personality components
profile = profile_data["profile"]
core_values = profile["core_values_motivations"]
communication = profile["communication_style_voice"]
cognitive = profile["cognitive_style_worldview"]
```

### Complete Pipeline with Persona Document

```python
# Complete pipeline with automatic approach selection
result = personality_profiler.create_complete_personality_pipeline(
    stories=stories,
    user_id="alex_001",
    user_name="Alex",
    use_structured_extraction=True  # Try structured first, fallback to raw text
)

# Access results
profile_data = result["profile_data"]
persona_document = result["persona_document"]
analysis_method = result["analysis_method"]

# Save persona document
with open("persona_alex.md", "w") as f:
    f.write(persona_document)
```

### Backward Compatibility

```python
# Works with legacy analysis format
legacy_analyses = [
    {
        "story_id": "001",
        "analysis": {
            "emotional_states": ["frustrated", "determined"],
            "values": ["autonomy", "competence"]
        }
    }
]

profile_data = personality_profiler.generate_personality_profile(
    analyses=legacy_analyses,
    user_id="legacy_user"
)
```

## Generated Persona Document Format

The system generates Persona.md documents with this structure:

```markdown
# Core Persona: [Name] - [Analysis Type]

You are [Name]. Your personality should reflect the following core traits.

## 1. Core Values & Motivations
- Your stories consistently show high value placed on **[Values]**
- You react negatively to situations involving **[Anti-values]**

## 2. Communication Style & Voice
- **Voice:** [Communication characteristics]
- **Tone:** [Dominant emotional tone]
- **Vocabulary:** [Language complexity and style]
- **Recurring Phrases:** [Unique expressions]

## 3. Cognitive Style & Worldview
- **Thinking Process:** [How they approach problems]
- **Outlook:** [Optimistic/pessimistic tendencies]
- **Focus:** [Temporal orientation]

## 4. Behavioral Guidelines
- [Specific instructions for AI behavior]
- [Communication patterns to emulate]
- [Decision-making approaches]
```

## Integration Points

### With Story Extraction Pipeline
- Automatically uses structured extraction results when available
- Falls back to raw text analysis when structured data unavailable
- Maintains consistency between extraction and personality analysis

### With Conversational Engine
- Persona documents directly usable as system prompts
- Personality traits inform response generation
- Communication style guides conversational behavior

### With Database Storage
- Automatic storage of personality profiles
- Version tracking and update management
- Retrieval for conversational systems

## Benefits

### 1. Dual Approach Flexibility
- **Day One Capability**: Generate personalities from raw stories immediately
- **Enhanced Precision**: Leverage structured data when available
- **Automatic Selection**: System chooses best approach based on available data

### 2. Comprehensive Analysis
- **Values & Motivations**: Core drivers and anti-values
- **Communication Style**: Voice, tone, vocabulary, unique expressions
- **Cognitive Patterns**: Thinking processes and worldview orientation

### 3. Practical Output
- **Structured Data**: JSON format for programmatic use
- **Human-Readable**: Persona documents for manual review
- **AI-Ready**: Direct integration with conversational systems

### 4. Scalability & Reliability
- **Schema Validation**: Consistent, parseable output
- **Error Handling**: Graceful degradation and fallback mechanisms
- **Backward Compatibility**: Works with existing analysis formats

## Testing

Run the comprehensive test suite:

```bash
python scripts/test_enhanced_personality.py
```

This demonstrates:
- Raw text personality analysis
- Persona document generation
- Complete pipeline functionality
- Backward compatibility
- Error handling and edge cases

## Future Enhancements

- **Multi-dimensional Analysis**: Expand personality dimensions
- **Confidence Scoring**: Add reliability metrics to personality traits
- **Dynamic Updates**: Real-time personality refinement with new stories
- **Cross-validation**: Compare raw text vs structured analysis results
- **Personality Evolution**: Track personality changes over time
