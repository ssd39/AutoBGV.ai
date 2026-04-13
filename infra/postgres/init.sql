-- AutoBGV PostgreSQL Initialization Script
-- Creates extensions and initial setup for all services

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgcrypto for hashing
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable pg_trgm for text search
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas for each service domain
CREATE SCHEMA IF NOT EXISTS workflow;
CREATE SCHEMA IF NOT EXISTS agent;
CREATE SCHEMA IF NOT EXISTS verification;

-- Grant privileges
GRANT ALL PRIVILEGES ON SCHEMA workflow TO autobgv;
GRANT ALL PRIVILEGES ON SCHEMA agent TO autobgv;
GRANT ALL PRIVILEGES ON SCHEMA verification TO autobgv;

-- Set search path
ALTER USER autobgv SET search_path TO public, workflow, agent, verification;
