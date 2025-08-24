"""Add content extraction fields

Revision ID: 004_add_content_extraction
Revises: 003_add_image_fields
Create Date: 2025-08-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_add_content_extraction'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add content extraction fields to articles table
    op.add_column('articles', sa.Column('full_content', sa.Text(), nullable=True))
    op.add_column('articles', sa.Column('content_html', sa.Text(), nullable=True))
    op.add_column('articles', sa.Column('extracted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('articles', sa.Column('extraction_status', sa.String(20), server_default='pending', nullable=False))
    op.add_column('articles', sa.Column('extraction_error', sa.Text(), nullable=True))
    op.add_column('articles', sa.Column('content_keywords', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('articles', sa.Column('content_summary', sa.Text(), nullable=True))
    op.add_column('articles', sa.Column('authors', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('articles', sa.Column('top_image_url', sa.String(500), nullable=True))
    op.add_column('articles', sa.Column('robots_txt_checked', sa.Boolean(), server_default='false', nullable=False))
    
    # Create index for extraction status for efficient querying
    op.create_index('ix_articles_extraction_status', 'articles', ['extraction_status'])
    op.create_index('ix_articles_extracted_at', 'articles', ['extracted_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_articles_extracted_at', table_name='articles')
    op.drop_index('ix_articles_extraction_status', table_name='articles')
    
    # Drop columns
    op.drop_column('articles', 'robots_txt_checked')
    op.drop_column('articles', 'top_image_url')
    op.drop_column('articles', 'authors')
    op.drop_column('articles', 'content_summary')
    op.drop_column('articles', 'content_keywords')
    op.drop_column('articles', 'extraction_error')
    op.drop_column('articles', 'extraction_status')
    op.drop_column('articles', 'extracted_at')
    op.drop_column('articles', 'content_html')
    op.drop_column('articles', 'full_content')