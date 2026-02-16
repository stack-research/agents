# Policy Pack

The policy pack captures environment-specific OWASP ASI control baselines.

Current file:

- `policy/asi-control-baselines.json`

## Purpose

Use this file as a governance baseline for:

- expected ASI controls by environment (`dev`, `staging`, `prod`)
- change-control strictness and approval posture
- production guardrails that differ from lower environments

## Structure

Top-level fields:

- `policy_pack`: identifier for this policy set
- `version`: policy version tag
- `description`: short policy summary
- `environments`: per-environment control blocks

Each environment contains:

- `change_control`: `relaxed`, `moderate`, or `strict`
- `human_approval_required`: boolean
- `llm_mode_allowed`: boolean
- `asi_controls`: control requirements for `ASI01` through `ASI10`

Each ASI control entry contains:

- `baseline`: expected enforcement level (`required`)
- `controls`: concrete control list to implement and test

## Update Guidance

When updating policy baseline controls:

1. Increment `version` in `policy/asi-control-baselines.json`.
2. Keep all environments and all ASI keys (`ASI01`..`ASI10`) present.
3. Add or adjust related tests before changing runtime behavior.
4. Reflect meaningful policy changes in `README.md` and `AGENTS.md`.
