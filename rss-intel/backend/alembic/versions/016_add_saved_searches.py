"""Add saved searches and search analytics tables

Revision ID: 016_add_saved_searches
Revises: 015_add_spam_reports
Create Date: 2025-01-27 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '016_add_saved_searches'
down_revision: Union[str, None] = '015_add_spam_reports'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Create saved_searches table
    op.create_table('saved_searches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=True),  # For future user system
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('search_query', sa.Text(), nullable=True),
        sa.Column('search_filters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('search_settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_used', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for saved_searches
    op.create_index('ix_saved_searches_user_id', 'saved_searches', ['user_id'])
    op.create_index('ix_saved_searches_created_at', 'saved_searches', ['created_at'])
    op.create_index('ix_saved_searches_last_used', 'saved_searches', ['last_used'])

    # Create search_analytics table
    op.create_table('search_analytics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=True),  # For future user system
        sa.Column('search_query', sa.Text(), nullable=False),
        sa.Column('search_filters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('search_type', sa.String(50), nullable=False),  # 'semantic', 'keyword', 'hybrid'
        sa.Column('result_count', sa.Integer(), nullable=False),
        sa.Column('search_time_ms', sa.Float(), nullable=False),
        sa.Column('page_requested', sa.Integer(), nullable=False, default=1),
        sa.Column('results_clicked', postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),  # IPv6 compatible
        sa.Column('referer', sa.String(500), nullable=True),
        sa.Column('search_timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for search_analytics
    op.create_index('ix_search_analytics_user_id', 'search_analytics', ['user_id'])
    op.create_index('ix_search_analytics_search_timestamp', 'search_analytics', ['search_timestamp'])
    op.create_index('ix_search_analytics_search_query', 'search_analytics', ['search_query'])
    op.create_index('ix_search_analytics_search_type', 'search_analytics', ['search_type'])
    op.create_index('ix_search_analytics_result_count', 'search_analytics', ['result_count'])

    # Create search_suggestions table for auto-complete
    op.create_table('search_suggestions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('suggestion_text', sa.String(500), nullable=False),
        sa.Column('search_count', sa.Integer(), nullable=False, default=1),
        sa.Column('last_searched', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('avg_result_count', sa.Float(), nullable=False, default=0.0),
        sa.Column('category', sa.String(100), nullable=True),  # 'manual', 'trending', 'popular'
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('suggestion_text')
    )
    
    # Create indexes for search_suggestions
    op.create_index('ix_search_suggestions_search_count', 'search_suggestions', ['search_count'])
    op.create_index('ix_search_suggestions_last_searched', 'search_suggestions', ['last_searched'])
    op.create_index('ix_search_suggestions_category', 'search_suggestions', ['category'])
    
    # Create popular_searches view for trending queries
    op.execute("""
        CREATE VIEW popular_searches AS
        SELECT 
            search_query,
            COUNT(*) as search_count,
            MAX(search_timestamp) as last_searched,
            AVG(result_count) as avg_results,
            AVG(search_time_ms) as avg_time_ms
        FROM search_analytics 
        WHERE search_timestamp >= CURRENT_DATE - INTERVAL '30 days'
            AND search_query IS NOT NULL 
            AND search_query != ''
        GROUP BY search_query
        HAVING COUNT(*) >= 3
        ORDER BY search_count DESC, last_searched DESC;
    """)

def downgrade() -> None:
    # Drop views first
    op.execute("DROP VIEW IF EXISTS popular_searches")
    
    # Drop tables
    op.drop_table('search_suggestions')
    op.drop_table('search_analytics')
    op.drop_table('saved_searches')