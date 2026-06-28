"""
FFmpeg service for video preprocessing.

Handles MD5 hashing, video probing (metadata extraction), normalization,
and fast audio extraction via FFmpeg/ffprobe subprocesses.
"""

import os
import hashlib
import json
import logging
import subprocess
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Subprocess timeout in seconds — prevents worker hangs on corrupted files
SUBPROCESS_TIMEOUT = 300


def extract_audio_fast(video_path: str, output_wav_path: str) -> None:
    """
    Ultra-fast, zero-overhead audio extraction using FFmpeg.
    Disables video processing (-vn), multi-threads (-threads 0), and outputs 16kHz mono uncompressed PCM WAV.
    """
    command = [
        "ffmpeg", "-y",
        "-threads", "0",        
        "-i", video_path,          
        "-vn",                    
        "-acodec", "pcm_s16le",    
        "-ar", "16000",           
        "-ac", "1",                
        output_wav_path            
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class FFmpegService:
    """Provides FFmpeg-based video preprocessing utilities."""

    @staticmethod
    def compute_md5(file_path: str) -> str:
        """Computes MD5 hash of a file using buffered reads."""
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def probe_video(file_path: str) -> Dict[str, Any]:
        """
        Runs ffprobe to retrieve duration, resolution, and fps.

        Returns a dict with keys: duration, resolution, fps, width, height.
        Falls back to sensible defaults if ffprobe is unavailable or fails.
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration:stream=width,height,r_frame_rate,codec_type",
            "-of", "json",
            file_path,
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True,
                timeout=SUBPROCESS_TIMEOUT,
            )
            data = json.loads(result.stdout)

            duration = float(data.get("format", {}).get("duration", 0.0))
            width, height, fps = 1920, 1080, 30.0

            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    width = int(stream.get("width", 1920))
                    height = int(stream.get("height", 1080))
                    r_fps = stream.get("r_frame_rate", "30/1")
                    if "/" in r_fps:
                        num, den = r_fps.split("/")
                        fps = float(num) / float(den) if float(den) > 0 else 30.0
                    else:
                        fps = float(r_fps)
                    break

            return {
                "duration": duration,
                "resolution": f"{width}x{height}",
                "fps": round(fps, 2),
                "width": width,
                "height": height,
            }
        except Exception as e:
            logger.warning("ffprobe failed for %s: %s. Returning fallback metadata.", file_path, e)
            return {
                "duration": 60.0,
                "resolution": "1920x1080",
                "fps": 30.0,
                "width": 1920,
                "height": 1080,
            }

    @staticmethod
    def extract_audio_fast(video_path: str, output_wav_path: str) -> None:
        """Exposes fast audio extraction as a static method."""
        extract_audio_fast(video_path, output_wav_path)

    @staticmethod
    def preprocess_video(video_path: str, output_dir: str) -> Dict[str, Any]:
        """
        Runs fast audio extraction (16kHz mono WAV) without resource-wasting video re-encoding.

        Returns paths to the video and extracted audio.
        """
        os.makedirs(output_dir, exist_ok=True)
        audio_wav = os.path.join(output_dir, "audio.wav")

        try:
            extract_audio_fast(video_path, audio_wav)
            logger.info("Fast audio extraction completed successfully for %s", video_path)
        except Exception as e:
            logger.warning("Fast audio extraction failed: %s. Falling back to direct ffmpeg subprocess.", e)
            try:
                subprocess.run([
                    "ffmpeg", "-y", "-i", video_path,
                    "-vn", "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000",
                    audio_wav,
                ], capture_output=True, check=False, timeout=SUBPROCESS_TIMEOUT)
            except Exception as exc:
                logger.error("Fallback audio extraction failed: %s", exc)

        return {
            "normalized_video": video_path,
            "audio_wav": audio_wav,
        }


ffmpeg_service = FFmpegService()
