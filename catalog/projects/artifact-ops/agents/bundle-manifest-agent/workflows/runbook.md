# Runbook: bundle-manifest-agent

## Steps

1. Validate `run_id` and resolve artifact list from `inventory` or by running inventory rules on `artifacts`.
2. Sort artifacts by `artifact_id` ascending.
3. Compute `manifest_entry_sha256` per entry then `bundle_root_sha256` over ordered hashes plus manifest metadata.

## Failure handling

- Empty inventory or invalid artifact rows: validation error upstream.
- Conflicting `run_id` between payload and inventory: prefer explicit payload `run_id` after sanitization.
