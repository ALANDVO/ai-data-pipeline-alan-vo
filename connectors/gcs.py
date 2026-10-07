import logging
from typing import List, Dict, Any, Optional

from connectors.base import BaseConnector
from config import settings

logger = logging.getLogger(__name__)

class GCSConnector(BaseConnector):
    '''Google Cloud Storage connector.'''

    def __init__(self):
        super().__init__("gcs", "Google Cloud Storage")
        self._client = None
        self._bucket = settings.gcs_bucket_name

    def _get_client(self):
        if self._client is None:
            from google.cloud import storage
            if settings.gcs_service_account_json:
                from google.oauth2 import service_account
                import json
                creds = service_account.Credentials.from_service_account_info(
                    json.loads(settings.gcs_service_account_json)
                )
                self._client = storage.Client(credentials=creds)
            else:
                self._client = storage.Client()
        return self._client

    def _get_bucket(self):
        client = self._get_client()
        return client.bucket(self._bucket)

    def list_objects(self, prefix: str = "") -> List[Dict[str, Any]]:
        bucket = self._get_bucket()
        blobs = bucket.list_blobs(prefix=prefix)
        return [
            {"name": b.name, "size": b.size, "updated": b.updated.isoformat() if b.updated else None}
            for b in blobs
        ]

    def read(self, path: str) -> bytes:
        bucket = self._get_bucket()
        blob = bucket.blob(path)
        return blob.download_as_bytes()

    def write(self, path: str, data: Any) -> bool:
        bucket = self._get_bucket()
        blob = bucket.blob(path)
        if isinstance(data, bytes):
            blob.upload_from_string(data)
        else:
            blob.upload_from_string(str(data))
        logger.info("Wrote to gs://%s/%s", self._bucket, path)
        return True

    def get_schema(self, path: str = "") -> List[Dict[str, Any]]:
        import json
        data = self.read(path)
        try:
            rows = json.loads(data.decode("utf-8"))
            if isinstance(rows, list) and rows:
                fields: Dict[str, set] = {}
                for row in rows[:100]:
                    for k, v in row.items():
                        fields.setdefault(k, set()).add(type(v).__name__)
                return [{"name": k, "type": sorted(t)[0]} for k, t in fields.items()]
        except Exception:
            pass
        return []

    def create_signed_url(self, path: str, expires_in: int = 3600) -> str:
        bucket = self._get_bucket()
        blob = bucket.blob(path)
        return blob.generate_signed_url(version="v4", expiration=expires_in)

gcs_connector = GCSConnector()
