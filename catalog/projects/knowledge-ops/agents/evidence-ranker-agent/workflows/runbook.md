1. Validate required fields: `assertions`, `evidence_items`.
2. Normalize each evidence item and compute a bounded score.
3. Sort descending by score and truncate to `max_evidence`.
4. Emit ranked evidence plus aggregate confidence.
5. If validation fails, return explicit field-level error.
