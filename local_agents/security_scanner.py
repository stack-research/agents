"""Configurable security scanner aligned to OWASP Agentic AI themes.

Discovers agents via glob (``**/agent.yaml`` by default) and evaluates
configurable check rules from a JSON rules file.  Works against any
agent catalog layout — no hardcoded directory structure.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .core import ValidationError

_DEFAULT_RULES_PATH = Path(__file__).resolve().parents[1] / "policy" / "scanner-rules.json"


@dataclass
class Finding:
    id: str
    severity: str
    asi: str
    title: str
    path: str
    recommendation: str

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "severity": self.severity,
            "asi": self.asi,
            "title": self.title,
            "path": self.path,
            "recommendation": self.recommendation,
        }


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _severity_points(severity: str) -> int:
    return {"low": 8, "medium": 15, "high": 25}.get(severity, 0)


def _load_rules(rules_path: Path | str | None = None) -> dict[str, Any]:
    path = Path(rules_path) if rules_path else _DEFAULT_RULES_PATH
    if not path.exists():
        raise ValidationError(f"scanner rules file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _evaluate_check(check: dict[str, Any], base_dir: Path, root: Path) -> Finding | None:
    """Evaluate a single check rule against a base directory.  Return a Finding on failure."""
    file_rel = check.get("file", "")
    if not file_rel:
        return None

    target = base_dir / file_rel
    text = _read_text(target).lower()
    rel_path = str(target.relative_to(root)) if target.is_relative_to(root) else str(target)

    # exists check
    if "exists" in check:
        if check["exists"] and not target.exists():
            return _finding(check, rel_path)
        if not check["exists"] and target.exists():
            return _finding(check, rel_path)
        return None

    # All text-based checks require the file to exist and have content.
    # A missing file is a finding only for contains / contains_any / contains_all.
    if not text:
        if "contains" in check or "contains_any" in check or "contains_all" in check:
            return _finding(check, rel_path)
        return None

    if "contains" in check:
        if check["contains"].lower() not in text:
            return _finding(check, rel_path)

    if "contains_any" in check:
        if not any(item.lower() in text for item in check["contains_any"]):
            return _finding(check, rel_path)

    if "contains_all" in check:
        if not all(item.lower() in text for item in check["contains_all"]):
            return _finding(check, rel_path)

    return None


def _finding(check: dict[str, Any], path: str) -> Finding:
    return Finding(
        id=check["id"],
        severity=check["severity"],
        asi=check["asi"],
        title=check["title"],
        path=path,
        recommendation=check["recommendation"],
    )


def scan_repository_controls(
    target_path: str,
    rules_path: str | None = None,
) -> dict[str, object]:
    """Scan an agent catalog at *target_path* using rules from *rules_path*.

    When *rules_path* is ``None`` the default rules at
    ``policy/scanner-rules.json`` are used.
    """
    root = Path(target_path).resolve()
    if not root.exists() or not root.is_dir():
        raise ValidationError(f"target_path does not exist or is not a directory: {target_path}")

    rules = _load_rules(rules_path)
    manifest = rules.get("agent_manifest", "agent.yaml")
    agent_checks = rules.get("agent_checks", [])
    repo_checks = rules.get("repo_checks", [])

    findings: list[Finding] = []

    # ── Discover agents via glob ───────────────────────────────────
    agent_dirs: list[Path] = []
    for manifest_path in sorted(root.rglob(manifest)):
        agent_dir = manifest_path.parent
        agent_dirs.append(agent_dir)

    # ── Agent-level checks ─────────────────────────────────────────
    for agent_dir in agent_dirs:
        for check in agent_checks:
            result = _evaluate_check(check, agent_dir, root)
            if result is not None:
                findings.append(result)

    # ── Repository-level checks ────────────────────────────────────
    for check in repo_checks:
        result = _evaluate_check(check, root, root)
        if result is not None:
            findings.append(result)

    # ── Summary ────────────────────────────────────────────────────
    risk_score = min(100, sum(_severity_points(f.severity) for f in findings))
    findings_out = [f.as_dict() for f in findings]
    summary = (
        f"Scanned {len(agent_dirs)} agents; "
        f"identified {len(findings_out)} findings."
    )

    return {
        "summary": summary,
        "risk_score": risk_score,
        "findings": findings_out,
    }
