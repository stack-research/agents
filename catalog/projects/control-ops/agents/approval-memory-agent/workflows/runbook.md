1. Validate subject, approver, and date fields.
2. Parse approved_at and expires_at as ISO dates.
3. Compute active/expired state from current date.
4. Generate deterministic approval record identifier.
5. Emit concise recall hint for follow-up governance checks.
