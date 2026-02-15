# Runbook

## Input Contract

```json
{
  "target_path": "."
}
```

## Steps

1. Resolve `target_path` to repository root.
2. Enumerate all agents under `catalog/projects/*/agents/*`.
3. Run control checks for prompt contracts, required files, and local security artifacts.
4. Build findings list with ASI mapping.
5. Compute normalized risk score.
6. Emit JSON output.

## Failure Modes

- Invalid path: return validation error.
- Missing catalog folder: return validation error.
