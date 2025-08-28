"""Add daily briefings tables

Revision ID: 014_add_daily_briefings
Revises: 013_add_spam_reports
Create Date: 2025-08-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '014_add_daily_briefings'
down_revision = '013_add_spam_reports'
branch_labels = None
depends_on = None


def upgrade():
    # Create daily_briefings table
    op.create_table('daily_briefings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('briefing_date', sa.Date(), nullable=False),
        sa.Column('time_slot', sa.String(length=10), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('subtitle', sa.Text(), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('published', sa.Boolean(), nullable=False),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_daily_briefings_id', 'daily_briefings', ['id'])
    op.create_index('ix_daily_briefings_briefing_date', 'daily_briefings', ['briefing_date'])
    op.create_index('ix_daily_briefings_time_slot', 'daily_briefings', ['time_slot'])
    op.create_index('ix_daily_briefing_date_slot', 'daily_briefings', ['briefing_date', 'time_slot'])

    # Create briefing_items table
    op.create_table('briefing_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('briefing_id', sa.Integer(), nullable=False),
        sa.Column('story_id', sa.Integer(), nullable=True),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('summary_language', sa.String(length=5), nullable=False),
        sa.Column('ai_summary', sa.Text(), nullable=True),
        sa.Column('recommendation_score', sa.Float(), nullable=True),
        sa.Column('recommendation_reasons', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ),
        sa.ForeignKeyConstraint(['briefing_id'], ['daily_briefings.id'], ),
        sa.ForeignKeyConstraint(['story_id'], ['stories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_briefing_items_id', 'briefing_items', ['id'])
    op.create_index('ix_briefing_items_briefing_id', 'briefing_items', ['briefing_id'])
    op.create_index('ix_briefing_items_story_id', 'briefing_items', ['story_id'])
    op.create_index('ix_briefing_items_article_id', 'briefing_items', ['article_id'])


def downgrade():
    op.drop_index('ix_briefing_items_article_id', table_name='briefing_items')
    op.drop_index('ix_briefing_items_story_id', table_name='briefing_items')
    op.drop_index('ix_briefing_items_briefing_id', table_name='briefing_items')
    op.drop_index('ix_briefing_items_id', table_name='briefing_items')
    op.drop_table('briefing_items')
    
    op.drop_index('ix_daily_briefing_date_slot', table_name='daily_briefings')
    op.drop_index('ix_daily_briefings_time_slot', table_name='daily_briefings')
    op.drop_index('ix_daily_briefings_briefing_date', table_name='daily_briefings')
    op.drop_index('ix_daily_briefings_id', table_name='daily_briefings')
    op.drop_table('daily_briefings')