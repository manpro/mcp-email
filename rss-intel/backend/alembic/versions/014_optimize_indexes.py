"""optimize indexes for performance

Revision ID: 014_optimize_indexes
Revises: 013_add_spam_reports
Create Date: 2025-08-27 06:40:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '014_optimize_indexes'
down_revision = '013_add_spam_reports'
branch_labels = None
depends_on = None

def upgrade():
    # Articles table optimization
    print("Creating performance indexes for articles table...")
    
    # Index for search queries (title and content)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_articles_search_gin 
        ON articles USING gin(to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, '')))
    """)
    
    # Index for published_at queries (trending, recent articles)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_articles_published_at_desc 
        ON articles (published_at DESC)
    """)
    
    # Index for score-based queries
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_articles_score_total_desc 
        ON articles (score_total DESC) WHERE score_total IS NOT NULL
    """)
    
    # Index for source filtering
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_articles_source 
        ON articles (source)
    """)
    
    # Index for created_at (used in background jobs)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_articles_created_at_desc 
        ON articles (created_at DESC)
    """)
    
    # Composite index for scoring and filtering
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_articles_score_published 
        ON articles (score_total DESC, published_at DESC) 
        WHERE score_total IS NOT NULL
    """)
    
    # Index for flags operations (JSON operations)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_articles_flags_gin 
        ON articles USING gin(flags) WHERE flags IS NOT NULL
    """)
    
    # Index for topics (AI analysis results)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_articles_topics_gin 
        ON articles USING gin(topics) WHERE topics IS NOT NULL
    """)
    
    # Article chunks table optimization
    print("Creating performance indexes for article_chunks table...")
    
    # Index for article_id lookups
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chunks_article_id 
        ON article_chunks (article_id)
    """)
    
    # Index for chunk_index within articles
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chunks_article_chunk 
        ON article_chunks (article_id, chunk_index)
    """)
    
    # Index for token_count filtering
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chunks_token_count 
        ON article_chunks (token_count) WHERE token_count IS NOT NULL
    """)
    
    # Events table optimization
    print("Creating performance indexes for events table...")
    
    # Index for article_id and event_type queries
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_article_type 
        ON events (article_id, event_type)
    """)
    
    # Index for created_at queries (trending analysis)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_created_at_desc 
        ON events (created_at DESC)
    """)
    
    # Composite index for trending queries
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_trending 
        ON events (created_at DESC, event_type, article_id) 
        WHERE created_at >= NOW() - INTERVAL '7 days'
    """)
    
    # Sources table optimization
    print("Creating performance indexes for sources table...")
    
    # Index for source_type filtering
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sources_type_enabled 
        ON sources (source_type, enabled) WHERE enabled = true
    """)
    
    # Index for last_checked queries
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sources_last_checked 
        ON sources (last_checked) WHERE last_checked IS NOT NULL
    """)
    
    # Ingest jobs optimization
    print("Creating performance indexes for ingest_jobs table...")
    
    # Index for status and created_at
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ingest_jobs_status_created 
        ON ingest_jobs (status, created_at DESC)
    """)
    
    # Index for source_id lookups
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ingest_jobs_source_id 
        ON ingest_jobs (source_id)
    """)
    
    # ML-related indexes
    print("Creating indexes for ML tables...")
    
    # Predictions table
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_article_model 
        ON predictions (article_id, model_id)
    """)
    
    # Training samples table
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_training_samples_article 
        ON training_samples (article_id)
    """)
    
    # User interactions table
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_interactions_user_article 
        ON user_interactions (user_id, article_id)
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_interactions_created_at 
        ON user_interactions (created_at DESC)
    """)
    
    print("All performance indexes created successfully!")

def downgrade():
    # Remove indexes in reverse order
    print("Removing performance indexes...")
    
    # User interactions indexes
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_user_interactions_created_at")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_user_interactions_user_article")
    
    # Training samples indexes
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_training_samples_article")
    
    # Predictions indexes
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_predictions_article_model")
    
    # Ingest jobs indexes
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_ingest_jobs_source_id")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_ingest_jobs_status_created")
    
    # Sources indexes
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_sources_last_checked")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_sources_type_enabled")
    
    # Events indexes
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_events_trending")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_events_created_at_desc")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_events_article_type")
    
    # Article chunks indexes
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_chunks_token_count")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_chunks_article_chunk")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_chunks_article_id")
    
    # Articles indexes
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_articles_topics_gin")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_articles_flags_gin")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_articles_score_published")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_articles_created_at_desc")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_articles_source")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_articles_score_total_desc")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_articles_published_at_desc")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_articles_search_gin")
    
    print("All performance indexes removed!")