-- CuraMind RAG & LLM Assistant Pure PostgreSQL Schema
-- No SQLAlchemy - Direct SQL DDL with pgvector support

CREATE EXTENSION IF NOT EXISTS vector;

-- Documents Table
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(36) PRIMARY KEY,
    workspace_id VARCHAR(36) NOT NULL,
    patient_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(64) NOT NULL,
    date VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'processing',
    processing_error TEXT,
    full_text TEXT,
    source VARCHAR(255),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_ws_patient ON documents(workspace_id, patient_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);

-- Extracted Fields Table (Structured data extracted from clinical documents)
CREATE TABLE IF NOT EXISTS extracted_fields (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    workspace_id VARCHAR(36) NOT NULL,
    label VARCHAR(128) NOT NULL,
    value TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    flagged BOOLEAN DEFAULT FALSE,
    confirmed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_extracted_fields_doc ON extracted_fields(document_id);
CREATE INDEX IF NOT EXISTS idx_extracted_fields_ws ON extracted_fields(workspace_id);

-- Document Chunks Table (Full-text chunks for vector similarity search)
-- Workspace & Patient IDs are explicitly denormalized for strict isolation without joins
CREATE TABLE IF NOT EXISTS document_chunks (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    workspace_id VARCHAR(36) NOT NULL,
    patient_id VARCHAR(36) NOT NULL,
    chunk_text TEXT NOT NULL,
    page_number INTEGER,
    chunk_index INTEGER NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chunks_workspace ON document_chunks(workspace_id);
CREATE INDEX IF NOT EXISTS idx_chunks_patient ON document_chunks(workspace_id, patient_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON document_chunks(document_id);
-- Full-Text Search GIN Index for Keyword Search (BM25 / tsvector)
CREATE INDEX IF NOT EXISTS idx_chunks_fts ON document_chunks USING GIN(to_tsvector('english', chunk_text));

-- Conversations Table (RAG Chat Sessions)
CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(36) PRIMARY KEY,
    workspace_id VARCHAR(36) NOT NULL,
    patient_id VARCHAR(36),
    user_id VARCHAR(36) NOT NULL,
    title VARCHAR(255) DEFAULT 'New Clinical Chat',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conversations_ws ON conversations(workspace_id);
CREATE INDEX IF NOT EXISTS idx_conversations_patient ON conversations(workspace_id, patient_id);

-- Conversation Messages Table
CREATE TABLE IF NOT EXISTS conversation_messages (
    id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_conv ON conversation_messages(conversation_id);

-- Audit Events Table
CREATE TABLE IF NOT EXISTS audit_events (
    id VARCHAR(36) PRIMARY KEY,
    workspace_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    user_email VARCHAR(255),
    patient_id VARCHAR(36),
    action VARCHAR(64) NOT NULL,
    detail TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_ws_patient ON audit_events(workspace_id, patient_id);
