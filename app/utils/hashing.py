import hashlib
import re


def normalize_text(text: str) -> str:
    """Lowercase, strip whitespace, collapse runs of whitespace."""
    return re.sub(r"\s+", " ", text.strip().lower())


def compute_content_hash(title: str, url: str) -> str:
    """SHA-256 of normalized(title) + normalized(url)."""
    normalized = normalize_text(title) + normalize_text(url)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
