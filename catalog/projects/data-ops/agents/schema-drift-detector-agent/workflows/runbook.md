# schema-drift-detector-agent runbook

1. Validate schema_before and schema_after are non-empty objects.
2. Compare keys between both schemas.
3. Identify additions, removals, and type changes.
4. Score drift severity based on breaking change count.
5. Generate recommended actions for detected drift.
6. Return JSON contract exactly.
