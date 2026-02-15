# Runbook

## Input Contract

Expected input payload:

```json
{
  "text": "I was charged twice this month and need a refund.",
  "labels": ["bug-report", "billing", "feature-request", "support", "feedback", "unknown"]
}
```

## Steps

1. Validate that `text` is non-empty.
2. Load labels from input or fallback defaults.
3. Infer dominant intent from the text.
4. Select one label.
5. Assign confidence in `[0,1]`.
6. Generate short rationale.
7. Emit JSON output.

## Failure Modes

- Empty text: return validation error.
- Missing labels and no defaults: return configuration error.
- No suitable intent: use `unknown` when available.
