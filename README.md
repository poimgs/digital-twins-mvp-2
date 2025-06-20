# Narrative Digital Twin MVP

A conversational AI system that creates a digital twin based on personal stories and narratives.

## Project Overview

This MVP creates a digital twin that can engage in conversations by:
1. Analyzing personal stories to extract internal states and personality traits
2. Using this analysis to generate contextually appropriate responses
3. Maintaining conversational state across interactions

## Project Structure

```
narrative-digital-twin/
├── .env                  # Environment variables and API keys
├── requirements.txt      # Python dependencies
├── README.md            # This file
├── data/stories/        # Raw story text files
├── config/              # Configuration and prompts
├── core/                # Core application logic
├── scripts/             # Setup and utility scripts
└── terminal_app/        # Command-line chat interface
```

## Setup Instructions

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   - Copy `.env.example` to `.env`
   - Add your OpenAI API key
   - Add your Supabase URL and API key

3. **Add Stories**
   - Place your story text files in `data/stories/`
   - Each file should contain one complete story

4. **Run Setup**
   ```bash
   python scripts/run_setup.py
   ```

5. **Start Chat**
   ```bash
   python terminal_app/chat.py
   ```

## Features

- **Story Analysis**: Extracts internal states and emotions from narratives
- **Personality Profiling**: Generates comprehensive personality profiles
- **Conversational Engine**: Context-aware response generation
- **Local Chat Interface**: Terminal-based conversation system

## Development

The project follows a modular architecture:
- `core/` contains reusable business logic
- `config/` centralizes settings and prompts
- `scripts/` provides setup and maintenance tools
- `terminal_app/` implements the user interface

## Next Steps

1. Telegram Bot Integration
2. Web Interface
3. Advanced Memory Management
4. Multi-user Support
