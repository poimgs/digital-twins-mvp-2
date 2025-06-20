-- Database Schema for Narrative Digital Twin MVP
-- This file contains the SQL commands to create the necessary tables in Supabase

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Stories table - stores raw story content
CREATE TABLE IF NOT EXISTS stories (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    filename VARCHAR(255),
    title VARCHAR(500),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Story analysis table - stores LLM analysis results
CREATE TABLE IF NOT EXISTS story_analysis (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    -- Trigger information
    trigger_title VARCHAR(500),
    trigger_description TEXT,
    trigger_category VARCHAR(100),
    -- Feelings/emotions
    emotions TEXT[], -- Array of emotion strings
    -- Thought/internal monologue
    internal_monologue TEXT,
    -- Value analysis
    violated_value VARCHAR(500),
    value_reasoning TEXT,
    confidence_score INTEGER CHECK (confidence_score >= 1 AND confidence_score <= 5),
    -- Keep raw response for debugging/audit
    raw_response TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Personality profiles table - stores generated personality profiles
CREATE TABLE IF NOT EXISTS personality_profiles (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id VARCHAR(100) DEFAULT 'default',
    profile JSONB NOT NULL,
    source_analyses_count INTEGER DEFAULT 0,
    raw_response TEXT,
    profile_version VARCHAR(50) DEFAULT '1.0',
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
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_stories_filename ON stories(filename);
CREATE INDEX IF NOT EXISTS idx_stories_created_at ON stories(created_at);
CREATE INDEX IF NOT EXISTS idx_story_analysis_story_id ON story_analysis(story_id);
CREATE INDEX IF NOT EXISTS idx_personality_profiles_user_id ON personality_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_user_id ON conversation_history(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_created_at ON conversation_history(created_at);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_stories_updated_at 
    BEFORE UPDATE ON stories 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_personality_profiles_updated_at 
    BEFORE UPDATE ON personality_profiles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) policies for Supabase
-- Note: Adjust these policies based on your authentication requirements

-- Enable RLS on all tables
ALTER TABLE stories ENABLE ROW LEVEL SECURITY;
ALTER TABLE story_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE personality_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_history ENABLE ROW LEVEL SECURITY;

-- For MVP, allow all operations (adjust for production)
CREATE POLICY "Allow all operations on stories" ON stories FOR ALL USING (true);
CREATE POLICY "Allow all operations on story_analysis" ON story_analysis FOR ALL USING (true);
CREATE POLICY "Allow all operations on personality_profiles" ON personality_profiles FOR ALL USING (true);
CREATE POLICY "Allow all operations on conversation_history" ON conversation_history FOR ALL USING (true);

-- Sample data insertion (optional)
-- Uncomment the following lines if you want to insert sample data

/*
INSERT INTO stories (filename, title, content, source) VALUES 
('sample_story.txt', 'Sample Story', 'This is a sample story for testing purposes.', 'manual_insert');
*/
