import os
import time
import re
import random
import logging
from typing import Dict, Any, List
from app.config import settings

logger = logging.getLogger(__name__)

def transcribe_with_groq(audio_path: str) -> List[Dict[str, Any]]:
    """
    Transcribes audio file using Groq Cloud API with whisper-large-v3-turbo.
    Returns standardized list of segments with start, end, and text.
    Implements retries with dynamic 429 backoff handling.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found at {audio_path}")

    api_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured in settings or environment.")

    try:
        from groq import Groq
    except ImportError:
        raise ImportError("The 'groq' package is required for Groq transcription. Please install it.")

    client = Groq(api_key=api_key)
    max_retries = 6

    for attempt in range(max_retries):
        try:
            with open(audio_path, "rb") as file_obj:
                response = client.audio.transcriptions.create(
                    file=(os.path.basename(audio_path), file_obj.read()),
                    model="whisper-large-v3-turbo",
                    response_format="verbose_json"
                )
            
            raw_segments = getattr(response, "segments", []) or []
            if not raw_segments and isinstance(response, dict):
                raw_segments = response.get("segments", [])

            segments = []
            for seg in raw_segments:
                if isinstance(seg, dict):
                    start_val = seg.get("start", 0.0)
                    end_val = seg.get("end", 0.0)
                    text_val = seg.get("text", "")
                else:
                    start_val = getattr(seg, "start", 0.0)
                    end_val = getattr(seg, "end", 0.0)
                    text_val = getattr(seg, "text", "")

                segments.append({
                    "start": float(start_val),
                    "end": float(end_val),
                    "text": str(text_val).strip()
                })

            if not segments and hasattr(response, "text"):
                segments.append({
                    "start": 0.0,
                    "end": 10.0,
                    "text": str(getattr(response, "text", "")).strip()
                })

            return segments

        except Exception as e:
            err_str = str(e)
            logger.warning(f"[Groq Transcription] Attempt {attempt + 1}/{max_retries} failed: {err_str}")
            if attempt == max_retries - 1:
                logger.error(f"[Groq Transcription CRITICAL] All retries exhausted for {audio_path}: {err_str}")
                raise RuntimeError(f"Groq transcription engine unavailable after {max_retries} retries: {err_str}") from e

            # Dynamic 429 handling or exponential backoff with jitter
            if "429" in err_str or "rate_limit" in err_str.lower() or "quota" in err_str.lower():
                match = re.search(r"Please retry in (\d+(?:\.\d+)?)s", err_str, re.IGNORECASE)
                if not match:
                    match = re.search(r"retry-after[:\s]+(\d+(?:\.\d+)?)", err_str, re.IGNORECASE)
                if match:
                    parsed_seconds = float(match.group(1))
                    sleep_time = parsed_seconds + 3.0
                    logger.info(f"[Groq] Rate limit hit (429). Sleeping {sleep_time:.2f}s...")
                else:
                    sleep_time = (2 ** (attempt + 1)) + random.uniform(1.0, 3.0)
            else:
                sleep_time = (2 ** (attempt + 1)) + random.uniform(1.0, 3.0)

            time.sleep(sleep_time)

    raise RuntimeError("Groq transcription failed unexpectedly.")

class WhisperService:
    def transcribe(self, audio_wav_path: str) -> Dict[str, Any]:
        """
        Wrapper method maintaining compatibility with service layer callers.
        """
        try:
            segments = transcribe_with_groq(audio_wav_path)
            return {"segments": segments}
        except Exception as e:
            logger.error(f"[WhisperService] Transcription error: {e}")
            raise e

whisper_service = WhisperService()
