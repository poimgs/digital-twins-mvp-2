-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Stories table - stores raw story content
CREATE TABLE IF NOT EXISTS stories (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    title VARCHAR(500),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Story analysis table - stores LLM analysis results
CREATE TABLE IF NOT EXISTS story_analysis (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    triggers TEXT[],
    emotions TEXT[],
    thoughts TEXT[], 
    values TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Personality profiles table - stores generated personality profiles
CREATE TABLE IF NOT EXISTS personality_profiles (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    -- user_id VARCHAR(100) DEFAULT 'default',
    values TEXT[],
    formality_vocabulary TEXT,
    tone TEXT,
    sentence_structure TEXT,
    recurring_phrases_metaphors TEXT,
    emotional_expression TEXT,
    storytelling_style TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Conversation history table - stores chat messages
CREATE TABLE IF NOT EXISTS conversation_history (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id VARCHAR(100) DEFAULT 'default',
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);