"""
SQLAlchemy ORM models for the VideoChecker AI database.

Tables:
  - jobs: Tracks video analysis jobs and their lifecycle state.
  - job_reports: Stores the final analysis report for completed jobs.
"""

import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, Text, JSON, ForeignKey,
)
from sqlalchemy.orm import relationship
from app.db.base import Base

logger = logging.getLogger(__name__)


class Job(Base):
    """Represents a video analysis job and its lifecycle metadata."""

    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(
        String(30), nullable=False, default="QUEUED",
        comment="QUEUED | PREPROCESSING | TRANSCRIBING | ANALYZING | VALIDATING | FINALIZING | DONE | FAILED",
    )
    original_filename = Column(String(255), nullable=False)
    gcs_path = Column(String(512), nullable=False)
    file_size_mb = Column(Float, nullable=False, default=0.0)
    duration_seconds = Column(Float, nullable=True, default=0.0)
    resolution = Column(String(50), nullable=True, default="1920x1080")
    fps = Column(Float, nullable=True, default=30.0)
    prompt = Column(Text, nullable=True, default="")
    model_used = Column(String(50), nullable=False, default="gemini-3.5-flash")
    mode = Column(String(20), nullable=False, default="realtime")
    video_language = Column(String(10), nullable=True, default="hu")
    report_language = Column(String(10), nullable=True, default="hu")

    # Cost tracking fields
    estimated_cost_usd = Column(Float, nullable=False, default=0.0)
    actual_cost_usd = Column(Float, nullable=True, default=0.0)
    input_tokens = Column(Integer, nullable=True, default=0)
    output_tokens = Column(Integer, nullable=True, default=0)
    whisper_minutes = Column(Float, nullable=True, default=0.0)
    long_context_applied = Column(Boolean, nullable=True, default=False)
    md5_hash = Column(String(32), nullable=True)

    # Rate-limit tracking
    is_quota_limited = Column(Boolean, nullable=True, default=False)
    retry_after_seconds = Column(Float, nullable=True, default=0.0)

    error_message = Column(Text, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    report = relationship(
        "JobReport", back_populates="job", uselist=False, cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id!r} status={self.status!r} file={self.original_filename!r}>"


class JobReport(Base):
    """Stores the final analysis report linked to a completed Job."""

    __tablename__ = "job_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )

    raw_response = Column(JSON, nullable=True)
    summary_json = Column(JSON, nullable=False)
    issues_json = Column(JSON, nullable=False)
    transcript_json = Column(JSON, nullable=True)
    markdown_report = Column(Text, nullable=False)

    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    job = relationship("Job", back_populates="report")

    def __repr__(self) -> str:
        return f"<JobReport id={self.id!r} job_id={self.job_id!r}>"
