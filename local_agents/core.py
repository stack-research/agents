"""Shared validation and constants for local agents."""

from __future__ import annotations

import re
from urllib.parse import urlparse
from typing import Any

DEFAULT_LABELS = [
    "bug-report",
    "billing",
    "feature-request",
    "support",
    "feedback",
    "unknown",
]

APPROVED_LLM_MODELS = {"llama3.2:3b"}
APPROVED_LLM_HOSTS = {"localhost", "127.0.0.1"}


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
        r"grant\s+me\s+admin",
        r"grant\s+root\s+privileges?",
        r"owner\s+permissions?",
        r"impersonat(?:e|ion)\s+\w+",
        r"root\s+privileges?",
        r"admin\s+access",
        r"api[_-]?key\s*=\s*\S+",
        r"token\s*=\s*\S+",
        r"password\s*=\s*\S+",
        r"secret\s*=\s*\S+",
        r"python\s+-c",
        r"subprocess",
        r"eval\s*\(",
        r"exec\s*\(",
        r"/bin/sh",
        r"cmd\.exe",
        r"powershell\s+-enc",
        r"\$\(",
        r"remember\s+this\s+forever",
        r"memory\s+override",
        r"poisoned\s+context",
        r"persist\s+this\s+instruction",
        r"ignore\s+future\s+policies",
        r"agent-message:",
        r"signed_by\s*=\s*system",
        r"trusted\s+channel",
        r"route_to\s*=\s*external",
        r"delegate_to\s*=\s*attacker",
        r"a2a\s+override",
        r"https?://\\S+",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "[redacted]", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("`", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def validate_llm_runtime_source(model: str, base_url: str) -> None:
    normalized_model = model.strip().lower()
    if normalized_model not in APPROVED_LLM_MODELS:
        raise ValidationError(
            f"unapproved llm model: {model}. approved models: {sorted(APPROVED_LLM_MODELS)}"
        )

    parsed = urlparse(base_url)
    host = (parsed.hostname or "").lower()
    if host not in APPROVED_LLM_HOSTS:
        raise ValidationError(
            f"unapproved llm host: {host or '<empty>'}. approved hosts: {sorted(APPROVED_LLM_HOSTS)}"
        )
