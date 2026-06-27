import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String(30), nullable=False, default="QUEUED")  # QUEUED, PREPROCESSING, TRANSCRIBING, ANALYZING, DONE, FAILED
    original_filename = Column(String(255), nullable=False)
    gcs_path = Column(String(512), nullable=False)
    file_size_mb = Column(Float, nullable=False, default=0.0)
    duration_seconds = Column(Float, nullable=True, default=0.0)
    resolution = Column(String(50), nullable=True, default="1920x1080")
    fps = Column(Float, nullable=True, default=30.0)
    prompt = Column(Text, nullable=True, default="")
    model_used = Column(String(50), nullable=False, default="gemini-3.1-pro")
    mode = Column(String(20), nullable=False, default="realtime")  # realtime or batch
    
    # Cost tracking fields
    estimated_cost_usd = Column(Float, nullable=False, default=0.0)
    actual_cost_usd = Column(Float, nullable=True, default=0.0)
    input_tokens = Column(Integer, nullable=True, default=0)
    output_tokens = Column(Integer, nullable=True, default=0)
    whisper_minutes = Column(Float, nullable=True, default=0.0)
    long_context_applied = Column(Boolean, nullable=True, default=False)
    md5_hash = Column(String(32), nullable=True)
    
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    report = relationship("JobReport", back_populates="job", uselist=False, cascade="all, delete-orphan")


class JobReport(Base):
    __tablename__ = "job_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    raw_response = Column(JSON, nullable=True)
    summary_json = Column(JSON, nullable=False)
    issues_json = Column(JSON, nullable=False)
    transcript_json = Column(JSON, nullable=True)
    markdown_report = Column(Text, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    job = relationship("Job", back_populates="report")
