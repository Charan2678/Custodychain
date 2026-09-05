import base64
import hashlib
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature


class KeyProvider:
    """
    Manages asymmetric Ed25519 keypairs for forensic handlers.
    Derives deterministic, persistent keys per handler name so signatures
    remain verifiable across server restarts without external KMS dependencies.
    """
    _keys: dict[str, ed25519.Ed25519PrivateKey] = {}

    @classmethod
    def get_private_key(cls, handler_name: str) -> ed25519.Ed25519PrivateKey:
        if handler_name not in cls._keys:
            # Derive deterministic 32-byte seed from handler name and forensic domain salt
            seed = hashlib.sha256(f"CustodyChain-Ed25519-Seed-v1:{handler_name}".encode()).digest()
            cls._keys[handler_name] = ed25519.Ed25519PrivateKey.from_private_bytes(seed)
        return cls._keys[handler_name]

    @classmethod
    def get_public_key_b64(cls, handler_name: str) -> str:
        priv = cls.get_private_key(handler_name)
        pub_bytes = priv.public_key().public_bytes_raw()
        return base64.b64encode(pub_bytes).decode("ascii")


def build_canonical_event_string(
    evidence_id: int,
    sequence: int,
    handler_name: str,
    action: str,
    hash_before: str,
    hash_after: str,
    timestamp_iso: str,
    previous_event_hash: str,
) -> str:
    """
    Standardized pipe-delimited canonical string format.
    Prevents cross-platform JSON whitespace or key-ordering discrepancies
    from invalidating digital signatures.
    """
    return (
        f"{evidence_id}|{sequence}|{handler_name}|{action}|"
        f"{hash_before}|{hash_after}|{timestamp_iso}|{previous_event_hash}"
    )


def sign_event(handler_name: str, canonical_string: str) -> str:
    """
    Digitally signs a canonical custody event using handler's Ed25519 private key.
    Returns Base64-encoded signature.
    """
    priv_key = KeyProvider.get_private_key(handler_name)
    signature_bytes = priv_key.sign(canonical_string.encode("utf-8"))
    return base64.b64encode(signature_bytes).decode("ascii")


def verify_event_signature(public_key_b64: str, canonical_string: str, signature_b64: str) -> bool:
    """
    Verifies an Ed25519 digital signature against the canonical event string.
    Returns True if valid, False if altered or forged.
    """
    try:
        pub_bytes = base64.b64decode(public_key_b64)
        sig_bytes = base64.b64decode(signature_b64)
        pub_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        pub_key.verify(sig_bytes, canonical_string.encode("utf-8"))
        return True
    except (InvalidSignature, ValueError, Exception):
        return False
