"""Add content column to articles table

Revision ID: 002
Revises: 001
Create Date: 2025-08-22

"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('articles', sa.Column('content', sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column('articles', 'content')