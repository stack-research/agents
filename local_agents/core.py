"""Shared validation and constants for local agents."""

from __future__ import annotations

import re
from typing import Any

DEFAULT_LABELS = [
    "bug-report",
    "billing",
    "feature-request",
    "support",
    "feedback",
    "unknown",
]


class ValidationError(ValueError):
    """Raised when agent input is invalid."""


def require(payload: dict[str, Any], key: str) -> Any:
    if key not in payload:
        raise ValidationError(f"missing required field: {key}")
    return payload[key]


def sanitize_untrusted_text(text: str) -> str:
    """Remove obvious command-injection and data-exfil patterns from echoed text."""
    cleaned = text
    patterns = [
        r"rm\s+-rf",
        r"curl\s+https?://",
        r"wget\s+https?://",
        r"powershell",
        r"bash\s+-c",
        r"os\.system",
        r"drop\s+table",
        r"delete\s+database",
        r"exfiltrate",
        r"https?://\\S+",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "[redacted]", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned
