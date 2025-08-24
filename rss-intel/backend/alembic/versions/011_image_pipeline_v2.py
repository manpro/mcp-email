"""Image pipeline v2 - enhanced extraction and diagnostics

Revision ID: 011_image_pipeline_v2
Revises: 010_add_story_clustering
Create Date: 2024-08-24 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '011_image_pipeline_v2'
down_revision = '010_add_story_clustering'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new image fields to articles table
    op.add_column('articles', sa.Column('image_stage', sa.String(50), nullable=True))
    op.add_column('articles', sa.Column('image_reason', sa.String(200), nullable=True))
    
    # Create index on has_image if it doesn't exist
    try:
        op.create_index('ix_articles_has_image', 'articles', ['has_image'])
    except:
        pass  # Index might already exist
    
    # Create image_diagnostics table
    op.create_table('image_diagnostics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('domain', sa.String(255), nullable=False),
        sa.Column('stage', sa.String(50), nullable=False),
        sa.Column('reason', sa.String(200), nullable=False),
        sa.Column('http_status', sa.Integer(), nullable=True),
        sa.Column('bytes', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ),
    )
    
    # Create indexes for diagnostics
    op.create_index('ix_image_diagnostics_domain', 'image_diagnostics', ['domain'])
    op.create_index('ix_image_diagnostics_created_at', 'image_diagnostics', ['created_at'])
    op.create_index('ix_image_diagnostics_domain_created', 'image_diagnostics', ['domain', 'created_at'])


def downgrade() -> None:
    # Drop diagnostics table
    op.drop_table('image_diagnostics')
    
    # Remove new columns from articles
    op.drop_column('articles', 'image_reason')
    op.drop_column('articles', 'image_stage')