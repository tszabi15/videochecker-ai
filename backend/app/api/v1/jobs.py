"""
Job management API endpoints.

Provides CRUD operations for video analysis jobs: upload, status check,
report retrieval, listing, and deletion.
"""

import os
import uuid
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Job, JobReport
from app.schemas.job import (
    JobCreateResponse, JobStatusResponse, JobListItem,
    ModelEnum, ModeEnum,
)
from app.schemas.report import ReportResponse
from app.services.gcs import gcs_service
from app.services.cost import estimate_job_cost
from app.tasks.pipeline import run_job_pipeline
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}


@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(""),
    model: ModelEnum = Form(ModelEnum.GEMINI_3_5_FLASH),
    mode: ModeEnum = Form(ModeEnum.REALTIME),
    video_language: Optional[str] = Form("hu"),
    report_language: Optional[str] = Form("hu"),
    db: Session = Depends(get_db),
) -> JobCreateResponse:
    """
    Upload a video file and create a new analysis job.

    Validates file extension and size, uploads to GCS, estimates cost,
    and enqueues the Celery processing pipeline.
    """
    # Guard against missing filename
    filename = file.filename or "untitled.mp4"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed formats: MP4, MOV, AVI, MKV",
        )

    job_id = str(uuid.uuid4())
    temp_file_path = os.path.join(settings.TEMP_DIR, f"upload_{job_id}{ext}")

    # Save uploaded file temporarily — wrapped in try/finally for cleanup on failure
    size_bytes = 0
    try:
        with open(temp_file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                buffer.write(chunk)
                size_bytes += len(chunk)

        file_size_mb = round(size_bytes / (1024 * 1024), 2)
        if file_size_mb > settings.MAX_VIDEO_SIZE_MB:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"File size ({file_size_mb} MB) exceeds maximum "
                    f"allowed limit of {settings.MAX_VIDEO_SIZE_MB} MB."
                ),
            )

        # Upload to GCS (or local fallback)
        gcs_blob_name = f"jobs/{job_id}/{filename}"
        gcs_path = gcs_service.upload_file(temp_file_path, gcs_blob_name)
        logger.info("Uploaded %s to %s (%.2f MB)", filename, gcs_path, file_size_mb)
    finally:
        # Always clean up the temporary upload file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    # Estimate cost pre-run
    est_cost = estimate_job_cost(
        model.value, file_size_mb, is_batch=(mode == ModeEnum.BATCH),
    )

    # Create Job record in DB
    job = Job(
        id=job_id,
        status="QUEUED",
        original_filename=filename,
        gcs_path=gcs_path,
        file_size_mb=file_size_mb,
        prompt=prompt,
        model_used=model.value,
        mode=mode.value,
        video_language=video_language or "hu",
        report_language=report_language or "hu",
        estimated_cost_usd=est_cost,
    )
    db.add(job)
    db.commit()

    # Enqueue async processing pipeline
    run_job_pipeline(job_id)
    logger.info("Job %s enqueued for pipeline processing", job_id)

    return JobCreateResponse(
        job_id=job_id,
        status="QUEUED",
        estimated_cost_usd=est_cost,
    )


@router.get("", response_model=List[JobListItem])
def list_jobs(db: Session = Depends(get_db)) -> List[JobListItem]:
    """Returns all jobs ordered by creation date (newest first)."""
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    results: List[JobListItem] = []
    for job in jobs:
        overall_score: Optional[float] = None
        if job.report and job.report.summary_json:
            overall_score = job.report.summary_json.get("overall_score")
        results.append(
            JobListItem(
                id=job.id,
                original_filename=job.original_filename,
                duration_seconds=job.duration_seconds,
                submitted_at=job.created_at,
                status=job.status,
                model_used=job.model_used,
                overall_score=overall_score,
                cost_usd=job.actual_cost_usd or job.estimated_cost_usd,
            )
        )
    return results


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str, db: Session = Depends(get_db)) -> JobStatusResponse:
    """Returns the current status and metadata for a specific job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found",
        )
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        original_filename=job.original_filename,
        model_used=job.model_used,
        mode=job.mode,
        video_language=job.video_language or "hu",
        report_language=job.report_language or "hu",
        created_at=job.created_at,
        updated_at=job.updated_at,
        error_message=job.error_message,
        estimated_cost_usd=job.estimated_cost_usd,
        actual_cost_usd=job.actual_cost_usd,
        duration_seconds=job.duration_seconds,
        is_quota_limited=job.is_quota_limited or False,
        retry_after_seconds=job.retry_after_seconds or 0.0,
    )


@router.get("/{job_id}/report", response_model=ReportResponse)
def get_job_report(job_id: str, db: Session = Depends(get_db)) -> ReportResponse:
    """Returns the full analysis report (JSON + Markdown) for a completed job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found",
        )
    if job.status != "DONE" or not job.report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report not ready. Current job status is '{job.status}'",
        )

    raw_res = dict(job.report.raw_response or {})
    raw_res["processing_model"] = job.model_used or "gemini-3.5-flash"
    raw_res["cost_usd"] = job.actual_cost_usd if job.actual_cost_usd is not None else (job.estimated_cost_usd or 0.0)
    return ReportResponse(
        json_report=raw_res,
        markdown_report=job.report.markdown_report,
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: str, db: Session = Depends(get_db)) -> None:
    """Deletes a job and its associated GCS files."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found",
        )

    # Delete file from GCS
    if job.gcs_path:
        try:
            gcs_service.delete_file(job.gcs_path)
        except Exception as e:
            logger.warning("Failed to delete GCS file %s: %s", job.gcs_path, e)

    db.delete(job)
    db.commit()
    logger.info("Deleted job %s and associated resources", job_id)
    return None
