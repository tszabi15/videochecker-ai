"""initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2026-06-27 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('gcs_path', sa.String(length=512), nullable=False),
        sa.Column('file_size_mb', sa.Float(), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('resolution', sa.String(length=50), nullable=True),
        sa.Column('fps', sa.Float(), nullable=True),
        sa.Column('prompt', sa.Text(), nullable=True),
        sa.Column('model_used', sa.String(length=50), nullable=False),
        sa.Column('mode', sa.String(length=20), nullable=False),
        sa.Column('estimated_cost_usd', sa.Float(), nullable=False),
        sa.Column('actual_cost_usd', sa.Float(), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('whisper_minutes', sa.Float(), nullable=True),
        sa.Column('long_context_applied', sa.Boolean(), nullable=True),
        sa.Column('md5_hash', sa.String(length=32), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'job_reports',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('raw_response', sa.JSON(), nullable=True),
        sa.Column('summary_json', sa.JSON(), nullable=False),
        sa.Column('issues_json', sa.JSON(), nullable=False),
        sa.Column('transcript_json', sa.JSON(), nullable=True),
        sa.Column('markdown_report', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id')
    )

def downgrade() -> None:
    op.drop_table('job_reports')
    op.drop_table('jobs')
