-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Bots table - stores bot configurations and metadata
CREATE TABLE IF NOT EXISTS bots (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    welcome_message TEXT NOT NULL,
    call_to_action TEXT NOT NULL,
    call_to_action_keyword TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(name)
);

-- Stories table - stores raw story content
CREATE TABLE IF NOT EXISTS stories (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
    title VARCHAR(500),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Story analysis table - stores LLM analysis results
CREATE TABLE IF NOT EXISTS story_analysis (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    summary TEXT,
    triggers TEXT[],
    emotions TEXT[],
    thoughts TEXT[],
    values TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Personality profiles table - stores generated personality profiles
CREATE TABLE IF NOT EXISTS personality_profiles (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
    values TEXT[],
    formality_vocabulary TEXT,
    tone TEXT,
    sentence_structure TEXT,
    recurring_phrases_metaphors TEXT,
    emotional_expression TEXT,
    storytelling_style TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(bot_id)
);

-- Conversation history table - stores chat messages
CREATE TABLE IF NOT EXISTS conversation_history (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    chat_id VARCHAR(255) NOT NULL,
    bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
    conversation_number INTEGER NOT NULL DEFAULT 1,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conversation state table - stores conversation summary and context
CREATE TABLE IF NOT EXISTS conversation_state (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    chat_id VARCHAR(255) NOT NULL,
    bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
    conversation_number INTEGER NOT NULL DEFAULT 1,
    summary TEXT DEFAULT '',
    current_warmth_level INTEGER DEFAULT 1 CHECK (current_warmth_level >= 1 AND current_warmth_level <= 6),
    max_warmth_achieved INTEGER DEFAULT 1 CHECK (max_warmth_achieved >= 1 AND max_warmth_achieved <= 6),
    follow_up_questions TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(chat_id, bot_id, conversation_number)
);

-- Token usage tracking table - stores LLM API usage metrics
CREATE TABLE IF NOT EXISTS token_usage (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
    chat_id VARCHAR(255),
    conversation_number INTEGER,
    operation_type VARCHAR(50) NOT NULL, -- 'conversation', 'follow_up_questions', 'story_analysis', 'personality_generation', etc.
    model VARCHAR(100) NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    temperature DECIMAL(3, 2),
    max_tokens INTEGER,
    request_metadata JSONB, -- Store additional context like system_prompt length, user_prompt length, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_stories_bot_id ON stories(bot_id);
CREATE INDEX IF NOT EXISTS idx_story_analysis_story_id ON story_analysis(story_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_chat_id ON conversation_history(chat_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_chat_conversation ON conversation_history(chat_id, conversation_number);
CREATE INDEX IF NOT EXISTS idx_conversation_state_chat_id ON conversation_state(chat_id);
CREATE INDEX IF NOT EXISTS idx_conversation_state_chat_conversation ON conversation_state(chat_id, conversation_number);