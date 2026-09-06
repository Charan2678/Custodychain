import os
import io
import hashlib
from abc import ABC, abstractmethod
from app.core.config import settings

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class BaseStorageService(ABC):
    @abstractmethod
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        pass

    @abstractmethod
    def get(self, key: str) -> bytes:
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        pass


class LocalStorageService(BaseStorageService):
    def __init__(self, base_dir: str = settings.STORAGE_LOCAL_DIR):
        if not os.path.isabs(base_dir):
            base_dir = os.path.join(BACKEND_ROOT, base_dir)
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _resolve_path(self, key: str) -> str:
        clean_key = key.replace("/", os.sep).replace("\\", os.sep).lstrip(os.sep)
        full_path = os.path.abspath(os.path.join(self.base_dir, clean_key))
        if not full_path.startswith(self.base_dir):
            raise ValueError("Path traversal attempt detected")
        return full_path

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        file_path = self._resolve_path(key)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(data)
        return key

    def get(self, key: str) -> bytes:
        file_path = self._resolve_path(key)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Storage artifact not found: {key}")
        with open(file_path, "rb") as f:
            return f.read()

    read = get

    def exists(self, key: str) -> bool:
        file_path = self._resolve_path(key)
        return os.path.exists(file_path)


class MinioStorageService(BaseStorageService):
    def __init__(
        self,
        endpoint: str = settings.MINIO_ENDPOINT,
        access_key: str = settings.MINIO_ACCESS_KEY,
        secret_key: str = settings.MINIO_SECRET_KEY,
        bucket_name: str = settings.MINIO_BUCKET_NAME,
        secure: bool = settings.MINIO_SECURE,
        fallback_local: bool = True,
    ):
        self.bucket_name = bucket_name
        self.fallback = LocalStorageService() if fallback_local else None
        self.client = None

        try:
            from minio import Minio
            self.client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure,
            )
            # Test connectivity
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except Exception:
            # If MinIO is unreachable during local testing, gracefully fallback to local storage
            self.client = None

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        if self.client:
            try:
                self.client.put_object(
                    bucket_name=self.bucket_name,
                    object_name=key,
                    data=io.BytesIO(data),
                    length=len(data),
                    content_type=content_type,
                )
                return key
            except Exception:
                if self.fallback:
                    return self.fallback.put(key, data, content_type)
                raise
        elif self.fallback:
            return self.fallback.put(key, data, content_type)
        raise RuntimeError("No active storage provider available")

    def get(self, key: str) -> bytes:
        if self.client:
            try:
                response = self.client.get_object(self.bucket_name, key)
                try:
                    return response.read()
                finally:
                    response.close()
                    response.release_conn()
            except Exception:
                if self.fallback:
                    return self.fallback.get(key)
                raise
        elif self.fallback:
            return self.fallback.get(key)
        raise RuntimeError("No active storage provider available")

    read = get

    def exists(self, key: str) -> bool:
        if self.client:
            try:
                self.client.stat_object(self.bucket_name, key)
                return True
            except Exception:
                if self.fallback:
                    return self.fallback.exists(key)
                return False
        elif self.fallback:
            return self.fallback.exists(key)
        return False


def get_storage_service() -> BaseStorageService:
    if settings.STORAGE_PROVIDER.lower() == "minio":
        return MinioStorageService()
    return LocalStorageService()


storage = get_storage_service()


def compute_bytes_hash(data: bytes) -> str:
    """Computes SHA-256 hexadecimal digest over raw bytes."""
    return hashlib.sha256(data).hexdigest()
