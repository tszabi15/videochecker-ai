import os
import shutil
from typing import Optional
from app.config import settings

try:
    from google.cloud import storage
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False

class GCSService:
    def __init__(self):
        self.bucket_name = settings.GCS_BUCKET_NAME
        self.project_id = settings.GCS_PROJECT_ID
        self._client = None
        
        # Local storage fallback directory
        self.local_gcs_dir = os.path.join(settings.TEMP_DIR, "gcs_mock")
        os.makedirs(self.local_gcs_dir, exist_ok=True)

    @property
    def client(self):
        if self._client is None and GCS_AVAILABLE:
            try:
                self._client = storage.Client(project=self.project_id)
            except Exception as e:
                print(f"[GCS] Cloud Storage client initialization failed, using local storage fallback: {e}")
                self._client = None
        return self._client

    def upload_file(self, local_path: str, destination_blob_name: str) -> str:
        """Uploads a file to GCS or local mock storage."""
        if self.client:
            try:
                bucket = self.client.bucket(self.bucket_name)
                blob = bucket.blob(destination_blob_name)
                blob.upload_from_filename(local_path)
                return f"gs://{self.bucket_name}/{destination_blob_name}"
            except Exception as e:
                print(f"[GCS] Upload failed: {e}. Falling back to local mock storage.")
        
        # Local fallback
        dest_path = os.path.join(self.local_gcs_dir, destination_blob_name)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy2(local_path, dest_path)
        return f"local://{dest_path}"

    def download_file(self, gcs_path: str, destination_path: str) -> str:
        """Downloads a file from GCS or local mock storage to local destination."""
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        
        if gcs_path.startswith("gs://") and self.client:
            try:
                blob_name = gcs_path.replace(f"gs://{self.bucket_name}/", "")
                bucket = self.client.bucket(self.bucket_name)
                blob = bucket.blob(blob_name)
                blob.download_to_filename(destination_path)
                return destination_path
            except Exception as e:
                print(f"[GCS] Download failed: {e}")
                
        if gcs_path.startswith("local://"):
            local_source = gcs_path.replace("local://", "")
            if os.path.exists(local_source):
                shutil.copy2(local_source, destination_path)
                return destination_path
                
        # If destination_path already exists or was passed directly
        if os.path.exists(gcs_path):
            shutil.copy2(gcs_path, destination_path)
            return destination_path
            
        raise FileNotFoundError(f"Source file not found for GCS path: {gcs_path}")

    def delete_file(self, gcs_path: str) -> bool:
        """Deletes a file from GCS or local mock storage."""
        if gcs_path.startswith("gs://") and self.client:
            try:
                blob_name = gcs_path.replace(f"gs://{self.bucket_name}/", "")
                bucket = self.client.bucket(self.bucket_name)
                blob = bucket.blob(blob_name)
                blob.delete()
                return True
            except Exception:
                pass
        elif gcs_path.startswith("local://"):
            local_source = gcs_path.replace("local://", "")
            if os.path.exists(local_source):
                os.remove(local_source)
                return True
        return False

gcs_service = GCSService()
