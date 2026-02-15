"""Database schema for Gulama's encrypted memory store."""

# SQLite schema — applied to SQLCipher encrypted database
SCHEMA_SQL = """
-- Conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    channel TEXT NOT NULL,
    user_id TEXT,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    summary TEXT,
    token_count INTEGER DEFAULT 0
);

-- Messages within conversations
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    token_count INTEGER DEFAULT 0,
    embedding_id TEXT
);

-- Extracted facts / long-term knowledge
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL CHECK(category IN ('preference', 'identity', 'knowledge', 'skill', 'context')),
    content TEXT NOT NULL,
    source_message_id TEXT REFERENCES messages(id),
    confidence REAL DEFAULT 1.0 CHECK(confidence BETWEEN 0.0 AND 1.0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    embedding_id TEXT
);

-- Token usage and cost tracking
CREATE TABLE IF NOT EXISTS cost_tracking (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0.0,
    channel TEXT,
    skill TEXT,
    conversation_id TEXT REFERENCES conversations(id)
);

-- Schema version for migrations
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category);
CREATE INDEX IF NOT EXISTS idx_cost_timestamp ON cost_tracking(timestamp);
CREATE INDEX IF NOT EXISTS idx_cost_provider ON cost_tracking(provider);

-- Insert initial schema version
INSERT OR IGNORE INTO schema_version (version) VALUES (1);
"""

CURRENT_SCHEMA_VERSION = 1
