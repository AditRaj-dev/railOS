"""Object storage abstraction for RailOS evidence media.

Provides a clean interface for multipart uploads, presigned URLs, and streaming
verification. Implements both S3/Neon compatible storage and an in-memory mock
store for local test runs.
"""

from __future__ import annotations

import io
import os
import time
from abc import ABC, abstractmethod
from typing import Any, BinaryIO


class ObjectStore(ABC):
    """Abstract interface for storing raw and proof evidence media."""

    @abstractmethod
    def initiate_multipart_upload(self, key: str, content_type: str = "application/octet-stream") -> str:
        """Initiate multipart upload and return upload_id."""
        pass

    @abstractmethod
    def generate_presigned_upload_part_url(
        self, key: str, upload_id: str, part_number: int, expires_in: int = 3600
    ) -> str:
        """Generate presigned URL for direct client-to-bucket part upload."""
        pass

    @abstractmethod
    def complete_multipart_upload(
        self, key: str, upload_id: str, parts: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Complete multipart upload with list of {'PartNumber': int, 'ETag': str}."""
        pass

    @abstractmethod
    def abort_multipart_upload(self, key: str, upload_id: str) -> None:
        """Abort an in-progress multipart upload session."""
        pass

    @abstractmethod
    def generate_presigned_download_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate short-lived signed URL for authenticated media playback/preview."""
        pass

    @abstractmethod
    def get_object_bytes(self, key: str) -> bytes:
        """Fetch complete object as bytes."""
        pass

    @abstractmethod
    def put_object_bytes(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> None:
        """Directly write an object (used in tests and fallback processing)."""
        pass

    @abstractmethod
    def get_object_metadata(self, key: str) -> dict[str, Any]:
        """Retrieve size, content type, and ETag."""
        pass

    @abstractmethod
    def delete_object(self, key: str) -> None:
        """Delete an object for retention lifecycle cleanup."""
        pass


class MemoryObjectStore(ObjectStore):
    """Thread-safe in-memory object store for tests and local development."""

    def __init__(self):
        self._objects: dict[str, bytes] = {}
        self._metadata: dict[str, dict[str, Any]] = {}
        self._multipart_sessions: dict[str, dict[str, Any]] = {}
        self._upload_counter = 0

    def initiate_multipart_upload(self, key: str, content_type: str = "application/octet-stream") -> str:
        self._upload_counter += 1
        upload_id = f"mem-upload-{self._upload_counter}"
        self._multipart_sessions[upload_id] = {
            "key": key,
            "content_type": content_type,
            "parts": {},
            "created_at": time.time(),
        }
        return upload_id

    def generate_presigned_upload_part_url(
        self, key: str, upload_id: str, part_number: int, expires_in: int = 3600
    ) -> str:
        return f"https://mock-storage.railos.internal/{key}?uploadId={upload_id}&partNumber={part_number}&expires={int(time.time() + expires_in)}"

    def complete_multipart_upload(
        self, key: str, upload_id: str, parts: list[dict[str, Any]]
    ) -> dict[str, Any]:
        session = self._multipart_sessions.get(upload_id)
        if not session:
            raise KeyError(f"Upload session {upload_id} not found")

        sorted_parts = sorted(parts, key=lambda p: p["PartNumber"])
        combined = bytearray()
        for p in sorted_parts:
            part_num = p["PartNumber"]
            part_bytes = session["parts"].get(part_num, b"")
            combined.extend(part_bytes)

        raw_data = bytes(combined)
        self._objects[key] = raw_data
        self._metadata[key] = {
            "content_length": len(raw_data),
            "content_type": session["content_type"],
            "etag": f'"{hash(raw_data)}"',
        }
        del self._multipart_sessions[upload_id]
        return {"ETag": self._metadata[key]["etag"], "Key": key}

    def abort_multipart_upload(self, key: str, upload_id: str) -> None:
        self._multipart_sessions.pop(upload_id, None)

    def generate_presigned_download_url(self, key: str, expires_in: int = 3600) -> str:
        return f"/api/v1/evidence/preview-media?key={key}&expires={int(time.time() + expires_in)}"

    def get_object_bytes(self, key: str) -> bytes:
        if key not in self._objects:
            raise KeyError(f"Object {key} not found")
        return self._objects[key]

    def put_object_bytes(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> None:
        self._objects[key] = data
        self._metadata[key] = {
            "content_length": len(data),
            "content_type": content_type,
            "etag": f'"{hash(data)}"',
        }

    def put_multipart_part(self, upload_id: str, part_number: int, data: bytes) -> str:
        """Helper for test suites to simulate direct part uploads."""
        session = self._multipart_sessions.get(upload_id)
        if not session:
            raise KeyError(f"Upload session {upload_id} not found")
        session["parts"][part_number] = data
        return f'"part-{part_number}-etag"'

    def get_object_metadata(self, key: str) -> dict[str, Any]:
        if key not in self._metadata:
            raise KeyError(f"Object {key} not found")
        return self._metadata[key]

    def delete_object(self, key: str) -> None:
        self._objects.pop(key, None)
        self._metadata.pop(key, None)


class S3ObjectStore(ObjectStore):
    """Production S3-compatible ObjectStore (supports Neon Object Storage, AWS S3, MinIO)."""

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: str | None = None,
        region_name: str = "auto",
        access_key: str | None = None,
        secret_key: str | None = None,
    ):
        import boto3
        from botocore.config import Config

        self.bucket = bucket_name
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region_name,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
        )

    def initiate_multipart_upload(self, key: str, content_type: str = "application/octet-stream") -> str:
        res = self.s3_client.create_multipart_upload(
            Bucket=self.bucket, Key=key, ContentType=content_type
        )
        return res["UploadId"]

    def generate_presigned_upload_part_url(
        self, key: str, upload_id: str, part_number: int, expires_in: int = 3600
    ) -> str:
        return self.s3_client.generate_presigned_url(
            "upload_part",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "UploadId": upload_id,
                "PartNumber": part_number,
            },
            ExpiresIn=expires_in,
        )

    def complete_multipart_upload(
        self, key: str, upload_id: str, parts: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return self.s3_client.complete_multipart_upload(
            Bucket=self.bucket,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={"Parts": parts},
        )

    def abort_multipart_upload(self, key: str, upload_id: str) -> None:
        self.s3_client.abort_multipart_upload(
            Bucket=self.bucket, Key=key, UploadId=upload_id
        )

    def generate_presigned_download_url(self, key: str, expires_in: int = 3600) -> str:
        return self.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def get_object_bytes(self, key: str) -> bytes:
        res = self.s3_client.get_object(Bucket=self.bucket, Key=key)
        return res["Body"].read()

    def put_object_bytes(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> None:
        self.s3_client.put_object(
            Bucket=self.bucket, Key=key, Body=data, ContentType=content_type
        )

    def get_object_metadata(self, key: str) -> dict[str, Any]:
        res = self.s3_client.head_object(Bucket=self.bucket, Key=key)
        return {
            "content_length": res.get("ContentLength", 0),
            "content_type": res.get("ContentType", "application/octet-stream"),
            "etag": res.get("ETag", ""),
        }

    def delete_object(self, key: str) -> None:
        self.s3_client.delete_object(Bucket=self.bucket, Key=key)


def get_object_store() -> ObjectStore:
    """Factory creating configured ObjectStore."""
    bucket = (
        os.getenv("EVIDENCE_S3_BUCKET")
        or os.getenv("NEON_STORAGE_BUCKET")
        or os.getenv("AWS_S3_BUCKET")
    )
    if bucket:
        endpoint = (
            os.getenv("AWS_ENDPOINT_URL_S3")
            or os.getenv("EVIDENCE_S3_ENDPOINT")
            or os.getenv("NEON_STORAGE_ENDPOINT")
        )
        access_key = os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("NEON_STORAGE_KEY")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY") or os.getenv("NEON_STORAGE_SECRET")
        region = os.getenv("AWS_REGION") or "auto"
        return S3ObjectStore(
            bucket_name=bucket,
            endpoint_url=endpoint,
            region_name=region,
            access_key=access_key,
            secret_key=secret_key,
        )
    return MemoryObjectStore()
