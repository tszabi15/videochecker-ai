from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from enum import Enum

class ModelEnum(str, Enum):
    GEMINI_3_1_PRO = "gemini-3.1-pro"
    GEMINI_3_5_FLASH = "gemini-3.5-flash"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"

class ModeEnum(str, Enum):
    REALTIME = "realtime"
    BATCH = "batch"

class JobStatusEnum(str, Enum):
    QUEUED = "QUEUED"
    PREPROCESSING = "PREPROCESSING"
    TRANSCRIBING = "TRANSCRIBING"
    ANALYZING = "ANALYZING"
    DONE = "DONE"
    FAILED = "FAILED"

class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatusEnum
    estimated_cost_usd: float

class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatusEnum
    original_filename: str
    model_used: str
    mode: str
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None
    estimated_cost_usd: float
    actual_cost_usd: Optional[float] = 0.0
    duration_seconds: Optional[float] = 0.0

class JobListItem(BaseModel):
    id: str
    original_filename: str
    duration_seconds: Optional[float] = 0.0
    submitted_at: datetime
    status: JobStatusEnum
    model_used: str
    overall_score: Optional[float] = None
    cost_usd: float

class CostStatsResponse(BaseModel):
    total_jobs: int
    completed_jobs: int
    total_spend_usd: float
    total_input_tokens: int
    total_output_tokens: int
    total_whisper_minutes: float
    spend_by_model: dict
