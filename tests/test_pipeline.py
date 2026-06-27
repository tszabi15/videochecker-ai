import pytest
from unittest.mock import patch, MagicMock
from app.services.gemini import gemini_service
from app.schemas.report import IssueReport

def test_gemini_mock_report_schema_validation():
    metadata = {"duration": 100.0, "resolution": "1920x1080", "fps": 30.0, "size_mb": 15.0}
    report_dict = gemini_service._generate_mock_report(metadata, "gemini-3.1-pro")
    
    # Validate structure against Pydantic schema
    validated_report = IssueReport(**report_dict)
    assert validated_report.video_duration_seconds == 100.0
    assert len(validated_report.issues) > 0
    assert validated_report.summary.overall_score >= 0.0

@patch("app.services.whisper.whisper_service.transcribe")
def test_whisper_fallback_transcription(mock_transcribe):
    mock_transcribe.return_value = {
        "segments": [{"start": 0.0, "end": 5.0, "text": "Test speech", "words": []}]
    }
    result = mock_transcribe("fake_path.wav")
    assert "segments" in result
    assert result["segments"][0]["text"] == "Test speech"
