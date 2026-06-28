"""add missing columns to jobs table

Revision ID: 002_add_missing_columns
Revises: 001_initial
Create Date: 2026-06-28 09:50:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_missing_columns'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Columns present in the SQLAlchemy model but missing from 001_initial
    op.add_column(
        'jobs',
        sa.Column('video_language', sa.String(length=10), nullable=True, server_default='hu'),
    )
    op.add_column(
        'jobs',
        sa.Column('report_language', sa.String(length=10), nullable=True, server_default='hu'),
    )
    op.add_column(
        'jobs',
        sa.Column('is_quota_limited', sa.Boolean(), nullable=True, server_default=sa.text('false')),
    )
    op.add_column(
        'jobs',
        sa.Column('retry_after_seconds', sa.Float(), nullable=True, server_default='0.0'),
    )


def downgrade() -> None:
    op.drop_column('jobs', 'retry_after_seconds')
    op.drop_column('jobs', 'is_quota_limited')
    op.drop_column('jobs', 'report_language')
    op.drop_column('jobs', 'video_language')
