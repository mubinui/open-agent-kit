-- Initialize PostgreSQL database for Orchestration Service
-- This script runs automatically when the database container starts

-- Enable pgvector extension for vector operations
CREATE EXTENSION IF NOT EXISTS vector;

-- Create additional schemas if needed
CREATE SCHEMA IF NOT EXISTS orchestration;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE orchestration TO orchestrator;
GRANT ALL PRIVILEGES ON SCHEMA public TO orchestrator;
GRANT ALL PRIVILEGES ON SCHEMA orchestration TO orchestrator;

-- Set default search path
ALTER DATABASE orchestration SET search_path TO public, orchestration;
