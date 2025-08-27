"""Add spam reports tracking

Revision ID: 015_add_spam_reports
Revises: 014_optimize_indexes
Create Date: 2025-01-27 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '015_add_spam_reports'
down_revision = '014_optimize_indexes'
branch_labels = None
depends_on = None


def upgrade():
    # Create spam_reports table
    op.create_table(
        'spam_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('report_type', sa.String(50), nullable=False),  # 'auto_detected', 'user_reported', 'manual_review'
        sa.Column('spam_probability', sa.Float(), nullable=False),
        sa.Column('content_score', sa.Float(), nullable=False),
        sa.Column('title_coherence', sa.Float(), nullable=False),
        sa.Column('recommendation', sa.String(20), nullable=False),  # 'accept', 'review', 'reject'
        sa.Column('spam_signals', postgresql.JSONB(), nullable=True),
        sa.Column('quality_issues', postgresql.JSONB(), nullable=True),
        sa.Column('detection_summary', sa.Text(), nullable=True),
        sa.Column('reported_by', sa.String(100), nullable=True),  # 'system' or user ID
        sa.Column('reviewed_by', sa.String(100), nullable=True),
        sa.Column('review_status', sa.String(20), nullable=True),  # 'pending', 'confirmed', 'false_positive'
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for spam_reports
    op.create_index('ix_spam_reports_article_id', 'spam_reports', ['article_id'])
    op.create_index('ix_spam_reports_report_type', 'spam_reports', ['report_type'])
    op.create_index('ix_spam_reports_recommendation', 'spam_reports', ['recommendation'])
    op.create_index('ix_spam_reports_review_status', 'spam_reports', ['review_status'])
    op.create_index('ix_spam_reports_created_at', 'spam_reports', ['created_at'])
    op.create_index('ix_spam_reports_spam_probability', 'spam_reports', ['spam_probability'])
    
    # Add spam tracking columns to articles table
    op.add_column('articles', sa.Column('spam_detected', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('articles', sa.Column('spam_probability', sa.Float(), nullable=True))
    op.add_column('articles', sa.Column('content_quality_score', sa.Float(), nullable=True))
    op.add_column('articles', sa.Column('title_coherence_score', sa.Float(), nullable=True))
    op.add_column('articles', sa.Column('spam_signals', postgresql.JSONB(), nullable=True))
    op.add_column('articles', sa.Column('last_spam_check', sa.DateTime(timezone=True), nullable=True))
    
    # Create indexes for new article spam columns
    op.create_index('ix_articles_spam_detected', 'articles', ['spam_detected'])
    op.create_index('ix_articles_spam_probability', 'articles', ['spam_probability'])
    op.create_index('ix_articles_content_quality_score', 'articles', ['content_quality_score'])
    op.create_index('ix_articles_last_spam_check', 'articles', ['last_spam_check'])
    
    # Create spam_detection_stats table for monitoring
    op.create_table(
        'spam_detection_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('total_articles_checked', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('spam_detected_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('false_positives', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('false_negatives', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('avg_spam_probability', sa.Float(), nullable=True),
        sa.Column('avg_content_score', sa.Float(), nullable=True),
        sa.Column('signal_type_counts', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date'),
    )
    
    # Create index for stats table
    op.create_index('ix_spam_detection_stats_date', 'spam_detection_stats', ['date'])


def downgrade():
    # Drop indexes first
    op.drop_index('ix_spam_detection_stats_date', table_name='spam_detection_stats')
    op.drop_index('ix_articles_last_spam_check', table_name='articles')
    op.drop_index('ix_articles_content_quality_score', table_name='articles')
    op.drop_index('ix_articles_spam_probability', table_name='articles')
    op.drop_index('ix_articles_spam_detected', table_name='articles')
    op.drop_index('ix_spam_reports_spam_probability', table_name='spam_reports')
    op.drop_index('ix_spam_reports_created_at', table_name='spam_reports')
    op.drop_index('ix_spam_reports_review_status', table_name='spam_reports')
    op.drop_index('ix_spam_reports_recommendation', table_name='spam_reports')
    op.drop_index('ix_spam_reports_report_type', table_name='spam_reports')
    op.drop_index('ix_spam_reports_article_id', table_name='spam_reports')
    
    # Drop tables
    op.drop_table('spam_detection_stats')
    op.drop_table('spam_reports')
    
    # Remove columns from articles table
    op.drop_column('articles', 'last_spam_check')
    op.drop_column('articles', 'spam_signals')
    op.drop_column('articles', 'title_coherence_score')
    op.drop_column('articles', 'content_quality_score')
    op.drop_column('articles', 'spam_probability')
    op.drop_column('articles', 'spam_detected')