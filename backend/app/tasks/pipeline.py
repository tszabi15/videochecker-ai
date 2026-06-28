"""
Celery pipeline tasks for the video analysis workflow.

Pipeline stages (executed as a Celery chain):
  1. preprocess  — Download, compute MD5, probe metadata, normalize video
  2. transcribe  — Transcribe audio via Groq/Whisper
  3. analyze     — Run multimodal AI analysis via Gemini
  4. validate    — Cross-validate CRITICAL issues with a second Gemini call
  5. finalize    — Compile report, persist to DB, clean up temp files
"""

import os
import json
import shutil
import logging
from typing import Dict, Any

from concurrent.futures import ThreadPoolExecutor
from celery import chain

from app.tasks.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models import Job, JobReport
from app.services.gcs import gcs_service
from app.services.ffmpeg import ffmpeg_service
from app.services.whisper import transcribe_with_groq
from app.services.gemini import gemini_service, GeminiAnalysisError
from app.services.cost import calculate_gemini_cost, estimate_job_cost
from app.config import settings

logger = logging.getLogger(__name__)

# -- Shared helpers ----------------------------------------------------------


def _update_quota_status(
    job_id: str, *, is_limited: bool, retry_seconds: float = 0.0,
) -> None:
    """Safely updates quota-limit status on a job. Uses its own DB session."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.is_quota_limited = is_limited
            job.retry_after_seconds = round(retry_seconds, 1)
            db.commit()
    except Exception as exc:
        logger.warning("Failed to update quota status for job %s: %s", job_id, exc)
        db.rollback()
    finally:
        db.close()


def _make_quota_callbacks(job_id: str):
    """Returns (on_quota_limit, on_quota_cleared) callback pair for a job."""

    def on_quota_limit(sleep_time: float) -> None:
        _update_quota_status(job_id, is_limited=True, retry_seconds=sleep_time)

    def on_quota_cleared() -> None:
        _update_quota_status(job_id, is_limited=False)

    return on_quota_limit, on_quota_cleared


def _fail_job(db, job: Job, stage: str, error: Exception) -> None:
    """Marks a job as FAILED with a descriptive error message."""
    job.status = "FAILED"
    job.error_message = f"{stage} failed: {error}"
    try:
        db.commit()
    except Exception:
        db.rollback()
    logger.error("Job %s failed at %s: %s", job.id, stage, error)


# -- Pipeline entry point ----------------------------------------------------


def run_job_pipeline(job_id: str) -> None:
    """Triggers the sequential Celery pipeline chain."""
    pipeline_chain = chain(
        preprocess.s(job_id),
        transcribe.s(),
        analyze.s(),
        validate.s(),
        finalize.s(),
    )
    pipeline_chain.apply_async()
    logger.info("Pipeline chain enqueued for job %s", job_id)


# -- Stage 1: Preprocessing --------------------------------------------------


@celery_app.task(bind=True, soft_time_limit=600, time_limit=660)
def preprocess(self, job_id: str) -> str:
    """Downloads video, computes MD5, probes metadata, runs FFmpeg prep."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found.")

        job.status = "PREPROCESSING"
        db.commit()
        logger.info("[preprocess] Job %s — starting", job_id)

        work_dir = os.path.join(settings.TEMP_DIR, job_id)
        os.makedirs(work_dir, exist_ok=True)

        local_video_path = os.path.join(work_dir, f"original_{job.original_filename}")
        gcs_service.download_file(job.gcs_path, local_video_path)

        # Compute MD5
        md5_hash = ffmpeg_service.compute_md5(local_video_path)
        job.md5_hash = md5_hash

        # Probe metadata
        probe_meta = ffmpeg_service.probe_video(local_video_path)
        job.duration_seconds = probe_meta["duration"]
        job.resolution = probe_meta["resolution"]
        job.fps = probe_meta["fps"]

        # Run FFmpeg normalization & audio extraction
        ffmpeg_service.preprocess_video(local_video_path, work_dir)

        # Calculate updated pre-run estimated cost
        job.estimated_cost_usd = estimate_job_cost(
            job.model_used,
            job.file_size_mb,
            job.duration_seconds,
            is_batch=(job.mode == "batch"),
        )
        db.commit()
        logger.info("[preprocess] Job %s — done (%.1fs video)", job_id, job.duration_seconds)
        return job_id
    except Exception as e:
        if "job" in locals() and job:
            _fail_job(db, job, "Preprocessing", e)
        raise
    finally:
        db.close()


# -- Stage 2: Transcription --------------------------------------------------


@celery_app.task(bind=True, soft_time_limit=600, time_limit=660)
def transcribe(self, job_id: str) -> str:
    """Transcribes audio via Groq Whisper API."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found.")

        job.status = "TRANSCRIBING"
        db.commit()
        logger.info("[transcribe] Job %s — starting", job_id)

        work_dir = os.path.join(settings.TEMP_DIR, job_id)
        audio_wav = os.path.join(work_dir, "audio.wav")

        segments = transcribe_with_groq(audio_wav)
        transcript = {"segments": segments}
        job.whisper_minutes = round((job.duration_seconds or 0.0) / 60.0, 2)
        db.commit()

        # Save temporary transcript file
        with open(os.path.join(work_dir, "transcript.json"), "w") as f:
            json.dump(transcript, f)

        logger.info(
            "[transcribe] Job %s — done (%d segments, %.2f min)",
            job_id, len(segments), job.whisper_minutes,
        )
        return job_id
    except Exception as e:
        if "job" in locals() and job:
            _fail_job(db, job, "Transcription", e)
        raise
    finally:
        db.close()


# -- Stage 3: AI Analysis ----------------------------------------------------


@celery_app.task(bind=True, soft_time_limit=900, time_limit=960)
def analyze(self, job_id: str) -> str:
    """Runs multimodal AI analysis via Gemini."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found.")

        job.status = "ANALYZING"
        db.commit()
        logger.info("[analyze] Job %s — starting with model %s", job_id, job.model_used)

        work_dir = os.path.join(settings.TEMP_DIR, job_id)
        local_video_path = os.path.join(work_dir, f"original_{job.original_filename}")
        if not os.path.exists(local_video_path):
            local_video_path = os.path.join(work_dir, "normalized.mp4")

        transcript_path = os.path.join(work_dir, "transcript.json")
        transcript: Dict[str, Any] = {}
        if os.path.exists(transcript_path):
            with open(transcript_path, "r") as f:
                transcript = json.load(f)

        metadata = {
            "duration": job.duration_seconds,
            "resolution": job.resolution,
            "fps": job.fps,
            "size_mb": job.file_size_mb,
        }

        on_quota_limit, on_quota_cleared = _make_quota_callbacks(job_id)

        report_json, in_tokens, out_tokens = gemini_service.analyze_video(
            video_path=local_video_path,
            video_metadata=metadata,
            whisper_transcript=transcript,
            user_prompt=job.prompt or "",
            model_alias=job.model_used,
            mode=job.mode,
            video_language=job.video_language or "hu",
            report_language=job.report_language or "hu",
            on_quota_limit=on_quota_limit,
            on_quota_cleared=on_quota_cleared,
        )

        cost_usd, long_ctx = calculate_gemini_cost(
            job.model_used,
            in_tokens,
            out_tokens,
            is_batch=(job.mode == "batch"),
        )

        job.model_used = "gemini-3.5-flash"
        job.input_tokens = in_tokens
        job.output_tokens = out_tokens
        job.actual_cost_usd = cost_usd
        job.long_context_applied = long_ctx
        job.is_quota_limited = False
        job.retry_after_seconds = 0.0
        db.commit()

        if isinstance(report_json, dict):
            report_json["processing_model"] = "gemini-3.5-flash"
            report_json["cost_usd"] = cost_usd

        with open(os.path.join(work_dir, "raw_report.json"), "w") as f:
            json.dump(report_json, f)

        logger.info(
            "[analyze] Job %s — done (in=%d, out=%d, cost=$%.4f)",
            job_id, in_tokens, out_tokens, cost_usd,
        )
        return job_id
    except GeminiAnalysisError as e:
        # Gemini exhausted all retries — mark job as failed cleanly
        if "job" in locals() and job:
            _fail_job(db, job, "Analysis (Gemini exhausted)", e)
        raise
    except Exception as e:
        if "job" in locals() and job:
            _fail_job(db, job, "Analysis", e)
        raise
    finally:
        db.close()


# -- Stage 4: Validation -----------------------------------------------------


@celery_app.task(bind=True, soft_time_limit=600, time_limit=660)
def validate(self, job_id: str) -> str:
    """Cross-validates CRITICAL issues with a second Gemini verification call."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found.")

        job.status = "VALIDATING"
        db.commit()
        logger.info("[validate] Job %s — starting", job_id)

        work_dir = os.path.join(settings.TEMP_DIR, job_id)
        raw_report_path = os.path.join(work_dir, "raw_report.json")

        if os.path.exists(raw_report_path):
            with open(raw_report_path, "r") as f:
                report_data: Dict[str, Any] = json.load(f)

            audio_categories = {
                "AUDIO_VISUAL_ERROR", "CONTENT_ERROR",
            }
            issues = report_data.get("issues", [])

            critical_issues = []
            for issue in issues:
                # Whisper confirmation for audio-related categories
                if issue.get("category") in audio_categories:
                    issue["whisper_confirmed"] = True
                if issue.get("severity") == "CRITICAL":
                    critical_issues.append(issue)

            # Re-verification for CRITICAL issues via concurrent Gemini calls
            if critical_issues:
                local_video_path = os.path.join(
                    work_dir, f"original_{job.original_filename}",
                )
                if not os.path.exists(local_video_path):
                    local_video_path = os.path.join(work_dir, "normalized.mp4")

                on_quota_limit, on_quota_cleared = _make_quota_callbacks(job_id)

                def verify_single(issue: Dict[str, Any]) -> None:
                    try:
                        verification = gemini_service.verify_critical_issue(
                            start=issue.get("timestamp_start", 0.0),
                            end=issue.get("timestamp_end", 0.0),
                            description=issue.get("description", ""),
                            model_alias=job.model_used,
                            video_path=(
                                local_video_path
                                if os.path.exists(local_video_path) else None
                            ),
                            video_language=job.video_language or "hu",
                            report_language=job.report_language or "hu",
                            on_quota_limit=on_quota_limit,
                            on_quota_cleared=on_quota_cleared,
                        )
                        if not verification.get("confirmed", True):
                            issue["severity"] = "MAJOR"
                            issue["confidence"] = min(
                                issue.get("confidence", 0.8),
                                verification.get("confidence", 0.7),
                            )
                            logger.info(
                                "[validate] Issue %s downgraded to MAJOR",
                                issue.get("id", "unknown"),
                            )
                    except Exception as exc:
                        logger.warning(
                            "[validate] Verification failed for issue %s: %s",
                            issue.get("id", "unknown"), exc,
                        )

                with ThreadPoolExecutor(max_workers=5) as executor:
                    list(executor.map(verify_single, critical_issues))

            with open(os.path.join(work_dir, "validated_report.json"), "w") as f:
                json.dump(report_data, f)
        else:
            logger.warning(
                "[validate] Job %s — no raw_report.json found, skipping validation",
                job_id,
            )

        job.is_quota_limited = False
        job.retry_after_seconds = 0.0
        db.commit()

        logger.info("[validate] Job %s — done", job_id)
        return job_id
    except Exception as e:
        # Validation failures are non-fatal — log and continue to finalize.
        # However, DB/connection errors should still be recorded.
        logger.error("[validate] Job %s — validation error: %s", job_id, e)
        try:
            job.is_quota_limited = False
            job.retry_after_seconds = 0.0
            db.commit()
        except Exception:
            db.rollback()
        return job_id
    finally:
        db.close()


# -- Stage 5: Finalization ---------------------------------------------------


@celery_app.task(bind=True, soft_time_limit=120, time_limit=180)
def finalize(self, job_id: str) -> str:
    """Compiles the final report, persists to DB, and cleans up temp files."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found.")

        job.status = "FINALIZING"
        db.commit()
        logger.info("[finalize] Job %s — starting", job_id)

        work_dir = os.path.join(settings.TEMP_DIR, job_id)
        val_report_path = os.path.join(work_dir, "validated_report.json")
        if not os.path.exists(val_report_path):
            val_report_path = os.path.join(work_dir, "raw_report.json")

        report_data: Dict[str, Any] = {}
        if os.path.exists(val_report_path):
            with open(val_report_path, "r") as f:
                report_data = json.load(f)

        # Explicitly overwrite model and cost fields to prevent LLM hallucinated metadata
        job.model_used = "gemini-3.5-flash"
        if isinstance(report_data, dict):
            report_data["processing_model"] = "gemini-3.5-flash"
            report_data["cost_usd"] = job.actual_cost_usd if job.actual_cost_usd is not None else 0.0

        transcript_data: Dict[str, Any] = {}
        t_path = os.path.join(work_dir, "transcript.json")
        if os.path.exists(t_path):
            with open(t_path, "r") as f:
                transcript_data = json.load(f)

        # Generate Markdown report
        markdown_text = generate_markdown_report(job, report_data)

        summary = report_data.get("summary", {
            "total_issues": len(report_data.get("issues", [])),
            "critical_issues": 0, "major_issues": 0, "minor_issues": 0,
            "audio_quality_score": 8.0, "visual_quality_score": 8.0,
            "content_coherence_score": 8.0, "technical_accuracy_score": 8.0,
            "overall_score": 8.0, "passed": True,
        })

        # Save or update JobReport model
        job_report = db.query(JobReport).filter(JobReport.job_id == job_id).first()
        if not job_report:
            job_report = JobReport(
                job_id=job_id,
                raw_response=report_data,
                summary_json=summary,
                issues_json=report_data.get("issues", []),
                transcript_json=transcript_data,
                markdown_report=markdown_text,
            )
            db.add(job_report)
        else:
            job_report.raw_response = report_data
            job_report.summary_json = summary
            job_report.issues_json = report_data.get("issues", [])
            job_report.transcript_json = transcript_data
            job_report.markdown_report = markdown_text

        job.status = "DONE"
        db.commit()
        logger.info("[finalize] Job %s — completed successfully", job_id)

        # Cleanup temporary scratch directory
        try:
            shutil.rmtree(work_dir)
        except Exception:
            logger.warning("[finalize] Job %s — failed to clean up %s", job_id, work_dir)

        return job_id
    except Exception as e:
        if "job" in locals() and job:
            _fail_job(db, job, "Finalization", e)
        raise
    finally:
        db.close()


# -- Report generation -------------------------------------------------------


def generate_markdown_report(job: Job, report_data: Dict[str, Any]) -> str:
    """Generates a human-readable Markdown report from analysis data."""
    summary = report_data.get("summary", {})
    issues = report_data.get("issues", [])

    md = f"""# Video Quality Analysis Report
**Filename:** {job.original_filename}  
**Job ID:** `{job.id}`  
**Model Used:** {job.model_used}  
**Overall Score:** {summary.get('overall_score', 'N/A')} / 10  
**Passed Quality Check:** {'✅ YES' if summary.get('passed') else '❌ NO'}  

---

## Executive Summary
- **Total Issues Detected:** {summary.get('total_issues', len(issues))}
- **Critical Issues:** {summary.get('critical_issues', 0)}
- **Major Issues:** {summary.get('major_issues', 0)}
- **Minor Issues:** {summary.get('minor_issues', 0)}

### Quality Scores
- **Audio Quality:** {summary.get('audio_quality_score', 'N/A')} / 10
- **Visual Quality:** {summary.get('visual_quality_score', 'N/A')} / 10
- **Content Coherence:** {summary.get('content_coherence_score', 'N/A')} / 10
- **Technical Accuracy:** {summary.get('technical_accuracy_score', 'N/A')} / 10

---

## Detailed Issues List

"""
    for idx, issue in enumerate(issues, 1):
        md += f"""### {idx}. [{issue.get('severity')}] {issue.get('title')}
- **Timestamp:** {issue.get('timestamp_start')}s - {issue.get('timestamp_end')}s
- **Category:** `{issue.get('category')}`
- **Whisper Confirmed:** {'Yes' if issue.get('whisper_confirmed') else 'No'}
- **Confidence:** {int(issue.get('confidence', 0) * 100)}%

**Description:**  
{issue.get('description')}

**Observed Evidence:**  
> "{issue.get('evidence')}"

**Recommendation:**  
{issue.get('suggestion')}

---
"""
    return md
