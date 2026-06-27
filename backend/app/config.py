import os
from typing import Dict, Any
from pydantic_settings import BaseSettings

MODEL_CONFIG: Dict[str, Dict[str, Any]] = {
    "HEAVY_ANALYZER": {
        "model_id": "gemini-3.5-flash",
        "input_price_per_m": 1.50,
        "output_price_per_m": 9.00,
        "input_price_per_m_long": 1.50,
        "output_price_per_m_long": 9.00,
        "context_window": 1_000_000,
        "batch_discount": 0.50,
    },
    "FAST_VERIFIER": {
        "model_id": "gemini-3.5-flash",
        "input_price_per_m": 1.50,
        "output_price_per_m": 9.00,
        "input_price_per_m_long": 1.50,
        "output_price_per_m_long": 9.00,
        "context_window": 1_000_000,
        "batch_discount": 0.50,
    },
    "gemini-3.1-pro": {
        "model_id": "gemini-3.1-pro-preview",
        "input_price_per_m": 2.00,
        "output_price_per_m": 12.00,
        "input_price_per_m_long": 4.00,   # above 200K tokens
        "output_price_per_m_long": 18.00,
        "context_window": 2_000_000,
        "batch_discount": 0.50,
    },
    "gemini-3.5-flash": {
        "model_id": "gemini-3.5-flash",
        "input_price_per_m": 1.50,
        "output_price_per_m": 9.00,
        "input_price_per_m_long": 1.50,
        "output_price_per_m_long": 9.00,
        "context_window": 1_000_000,
        "batch_discount": 0.50,
    },
    "gemini-2.5-flash": {
        "model_id": "gemini-2.5-flash",
        "input_price_per_m": 0.30,
        "output_price_per_m": 2.50,
        "input_price_per_m_long": 0.30,
        "output_price_per_m_long": 2.50,
        "context_window": 1_000_000,
        "batch_discount": 0.50,
    },
}

import tempfile

class Settings(BaseSettings):
    PROJECT_NAME: str = "Video Quality Checker AI"
    API_V1_STR: str = "/api/v1"
    
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    GCS_BUCKET_NAME: str = "videochecker-ai-bucket"
    GCS_PROJECT_ID: str = "videochecker-ai-project"
    
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/videochecker"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    WHISPER_BACKEND: str = "api"  # "api" or "local"
    MAX_VIDEO_SIZE_MB: int = 2048
    DEFAULT_MODEL: str = "HEAVY_ANALYZER"
    
    TEMP_DIR: str = "/tmp/videochecker"

    class Config:
        env_file = ".env"
        extra = "ignore"

def _resolve_temp_dir(preferred_path: str) -> str:
    try:
        os.makedirs(preferred_path, exist_ok=True)
        test_path = os.path.join(preferred_path, f".perm_test_{os.getpid()}")
        with open(test_path, "w") as f:
            f.write("test")
        os.remove(test_path)
        return preferred_path
    except (PermissionError, OSError):
        fallback = os.path.join(tempfile.gettempdir(), "videochecker_scratch")
        os.makedirs(fallback, exist_ok=True)
        return fallback

settings = Settings()
settings.TEMP_DIR = _resolve_temp_dir(settings.TEMP_DIR)
