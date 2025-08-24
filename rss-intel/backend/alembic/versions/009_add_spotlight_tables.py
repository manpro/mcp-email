"""add_spotlight_tables

Revision ID: 009_add_spotlight_tables
Revises: 008_add_user_events_tracking
Create Date: 2025-08-24 09:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '009_add_spotlight_tables'
down_revision = '008_add_user_events_tracking'
branch_labels = None
depends_on = None


def upgrade():
    # Create spotlight_issues table for daily digests
    op.create_table('spotlight_issues',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('issue_date', sa.DateTime(timezone=True), nullable=False, unique=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('subtitle', sa.String(500), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('published', sa.Boolean(), default=False, nullable=False),
        sa.Column('metrics', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('ix_spotlight_issues_date', 'spotlight_issues', ['issue_date'])
    op.create_index('ix_spotlight_issues_published', 'spotlight_issues', ['published'])
    
    # Create spotlight_items table for individual digest items
    op.create_table('spotlight_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('issue_id', sa.Integer(), nullable=False),
        sa.Column('story_id', sa.Integer(), nullable=True),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('section', sa.String(50), nullable=False),  # 'must_read' or 'also_worth'
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('summary_language', sa.String(10), default='en', nullable=False),
        sa.Column('recommendation_score', sa.Float(), nullable=True),
        sa.Column('recommendation_reasons', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['issue_id'], ['spotlight_issues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['story_id'], ['stories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('ix_spotlight_items_issue', 'spotlight_items', ['issue_id'])
    op.create_index('ix_spotlight_items_section', 'spotlight_items', ['section'])
    
    # Create spotlight_config table for settings
    op.create_table('spotlight_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(100), nullable=False, unique=True),
        sa.Column('value', postgresql.JSONB(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Insert default config
    op.execute("""
        INSERT INTO spotlight_config (key, value, description) VALUES
        ('schedule', '{"hour": 7, "minute": 0, "timezone": "Europe/Stockholm"}', 'Daily generation schedule'),
        ('sections', '{"must_read": 3, "also_worth": 5}', 'Number of items per section'),
        ('scoring_weights', '{"rule_score": 0.3, "ml_score": 0.3, "trend_score": 0.2, "freshness": 0.2}', 'Scoring weights for selection'),
        ('diversity_rules', '{"max_per_source": 2, "max_per_topic": 3, "require_watchlist": true}', 'Diversity constraints'),
        ('summary_config', '{"max_length": 220, "language": "en", "style": "factual"}', 'Summary generation settings'),
        ('export_config', '{"rss_enabled": true, "slack_enabled": false, "email_enabled": false}', 'Export channel settings')
    """)


def downgrade():
    op.drop_table('spotlight_config')
    op.drop_table('spotlight_items')
    op.drop_table('spotlight_issues')