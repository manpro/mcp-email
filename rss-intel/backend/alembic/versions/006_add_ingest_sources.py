"""Add ingest sources

Revision ID: 006_add_ingest_sources
Revises: 005_ml_tables
Create Date: 2025-08-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_add_ingest_sources'
down_revision = '005_ml_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create source types enum
    source_type_enum = postgresql.ENUM(
        'rss', 'json', 'sitemap', 'api', 'email', 'activitypub', 'webhook',
        name='source_type_enum'
    )
    source_type_enum.create(op.get_bind())
    
    # Create sources table
    op.create_table('sources',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('type', source_type_enum, nullable=False),
        sa.Column('config', postgresql.JSONB(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_fetch_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
    )
    
    # Create ingest_jobs table
    op.create_table('ingest_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_id', sa.Integer(), sa.ForeignKey('sources.id'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='running'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('items_found', sa.Integer(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
    )
    
    # Create article_chunks table
    op.create_table('article_chunks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('articles.id'), nullable=False),
        sa.Column('chunk_ix', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Add new columns to articles table
    op.add_column('articles', sa.Column('lang', sa.String(5), nullable=True))
    op.add_column('articles', sa.Column('near_dup_id', sa.Integer(), sa.ForeignKey('articles.id'), nullable=True))
    
    # Create indexes
    op.create_index('ix_sources_type', 'sources', ['type'])
    op.create_index('ix_sources_enabled', 'sources', ['enabled'])
    op.create_index('ix_ingest_jobs_source_id', 'ingest_jobs', ['source_id'])
    op.create_index('ix_ingest_jobs_status', 'ingest_jobs', ['status'])
    op.create_index('ix_ingest_jobs_started_at', 'ingest_jobs', ['started_at'])
    op.create_index('ix_article_chunks_article_id', 'article_chunks', ['article_id'])
    op.create_index('ix_articles_source_published', 'articles', ['source', 'published_at'])
    op.create_index('ix_articles_lang', 'articles', ['lang'])
    op.create_index('ix_articles_near_dup_id', 'articles', ['near_dup_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_articles_near_dup_id', table_name='articles')
    op.drop_index('ix_articles_lang', table_name='articles')
    op.drop_index('ix_articles_source_published', table_name='articles')
    op.drop_index('ix_article_chunks_article_id', table_name='article_chunks')
    op.drop_index('ix_ingest_jobs_started_at', table_name='ingest_jobs')
    op.drop_index('ix_ingest_jobs_status', table_name='ingest_jobs')
    op.drop_index('ix_ingest_jobs_source_id', table_name='ingest_jobs')
    op.drop_index('ix_sources_enabled', table_name='sources')
    op.drop_index('ix_sources_type', table_name='sources')
    
    # Drop columns from articles
    op.drop_column('articles', 'near_dup_id')
    op.drop_column('articles', 'lang')
    
    # Drop tables
    op.drop_table('article_chunks')
    op.drop_table('ingest_jobs')
    op.drop_table('sources')
    
    # Drop enum
    postgresql.ENUM(name='source_type_enum').drop(op.get_bind())