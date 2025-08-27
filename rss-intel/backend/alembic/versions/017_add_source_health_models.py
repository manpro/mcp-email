"""Add source health monitoring models

Revision ID: 017_add_source_health_models
Revises: 016_add_saved_searches
Create Date: 2025-08-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '017_add_source_health_models'
down_revision = '016_add_saved_searches'
branch_labels = None
depends_on = None


def upgrade():
    # Create source_health_reports table
    op.create_table('source_health_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_name', sa.String(length=500), nullable=False),
        sa.Column('analysis_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('analysis_period_days', sa.Integer(), nullable=False, default=7),
        sa.Column('total_articles', sa.Integer(), nullable=False, default=0),
        sa.Column('successful_extractions', sa.Integer(), nullable=False, default=0),
        sa.Column('failed_extractions', sa.Integer(), nullable=False, default=0),
        sa.Column('cloudflare_blocks', sa.Integer(), nullable=False, default=0),
        sa.Column('paywall_hits', sa.Integer(), nullable=False, default=0),
        sa.Column('low_content_articles', sa.Integer(), nullable=False, default=0),
        sa.Column('spam_articles', sa.Integer(), nullable=False, default=0),
        sa.Column('extraction_success_rate', sa.Float(), nullable=False, default=0.0),
        sa.Column('content_quality_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('health_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('health_status', sa.String(length=50), nullable=False),
        sa.Column('last_successful_extraction', sa.DateTime(timezone=True), nullable=True),
        sa.Column('issues', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('health_metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('recommendations', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_source_health_reports_id', 'source_health_reports', ['id'])
    op.create_index('ix_source_health_reports_source_name', 'source_health_reports', ['source_name'])
    op.create_index('ix_source_health_reports_analysis_date', 'source_health_reports', ['analysis_date'])
    op.create_index('ix_source_health_reports_health_status', 'source_health_reports', ['health_status'])

    # Create content_extraction_results table
    op.create_table('content_extraction_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('extraction_attempt_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('original_url', sa.Text(), nullable=False),
        sa.Column('final_url', sa.Text(), nullable=True),
        sa.Column('source_name', sa.String(length=500), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False, default=False),
        sa.Column('http_status_code', sa.Integer(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('content_length', sa.Integer(), nullable=True),
        sa.Column('extracted_content_length', sa.Integer(), nullable=True),
        sa.Column('failure_reason', sa.String(length=100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('blocked_by', sa.String(length=100), nullable=True),
        sa.Column('content_quality_score', sa.Float(), nullable=True),
        sa.Column('title_content_coherence', sa.Float(), nullable=True),
        sa.Column('spam_probability', sa.Float(), nullable=True),
        sa.Column('user_agent_used', sa.String(length=500), nullable=True),
        sa.Column('proxy_used', sa.String(length=100), nullable=True),
        sa.Column('extraction_method', sa.String(length=50), nullable=True),
        sa.Column('response_headers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('response_indicators', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_content_extraction_results_id', 'content_extraction_results', ['id'])
    op.create_index('ix_content_extraction_results_article_id', 'content_extraction_results', ['article_id'])
    op.create_index('ix_content_extraction_results_extraction_attempt_at', 'content_extraction_results', ['extraction_attempt_at'])
    op.create_index('ix_content_extraction_results_source_name', 'content_extraction_results', ['source_name'])
    op.create_index('ix_content_extraction_results_success', 'content_extraction_results', ['success'])
    op.create_index('ix_content_extraction_results_failure_reason', 'content_extraction_results', ['failure_reason'])

    # Create source_quality_metrics table
    op.create_table('source_quality_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_name', sa.String(length=500), nullable=False),
        sa.Column('metric_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('articles_published', sa.Integer(), nullable=False, default=0),
        sa.Column('articles_successfully_extracted', sa.Integer(), nullable=False, default=0),
        sa.Column('articles_failed_extraction', sa.Integer(), nullable=False, default=0),
        sa.Column('articles_marked_spam', sa.Integer(), nullable=False, default=0),
        sa.Column('avg_content_quality', sa.Float(), nullable=False, default=0.0),
        sa.Column('avg_title_coherence', sa.Float(), nullable=False, default=0.0),
        sa.Column('avg_content_length', sa.Integer(), nullable=False, default=0),
        sa.Column('avg_extraction_time_ms', sa.Integer(), nullable=False, default=0),
        sa.Column('cloudflare_blocks_count', sa.Integer(), nullable=False, default=0),
        sa.Column('paywall_hits_count', sa.Integer(), nullable=False, default=0),
        sa.Column('timeout_errors_count', sa.Integer(), nullable=False, default=0),
        sa.Column('extraction_success_rate', sa.Float(), nullable=False, default=0.0),
        sa.Column('content_quality_rate', sa.Float(), nullable=False, default=0.0),
        sa.Column('spam_rate', sa.Float(), nullable=False, default=0.0),
        sa.Column('trend_direction', sa.String(length=20), nullable=True),
        sa.Column('trend_confidence', sa.Float(), nullable=False, default=0.0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_source_quality_metrics_id', 'source_quality_metrics', ['id'])
    op.create_index('ix_source_quality_metrics_source_name', 'source_quality_metrics', ['source_name'])
    op.create_index('ix_source_quality_metrics_metric_date', 'source_quality_metrics', ['metric_date'])

    # Create source_health_alerts table
    op.create_table('source_health_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_name', sa.String(length=500), nullable=False),
        sa.Column('alert_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=True),
        sa.Column('threshold_value', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='active'),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('recommended_actions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_source_health_alerts_id', 'source_health_alerts', ['id'])
    op.create_index('ix_source_health_alerts_source_name', 'source_health_alerts', ['source_name'])
    op.create_index('ix_source_health_alerts_alert_type', 'source_health_alerts', ['alert_type'])
    op.create_index('ix_source_health_alerts_severity', 'source_health_alerts', ['severity'])
    op.create_index('ix_source_health_alerts_status', 'source_health_alerts', ['status'])
    op.create_index('ix_source_health_alerts_created_at', 'source_health_alerts', ['created_at'])


def downgrade():
    op.drop_table('source_health_alerts')
    op.drop_table('source_quality_metrics')
    op.drop_table('content_extraction_results')
    op.drop_table('source_health_reports')