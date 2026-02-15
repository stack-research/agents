"""Deterministic security scanner aligned to OWASP Agentic AI themes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .core import ValidationError


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
    return {"low": 8, "medium": 15, "high": 25}[severity]


def scan_repository_controls(target_path: str) -> dict[str, object]:
    root = Path(target_path).resolve()
    if not root.exists() or not root.is_dir():
        raise ValidationError(f"target_path does not exist or is not a directory: {target_path}")

    agents_root = root / "catalog" / "projects"
    if not agents_root.exists():
        raise ValidationError(f"catalog projects folder not found under: {root}")

    findings: list[Finding] = []
    project_count = 0
    agent_count = 0

    for project_dir in sorted(agents_root.iterdir()):
        if not project_dir.is_dir():
            continue
        project_count += 1
        agents_dir = project_dir / "agents"
        if not agents_dir.exists():
            findings.append(
                Finding(
                    id="SEC-ASI08-001",
                    severity="medium",
                    asi="ASI08",
                    title="Project missing agents directory",
                    path=str(project_dir.relative_to(root)),
                    recommendation="Create agents/ and define at least one scoped agent to keep project boundaries explicit.",
                )
            )
            continue

        for agent_dir in sorted(agents_dir.iterdir()):
            if not agent_dir.is_dir():
                continue
            agent_count += 1
            rel_agent = str(agent_dir.relative_to(root))

            prompt_path = agent_dir / "prompts" / "system.md"
            prompt_text = _read_text(prompt_path).lower()
            if "do not include extra keys" not in prompt_text:
                findings.append(
                    Finding(
                        id="SEC-ASI01-001",
                        severity="medium",
                        asi="ASI01",
                        title="Prompt lacks strict output-boundary reminder",
                        path=rel_agent + "/prompts/system.md",
                        recommendation="Add explicit output-boundary language to reduce goal/prompt hijack ambiguity.",
                    )
                )
            if "validate" not in prompt_text and "untrusted" not in prompt_text:
                findings.append(
                    Finding(
                        id="SEC-ASI01-002",
                        severity="low",
                        asi="ASI01",
                        title="Prompt does not mention validation or untrusted input",
                        path=rel_agent + "/prompts/system.md",
                        recommendation="Document validation or untrusted-input handling to reduce injection risk.",
                    )
                )

            runbook_path = agent_dir / "workflows" / "runbook.md"
            runbook_text = _read_text(runbook_path).lower()
            if "failure" not in runbook_text:
                findings.append(
                    Finding(
                        id="SEC-ASI08-002",
                        severity="low",
                        asi="ASI08",
                        title="Runbook does not document failure handling",
                        path=rel_agent + "/workflows/runbook.md",
                        recommendation="Add explicit failure modes and mitigation steps to reduce cascading failures.",
                    )
                )

    gitignore_text = _read_text(root / ".gitignore")
    if "__pycache__/" not in gitignore_text or "*.pyc" not in gitignore_text:
        findings.append(
            Finding(
                id="SEC-ASI04-001",
                severity="low",
                asi="ASI04",
                title="Git ignore policy is missing Python cache artifacts",
                path=".gitignore",
                recommendation="Ignore build/runtime artifacts to reduce accidental supply-chain and repo hygiene issues.",
            )
        )

    if not (root / "docker-compose.yml").exists():
        findings.append(
            Finding(
                id="SEC-ASI04-002",
                severity="low",
                asi="ASI04",
                title="No local container orchestration baseline found",
                path="docker-compose.yml",
                recommendation="Define containerized local runtime controls for reproducible and isolated security testing.",
            )
        )

    risk_score = min(100, sum(_severity_points(item.severity) for item in findings))
    findings_out = [item.as_dict() for item in findings]
    summary = (
        f"Scanned {project_count} projects and {agent_count} agents; "
        f"identified {len(findings_out)} findings."
    )

    return {
        "summary": summary,
        "risk_score": risk_score,
        "findings": findings_out,
    }
