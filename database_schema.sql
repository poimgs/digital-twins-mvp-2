-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Stories table - stores raw story content
CREATE TABLE IF NOT EXISTS stories (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    filename VARCHAR(255),
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
-- The profile JSONB field contains structured personality data with three main categories:
-- 1. core_values_motivations: Analysis of guiding principles and motivations
-- 2. communication_style_voice: How the individual communicates and expresses themselves
-- 3. cognitive_style_worldview: How they think, process information, and view the world
CREATE TABLE IF NOT EXISTS personality_profiles (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id VARCHAR(100) DEFAULT 'default',
    profile JSONB NOT NULL,
    source_analyses_count INTEGER DEFAULT 0,
    profile_version VARCHAR(50) DEFAULT '2.0',
    raw_response TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Add indexes for better query performance on personality profiles
CREATE INDEX IF NOT EXISTS idx_personality_profiles_user_id ON personality_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_personality_profiles_version ON personality_profiles(profile_version);

-- Add GIN index for JSONB profile field to enable efficient queries on personality data
CREATE INDEX IF NOT EXISTS idx_personality_profiles_profile_gin ON personality_profiles USING GIN (profile);

-- Conversation history table - stores chat messages
CREATE TABLE IF NOT EXISTS conversation_history (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id VARCHAR(100) DEFAULT 'default',
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
