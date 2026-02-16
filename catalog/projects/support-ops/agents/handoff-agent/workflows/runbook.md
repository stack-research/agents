# Runbook

## Input Contract

```json
{
  "shift_label": "night-shift-2026-02-16",
  "incidents": [
    {"id": "inc-1", "severity": "sev1", "status": "mitigating", "owner": "oncall-a", "next_step": "verify rollback"},
    {"id": "inc-2", "severity": "sev3", "status": "monitoring", "owner": "oncall-b", "next_step": "watch error budget"}
  ],
  "handoff_window": "next 8 hours"
}
```

## Steps

1. Validate shift label and incident payload shape.
2. Count unresolved incidents.
3. Select sev1/sev2 unresolved items as critical handoff items.
4. Draft concise handoff brief.
5. Emit exactly three recommended checks.
6. Return strict output JSON.

## Failure Modes

- Missing required fields: return validation error.
- Invalid severity or status: return validation error.
- Non-object incident entries: return validation error.
