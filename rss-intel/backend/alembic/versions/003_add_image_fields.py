"""Add image fields to articles

Revision ID: 003_add_image_fields
Revises: 002_add_content_column
Create Date: 2025-01-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add image fields to articles table
    op.add_column('articles', sa.Column('image_src_url', sa.Text(), nullable=True))
    op.add_column('articles', sa.Column('image_proxy_path', sa.Text(), nullable=True))
    op.add_column('articles', sa.Column('image_width', sa.Integer(), nullable=True))
    op.add_column('articles', sa.Column('image_height', sa.Integer(), nullable=True))
    op.add_column('articles', sa.Column('image_blurhash', sa.String(length=120), nullable=True))
    op.add_column('articles', sa.Column('has_image', sa.Boolean(), nullable=True))
    
    # Create indexes
    op.create_index('ix_articles_has_image', 'articles', ['has_image'])
    op.create_index('ix_article_has_image_score', 'articles', ['has_image', 'score_total', 'published_at'])
    op.create_index(op.f('ix_articles_image_proxy_path'), 'articles', ['image_proxy_path'], unique=True)
    
    # Set default value for has_image
    op.execute("UPDATE articles SET has_image = false WHERE has_image IS NULL")
    op.alter_column('articles', 'has_image', nullable=False, server_default=sa.text('false'))


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_article_has_image_score', table_name='articles')
    op.drop_index('ix_articles_has_image', table_name='articles')
    op.drop_index(op.f('ix_articles_image_proxy_path'), table_name='articles')
    
    # Drop columns
    op.drop_column('articles', 'has_image')
    op.drop_column('articles', 'image_blurhash')
    op.drop_column('articles', 'image_height')
    op.drop_column('articles', 'image_width')
    op.drop_column('articles', 'image_proxy_path')
    op.drop_column('articles', 'image_src_url')