"""
GCP Cloud Storage helpers.

Provides a single async upload function that wraps the synchronous
google-cloud-storage client via asyncio.to_thread so it does not block
the event loop.

Auth (in priority order):
  1. google_service_account_json env var — full service-account JSON string.
     Use locally or when explicit credentials are required.

     ⚠️  dotenv NOTE: service-account JSON contains newlines in the private
     key which break standard .env parsing. Store the value as a single-line
     string by minifying the JSON (remove all whitespace/newlines), then wrap
     it in single quotes in your .env file:

         google_service_account_json='{"type":"service_account","private_key":"-----BEGIN RSA PRIVATE KEY-----\\nMIIE...\\n-----END RSA PRIVATE KEY-----\\n",...}'

     Alternatively, set it as a shell environment variable before starting the
     server so dotenv parsing is bypassed entirely:

         export google_service_account_json="$(cat path/to/key.json | tr -d '\\n')"

  2. Application Default Credentials (ADC) — automatic on Cloud Run via the
     service account attached to the revision. No config needed in prod.

Required IAM role on the bucket:
    roles/storage.objectCreator  (upload)
    roles/storage.legacyBucketReader  (make_public / set object ACL)

Install:
    pip install -e ".[gcp]"
"""

from __future__ import annotations

import asyncio
import io
import json
import os

import structlog

logger = structlog.get_logger()


async def upload_csv(bucket_name: str, blob_name: str, csv_content: str) -> str | None:
    """Upload a CSV string to GCS and return the public HTTPS URL.

    Returns ``https://storage.googleapis.com/{bucket}/{blob}`` on success,
    or ``None`` if the upload fails (logged as a warning — never raises).

    Args:
        bucket_name: GCS bucket name.
        blob_name:   Object path within the bucket.
        csv_content: UTF-8 CSV string to upload.
    """
    try:
        from google.cloud import storage  # type: ignore[import-untyped]
    except ImportError:
        logger.warning(
            "gcs_upload_skipped",
            reason="google-cloud-storage not installed; run: pip install -e '.[gcp]'",
        )
        return None

    # Read credentials in the async context (main thread) where the settings /
    # environment is guaranteed to be fully loaded, then pass the raw values
    # into the thread so the sync client never touches settings directly.
    # This avoids dotenv multi-line parsing issues swallowing the JSON.
    sa_json_str = _read_sa_json()
    project_id = _read_project_id()

    def _upload() -> str:
        if sa_json_str:
            from google.oauth2 import service_account  # type: ignore[import-untyped]
            creds = service_account.Credentials.from_service_account_info(
                json.loads(sa_json_str),
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            client = storage.Client(credentials=creds, project=project_id or None)
        else:
            # ADC — automatic on Cloud Run via the attached service account.
            client = storage.Client()

        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        data = csv_content.encode()
        blob.upload_from_file(io.BytesIO(data), content_type="text/csv", size=len(data))
        return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"

    try:
        url = await asyncio.to_thread(_upload)
        logger.info("gcs_upload_success", bucket=bucket_name, blob=blob_name, url=url)
        return url
    except Exception as exc:
        logger.warning("gcs_upload_failed", bucket=bucket_name, blob=blob_name, error=str(exc))
        return None


def _read_sa_json() -> str:
    """Return the service-account JSON string from settings or the environment.

    Tries pydantic settings first; falls back to os.environ directly so that
    the value is available even when dotenv multi-line parsing swallows it.
    """
    # Lazy import to avoid circular imports at module load time.
    from app.config import settings  # noqa: PLC0415

    value = settings.google_service_account_json
    if not value:
        # Fallback: read directly from the process environment in case dotenv
        # failed to parse the multi-line JSON (e.g. newlines in private_key).
        value = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")

    if not value:
        logger.warning(
            "gcs_no_credentials",
            reason=(
                "GOOGLE_SERVICE_ACCOUNT_JSON is not set; falling back to ADC. "
                "If running locally, set it in .env as a minified single-line JSON string."
            ),
        )
    return value


def _read_project_id() -> str:
    from app.config import settings  # noqa: PLC0415
    return settings.google_project_id or os.environ.get("GOOGLE_PROJECT_ID", "")
