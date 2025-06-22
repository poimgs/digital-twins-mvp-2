-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Bots table - stores bot configurations and metadata
CREATE TABLE IF NOT EXISTS bots (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    welcome_message TEXT NOT NULL,
    call_to_action TEXT NOT NULL,
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
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conversation state table - stores conversation summary and context
CREATE TABLE IF NOT EXISTS conversation_state (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    chat_id VARCHAR(255) NOT NULL,
    bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
    summary TEXT DEFAULT '',
    call_to_action_shown BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(chat_id, bot_id)
);