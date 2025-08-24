"""Add story clustering tables

Revision ID: 010_add_story_clustering
Revises: 009_add_spotlight_tables
Create Date: 2025-08-24 15:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010_add_story_clustering'
down_revision = '009_add_spotlight_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create stories table
    op.create_table('stories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('canonical_title', sa.String(length=500), nullable=False),
        sa.Column('canonical_url', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('best_image_url', sa.Text(), nullable=True),
        sa.Column('best_image_proxy_path', sa.String(length=500), nullable=True),
        sa.Column('sources', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('first_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('article_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('max_score', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('stance', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_stories_first_seen', 'stories', ['first_seen'])
    op.create_index('idx_stories_last_seen', 'stories', ['last_seen'])
    op.create_index('idx_stories_content_hash', 'stories', ['content_hash'])
    op.create_index('idx_stories_canonical_url', 'stories', ['canonical_url'])
    
    # Add story_id to articles table
    op.add_column('articles', sa.Column('story_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_articles_story_id', 'articles', 'stories', ['story_id'], ['id'])
    op.create_index('idx_articles_story_id', 'articles', ['story_id'])
    
    # Create story clustering metadata table
    op.create_table('story_similarities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('story_a_id', sa.Integer(), nullable=False),
        sa.Column('story_b_id', sa.Integer(), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=False),
        sa.Column('similarity_type', sa.String(length=50), nullable=False), # 'exact', 'near_dup', 'semantic'
        sa.Column('algorithm', sa.String(length=50), nullable=False), # 'content_hash', 'simhash', 'minhash', 'embedding'
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['story_a_id'], ['stories.id'], ),
        sa.ForeignKeyConstraint(['story_b_id'], ['stories.id'], )
    )
    op.create_index('idx_similarities_story_a', 'story_similarities', ['story_a_id'])
    op.create_index('idx_similarities_story_b', 'story_similarities', ['story_b_id'])
    op.create_index('idx_similarities_score', 'story_similarities', ['similarity_score'])


def downgrade():
    op.drop_table('story_similarities')
    op.drop_constraint('fk_articles_story_id', 'articles', type_='foreignkey')
    op.drop_index('idx_articles_story_id', table_name='articles')
    op.drop_column('articles', 'story_id')
    op.drop_table('stories')