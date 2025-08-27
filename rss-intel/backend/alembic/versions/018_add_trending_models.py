"""Add trending analysis models

Revision ID: 018_add_trending_models
Revises: 017_add_source_health_models
Create Date: 2025-08-27 12:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '018_add_trending_models'
down_revision = '017_add_source_health_models'
branch_labels = None
depends_on = None


def upgrade():
    # Create trending_topics table
    op.create_table('trending_topics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('topic_name', sa.String(length=200), nullable=False),
        sa.Column('topic_type', sa.String(length=50), nullable=False),
        sa.Column('trend_score', sa.Float(), nullable=False),
        sa.Column('velocity', sa.Float(), nullable=False, default=0.0),
        sa.Column('article_count', sa.Integer(), nullable=False, default=0),
        sa.Column('unique_sources', sa.Integer(), nullable=False, default=0),
        sa.Column('engagement_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('related_article_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('trend_direction', sa.String(length=20), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, default=0.0),
        sa.Column('prediction_accuracy', sa.Float(), nullable=True),
        sa.Column('first_detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('peak_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_viral', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_trending_topics_id', 'trending_topics', ['id'])
    op.create_index('ix_trending_topics_topic_name', 'trending_topics', ['topic_name'])
    op.create_index('ix_trending_topics_topic_type', 'trending_topics', ['topic_type'])
    op.create_index('ix_trending_topics_trend_score', 'trending_topics', ['trend_score'])
    op.create_index('ix_trending_topics_trend_direction', 'trending_topics', ['trend_direction'])
    op.create_index('ix_trending_topics_first_detected_at', 'trending_topics', ['first_detected_at'])
    op.create_index('ix_trending_topics_is_active', 'trending_topics', ['is_active'])
    op.create_index('ix_trending_topics_is_viral', 'trending_topics', ['is_viral'])

    # Create topic_clusters table
    op.create_table('topic_clusters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cluster_name', sa.String(length=200), nullable=False),
        sa.Column('cluster_type', sa.String(length=50), nullable=False),
        sa.Column('keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('article_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('coherence_score', sa.Float(), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('timespan_hours', sa.Float(), default=0.0),
        sa.Column('first_article_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_article_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('geographic_spread', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('source_diversity', sa.Float(), default=0.0),
        sa.Column('unique_sources', sa.Integer(), default=0),
        sa.Column('analysis_method', sa.String(length=100), nullable=True),
        sa.Column('algorithm_version', sa.String(length=50), nullable=True),
        sa.Column('analysis_parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_topic_clusters_id', 'topic_clusters', ['id'])

    # Create topic_analyses table
    op.create_table('topic_analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('analysis_type', sa.String(length=50), nullable=False),
        sa.Column('time_window_hours', sa.Integer(), nullable=False),
        sa.Column('articles_analyzed', sa.Integer(), default=0),
        sa.Column('sources_analyzed', sa.Integer(), default=0),
        sa.Column('topics_found', sa.Integer(), default=0),
        sa.Column('clusters_found', sa.Integer(), default=0),
        sa.Column('viral_articles', sa.Integer(), default=0),
        sa.Column('emerging_topics', sa.Integer(), default=0),
        sa.Column('analysis_quality_score', sa.Float(), default=0.0),
        sa.Column('confidence_level', sa.Float(), default=0.0),
        sa.Column('analysis_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('trending_keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('predictions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('execution_time_seconds', sa.Float(), nullable=True),
        sa.Column('memory_usage_mb', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='completed'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_topic_analyses_id', 'topic_analyses', ['id'])
    op.create_index('ix_topic_analyses_analysis_type', 'topic_analyses', ['analysis_type'])
    op.create_index('ix_topic_analyses_created_at', 'topic_analyses', ['created_at'])

    # Create viral_content table
    op.create_table('viral_content',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('viral_score', sa.Float(), nullable=False),
        sa.Column('engagement_rate', sa.Float(), default=0.0),
        sa.Column('share_velocity', sa.Float(), default=0.0),
        sa.Column('peak_engagement_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('viral_triggers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('viral_keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('engagement_pattern', sa.String(length=50), nullable=True),
        sa.Column('viral_regions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('cross_platform', sa.Boolean(), default=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('detection_method', sa.String(length=100), nullable=True),
        sa.Column('confidence', sa.Float(), default=0.0),
        sa.Column('first_viral_indicator', sa.DateTime(timezone=True), nullable=True),
        sa.Column('viral_decay_started', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_still_viral', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('article_id')
    )
    op.create_index('ix_viral_content_id', 'viral_content', ['id'])
    op.create_index('ix_viral_content_article_id', 'viral_content', ['article_id'])
    op.create_index('ix_viral_content_viral_score', 'viral_content', ['viral_score'])

    # Create trend_predictions table
    op.create_table('trend_predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('topic_name', sa.String(length=200), nullable=False),
        sa.Column('prediction_type', sa.String(length=50), nullable=False),
        sa.Column('predicted_score', sa.Float(), nullable=False),
        sa.Column('confidence_level', sa.Float(), nullable=False),
        sa.Column('prediction_horizon_hours', sa.Integer(), nullable=False),
        sa.Column('based_on_articles', sa.Integer(), default=0),
        sa.Column('based_on_sources', sa.Integer(), default=0),
        sa.Column('algorithm_used', sa.String(length=100), nullable=True),
        sa.Column('input_features', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('actual_score', sa.Float(), nullable=True),
        sa.Column('prediction_accuracy', sa.Float(), nullable=True),
        sa.Column('outcome_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='active'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_trend_predictions_id', 'trend_predictions', ['id'])
    op.create_index('ix_trend_predictions_topic_name', 'trend_predictions', ['topic_name'])
    op.create_index('ix_trend_predictions_created_at', 'trend_predictions', ['created_at'])
    op.create_index('ix_trend_predictions_expires_at', 'trend_predictions', ['expires_at'])


def downgrade():
    op.drop_table('trend_predictions')
    op.drop_table('viral_content')
    op.drop_table('topic_analyses')
    op.drop_table('topic_clusters')
    op.drop_table('trending_topics')