import base64
import hashlib
from typing import Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

GENESIS_HASH = "0" * 64


def generate_keypair() -> Tuple[str, str]:
    """
    Generates a fresh Ed25519 private/public keypair.
    Returns (private_key_b64, public_key_b64).
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    priv_bytes = private_key.private_bytes_raw()
    pub_bytes = public_key.public_bytes_raw()

    return (
        base64.b64encode(priv_bytes).decode("ascii"),
        base64.b64encode(pub_bytes).decode("ascii"),
    )


def sign_payload(private_key_b64: str, payload_str: str) -> str:
    """Signs a UTF-8 payload using Ed25519 private key. Returns Base64 signature."""
    priv_bytes = base64.b64decode(private_key_b64.encode("ascii"))
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
    signature = private_key.sign(payload_str.encode("utf-8"))
    return base64.b64encode(signature).decode("ascii")


def verify_signature(public_key_b64: str, payload_str: str, signature_b64: str) -> bool:
    """Verifies an Ed25519 signature against canonical payload string."""
    try:
        pub_bytes = base64.b64decode(public_key_b64.encode("ascii"))
        sig_bytes = base64.b64decode(signature_b64.encode("ascii"))
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        public_key.verify(sig_bytes, payload_str.encode("utf-8"))
        return True
    except (InvalidSignature, ValueError, Exception):
        return False


def build_canonical_event_string(
    evidence_id: str,
    sequence_number: int,
    actor_id: str,
    tool_id: str | None,
    operation: str,
    input_artifact_hash: str,
    output_artifact_hash: str,
    occurred_at_str: str,
    previous_event_hash: str,
) -> str:
    """
    Builds the deterministic, immutable canonical representation of a custody event.
    Any alteration of any field produces an invalid signature and broken event hash.
    """
    return (
        f"{evidence_id}|"
        f"{sequence_number}|"
        f"{actor_id}|"
        f"{tool_id or 'NONE'}|"
        f"{operation}|"
        f"{input_artifact_hash}|"
        f"{output_artifact_hash}|"
        f"{occurred_at_str}|"
        f"{previous_event_hash}"
    )


def compute_event_hash(canonical_str: str, previous_event_hash: str) -> str:
    """
    Computes cryptographic SHA-256 event hash linking to the preceding event.
    event_hash = SHA256(previous_event_hash | canonical_event_data)
    """
    payload = f"{previous_event_hash}|{canonical_str}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
