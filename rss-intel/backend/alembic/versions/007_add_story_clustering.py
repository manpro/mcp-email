"""Add story clustering tables and fields

Revision ID: 007
Revises: 006
Create Date: 2025-08-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '007_add_story_clustering'
down_revision = '006_add_ingest_sources'
branch_labels = None
depends_on = None


def upgrade():
    # Create stories table
    op.create_table(
        'stories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('canonical_title', sa.Text(), nullable=False),
        sa.Column('best_image', sa.Text(), nullable=True),
        sa.Column('sources', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('first_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('stance', sa.ARRAY(sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_stories_first_seen', 'first_seen'),
        sa.Index('ix_stories_last_seen', 'last_seen'),
        sa.Index('ix_stories_confidence', 'confidence')
    )
    
    # Add clustering fields to articles table (skip content_hash as it exists)
    op.add_column('articles', sa.Column('story_id', sa.Integer(), nullable=True))
    op.add_column('articles', sa.Column('canonical_url', sa.Text(), nullable=True))
    op.add_column('articles', sa.Column('simhash', sa.BigInteger(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key('fk_articles_story_id', 'articles', 'stories', ['story_id'], ['id'])
    
    # Add indexes for clustering fields (skip content_hash as index exists)
    op.create_index('ix_articles_story_id', 'articles', ['story_id'])
    op.create_index('ix_articles_canonical_url', 'articles', ['canonical_url'])
    op.create_index('ix_articles_simhash', 'articles', ['simhash'])
    
    # Add trigger to update stories.updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_stories_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        
        CREATE TRIGGER update_stories_updated_at 
        BEFORE UPDATE ON stories
        FOR EACH ROW EXECUTE FUNCTION update_stories_updated_at();
    """)


def downgrade():
    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS update_stories_updated_at ON stories;")
    op.execute("DROP FUNCTION IF EXISTS update_stories_updated_at();")
    
    # Drop indexes (skip content_hash)
    op.drop_index('ix_articles_simhash', 'articles')
    op.drop_index('ix_articles_canonical_url', 'articles')
    op.drop_index('ix_articles_story_id', 'articles')
    
    # Drop foreign key
    op.drop_constraint('fk_articles_story_id', 'articles', type_='foreignkey')
    
    # Drop columns from articles (skip content_hash)
    op.drop_column('articles', 'simhash')
    op.drop_column('articles', 'canonical_url')
    op.drop_column('articles', 'story_id')
    
    # Drop stories table
    op.drop_table('stories')