import io
import pytest
from unittest.mock import patch

def test_upload_invalid_file_extension(client):
    file_content = b"fake video bytes"
    response = client.post(
        "/api/v1/jobs",
        files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
        data={"model": "gemini-3.1-pro", "mode": "realtime"}
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]

@patch("app.api.v1.jobs.run_job_pipeline")
@patch("app.api.v1.jobs.gcs_service.upload_file")
def test_successful_job_creation(mock_gcs_upload, mock_run_pipeline, client):
    mock_gcs_upload.return_value = "gs://mock-bucket/jobs/test.mp4"
    file_content = b"fake mp4 content"
    
    response = client.post(
        "/api/v1/jobs",
        files={"file": ("test.mp4", io.BytesIO(file_content), "video/mp4")},
        data={"prompt": "Check video quality", "model": "gemini-3.1-pro", "mode": "realtime"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "QUEUED"
    assert data["estimated_cost_usd"] > 0
    assert mock_run_pipeline.called

def test_get_job_not_found(client):
    response = client.get("/api/v1/jobs/nonexistent-id")
    assert response.status_code == 404
