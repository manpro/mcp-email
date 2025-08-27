"""add spam reports table

Revision ID: 013_add_spam_reports
Revises: 012_add_content_type
Create Date: 2025-08-26 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '013_add_spam_reports'
down_revision = '012_add_content_type'
branch_labels = None
depends_on = None


def upgrade():
    # Create spam_reports table
    op.create_table(
        'spam_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('reported_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),  # 'user_feedback', 'ml_detection', etc.
        sa.Column('reason', sa.String(100), nullable=False),  # 'promotional_content', 'spam', etc.
        sa.Column('report_count', sa.Integer(), default=1, nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('article_id', name='uq_spam_reports_article_id')
    )
    
    # Create index for efficient queries
    op.create_index('idx_spam_reports_reported_at', 'spam_reports', ['reported_at'])
    op.create_index('idx_spam_reports_source', 'spam_reports', ['source'])


def downgrade():
    op.drop_index('idx_spam_reports_source')
    op.drop_index('idx_spam_reports_reported_at')
    op.drop_table('spam_reports')