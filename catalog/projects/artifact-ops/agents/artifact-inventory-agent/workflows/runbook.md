# Runbook: artifact-inventory-agent

## Steps

1. Validate `run_id` and non-empty `artifacts` array (max 64 items).
2. For each artifact, sanitize `logical_path`, validate `role`, compute or validate `content_sha256`.
3. Emit stable `artifact_id` per artifact and set `inventory_status`.

## Failure handling

- Missing `logical_path` or invalid `role`: validation error; do not guess paths.
- Invalid `content_sha256` format: validation error.
- Missing digest and no `inline_text`: allowed; marks `inventory_status` partial.
