"""Deterministic builders for failure-ops agents."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .core import ValidationError, require, sanitize_untrusted_text

ALLOWED_IMPACT = frozenset({"low", "medium", "high"})
ALLOWED_CONFIDENCE = frozenset({"low", "medium", "high"})
ALLOWED_BLAST = frozenset({"localized", "tier", "cross-system", "global"})
MAX_OBSERVATIONS = 64
MAX_FAILURE_MODES = 64
MAX_CLUSTERS = 16
MAX_STEPS = 12


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _impact_from_text(text: str) -> str:
    low = text.lower()
    if any(token in low for token in ["sev1", "critical", "all regions", "outage", "global"]):
        return "high"
    if any(token in low for token in ["degraded", "partial", "slow", "timeout"]):
        return "medium"
    return "low"


def _truncate_words(text: str, count: int) -> str:
    return " ".join(text.split()[:count])


def build_failure_library(payload: dict[str, Any]) -> dict[str, Any]:
    incident_id = require(payload, "incident_id")
    observations = require(payload, "observations")
    if not isinstance(incident_id, str) or not incident_id.strip():
        raise ValidationError("incident_id must be a non-empty string")
    if not isinstance(observations, list) or not observations:
        raise ValidationError("observations must be a non-empty array")
    if len(observations) > MAX_OBSERVATIONS:
        raise ValidationError(f"observations must have at most {MAX_OBSERVATIONS} items")

    incident_safe = sanitize_untrusted_text(_truncate_words(incident_id.strip(), 12))[:120]
    failure_modes: list[dict[str, Any]] = []
    complete = True
    for obs in observations[:MAX_OBSERVATIONS]:
        if not isinstance(obs, dict):
            raise ValidationError("each observation must be an object")
        service = obs.get("service")
        symptom = obs.get("symptom")
        impact_raw = obs.get("impact")
        trigger = obs.get("trigger", "unknown trigger")
        env = obs.get("environment", "unknown")
        if not isinstance(service, str) or not service.strip():
            raise ValidationError("each observation requires a non-empty service")
        if not isinstance(symptom, str) or not symptom.strip():
            raise ValidationError("each observation requires a non-empty symptom")
        if not isinstance(impact_raw, str) or not impact_raw.strip():
            raise ValidationError("each observation requires a non-empty impact")
        if trigger is not None and not isinstance(trigger, str):
            raise ValidationError("trigger must be a string when provided")
        if env is not None and not isinstance(env, str):
            raise ValidationError("environment must be a string when provided")

        service_safe = sanitize_untrusted_text(service.strip())[:80]
        symptom_safe = sanitize_untrusted_text(_truncate_words(symptom.strip(), 18))[:220]
        trigger_safe = sanitize_untrusted_text(_truncate_words((trigger or "unknown trigger").strip(), 12))[:140]
        env_safe = sanitize_untrusted_text((env or "unknown").strip())[:32]
        impact = impact_raw.strip().lower()
        if impact not in ALLOWED_IMPACT:
            impact = _impact_from_text(impact_raw)

        timeline_hint = obs.get("timeline_hint", "")
        hint_safe = ""
        if timeline_hint is not None:
            if not isinstance(timeline_hint, str):
                raise ValidationError("timeline_hint must be a string when provided")
            hint_safe = sanitize_untrusted_text(_truncate_words(timeline_hint.strip(), 10))[:120]

        preconditions = [f"{env_safe} environment active"]
        if hint_safe:
            preconditions.append(hint_safe)
        indicators = [f"{service_safe} reports {symptom_safe.lower()}"]
        tags = [service_safe.split("-")[0][:24].lower(), "failure-mode"]
        confidence = "high" if impact == "high" else "medium"
        if not hint_safe:
            confidence = "medium" if impact in {"high", "medium"} else "low"
            complete = False

        mode_core = {
            "environment": env_safe,
            "impact": impact,
            "service": service_safe,
            "symptom": symptom_safe,
            "trigger": trigger_safe,
        }
        mode_hash = _sha256_hex(_canonical_json(mode_core).encode("utf-8"))[:12]
        slug = "".join(ch if ch.isalnum() else "-" for ch in service_safe.lower()).strip("-") or "service"
        failure_mode_id = f"fm-{slug[:30]}-{mode_hash}"
        failure_modes.append(
            {
                "failure_mode_id": failure_mode_id,
                "service": service_safe,
                "symptom": symptom_safe,
                "trigger": trigger_safe,
                "impact": impact,
                "environment": env_safe,
                "preconditions": preconditions[:3],
                "indicators": indicators[:3],
                "tags": [t for t in tags if t][:4],
                "confidence": confidence,
            }
        )

    status = "complete" if complete else "partial"
    notes = "Failure mode library normalized from incident observations."
    if status == "partial":
        notes = "Failure mode library generated with reduced confidence for observations missing timeline context."
    return {
        "incident_id": incident_safe,
        "failure_modes": failure_modes[:MAX_FAILURE_MODES],
        "library_status": status,
        "library_notes": _truncate_words(notes, 22),
    }


def build_blast_pattern_clusters(payload: dict[str, Any]) -> dict[str, Any]:
    incident_id = require(payload, "incident_id")
    failure_modes = require(payload, "failure_modes")
    dependency_hints = payload.get("dependency_hints", [])
    if not isinstance(incident_id, str) or not incident_id.strip():
        raise ValidationError("incident_id must be a non-empty string")
    if not isinstance(failure_modes, list) or not failure_modes:
        raise ValidationError("failure_modes must be a non-empty array")
    if len(failure_modes) > MAX_FAILURE_MODES:
        raise ValidationError(f"failure_modes must have at most {MAX_FAILURE_MODES} items")
    if dependency_hints is None:
        dependency_hints = []
    if not isinstance(dependency_hints, list) or not all(isinstance(h, str) for h in dependency_hints):
        raise ValidationError("dependency_hints must be an array of strings when provided")

    incident_safe = sanitize_untrusted_text(_truncate_words(incident_id.strip(), 12))[:120]
    grouped: dict[str, dict[str, Any]] = {}
    for raw in failure_modes[:MAX_FAILURE_MODES]:
        if not isinstance(raw, dict):
            raise ValidationError("each failure mode must be an object")
        fid = raw.get("failure_mode_id")
        service = raw.get("service")
        impact = raw.get("impact", "medium")
        conf = raw.get("confidence", "medium")
        if not isinstance(fid, str) or not fid.strip():
            raise ValidationError("each failure mode requires failure_mode_id")
        if not isinstance(service, str) or not service.strip():
            raise ValidationError("each failure mode requires service")
        if not isinstance(impact, str):
            raise ValidationError("impact must be a string")
        if not isinstance(conf, str):
            raise ValidationError("confidence must be a string")
        impact_s = impact.strip().lower()
        if impact_s not in ALLOWED_IMPACT:
            impact_s = "medium"
        conf_s = conf.strip().lower()
        if conf_s not in ALLOWED_CONFIDENCE:
            conf_s = "medium"
        key = sanitize_untrusted_text(service.strip())[:80].lower()
        bucket = grouped.setdefault(
            key,
            {"failure_mode_ids": [], "impact": impact_s, "confidence": conf_s, "services": set([key])},
        )
        bucket["failure_mode_ids"].append(sanitize_untrusted_text(fid.strip())[:120])
        if impact_s == "high":
            bucket["impact"] = "high"
        elif bucket["impact"] == "low" and impact_s == "medium":
            bucket["impact"] = "medium"
        if conf_s == "low":
            bucket["confidence"] = "low"
        elif conf_s == "high" and bucket["confidence"] == "medium":
            bucket["confidence"] = "high"

    hint_text = " ".join(dependency_hints).lower()
    clusters: list[dict[str, Any]] = []
    for service, info in grouped.items():
        fids = sorted(set(info["failure_mode_ids"]))
        services = sorted(set([service] + [s for s in grouped.keys() if s != service and s in hint_text]))
        blast = "localized"
        if len(services) >= 3:
            blast = "global"
        elif len(services) == 2:
            blast = "cross-system"
        elif info["impact"] == "high":
            blast = "tier"
        cluster_core = {"blast": blast, "fids": fids, "services": services}
        cluster_id = f"cluster-{_sha256_hex(_canonical_json(cluster_core).encode('utf-8'))[:12]}"
        rationale = f"Clustered by service overlap and impact level {info['impact']}."
        if dependency_hints:
            rationale = "Clustered using service overlap, impact, and dependency hints."
        clusters.append(
            {
                "cluster_id": cluster_id,
                "blast_pattern": blast,
                "failure_mode_ids": fids[:32],
                "services": services[:16],
                "rationale": sanitize_untrusted_text(_truncate_words(rationale, 18)),
                "confidence": info["confidence"],
            }
        )

    if not clusters:
        raise ValidationError("unable to derive clusters from failure_modes")
    return {
        "incident_id": incident_safe,
        "clusters": clusters[:MAX_CLUSTERS],
        "clustering_notes": "Clustered failure modes using service overlap and bounded impact inference.",
    }


def build_rollback_playbook(payload: dict[str, Any]) -> dict[str, Any]:
    incident_id = require(payload, "incident_id")
    clusters = require(payload, "clusters")
    if not isinstance(incident_id, str) or not incident_id.strip():
        raise ValidationError("incident_id must be a non-empty string")
    if not isinstance(clusters, list) or not clusters:
        raise ValidationError("clusters must be a non-empty array")
    incident_safe = sanitize_untrusted_text(_truncate_words(incident_id.strip(), 12))[:120]

    current_state = payload.get("current_state") or {}
    constraints = payload.get("rollback_constraints") or {}
    if not isinstance(current_state, dict):
        raise ValidationError("current_state must be an object when provided")
    if not isinstance(constraints, dict):
        raise ValidationError("rollback_constraints must be an object when provided")

    high_risk = False
    services: set[str] = set()
    for c in clusters[:MAX_CLUSTERS]:
        if not isinstance(c, dict):
            raise ValidationError("each cluster must be an object")
        cid = c.get("cluster_id")
        blast = c.get("blast_pattern")
        svc = c.get("services", [])
        if not isinstance(cid, str) or not cid.strip():
            raise ValidationError("each cluster requires cluster_id")
        if blast not in ALLOWED_BLAST:
            raise ValidationError("blast_pattern must be one of localized, tier, cross-system, global")
        if not isinstance(svc, list):
            raise ValidationError("cluster services must be an array")
        for s in svc:
            if isinstance(s, str) and s.strip():
                services.add(sanitize_untrusted_text(s.strip())[:80])
        if blast in {"cross-system", "global"}:
            high_risk = True

    requires_approval = bool(constraints.get("requires_approval"))
    backup_confirmed = bool(constraints.get("backup_confirmed", False))
    rollback_class = "standard"
    if high_risk:
        rollback_class = "elevated"
    if high_risk and (requires_approval or not backup_confirmed):
        rollback_class = "critical"

    steps = [
        {
            "step_id": "step-1",
            "action": "Freeze new deploys for affected services.",
            "owner": "release-manager",
            "success_criteria": "No rollout events observed for 5 minutes.",
        },
        {
            "step_id": "step-2",
            "action": "Rollback affected services to previous stable release.",
            "owner": "oncall-sre",
            "success_criteria": "Primary error rate trends to baseline.",
        },
    ]
    if services:
        service_label = ", ".join(sorted(services)[:4])
        steps[1]["action"] = f"Rollback {service_label} to previous stable release."
    if current_state.get("active_release"):
        rel = sanitize_untrusted_text(str(current_state["active_release"]).strip())[:80]
        steps.append(
            {
                "step_id": "step-3",
                "action": f"Verify rollback replaced release {rel}.",
                "owner": "incident-commander",
                "success_criteria": "Rollback version is confirmed in deployment records.",
            }
        )

    prereq = ["Incident commander assigned", "Rollback approval recorded", "Recovery backup verified"]
    abort_conditions = ["Data integrity checks fail during rollback execution"]
    if not backup_confirmed:
        abort_conditions.append("No verified backup snapshot exists for affected services")
    verification = ["Synthetic checks pass for impacted user flows", "Error rate remains below threshold for 10 minutes"]
    escalation = ["Escalate to service owner if rollback does not reduce error rate within 10 minutes"]

    core = {"incident_id": incident_safe, "rollback_class": rollback_class, "services": sorted(services)}
    playbook_id = f"rb-{incident_safe.lower().replace(' ', '-')[:40]}-{_sha256_hex(_canonical_json(core).encode('utf-8'))[:12]}"
    return {
        "incident_id": incident_safe,
        "playbook_id": playbook_id,
        "rollback_class": rollback_class,
        "steps": steps[:MAX_STEPS],
        "prerequisites": prereq[:6],
        "abort_conditions": abort_conditions[:6],
        "verification_checks": verification[:6],
        "escalation_points": escalation[:6],
        "playbook_notes": "Generated rollback playbook from clustered failure blast patterns and safety constraints.",
    }
