"""
Google Cloud Storage service with local filesystem fallback.

Provides upload, download, and delete operations for video files.
When GCS credentials are unavailable, files are stored in a local mock directory.
"""

import os
import shutil
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

try:
    from google.cloud import storage
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False


class GCSService:
    """Manages file storage via Google Cloud Storage or local fallback."""

    def __init__(self) -> None:
        self.bucket_name: str = settings.GCS_BUCKET_NAME
        self.project_id: str = settings.GCS_PROJECT_ID
        self._client = None

        # Local storage fallback directory
        self.local_gcs_dir: str = os.path.join(settings.TEMP_DIR, "gcs_mock")
        os.makedirs(self.local_gcs_dir, exist_ok=True)

    @property
    def client(self):
        """Lazy-initializes the GCS client. Returns None if unavailable."""
        if self._client is None and GCS_AVAILABLE:
            try:
                self._client = storage.Client(project=self.project_id)
            except Exception as e:
                logger.warning("GCS client init failed, using local fallback: %s", e)
                self._client = None
        return self._client

    def upload_file(self, local_path: str, destination_blob_name: str) -> str:
        """
        Uploads a file to GCS or local mock storage.

        Returns the storage path (gs:// or local://).
        """
        if self.client:
            try:
                bucket = self.client.bucket(self.bucket_name)
                blob = bucket.blob(destination_blob_name)
                blob.upload_from_filename(local_path)
                gcs_path = f"gs://{self.bucket_name}/{destination_blob_name}"
                logger.info("Uploaded to GCS: %s", gcs_path)
                return gcs_path
            except Exception as e:
                logger.warning("GCS upload failed: %s. Falling back to local.", e)

        # Local fallback
        dest_path = os.path.join(self.local_gcs_dir, destination_blob_name)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy2(local_path, dest_path)
        local_uri = f"local://{dest_path}"
        logger.info("Uploaded to local storage: %s", local_uri)
        return local_uri

    def download_file(self, gcs_path: str, destination_path: str) -> str:
        """
        Downloads a file from GCS or local mock storage to a local destination.

        Returns the destination path on success.
        Raises FileNotFoundError if the source cannot be located.
        """
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)

        if gcs_path.startswith("gs://") and self.client:
            try:
                blob_name = gcs_path.replace(f"gs://{self.bucket_name}/", "")
                bucket = self.client.bucket(self.bucket_name)
                blob = bucket.blob(blob_name)
                blob.download_to_filename(destination_path)
                logger.info("Downloaded from GCS: %s", gcs_path)
                return destination_path
            except Exception as e:
                logger.warning("GCS download failed: %s", e)

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
        """
        Deletes a file from GCS or local mock storage.

        Returns True if the file was deleted, False otherwise.
        """
        if gcs_path.startswith("gs://") and self.client:
            try:
                blob_name = gcs_path.replace(f"gs://{self.bucket_name}/", "")
                bucket = self.client.bucket(self.bucket_name)
                blob = bucket.blob(blob_name)
                blob.delete()
                logger.info("Deleted from GCS: %s", gcs_path)
                return True
            except Exception as e:
                logger.warning("GCS delete failed for %s: %s", gcs_path, e)
        elif gcs_path.startswith("local://"):
            local_source = gcs_path.replace("local://", "")
            if os.path.exists(local_source):
                os.remove(local_source)
                logger.info("Deleted local file: %s", local_source)
                return True
        return False


gcs_service = GCSService()
