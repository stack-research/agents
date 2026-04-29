## Projects To Revisit First

Add or update the project selected. Then update the roadmap checklist when finished. If you see or think of anything to add, add it to the list(s) below. Otherwise report back and wait for further instructions.

- [x] `research-ops`
  - Add `source-planner-agent` (plans what evidence to fetch next, not just synthesize what is present).
  - Add `gap-detector-agent` (finds missing proof for current assertions).
  - Tooling: reusable “evidence contract” shared with `knowledge-ops`.

- [x] `workflow-ops`
  - Add `retry-policy-agent` (decides retry/backoff/escalation for failed stages).
  - Add `dependency-router-agent` (routes based on prerequisites, not only intent text).
  - Tooling: standard stage timing + failure taxonomy fields.

- [x] `control-ops`
  - Add `exception-policy-agent` (handles controlled policy exceptions with expiry and owner).
  - Add `approval-memory-agent` (tracks what was approved, by whom, and when it expires).
  - Tooling: stronger “why blocked” structured output for downstream automation.

- [ ] `observability-ops`
  - Add `change-correlation-agent` (maps metric/log shifts to deploy/config events).
  - Add `alert-tuner-agent` (suggests threshold tuning from noise patterns).
  - Tooling: shared incident signal schema consumable by pipelines.

- [ ] `agent-incident-drill` (scenario project)
  - Add alternate drills (data corruption, auth lockout, supply-chain compromise).
  - Tooling: benchmark scorecard deltas across drill runs.

---

## New Catalog Project Ideas

- [ ] `eval-ops`
  - Agents for benchmark curation, regression scoring, and drift-over-time quality reports.

- [ ] `experiment-ops`
  - Agents for hypothesis registration, experiment plan generation, and result adjudication.

- [ ] `artifact-ops`
  - Agents to package run artifacts into reproducible bundles (inputs, outputs, lineage, checksums).

- [ ] `interop-ops`
  - Agents for cross-repo contract validation (schema compatibility, version negotiation, migration hints).

- [ ] `cost-ops`
  - Agents for token/runtime cost attribution, budget guardrails, and per-pipeline optimization suggestions.

- [ ] `failure-ops`
  - Agents focused on failure mode libraries, blast-pattern clustering, and rollback playbook generation.
