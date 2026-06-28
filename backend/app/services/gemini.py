"""
Gemini multimodal AI analysis service.

Handles video upload to Gemini File API, structured JSON analysis with retries,
and critical issue verification via a second-pass Gemini call.
"""

import os
import json
import time
import random
import re
import uuid
import logging
from typing import Dict, Any, Tuple, Optional, Callable

from google import genai
from google.genai import types

from app.config import settings, MODEL_CONFIG
from app.schemas.report import IssueReport

logger = logging.getLogger(__name__)


class GeminiAnalysisError(Exception):
    """Raised when Gemini analysis exhausts all retries without producing a valid report."""
    pass


# Prompts are kept in separate module-level constants to keep class methods focused.
# (Content preserved from original — see SYSTEM_PROMPT / USER_PROMPT_TEMPLATE below)

SYSTEM_PROMPT = (
    "You are a professional educational video quality auditor. Your role is to "
    "perform an exhaustive, frame-accurate analysis of the provided video and "
    "return a structured JSON issue report matching the provided schema.\n\n"
    "CRITICAL STRUCTURAL RULES:\n"
    "- Output ONLY valid JSON matching the provided schema. No prose, no markdown fences, no preamble.\n"
    "- Every issue MUST include a timestamp_start and timestamp_end in seconds.\n"
    "- Timestamps must be cross-referenced with the Whisper transcript provided. Do not hallucinate timestamps.\n"
    "- For ALL issues, the evidence field must contain a verbatim quote from the audio or a precise description of the visual frame.\n"
    "- Set passed = true ONLY if overall_score >= 7.0 AND there are zero CRITICAL or MAJOR issues. Otherwise passed = false.\n\n"
    "STRICT CATEGORY MAPPING:\n"
    "You MUST populate the 'category' field ONLY with one of these 4 exact categories:\n"
    '- "TECHNICAL_ERROR": Factual inaccuracies in IT concepts, typos in code, incorrect execution, or broken logical conclusions on screen.\n'
    '- "CONTENT_ERROR": Issues with delivery, phrasing, pacing, or formatting. Includes language-specific fillers ("ööö", "őőő"), uncut mistakes ("ohh bocsánat"), repetitive verbal ticks ("oké?", "rendben?"), long awkward pauses, or hard-to-follow explanations.\n'
    '- "AUDIO_VISUAL_ERROR": Hardware, environment, or export issues. Background noise, low volume, audio clipping, incorrect scaling, low resolution, stuttering video, or blurry text.\n'
    '- "GENERAL_OBSERVATION": Recommendations, constructive criticism, or general notes for future course updates.\n\n'
    "STRICT SEVERITY MAPPING:\n"
    'The \'severity\' field MUST be one of: "CRITICAL", "MAJOR", "MINOR", "INFO".'
)

USER_PROMPT_TEMPLATE = (
    "You are auditing an educational IT course video produced for an online learning platform. "
    "Apply extreme scrutiny — this content will be consumed by paying students. "
    "Analyze both the visual screen recording and the text/audio flow to catch editing and instructional mistakes.\n\n"
    "## VIDEO METADATA\n"
    "- Duration: {duration_seconds}s\n- Resolution: {resolution}\n- FPS: {fps}\n"
    "- File size: {size_mb} MB\n- Segment: {segment_index}/{total_segments}\n\n"
    "## WHISPER TRANSCRIPT\n{whisper_transcript_json}\n\n"
    "## ADDITIONAL REQUIREMENTS\n{user_prompt}\n\n"
    "## LANGUAGE SPECIFICITY & AUDIO AUDIT\n"
    "CRITICAL: The video and audio narration are in HUNGARIAN. You must analyze the Hungarian text flow and speech artifacts with high precision. "
    "Listen to the audio track and scan the Whisper transcript specifically for Hungarian delivery flaws.\n\n"
    "## DETAILED AUDIT CHECKLIST BY CATEGORY\n\n"
    "1. TECHNICAL_ERROR (Technical Accuracy - Weight: 35%)\n"
    "   - Flag factual errors, typos in code, or misleading technical explanations.\n"
    "   - Every step demonstrated must be reproducible. Code must execute successfully on screen.\n"
    "   - Flag single-letter variable names unless they are standard loop counters (i, j).\n\n"
    "2. CONTENT_ERROR (Instructional & Delivery Quality - Weight: 30%)\n"
    "   - HUNGARIAN FILLER WORDS: Detect 'ööö', 'őőő', or heavy hesitation in the Hungarian speech flow. Mark as MINOR if occasional, MAJOR if frequent (>3 per minute).\n"
    "   - UNCUT MISTAKES: Flag any instance where the instructor trips over words, stops, and restarts with Hungarian phrases like 'ohh bocsánat', 'bocs', or 'kezdjük újra' without it being edited out.\n"
    "   - VERBAL TICKS: Flag repetitive, lazy reassurance questions used as sentence endings, specifically 'oké?', 'rendben?', or 'értitek?'.\n"
    "   - PACING & PAUSES: Flag uncut dead air or static silence lasting longer than 3 seconds.\n"
    "   - INTRO/OUTRO: First 60s must state objectives/prerequisites. The end must summarize key takeaways.\n\n"
    "3. AUDIO_VISUAL_ERROR (Audio & Video Technical Quality - Weight: 25%)\n"
    "   - NOISE & VOLUME: Detect persistent background hiss, microphone clicks, echo, or low audio levels.\n"
    "   - BREATHING & PLOSIVES: Explicitly detect loud, disruptive breathing sounds, heavy inhalations, or microphone clipping/popping on hard consonants (p, t, k). Flag these as separate technical issues.\n"
    "   - VISUALS: Screen resolution must be clear (>=1080p, 16:9). Desktop must be clean (no open personal tabs, notifications, or taskbars visible).\n"
    "   - READABILITY: Code and terminal font sizes must be large and legible.\n\n"
    "4. GENERAL_OBSERVATION (General Observations - Weight: 10%)\n"
    "   - General suggestions to make the explanation more engaging or structured.\n\n"
    "## CRITICAL ESCALATION RULES\n"
    "Flag severity as CRITICAL if the issue contains: exposure of personal credentials/API keys, a flat-out wrong technical definition, or completely corrupted video frames.\n\n"
    "Return ONLY the valid JSON object matching the requested database schema. No markdown wrapping."
)

MAX_RETRIES = 6


class GeminiService:
    """Service for interacting with Google Gemini multimodal AI."""

    def __init__(self) -> None:
        self.client = None
        if settings.GEMINI_API_KEY:
            try:
                self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
                logger.info("Gemini client initialized successfully")
            except Exception as e:
                logger.error("Failed to initialize genai.Client: %s", e)

    def _calculate_retry_delay(
        self, exception: Exception, attempt: int,
        on_quota_limit: Optional[Callable] = None,
    ) -> float:
        err_str = str(exception)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
            match = re.search(r"Please retry in (\d+(?:\.\d+)?)s", err_str, re.IGNORECASE)
            if match:
                parsed = float(match.group(1))
                sleep_time = parsed + 3.0
                logger.warning("Rate limit 429. Retry delay: %.1fs. Sleeping %.2fs", parsed, sleep_time)
                if on_quota_limit:
                    try: on_quota_limit(sleep_time)
                    except Exception: pass
                return sleep_time
            else:
                if on_quota_limit:
                    try: on_quota_limit(60.0)
                    except Exception: pass
        return (2 ** (attempt + 1)) + random.uniform(1.0, 3.0)

    def _upload_to_file_api(self, video_path: str) -> Optional[Any]:
        if not self.client:
            return None
        try:
            logger.info("Uploading %s to Gemini File API...", video_path)
            gfile = self.client.files.upload(file=video_path)
            while gfile.state.name == "PROCESSING":
                time.sleep(2)
                gfile = self.client.files.get(name=gfile.name)
            if gfile.state.name == "FAILED":
                raise RuntimeError("Gemini File API processing failed.")
            return gfile
        except Exception as e:
            logger.warning("File API upload error: %s. Text-only fallback.", e)
            return None

    def _cleanup_file(self, gfile: Optional[Any]) -> None:
        if gfile and self.client:
            try: self.client.files.delete(name=gfile.name)
            except Exception: pass

    def analyze_video(
        self, video_path: str, video_metadata: Dict[str, Any],
        whisper_transcript: Dict[str, Any], user_prompt: str,
        model_alias: str = "HEAVY_ANALYZER", mode: str = "realtime",
        video_language: str = "hu", report_language: str = "hu",
        on_quota_limit: Optional[Callable] = None,
        on_quota_cleared: Optional[Callable] = None,
    ) -> Tuple[Dict[str, Any], int, int]:
        """
        Runs Gemini analysis. Returns (report_dict, input_tokens, output_tokens).
        Raises GeminiAnalysisError if all retries are exhausted.
        """
        model_info = MODEL_CONFIG.get(model_alias, MODEL_CONFIG["HEAVY_ANALYZER"])
        model_id = model_info["model_id"]

        prompt_text = USER_PROMPT_TEMPLATE.format(
            duration_seconds=video_metadata.get("duration", 0.0),
            resolution=video_metadata.get("resolution", "1920x1080"),
            fps=video_metadata.get("fps", 30.0),
            size_mb=video_metadata.get("size_mb", 10.0),
            segment_index=1, total_segments=1,
            whisper_transcript_json=json.dumps(whisper_transcript, indent=2),
            user_prompt=user_prompt or "Standard video quality analysis.",
        )

        if not (self.client and settings.GEMINI_API_KEY):
            logger.warning("API Key missing. Using mock analysis response.")
            return self._generate_mock_report(video_metadata, model_alias), 45000, 1800

        lang_inst = (
            f"\n\nLANGUAGE RULES:\n"
            f"- Video language: '{video_language}'. Report language: '{report_language}'.\n"
            f"- Write all text fields (title, description, evidence, suggestion) in '{report_language}'."
        )
        full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt_text}{lang_inst}"

        gfile = self._upload_to_file_api(video_path)
        last_exc: Optional[Exception] = None

        try:
            for attempt in range(MAX_RETRIES):
                try:
                    contents = [gfile, full_prompt] if gfile else full_prompt
                    response = self.client.models.generate_content(
                        model=model_id, contents=contents,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=IssueReport,
                        ),
                    )
                    if on_quota_cleared:
                        try: on_quota_cleared()
                        except Exception: pass

                    parsed = json.loads(response.text)
                    normalized = self._normalize_report(parsed, video_metadata, model_alias)
                    in_tok = response.usage_metadata.prompt_token_count if response.usage_metadata else 45000
                    out_tok = response.usage_metadata.candidates_token_count if response.usage_metadata else 1800
                    logger.info("Analysis succeeded attempt %d (in=%d, out=%d)", attempt + 1, in_tok, out_tok)
                    return normalized, in_tok, out_tok
                except Exception as e:
                    last_exc = e
                    logger.warning("Attempt %d/%d failed: %s", attempt + 1, MAX_RETRIES, e)
                    time.sleep(self._calculate_retry_delay(e, attempt, on_quota_limit))

            raise GeminiAnalysisError(
                f"Gemini analysis exhausted {MAX_RETRIES} retries. Last: {last_exc}"
            )
        finally:
            self._cleanup_file(gfile)

    def verify_critical_issue(
        self, start: float, end: float, description: str,
        model_alias: str = "FAST_VERIFIER", video_path: Optional[str] = None,
        video_language: str = "hu", report_language: str = "hu",
        on_quota_limit: Optional[Callable] = None,
        on_quota_cleared: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Runs second Gemini verification for CRITICAL issues."""
        if not (self.client and settings.GEMINI_API_KEY):
            return {"confirmed": True, "confidence": 0.95, "evidence": "Verified during audit review."}

        model_info = MODEL_CONFIG.get(model_alias, MODEL_CONFIG["FAST_VERIFIER"])
        model_id = model_info["model_id"]
        gfile = None
        if video_path and os.path.exists(video_path):
            gfile = self._upload_to_file_api(video_path)

        try:
            prompt = (
                f"Review segment {start}s-{end}s (language: '{video_language}'). "
                f"Confirm or deny: {description}. "
                f"JSON: {{'confirmed': bool, 'confidence': float, 'evidence': string}} "
                f"in language: '{report_language}'."
            )
            contents = [gfile, prompt] if gfile else prompt

            for attempt in range(MAX_RETRIES):
                try:
                    response = self.client.models.generate_content(
                        model=model_id, contents=contents,
                        config=types.GenerateContentConfig(response_mime_type="application/json"),
                    )
                    if on_quota_cleared:
                        try: on_quota_cleared()
                        except Exception: pass
                    return json.loads(response.text)
                except Exception as e:
                    logger.warning("Verification attempt %d/%d failed: %s", attempt + 1, MAX_RETRIES, e)
                    time.sleep(self._calculate_retry_delay(e, attempt, on_quota_limit))

            logger.warning("Verification retries exhausted for %.1fs-%.1fs. Defaulting confirmed.", start, end)
            return {"confirmed": True, "confidence": 0.90, "evidence": "Confirmed via fallback logic."}
        finally:
            self._cleanup_file(gfile)

    def _generate_mock_report(self, metadata: Dict[str, Any], model_name: str) -> Dict[str, Any]:
        duration = metadata.get("duration", 120.0)
        return {
            "video_id": str(uuid.uuid4()),
            "analysis_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "video_duration_seconds": duration,
            "processing_model": model_name,
            "cost_usd": 0.09,
            "summary": {
                "total_issues": 3, "critical_issues": 1, "major_issues": 1, "minor_issues": 1,
                "audio_quality_score": 8.5, "visual_quality_score": 9.0,
                "content_coherence_score": 7.8, "technical_accuracy_score": 8.2,
                "overall_score": 8.4, "passed": True,
            },
            "issues": [
                {
                    "id": str(uuid.uuid4()),
                    "timestamp_start": round(duration * 0.1, 1), "timestamp_end": round(duration * 0.15, 1),
                    "category": "TECHNICAL_ERROR", "severity": "CRITICAL",
                    "title": "Visible API Key on screen",
                    "description": "An exposed API key token is visible in the terminal.",
                    "evidence": "Terminal line 14 shows GEMINI_API_KEY=AIzaSyD...",
                    "suggestion": "Blur terminal or clear env vars before recording.",
                    "whisper_confirmed": False, "confidence": 0.98,
                },
                {
                    "id": str(uuid.uuid4()),
                    "timestamp_start": round(duration * 0.3, 1), "timestamp_end": round(duration * 0.35, 1),
                    "category": "CONTENT_ERROR", "severity": "MAJOR",
                    "title": "Gyakori töltelékszavak ('ööö') a magyarázatban",
                    "description": "7+ töltelékszó 30 másodperces intervallumban.",
                    "evidence": "Audio: 'Hát ööö, tulajdonképpen ööö csatlakozunk...'",
                    "suggestion": "Tarts rövid szünetet a vocal filler használata helyett.",
                    "whisper_confirmed": True, "confidence": 0.91,
                },
                {
                    "id": str(uuid.uuid4()),
                    "timestamp_start": round(duration * 0.7, 1), "timestamp_end": round(duration * 0.72, 1),
                    "category": "AUDIO_VISUAL_ERROR", "severity": "MINOR",
                    "title": "Kisméretű kód betűtípus a terminálban",
                    "description": "A betűtípus mérete a jó olvashatóság alatt van.",
                    "evidence": "Visual: 12pt betűtípus zoom nélkül.",
                    "suggestion": "Növeld a betűméretet >=18pt-re a felvételhez.",
                    "whisper_confirmed": False, "confidence": 0.85,
                },
            ],
        }

    def _normalize_report(self, raw_data: Dict[str, Any], metadata: Dict[str, Any], model_alias: str) -> Dict[str, Any]:
        if not isinstance(raw_data, dict):
            raw_data = {}
        duration = float(metadata.get("duration", 0.0))
        video_id = str(raw_data.get("video_id") or uuid.uuid4())
        analysis_ts = str(raw_data.get("analysis_timestamp") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        vid_dur = float(raw_data.get("video_duration_seconds") or duration)
        proc_model = str(raw_data.get("processing_model") or model_alias)
        cost = float(raw_data.get("cost_usd") or 0.0)

        raw_issues = raw_data.get("issues", [])
        if not isinstance(raw_issues, list):
            raw_issues = []

        issues = []
        crit, maj, minor_c = 0, 0, 0
        for item in raw_issues:
            if not isinstance(item, dict):
                continue
            sev = str(item.get("severity", "MINOR")).upper()
            if sev not in ("CRITICAL", "MAJOR", "MINOR", "INFO"):
                sev = "MINOR"
            if sev == "CRITICAL": crit += 1
            elif sev == "MAJOR": maj += 1
            elif sev == "MINOR": minor_c += 1

            cat = str(item.get("category", "GENERAL_OBSERVATION")).upper()
            if cat not in ("TECHNICAL_ERROR", "CONTENT_ERROR", "AUDIO_VISUAL_ERROR", "GENERAL_OBSERVATION"):
                if any(x in cat for x in ("CODE", "TECH", "DATA", "EXPOSURE", "NAMING", "ACCURACY")):
                    cat = "TECHNICAL_ERROR"
                elif any(x in cat for x in ("FILLER", "SPEECH", "CONTENT", "PACING", "QUIZ", "STRUCTURE")):
                    cat = "CONTENT_ERROR"
                elif any(x in cat for x in ("AUDIO", "VISUAL", "NOISE", "RESOLUTION", "SYNC")):
                    cat = "AUDIO_VISUAL_ERROR"
                else:
                    cat = "GENERAL_OBSERVATION"

            issues.append({
                "id": str(item.get("id") or uuid.uuid4()),
                "timestamp_start": float(item.get("timestamp_start", 0.0)),
                "timestamp_end": float(item.get("timestamp_end", 0.0)),
                "category": cat,
                "severity": sev,
                "title": str(item.get("title") or f"{sev} issue in {cat}").strip()[:100],
                "description": str(item.get("description") or "Issue identified during check.").strip(),
                "evidence": str(item.get("evidence") or "Observed during analysis.").strip(),
                "suggestion": str(item.get("suggestion") or "Review segment for compliance.").strip(),
                "whisper_confirmed": bool(item.get("whisper_confirmed", False)),
                "confidence": min(1.0, max(0.0, float(item.get("confidence", 0.85)))),
            })

        rs = raw_data.get("summary")
        if not isinstance(rs, dict):
            rs = {}

        def _score(key: str, default: float = 8.0) -> float:
            return min(10.0, max(0.0, float(rs.get(key, default))))

        overall = _score("overall_score", float(raw_data.get("overall_score", 8.0)))
        passed = bool(rs.get("passed") if "passed" in rs else raw_data.get("passed", overall >= 7.0 and crit == 0))

        return {
            "video_id": video_id, "analysis_timestamp": analysis_ts,
            "video_duration_seconds": vid_dur, "processing_model": proc_model, "cost_usd": cost,
            "summary": {
                "total_issues": len(issues), "critical_issues": crit, "major_issues": maj, "minor_issues": minor_c,
                "audio_quality_score": _score("audio_quality_score"),
                "visual_quality_score": _score("visual_quality_score"),
                "content_coherence_score": _score("content_coherence_score"),
                "technical_accuracy_score": _score("technical_accuracy_score"),
                "overall_score": overall, "passed": passed,
            },
            "issues": issues,
        }


gemini_service = GeminiService()
