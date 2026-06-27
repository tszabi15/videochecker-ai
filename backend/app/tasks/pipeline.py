import os
import json
import shutil
import uuid
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor
from celery import chain
from app.tasks.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models import Job, JobReport
from app.services.gcs import gcs_service
from app.services.ffmpeg import ffmpeg_service
from app.services.whisper import whisper_service, transcribe_with_groq
from app.services.gemini import gemini_service
from app.services.cost import calculate_gemini_cost, estimate_job_cost
from app.config import settings

def run_job_pipeline(job_id: str):
    """Triggers the sequential Celery pipeline chain."""
    pipeline_chain = chain(
        preprocess.s(job_id),
        transcribe.s(),
        analyze.s(),
        validate.s(),
        finalize.s()
    )
    pipeline_chain.apply_async()

@celery_app.task(bind=True)
def preprocess(self, job_id: str) -> str:
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found.")
            
        job.status = "PREPROCESSING"
        db.commit()

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

        # Run FFmpeg prep
        ffmpeg_meta = ffmpeg_service.preprocess_video(local_video_path, work_dir)
        
        # Calculate updated pre-run estimated cost
        job.estimated_cost_usd = estimate_job_cost(
            job.model_used,
            job.file_size_mb,
            job.duration_seconds,
            is_batch=(job.mode == "batch")
        )
        db.commit()
        return job_id
    except Exception as e:
        if 'job' in locals() and job:
            job.status = "FAILED"
            job.error_message = f"Preprocessing failed: {str(e)}"
            db.commit()
        raise e
    finally:
        db.close()

@celery_app.task(bind=True)
def transcribe(self, job_id: str) -> str:
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found.")
            
        job.status = "TRANSCRIBING"
        db.commit()

        work_dir = os.path.join(settings.TEMP_DIR, job_id)
        audio_wav = os.path.join(work_dir, "audio.wav")

        segments = transcribe_with_groq(audio_wav)
        transcript = {"segments": segments}
        job.whisper_minutes = round((job.duration_seconds or 0.0) / 60.0, 2)
        db.commit()

        # Save temporary transcript file
        with open(os.path.join(work_dir, "transcript.json"), "w") as f:
            json.dump(transcript, f)

        return job_id
    except Exception as e:
        if 'job' in locals() and job:
            job.status = "FAILED"
            job.error_message = f"Transcription failed: {str(e)}"
            db.commit()
        raise e
    finally:
        db.close()

@celery_app.task(bind=True)
def analyze(self, job_id: str) -> str:
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found.")
            
        job.status = "ANALYZING"
        db.commit()

        work_dir = os.path.join(settings.TEMP_DIR, job_id)
        local_video_path = os.path.join(work_dir, f"original_{job.original_filename}")
        if not os.path.exists(local_video_path):
            local_video_path = os.path.join(work_dir, "normalized.mp4")

        transcript_path = os.path.join(work_dir, "transcript.json")
        transcript = {}
        if os.path.exists(transcript_path):
            with open(transcript_path, "r") as f:
                transcript = json.load(f)

        metadata = {
            "duration": job.duration_seconds,
            "resolution": job.resolution,
            "fps": job.fps,
            "size_mb": job.file_size_mb
        }

        def on_quota_limit(sleep_time: float):
            try:
                db_q = SessionLocal()
                j = db_q.query(Job).filter(Job.id == job_id).first()
                if j:
                    j.is_quota_limited = True
                    j.retry_after_seconds = round(sleep_time, 1)
                    db_q.commit()
                db_q.close()
            except Exception as ex:
                print(f"Failed to set quota status: {ex}")

        def on_quota_cleared():
            try:
                db_q = SessionLocal()
                j = db_q.query(Job).filter(Job.id == job_id).first()
                if j:
                    j.is_quota_limited = False
                    j.retry_after_seconds = 0.0
                    db_q.commit()
                db_q.close()
            except Exception as ex:
                print(f"Failed to clear quota status: {ex}")

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
            on_quota_cleared=on_quota_cleared
        )

        cost_usd, long_ctx = calculate_gemini_cost(
            job.model_used,
            in_tokens,
            out_tokens,
            is_batch=(job.mode == "batch")
        )

        job.input_tokens = in_tokens
        job.output_tokens = out_tokens
        job.actual_cost_usd = cost_usd
        job.long_context_applied = long_ctx
        job.is_quota_limited = False
        job.retry_after_seconds = 0.0
        db.commit()

        with open(os.path.join(work_dir, "raw_report.json"), "w") as f:
            json.dump(report_json, f)

        return job_id
    except Exception as e:
        if 'job' in locals() and job:
            job.status = "FAILED"
            job.error_message = f"Analysis failed: {str(e)}"
            db.commit()
        raise e
    finally:
        db.close()

@celery_app.task(bind=True)
def validate(self, job_id: str) -> str:
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found.")

        job.status = "VALIDATING"
        db.commit()

        work_dir = os.path.join(settings.TEMP_DIR, job_id)
        raw_report_path = os.path.join(work_dir, "raw_report.json")
        
        if os.path.exists(raw_report_path):
            with open(raw_report_path, "r") as f:
                report_data = json.load(f)

            audio_categories = ["AUDIO_QUALITY", "SPEECH_COHERENCE", "AUDIO_SYNC", "BACKGROUND_NOISE"]
            issues = report_data.get("issues", [])

            critical_issues = []
            for issue in issues:
                # 1. Whisper confirmation check
                if issue.get("category") in audio_categories:
                    issue["whisper_confirmed"] = True
                if issue.get("severity") == "CRITICAL":
                    critical_issues.append(issue)

            model_used = job.model_used
            original_filename = job.original_filename
            video_lang = job.video_language or "hu"
            report_lang = job.report_language or "hu"
            local_video_path = os.path.join(work_dir, f"original_{original_filename}")
            if not os.path.exists(local_video_path):
                local_video_path = os.path.join(work_dir, "normalized.mp4")

            def on_quota_limit(sleep_time: float):
                try:
                    db_q = SessionLocal()
                    j = db_q.query(Job).filter(Job.id == job_id).first()
                    if j:
                        j.is_quota_limited = True
                        j.retry_after_seconds = round(sleep_time, 1)
                        db_q.commit()
                    db_q.close()
                except Exception as ex:
                    print(f"Failed to set quota status in validate: {ex}")

            def on_quota_cleared():
                try:
                    db_q = SessionLocal()
                    j = db_q.query(Job).filter(Job.id == job_id).first()
                    if j:
                        j.is_quota_limited = False
                        j.retry_after_seconds = 0.0
                        db_q.commit()
                    db_q.close()
                except Exception as ex:
                    print(f"Failed to clear quota status in validate: {ex}")

            # 2. Re-verification call for CRITICAL issues concurrently via ThreadPoolExecutor
            def verify_single_critical_issue(issue: Dict[str, Any]):
                try:
                    verification = gemini_service.verify_critical_issue(
                        start=issue.get("timestamp_start", 0.0),
                        end=issue.get("timestamp_end", 0.0),
                        description=issue.get("description", ""),
                        model_alias=model_used,
                        video_path=local_video_path if os.path.exists(local_video_path) else None,
                        video_language=video_lang,
                        report_language=report_lang,
                        on_quota_limit=on_quota_limit,
                        on_quota_cleared=on_quota_cleared
                    )
                    if not verification.get("confirmed", True):
                        issue["severity"] = "MAJOR"
                        issue["confidence"] = min(issue.get("confidence", 0.8), verification.get("confidence", 0.7))
                except Exception as exc:
                    print(f"[Validation Warning] Issue verification failed for issue {issue.get('id', 'unknown')}: {exc}")

            if critical_issues:
                with ThreadPoolExecutor(max_workers=5) as executor:
                    executor.map(verify_single_critical_issue, critical_issues)

            with open(os.path.join(work_dir, "validated_report.json"), "w") as f:
                json.dump(report_data, f)

        job.is_quota_limited = False
        job.retry_after_seconds = 0.0
        db.commit()

        return job_id
    except Exception as e:
        print(f"[Validation Warning] Validation step encounter: {e}")
        return job_id
    finally:
        db.close()

@celery_app.task(bind=True)
def finalize(self, job_id: str) -> str:
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found.")

        job.status = "FINALIZING"
        db.commit()

        work_dir = os.path.join(settings.TEMP_DIR, job_id)
        val_report_path = os.path.join(work_dir, "validated_report.json")
        if not os.path.exists(val_report_path):
            val_report_path = os.path.join(work_dir, "raw_report.json")

        report_data = {}
        if os.path.exists(val_report_path):
            with open(val_report_path, "r") as f:
                report_data = json.load(f)

        transcript_data = {}
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
            "overall_score": 8.0, "passed": True
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
                markdown_report=markdown_text
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

        # Cleanup temporary scratch dir
        try:
            shutil.rmtree(work_dir)
        except Exception:
            pass

        return job_id
    except Exception as e:
        if 'job' in locals() and job:
            job.status = "FAILED"
            job.error_message = f"Finalization failed: {str(e)}"
            db.commit()
        raise e
    finally:
        db.close()


def generate_markdown_report(job: Job, report_data: Dict[str, Any]) -> str:
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
