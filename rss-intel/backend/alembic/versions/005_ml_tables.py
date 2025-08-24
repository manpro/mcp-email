"""Add ML tables for personalized learning

Revision ID: 005_ml_tables
Revises: 004_add_content_extraction
Create Date: 2025-08-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '005_ml_tables'
down_revision = '004_add_content_extraction'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Events table for user interactions
    op.create_table('events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('articles.id'), nullable=False),
        sa.Column('user_id', sa.String(50), nullable=False, server_default='owner'),
        sa.Column('type', sa.String(20), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('visible_ms', sa.Integer(), nullable=True),
        sa.Column('scroll_pct', sa.SmallInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("type IN ('impression', 'open', 'external_click', 'star', 'label_add', 'dismiss', 'mark_read')")
    )
    op.create_index('ix_events_created_at', 'events', ['created_at'])
    op.create_index('ix_events_article_user', 'events', ['article_id', 'user_id'])
    
    # Article vectors table for embeddings
    op.create_table('article_vectors',
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('articles.id'), primary_key=True),
        sa.Column('emb', postgresql.ARRAY(sa.Float), nullable=False),  # Will be vector(384) after pgvector
        sa.Column('title_len', sa.Integer(), nullable=False),
        sa.Column('has_image', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('source', sa.String(100), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index('ix_article_vectors_published_at', 'article_vectors', ['published_at'], postgresql_using='btree')
    
    # Models table for ML artifacts
    op.create_table('models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(20), nullable=False, server_default='logreg'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('metrics', postgresql.JSONB(), nullable=True),
        sa.Column('artifact_path', sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Predictions table
    op.create_table('predictions',
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('articles.id'), nullable=False),
        sa.Column('model_id', sa.Integer(), sa.ForeignKey('models.id'), nullable=False),
        sa.Column('p_read', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('article_id', 'model_id')
    )
    
    # A/B config table
    op.create_table('ab_config',
        sa.Column('key', sa.String(50), primary_key=True),
        sa.Column('value', postgresql.JSONB(), nullable=False)
    )
    
    # Insert default A/B config
    op.execute("""
        INSERT INTO ab_config (key, value) VALUES
        ('epsilon', '0.1'),
        ('mmr_lambda', '0.25'), 
        ('control_ratio', '0.2'),
        ('enabled', 'true')
    """)

def downgrade() -> None:
    op.drop_table('ab_config')
    op.drop_table('predictions')
    op.drop_table('models')
    op.drop_table('article_vectors')
    op.drop_table('events')