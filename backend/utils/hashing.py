import hashlib


def compute_hash(content: str) -> str:
    """Returns the SHA-256 hex digest of the given string content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
