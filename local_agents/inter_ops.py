"""Deterministic builders for inter-ops agents."""

from __future__ import annotations

from typing import Any

from .core import ValidationError, require, sanitize_untrusted_text

ALLOWED_MODES = frozenset({"backward", "forward", "full"})
ALLOWED_TYPES = frozenset({"string", "number", "integer", "boolean", "object", "array"})


def _normalize_schema(schema: Any, label: str) -> tuple[dict[str, str], set[str]]:
    if not isinstance(schema, dict):
        raise ValidationError(f"{label} must be an object")
    props = schema.get("properties")
    req = schema.get("required", [])
    if not isinstance(props, dict):
        raise ValidationError(f"{label}.properties must be an object")
    if req is None:
        req = []
    if not isinstance(req, list) or not all(isinstance(x, str) for x in req):
        raise ValidationError(f"{label}.required must be an array of strings")

    out_props: dict[str, str] = {}
    for field, spec in props.items():
        if not isinstance(field, str) or not field.strip():
            raise ValidationError(f"{label}.properties keys must be non-empty strings")
        if not isinstance(spec, dict):
            raise ValidationError(f"{label}.properties[{field}] must be an object")
        t = spec.get("type")
        if not isinstance(t, str) or not t.strip():
            raise ValidationError(f"{label}.properties[{field}].type must be a non-empty string")
        t_low = t.strip().lower()
        if t_low not in ALLOWED_TYPES:
            raise ValidationError(f"{label}.properties[{field}].type unsupported: {t_low}")
        out_props[sanitize_untrusted_text(field.strip())[:80]] = t_low
    return out_props, {sanitize_untrusted_text(x.strip())[:80] for x in req if x.strip()}


def validate_schema_compat(payload: dict[str, Any]) -> dict[str, Any]:
    contract_name = require(payload, "contract_name")
    producer_schema = require(payload, "producer_schema")
    consumer_schema = require(payload, "consumer_schema")
    compat_mode = payload.get("compat_mode", "backward")

    if not isinstance(contract_name, str) or not contract_name.strip():
        raise ValidationError("contract_name must be a non-empty string")
    if not isinstance(compat_mode, str) or compat_mode.strip().lower() not in ALLOWED_MODES:
        raise ValidationError("compat_mode must be one of backward, forward, full")
    mode = compat_mode.strip().lower()

    p_props, p_req = _normalize_schema(producer_schema, "producer_schema")
    c_props, c_req = _normalize_schema(consumer_schema, "consumer_schema")

    breaking: list[str] = []
    non_breaking: list[str] = []
    actions: list[str] = []

    all_fields = sorted(set(p_props.keys()) | set(c_props.keys()))
    for field in all_fields:
        in_p = field in p_props
        in_c = field in c_props
        if in_p and not in_c:
            msg = f"consumer missing producer field: {field}"
            if mode in {"backward", "full"}:
                breaking.append(msg)
            else:
                non_breaking.append(msg)
            continue
        if in_c and not in_p:
            msg = f"consumer optional field added: {field}"
            if field in c_req and mode in {"forward", "full"}:
                breaking.append(f"consumer requires new field absent in producer: {field}")
            else:
                non_breaking.append(msg)
            continue

        p_type = p_props[field]
        c_type = c_props[field]
        if p_type != c_type:
            breaking.append(f"type mismatch for {field}: producer {p_type}, consumer {c_type}")
        elif field in p_req and field not in c_req:
            non_breaking.append(f"consumer relaxed required field: {field}")
        elif field not in p_req and field in c_req and mode in {"forward", "full"}:
            breaking.append(f"consumer made optional field required: {field}")

    if breaking:
        status = "incompatible"
        actions.append("Coordinate contract migration and preserve required producer fields.")
        actions.append("Add compatibility tests for each breaking field before release.")
    elif non_breaking:
        status = "compatible_with_warnings"
        actions.append("Document non-breaking schema deltas for consumers.")
        actions.append("Add fixture coverage for both old and new payload variants.")
    else:
        status = "compatible"
        actions.append("No schema migration needed for current mode.")

    notes = f"Validated producer/consumer fields with mode {mode} using payload snapshots only."
    return {
        "contract_name": sanitize_untrusted_text(" ".join(contract_name.strip().split()[:10]))[:120],
        "compatibility_status": status,
        "breaking_changes": [sanitize_untrusted_text(" ".join(x.split()[:14])) for x in breaking[:8]],
        "non_breaking_changes": [sanitize_untrusted_text(" ".join(x.split()[:14])) for x in non_breaking[:8]],
        "recommended_actions": [sanitize_untrusted_text(" ".join(x.split()[:14])) for x in actions[:6]],
        "validation_notes": sanitize_untrusted_text(" ".join(notes.split()[:20])),
    }
