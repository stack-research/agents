"""Deterministic builders for artifact-ops: inventory, manifest, bundle seal."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .core import ValidationError, require, sanitize_untrusted_text

ALLOWED_ROLES = frozenset({"input", "output", "intermediate"})
MAX_ARTIFACTS = 64
MAX_INLINE_TEXT = 4096
MAX_LINEAGE_RECORDS = 16
SHA256_HEX = re.compile(r"^[a-f0-9]{64}$")
MANIFEST_VERSION = "1.0"


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_artifact_inventory(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = require(payload, "run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValidationError("run_id must be a non-empty string")
    run_id_safe = sanitize_untrusted_text(run_id.strip())[:120]

    artifacts = require(payload, "artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValidationError("artifacts must be a non-empty array")
    if len(artifacts) > MAX_ARTIFACTS:
        raise ValidationError(f"artifacts must have at most {MAX_ARTIFACTS} items")

    out_artifacts: list[dict[str, Any]] = []
    complete = True
    for raw in artifacts:
        if not isinstance(raw, dict):
            raise ValidationError("each artifact must be an object")
        logical_path = raw.get("logical_path", "")
        if not isinstance(logical_path, str) or not logical_path.strip():
            raise ValidationError("each artifact requires a non-empty logical_path")
        role = raw.get("role", "")
        if role not in ALLOWED_ROLES:
            raise ValidationError("artifact role must be one of: input, output, intermediate")

        path_safe = sanitize_untrusted_text(logical_path.strip())[:260]
        digest: str | None = None
        if raw.get("content_sha256") is not None:
            cs = raw["content_sha256"]
            if not isinstance(cs, str) or not SHA256_HEX.match(cs.strip().lower()):
                raise ValidationError("content_sha256 must be a 64-character lowercase hex string")
            digest = cs.strip().lower()
        elif raw.get("inline_text") is not None:
            it = raw["inline_text"]
            if not isinstance(it, str):
                raise ValidationError("inline_text must be a string")
            text_safe = sanitize_untrusted_text(it)[:MAX_INLINE_TEXT]
            digest = _sha256_hex(text_safe.encode("utf-8"))
        else:
            complete = False
            digest = ""

        entry_for_id = _canonical_json({"content_sha256": digest, "logical_path": path_safe, "role": role})
        aid_hash = _sha256_hex(entry_for_id.encode("utf-8"))[:12]
        slug = "".join(ch if ch.isalnum() else "-" for ch in path_safe.lower())[:24].strip("-") or "art"
        artifact_id = f"{slug}-{aid_hash}"

        out_artifacts.append(
            {
                "artifact_id": artifact_id,
                "logical_path": path_safe,
                "role": role,
                "content_sha256": digest or "",
            }
        )

    status = "complete" if complete else "partial"
    if complete:
        inventory_notes = " ".join(
            "Inventory normalized every artifact has a content digest suitable for bundle-manifest-agent.".split()[:24]
        )
    else:
        inventory_notes = " ".join(
            "Partial inventory some artifacts lack content_sha256 or inline_text seal with gaps or add digests.".split()[:24]
        )

    return {
        "run_id": run_id_safe,
        "inventory_status": status,
        "artifacts": out_artifacts,
        "inventory_notes": inventory_notes,
    }


def build_bundle_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = require(payload, "run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValidationError("run_id must be a non-empty string")
    run_id_safe = sanitize_untrusted_text(run_id.strip())[:120]

    inv = payload.get("inventory")
    if inv is not None:
        if not isinstance(inv, dict):
            raise ValidationError("inventory must be an object")
        arts = inv.get("artifacts")
        if not isinstance(arts, list) or not arts:
            raise ValidationError("inventory.artifacts must be a non-empty array")
        normalized: list[dict[str, Any]] = []
        for a in arts:
            if not isinstance(a, dict):
                raise ValidationError("inventory artifact must be an object")
            aid = a.get("artifact_id", "")
            lp = a.get("logical_path", "")
            role = a.get("role", "")
            digest = a.get("content_sha256", "")
            if not isinstance(aid, str) or not aid.strip():
                raise ValidationError("each inventory artifact needs artifact_id")
            if not isinstance(lp, str) or not lp.strip():
                raise ValidationError("each inventory artifact needs logical_path")
            if role not in ALLOWED_ROLES:
                raise ValidationError("inventory artifact role must be input, output, or intermediate")
            if not isinstance(digest, str):
                raise ValidationError("content_sha256 must be a string when present")
            digest_s = digest.strip().lower()
            if digest_s and not SHA256_HEX.match(digest_s):
                raise ValidationError("content_sha256 must be empty or 64 hex characters")
            normalized.append(
                {
                    "artifact_id": aid.strip()[:200],
                    "logical_path": sanitize_untrusted_text(lp.strip())[:260],
                    "role": role,
                    "content_sha256": digest_s,
                }
            )
    else:
        inv_out = build_artifact_inventory({"run_id": run_id_safe, "artifacts": require(payload, "artifacts")})
        normalized = inv_out["artifacts"]

    normalized.sort(key=lambda x: x["artifact_id"])

    entries: list[dict[str, Any]] = []
    for item in normalized:
        entry_core = {
            "artifact_id": item["artifact_id"],
            "content_sha256": item["content_sha256"],
            "logical_path": item["logical_path"],
            "role": item["role"],
        }
        manifest_entry_sha256 = _sha256_hex(_canonical_json(entry_core).encode("utf-8"))
        entries.append({**item, "manifest_entry_sha256": manifest_entry_sha256})

    root_payload = {
        "entry_hashes": [e["manifest_entry_sha256"] for e in entries],
        "manifest_version": MANIFEST_VERSION,
        "run_id": run_id_safe,
    }
    bundle_root_sha256 = _sha256_hex(_canonical_json(root_payload).encode("utf-8"))

    reproducibility_notes = " ".join(
        (
            "Ordering policy entries sorted by artifact_id ascending.",
            "bundle_root_sha256 covers manifest_version run_id and ordered manifest_entry_sha256 values only no timestamps.",
        )
    )
    reproducibility_notes = " ".join(reproducibility_notes.split()[:36])

    return {
        "bundle_root_sha256": bundle_root_sha256,
        "entries": entries,
        "manifest_version": MANIFEST_VERSION,
        "reproducibility_notes": reproducibility_notes,
        "run_id": run_id_safe,
    }


def seal_repro_bundle(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = require(payload, "run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValidationError("run_id must be a non-empty string")
    run_id_safe = sanitize_untrusted_text(run_id.strip())[:120]

    root = require(payload, "bundle_root_sha256")
    if not isinstance(root, str) or not SHA256_HEX.match(root.strip().lower()):
        raise ValidationError("bundle_root_sha256 must be a 64-character lowercase hex string")
    root_safe = root.strip().lower()

    manifest_summary = payload.get("manifest_summary", "")
    if manifest_summary is not None and not isinstance(manifest_summary, str):
        raise ValidationError("manifest_summary must be a string when provided")
    summary_safe = sanitize_untrusted_text((manifest_summary or "").strip())[:400]

    toolchain = payload.get("toolchain_fingerprint", "")
    if toolchain is not None and not isinstance(toolchain, str):
        raise ValidationError("toolchain_fingerprint must be a string when provided")
    tool_safe = sanitize_untrusted_text((toolchain or "").strip())[:200]

    lineage_records = payload.get("lineage_records") or []
    if not isinstance(lineage_records, list):
        raise ValidationError("lineage_records must be an array when provided")
    lineage_records = lineage_records[:MAX_LINEAGE_RECORDS]

    lineage_attachment: list[dict[str, Any]] = []
    has_lineage = bool(lineage_records)
    all_lineage_ids = True
    if not has_lineage:
        all_lineage_ids = False
    for rec in lineage_records:
        if not isinstance(rec, dict):
            all_lineage_ids = False
            continue
        lid = rec.get("lineage_id", "")
        if isinstance(lid, str) and lid.strip():
            lid_safe = sanitize_untrusted_text(lid.strip())[:120]
        else:
            all_lineage_ids = False
            lid_safe = ""
        attachment_digest = _sha256_hex(_canonical_json(rec).encode("utf-8"))[:16]
        lineage_attachment.append(
            {
                "attachment_digest": attachment_digest,
                "lineage_id": lid_safe or "unknown",
            }
        )

    seal_status = "sealed" if has_lineage and all_lineage_ids else "sealed_with_gaps"

    bundle_core = _canonical_json({"bundle_root_sha256": root_safe, "run_id": run_id_safe})
    bundle_suffix = _sha256_hex(bundle_core.encode("utf-8"))[:12]
    slug = "".join(ch if ch.isalnum() else "-" for ch in run_id_safe.lower())[:20].strip("-") or "run"
    bundle_id = f"{slug}-bundle-{bundle_suffix}"

    verification_checklist = [
        "Rebuild artifact inventory and confirm artifact_id stability",
        "Recompute each manifest_entry_sha256 from canonical entry fields",
        "Recompute bundle_root_sha256 from manifest_version run_id and ordered entry hashes",
        "Verify each file matches content_sha256 out of band",
        "Compare lineage_attachment digests to source lineage records",
    ]
    if tool_safe:
        verification_checklist.append("Record toolchain_fingerprint alongside bundle for environment parity")

    seal_notes = " ".join(
        (
            f"Seal status {seal_status} for run {run_id_safe}.",
            summary_safe[:120] if summary_safe else "No manifest_summary provided.",
        )
    )
    seal_notes = " ".join(seal_notes.split()[:32])

    return {
        "bundle_id": bundle_id,
        "bundle_root_sha256": root_safe,
        "lineage_attachment": lineage_attachment[:MAX_LINEAGE_RECORDS],
        "manifest_summary": summary_safe,
        "run_id": run_id_safe,
        "seal_notes": seal_notes,
        "seal_status": seal_status,
        "toolchain_fingerprint": tool_safe,
        "verification_checklist": verification_checklist[:6],
    }
