from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class SeverityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFO = "INFO"

class CategoryEnum(str, Enum):
    TECHNICAL_ERROR = "TECHNICAL_ERROR"
    CONTENT_ERROR = "CONTENT_ERROR"
    AUDIO_VISUAL_ERROR = "AUDIO_VISUAL_ERROR"
    GENERAL_OBSERVATION = "GENERAL_OBSERVATION"

class IssueItem(BaseModel):
    id: str = Field(..., description="UUID of the issue")
    timestamp_start: float = Field(..., description="Start timestamp in seconds")
    timestamp_end: float = Field(..., description="End timestamp in seconds")
    category: CategoryEnum = Field(..., description="Issue category: TECHNICAL_ERROR, CONTENT_ERROR, AUDIO_VISUAL_ERROR, GENERAL_OBSERVATION")
    severity: SeverityEnum = Field(..., description="Severity rating: CRITICAL, MAJOR, MINOR, INFO")
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
