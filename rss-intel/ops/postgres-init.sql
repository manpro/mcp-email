-- Initialize PostgreSQL for RSS Intelligence Dashboard

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create custom types
CREATE TYPE article_flag AS ENUM ('hot', 'interesting', 'archived', 'read');

-- Ensure database is ready for both FreshRSS and our backend
GRANT ALL PRIVILEGES ON DATABASE rssintel TO rss;
GRANT ALL ON SCHEMA public TO rss;