from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class SeverityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFO = "INFO"

class CategoryEnum(str, Enum):
    AUDIO_QUALITY = "AUDIO_QUALITY"
    AUDIO_SYNC = "AUDIO_SYNC"
    SPEECH_COHERENCE = "SPEECH_COHERENCE"
    BACKGROUND_NOISE = "BACKGROUND_NOISE"
    VISUAL_QUALITY = "VISUAL_QUALITY"
    RESOLUTION = "RESOLUTION"
    LIP_SYNC = "LIP_SYNC"
    SCREEN_CLUTTER = "SCREEN_CLUTTER"
    CONTENT_STRUCTURE = "CONTENT_STRUCTURE"
    MISSING_INTRODUCTION = "MISSING_INTRODUCTION"
    MISSING_SUMMARY = "MISSING_SUMMARY"
    CONTENT_ACCURACY = "CONTENT_ACCURACY"
    MISSING_WHY_EXPLANATION = "MISSING_WHY_EXPLANATION"
    TERMINOLOGY_INCONSISTENCY = "TERMINOLOGY_INCONSISTENCY"
    CODE_ERROR = "CODE_ERROR"
    COPY_PASTE_VIOLATION = "COPY_PASTE_VIOLATION"
    NAMING_CONVENTION = "NAMING_CONVENTION"
    PACING = "PACING"
    FILLER_WORDS = "FILLER_WORDS"
    MISSING_TIMESTAMPS = "MISSING_TIMESTAMPS"
    SENSITIVE_DATA_EXPOSURE = "SENSITIVE_DATA_EXPOSURE"
    MISSING_VERSION_INFO = "MISSING_VERSION_INFO"
    MISSING_QUIZ = "MISSING_QUIZ"
    METADATA = "METADATA"

class IssueItem(BaseModel):
    id: str = Field(..., description="UUID of the issue")
    timestamp_start: float = Field(..., description="Start timestamp in seconds")
    timestamp_end: float = Field(..., description="End timestamp in seconds")
    category: str = Field(..., description="Issue category")
    severity: str = Field(..., description="Severity rating: CRITICAL, MAJOR, MINOR, INFO")
    title: str = Field(..., description="Short title, max 10 words")
    description: str = Field(..., description="Detailed description of the issue")
    evidence: str = Field(..., description="Direct verbatim quote or precise visual frame description")
    suggestion: str = Field(..., description="Actionable recommendation to fix")
    whisper_confirmed: bool = Field(False, description="Cross-validated with audio transcript")
    confidence: float = Field(..., description="Confidence score from 0 to 1")

class ReportSummary(BaseModel):
    total_issues: int
    critical_issues: int
    major_issues: int
    minor_issues: int
    audio_quality_score: float = Field(..., ge=0, le=10)
    visual_quality_score: float = Field(..., ge=0, le=10)
    content_coherence_score: float = Field(..., ge=0, le=10)
    technical_accuracy_score: float = Field(..., ge=0, le=10)
    overall_score: float = Field(..., ge=0, le=10)
    passed: bool

class IssueReport(BaseModel):
    video_id: str
    analysis_timestamp: str
    video_duration_seconds: float
    processing_model: str
    cost_usd: float
    summary: ReportSummary
    issues: List[IssueItem]

class ReportResponse(BaseModel):
    json_report: IssueReport
    markdown_report: str
