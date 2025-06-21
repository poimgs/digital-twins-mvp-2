# Narrative Digital Twin MVP - Multi-Bot System

A conversational AI system that creates multiple digital twins based on personal stories and narratives.

## Project Overview

This MVP creates digital twins that can engage in conversations by:

1. Analyzing personal stories to extract internal states and personality traits
2. Using this analysis to generate contextually appropriate responses
3. Maintaining conversational state across interactions
4. Supporting multiple bots with unique personalities and stories

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

4. **Set Up Multi-Bot System**

   ```bash
   python scripts/migrate_to_multibot.py
   ```

5. **Create Additional Bots (Optional)**

   ```bash
   python scripts/bot_manager.py
   ```

6. **Start Terminal Chat**

   ```bash
   python terminal_app/chat.py
   ```

7. **Set Up Telegram Bot (Optional)**

   - Create a Telegram bot via [@BotFather](https://t.me/botfather)
   - Get your bot token
   - Start the Telegram bot:

   ```bash
   python scripts/telegram_manager.py
   ```

   Or directly:

   ```bash
   python telegram_app/telegram_bot.py <bot_id> <telegram_bot_token>
   ```

## Features

- **Multi-Bot Support**: Create and manage multiple digital twins
- **Telegram Integration**: Deploy bots directly to Telegram with interactive features
- **Story Analysis**: Extracts internal states and emotions from narratives
- **Personality Profiling**: Generates comprehensive personality profiles
- **Conversational Engine**: Context-aware response generation
- **Bot Selection**: Choose which digital twin to chat with
- **Interactive Follow-ups**: Clickable follow-up questions in Telegram
- **Chat Management**: Separate conversation histories per bot-user pair
- **Dual Interface**: Both terminal and Telegram chat interfaces

## Development

The project follows a modular architecture:

- `core/` contains reusable business logic
- `config/` centralizes settings and prompts
- `scripts/` provides setup and maintenance tools
- `terminal_app/` implements the user interface

## Multi-Bot Architecture

The system now supports multiple bots with the following key concepts:

- **Bot**: Each bot has its own personality profile, stories, welcome message, and call-to-action
- **Chat ID**: For Telegram, uses `{bot_id}_{telegram_chat_id}`. For terminal, uses `{bot_id}_default`
- **Isolated Conversations**: Each bot-user pair maintains separate conversation history
- **Bot Management**: Create, update, and manage bots through utility scripts
- **Telegram Integration**: Each bot can be deployed to Telegram with its own bot token

## Database Schema

The multi-bot system uses the following key tables:

- `bots`: Store bot configurations and metadata
- `personality_profiles`: Bot-specific personality data
- `stories`: Stories associated with specific bots
- `conversation_history`: Messages identified by chat_id
- `conversation_state`: Conversation summaries per chat_id

## Telegram Bot Features

- **Interactive Follow-ups**: Follow-up questions appear as clickable buttons
- **Bot Commands**: `/start`, `/help`, `/reset` commands
- **Typing Indicators**: Shows when the bot is "thinking"
- **Markdown Support**: Rich text formatting in responses
- **Error Handling**: Graceful error handling and user feedback

## Next Steps

1. ✅ Telegram Bot Integration (Complete)
2. Web Interface
3. Advanced Memory Management
4. Call-to-Action Implementation
5. Story Filtering by Bot Context
6. Multi-language Support
7. Voice Message Integration
