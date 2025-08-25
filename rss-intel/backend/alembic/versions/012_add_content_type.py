"""Add content_type field to distinguish articles from events

Revision ID: 012_add_content_type
Revises: 011_image_pipeline_v2
Create Date: 2025-08-25 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '012_add_content_type'
down_revision = '011_image_pipeline_v2'
branch_labels = None
depends_on = None


def upgrade():
    # Add content_type column to articles table
    op.add_column('articles', 
                  sa.Column('content_type', sa.String(20), nullable=True, server_default='article'))
    
    # Create index for content_type
    op.create_index('ix_articles_content_type', 'articles', ['content_type'])
    
    # Update existing records - identify events by URL pattern
    op.execute("""
        UPDATE articles 
        SET content_type = 'event' 
        WHERE url LIKE '%/event-info/%'
    """)
    
    # Make column not nullable after populating existing data
    op.alter_column('articles', 'content_type', nullable=False)


def downgrade():
    # Drop index
    op.drop_index('ix_articles_content_type', 'articles')
    
    # Drop column
    op.drop_column('articles', 'content_type')