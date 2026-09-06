import os
import json
from pathlib import Path
from typing import Dict, Tuple
from app.infrastructure.cryptography.signatures import generate_keypair

BACKEND_ROOT = Path(__file__).resolve().parents[3]
KEYSTORE_PATH = str(BACKEND_ROOT / "storage" / "keystore.json")


class SecureKeyManager:
    """
    Manages cryptographic keypairs for actors and tools.
    Public keys are stored in the database registry.
    Private keys are managed securely in local key vault (or HSM/KMS in production).
    """
    def __init__(self, storage_path: str = KEYSTORE_PATH):
        self.storage_path = storage_path
        self._keys: Dict[str, Dict[str, str]] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    self._keys = json.load(f)
            except Exception:
                self._keys = {}
        else:
            self._keys = {}

    def _save(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(self._keys, f, indent=2)

    def get_or_create_keypair(self, entity_id_or_name: str) -> Tuple[str, str]:
        """Returns (private_key_b64, public_key_b64) for given entity."""
        if entity_id_or_name in self._keys:
            data = self._keys[entity_id_or_name]
            return data["private_key"], data["public_key"]

        priv, pub = generate_keypair()
        self._keys[entity_id_or_name] = {
            "private_key": priv,
            "public_key": pub,
        }
        self._save()
        return priv, pub

    def get_public_key(self, entity_id_or_name: str) -> str:
        _, pub = self.get_or_create_keypair(entity_id_or_name)
        return pub

    def get_private_key(self, entity_id_or_name: str) -> str:
        priv, _ = self.get_or_create_keypair(entity_id_or_name)
        return priv


key_manager = SecureKeyManager()
