# Runbook: bundle-seal-agent

## Steps

1. Validate `bundle_root_sha256` as 64 hex characters.
2. Normalize optional lineage records into `lineage_attachment` with digests.
3. Emit `bundle_id`, `seal_status`, and `verification_checklist`.

## Failure handling

- Invalid root hash: validation error.
- Missing lineage: allowed; `seal_status` becomes `sealed_with_gaps`.
