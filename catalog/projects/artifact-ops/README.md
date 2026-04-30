# artifact-ops

Run reproducibility packaging: normalize run artifacts (inputs, outputs, intermediates), build a canonical manifest with aggregate checksum, and seal a bundle descriptor with lineage references and verification steps.

## Agents

1. **`artifact-inventory-agent`** — Normalizes `artifacts[]` with roles and stable `artifact_id` values; derives `content_sha256` from `inline_text` or accepts caller-supplied digests.
2. **`bundle-manifest-agent`** — Emits sorted manifest `entries`, per-entry `manifest_entry_sha256`, and `bundle_root_sha256` (no filesystem access; digests are supplied in payload).
3. **`bundle-seal-agent`** — Produces `bundle_id`, `seal_status`, `lineage_attachment`, and `verification_checklist` from a root hash plus optional lineage records.

## Local commands

Deterministic:

```bash
python3 scripts/run_agent.py --agent artifact-ops.artifact-inventory-agent \
  --input catalog/projects/artifact-ops/agents/artifact-inventory-agent/examples/example-input.json --pretty
python3 scripts/run_agent.py --agent artifact-ops.bundle-manifest-agent \
  --input catalog/projects/artifact-ops/agents/bundle-manifest-agent/examples/example-input.json --pretty
python3 scripts/run_agent.py --agent artifact-ops.bundle-seal-agent \
  --input catalog/projects/artifact-ops/agents/bundle-seal-agent/examples/example-input.json --pretty
```

LLM mode:

```bash
AGENT_MODE=llm python3 scripts/run_agent.py --agent artifact-ops.artifact-inventory-agent \
  --input catalog/projects/artifact-ops/agents/artifact-inventory-agent/examples/example-input.json --pretty
```

Tests:

```bash
python3 -m unittest tests.test_artifact_ops tests.test_artifact_ops_llm -v
```
