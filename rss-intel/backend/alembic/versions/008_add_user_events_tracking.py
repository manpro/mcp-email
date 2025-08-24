"""add_user_events_tracking

Revision ID: 008_add_user_events_tracking
Revises: 007_add_story_clustering
Create Date: 2025-08-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '008_add_user_events_tracking'
down_revision = '007_add_story_clustering'
branch_labels = None
depends_on = None


def upgrade():
    # Create events table for user interaction tracking
    op.create_table('events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('visible_ms', sa.Integer(), nullable=True),
        sa.Column('scroll_pct', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add indexes for performance
    op.create_index('ix_events_article_id', 'events', ['article_id'])
    op.create_index('ix_events_type_created', 'events', ['event_type', 'created_at'])
    op.create_index('ix_events_created_at', 'events', ['created_at'])
    
    # Create ML tables for personalization
    op.create_table('article_vectors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('title_len', sa.Integer(), nullable=True),
        sa.Column('has_image', sa.Boolean(), nullable=True),
        sa.Column('source_hash', sa.String(32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('ix_article_vectors_article_id', 'article_vectors', ['article_id'])
    
    # Create models table for ML model versioning
    op.create_table('ml_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_type', sa.String(50), nullable=False),
        sa.Column('version', sa.String(20), nullable=False),
        sa.Column('params', postgresql.JSONB(), nullable=True),
        sa.Column('metrics', postgresql.JSONB(), nullable=True),
        sa.Column('model_path', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('ix_ml_models_type_active', 'ml_models', ['model_type', 'is_active'])
    
    # Create predictions table
    op.create_table('predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('features', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['model_id'], ['ml_models.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('ix_predictions_article_id', 'predictions', ['article_id'])
    op.create_index('ix_predictions_model_id', 'predictions', ['model_id'])


def downgrade():
    op.drop_table('predictions')
    op.drop_table('ml_models')
    op.drop_table('article_vectors')
    op.drop_table('events')