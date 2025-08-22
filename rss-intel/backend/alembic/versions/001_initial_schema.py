"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create articles table
    op.create_table('articles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('freshrss_entry_id', sa.String(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('content_hash', sa.String(), nullable=False),
        sa.Column('score_total', sa.Integer(), nullable=True),
        sa.Column('scores', sa.JSON(), nullable=True),
        sa.Column('entities', sa.JSON(), nullable=True),
        sa.Column('topics', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('flags', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_articles_freshrss_entry_id', 'articles', ['freshrss_entry_id'], unique=True)
    op.create_index('ix_articles_published_at', 'articles', ['published_at'])
    op.create_index('ix_articles_score_total', 'articles', ['score_total'])
    op.create_index('ix_articles_content_hash', 'articles', ['content_hash'])
    op.create_index('ix_article_score_published', 'articles', ['score_total', 'published_at'])
    op.create_index('ix_articles_id', 'articles', ['id'])
    
    # Create runs table
    op.create_table('runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('new_entries', sa.Integer(), nullable=True),
        sa.Column('scored', sa.Integer(), nullable=True),
        sa.Column('errors', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_runs_id', 'runs', ['id'])


def downgrade() -> None:
    op.drop_index('ix_runs_id', table_name='runs')
    op.drop_table('runs')
    op.drop_index('ix_article_score_published', table_name='articles')
    op.drop_index('ix_articles_content_hash', table_name='articles')
    op.drop_index('ix_articles_score_total', table_name='articles')
    op.drop_index('ix_articles_published_at', table_name='articles')
    op.drop_index('ix_articles_freshrss_entry_id', table_name='articles')
    op.drop_index('ix_articles_id', table_name='articles')
    op.drop_table('articles')