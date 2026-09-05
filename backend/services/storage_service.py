import os
from pathlib import Path


class StorageService:
    """
    Abstract storage interface for digital evidence artifacts.
    Decouples business logic from filesystem vs S3 / WORM storage.
    """
    def put(self, storage_key: str, data: bytes | str) -> str:
        raise NotImplementedError

    def get(self, storage_key: str) -> bytes:
        raise NotImplementedError

    def exists(self, storage_key: str) -> bool:
        raise NotImplementedError


class LocalStorageService(StorageService):
    def __init__(self, base_dir: str | None = None):
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "artifacts")
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, storage_key: str) -> Path:
        # Sanitize storage key to avoid path traversal
        clean_key = storage_key.replace("..", "").lstrip("/\\")
        target = self.base_dir / clean_key
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def put(self, storage_key: str, data: bytes | str) -> str:
        target = self._resolve_path(storage_key)
        if isinstance(data, str):
            data = data.encode("utf-8")
        target.write_bytes(data)
        return str(target)

    def get(self, storage_key: str) -> bytes:
        target = self._resolve_path(storage_key)
        if not target.exists():
            raise FileNotFoundError(f"Artifact {storage_key} not found in storage.")
        return target.read_bytes()

    def exists(self, storage_key: str) -> bool:
        return self._resolve_path(storage_key).exists()


# Global storage instance
storage = LocalStorageService()
