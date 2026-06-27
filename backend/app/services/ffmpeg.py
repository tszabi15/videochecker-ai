import os
import hashlib
import json
import subprocess
from typing import Dict, Any, List

class FFmpegService:
    @staticmethod
    def compute_md5(file_path: str) -> str:
        """Computes MD5 hash of a file."""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def probe_video(file_path: str) -> Dict[str, Any]:
        """Runs ffprobe to retrieve duration, resolution, fps."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration:stream=width,height,r_frame_rate,codec_type",
            "-of", "json",
            file_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
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
                "height": height
            }
        except Exception as e:
            print(f"[FFmpeg] Probe failed or ffprobe missing: {e}. Returning fallback metadata.")
            return {
                "duration": 60.0,
                "resolution": "1920x1080",
                "fps": 30.0,
                "width": 1920,
                "height": 1080
            }

    @staticmethod
    def preprocess_video(video_path: str, output_dir: str) -> Dict[str, Any]:
        """
        Runs FFmpeg normalization, frame extraction, and audio extraction.
        """
        os.makedirs(output_dir, exist_ok=True)
        
        normalized_video = os.path.join(output_dir, "normalized.mp4")
        audio_wav = os.path.join(output_dir, "audio.wav")
        frames_dir = os.path.join(output_dir, "frames")
        os.makedirs(frames_dir, exist_ok=True)
        
        # 1. Normalize video to max 1080p
        norm_cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", "scale='min(1920\,iw)':-2",
            "-c:v", "libx264", "-crf", "23", "-preset", "fast",
            "-c:a", "aac",
            normalized_video
        ]
        
        # 2. Extract audio to WAV 16kHz mono
        audio_cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000",
            audio_wav
        ]
        
        # 3. Extract frames at 1fps
        frame_cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", "fps=1",
            "-q:v", "2",
            os.path.join(frames_dir, "frame_%04d.jpg")
        ]
        
        try:
            subprocess.run(norm_cmd, capture_output=True, check=False)
        except Exception as e:
            print(f"[FFmpeg] Normalization skipped: {e}")
            normalized_video = video_path

        try:
            subprocess.run(audio_cmd, capture_output=True, check=False)
        except Exception as e:
            print(f"[FFmpeg] Audio extraction warning: {e}")

        try:
            subprocess.run(frame_cmd, capture_output=True, check=False)
        except Exception as e:
            print(f"[FFmpeg] Frame extraction warning: {e}")
            
        return {
            "normalized_video": normalized_video if os.path.exists(normalized_video) else video_path,
            "audio_wav": audio_wav,
            "frames_dir": frames_dir
        }

ffmpeg_service = FFmpegService()
