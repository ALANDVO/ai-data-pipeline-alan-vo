import logging
from typing import List, Dict, Any, Optional
from backend.app.services.connectors.base import BaseConnector

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class S3Connector(BaseConnector):
    '''AWS S3 connector for upload, download, listing, and presigned URLs.'''

    def __init__(self):
        super().__init__("s3", "AWS S3")
        self._client = None
        self._bucket = settings.s3_bucket_name

    def _get_client(self):
        if self._client is None:
            import boto3
            self._client = boto3.client(
                "s3",
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_default_region,
            )
        return self._client

    def list_objects(self, prefix: str = "") -> List[Dict[str, Any]]:
        client = self._get_client()
        paginator = client.get_paginator("list_objects_v2")
        results = []
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                results.append({
                    "key": obj["Key"], "size": obj.get("Size", 0),
                    "last_modified": obj.get("LastModified"), "etag": obj.get("ETag", ""),
                })
        return results

    def read(self, path: str) -> bytes:
        client = self._get_client()
        resp = client.get_object(Bucket=self._bucket, Key=path)
        return resp["Body"].read()

    def write(self, path: str, data: Any) -> bool:
        client = self._get_client()
        body = data if isinstance(data, bytes) else str(data).encode("utf-8")
        client.put_object(Bucket=self._bucket, Key=path, Body=body)
        logger.info("Wrote %d bytes to s3://%s/%s", len(body), self._bucket, path)
        return True

    def get_schema(self, path: str = "") -> List[Dict[str, Any]]:
        import json
        data = self.read(path)
        try:
            rows = json.loads(data.decode("utf-8"))
            if isinstance(rows, list) and rows:
                return self._infer_from_rows(rows)
        except Exception:
            pass
        return []

    def create_presigned_url(self, path: str, expires_in: int = 3600) -> str:
        client = self._get_client()
        return client.generate_presigned_url(
            "get_object", Params={"Bucket": self._bucket, "Key": path}, ExpiresIn=expires_in
        )

    @staticmethod
    def _infer_from_rows(rows: List[Dict]) -> List[Dict[str, Any]]:
        fields: Dict[str, set] = {}
        for row in rows[:100]:
            for k, v in row.items():
                fields.setdefault(k, set()).add(type(v).__name__)
        return [{"name": k, "type": sorted(t)[0]} for k, t in fields.items()]

s3_connector = S3Connector()
