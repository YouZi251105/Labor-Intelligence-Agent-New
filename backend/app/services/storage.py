from functools import lru_cache
from pathlib import Path
from typing import Protocol, cast

import boto3

from app.core.config import BACKEND_DIR, get_settings


class StorageBackend(Protocol):
    def save(self, key: str, content: bytes) -> str: ...

    def read(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...

    def exists(self, key: str) -> bool: ...


class LocalStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if not candidate.is_relative_to(self.root) or candidate == self.root:
            raise ValueError("非法存储路径")
        return candidate

    def save(self, key: str, content: bytes) -> str:
        target = self._resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return key

    def read(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def delete(self, key: str) -> None:
        target = self._resolve(key)
        target.unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        try:
            return self._resolve(key).is_file()
        except ValueError:
            return False


class S3Storage:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool,
    ) -> None:
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=f"{'https' if secure else 'http'}://{endpoint}",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
        )

    def save(self, key: str, content: bytes) -> str:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=content)
        return key

    def read(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return cast(bytes, response["Body"].read())

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except self.client.exceptions.ClientError:
            return False


def get_storage_root() -> Path:
    settings = get_settings()
    configured = Path(settings.upload_dir)
    return configured if configured.is_absolute() else BACKEND_DIR / configured


@lru_cache
def get_storage() -> StorageBackend:
    settings = get_settings()
    if settings.storage_backend.lower() == "s3":
        return S3Storage(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            bucket=settings.minio_bucket,
            secure=settings.minio_secure,
        )
    return LocalStorage(get_storage_root())
