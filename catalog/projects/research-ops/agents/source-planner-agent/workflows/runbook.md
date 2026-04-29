1. Validate `query` and optional `current_evidence`, `budget_limit`.
2. Score existing evidence coverage and identify weak areas.
3. Generate bounded fetch plan steps with source priorities.
4. Emit `coverage_target` as a numeric threshold.
5. Return validation error for malformed evidence items.
