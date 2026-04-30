# Agent Catalog

This repository is a growing catalog of reusable AI agents organized by project.

## Goals

- Keep each agent self-contained and easy to run.
- Reuse project-level patterns so new agents are quick to add.
- Document every agent clearly as the catalog scales.

## Repository Structure

- `AGENTS.md` - contribution and catalog conventions (slim); full agent/project index lives in **`catalog/README.md`**.
- `.agents/` - Agent Skills (project scope); see **[`.agents/README.md`](.agents/README.md)** (skills under **`.agents/skills/`**, per [Where to scan](https://agentskills.io/client-implementation/adding-skills-support#where-to-scan)).
- `catalog/` - all projects and their agents; open **[`catalog/README.md`](catalog/README.md)** for the canonical catalog index.
- `docs/` - cross-cutting architecture and standards.

```text
catalog/
  projects/
    <project>/
      README.md
      agents/
        <agent>/
          agent.yaml
          prompts/
          workflows/
          examples/
          tests/
```

## Current Projects

1. `starter-kit`
   - `heartbeat-agent`: simple status summarizer and health signal formatter.
   - `classifier-agent`: classifies text into one intent label with confidence.
2. `support-ops`
   - `triage-agent`: converts inbound support text into priority/category/next-action.
   - `reply-drafter-agent`: drafts concise customer reply subject/body from structured triage fields.
   - `summary-agent`: summarizes weekly support ticket trends and follow-up actions.
   - `handoff-agent`: generates shift-transition briefs from active incidents.
3. `security-ops`
   - `agentic-security-scanner-agent`: scans repo controls and maps findings to OWASP ASI categories.
4. `planner-executor`
   - `planner-agent`: converts a goal and constraints into a bounded execution plan.
   - `executor-agent`: summarizes progress and completion state from plan steps.
5. `research-ops`
   - `source-planner-agent`: plans what evidence to collect next from a research question.
   - `retrieval-agent`: extracts bounded notes from query + source hints.
   - `gap-detector-agent`: detects unsupported assertions and collection gaps.
   - `synthesis-agent`: converts notes into audience-aware summary and actions.
6. `knowledge-ops`
   - `evidence-ranker-agent`: scores and ranks candidate evidence for downstream use.
   - `claim-trace-agent`: maps assertions to evidence references and support states.
   - `memory-curator-agent`: distills run artifacts into reusable memory entries.
   - `temporal-watch-agent`: compares snapshots over time and emits drift signals.
7. `qa-ops`
   - `test-case-generator-agent`: generates bounded QA scenarios from feature requirements.
   - `regression-triage-agent`: classifies regression cause/severity and proposes follow-up actions.
8. `workflow-ops`
   - `router-agent`: routes work items to the best-fit agent with a priority.
   - `dependency-router-agent`: routes work only when prerequisites are satisfied.
   - `retry-policy-agent`: decides retry/backoff/escalation policy for failed stages.
   - `checkpoint-agent`: records workflow stage/status checkpoints for traceability.
9. `control-ops`
   - `lineage-recorder-agent`: structures decision events into append-only lineage records.
   - `scope-validator-agent`: validates proposed actions against governance requirements with pass/review/fail gating.
   - `exception-policy-agent`: evaluates controlled policy exceptions with explicit owner and expiry.
   - `approval-memory-agent`: tracks approval state and expiration for governance recall.
   - `blast-radius-assessor-agent`: estimates blast radius from weighted permission, dependency, and resource-limit factors.
   - `kill-path-auditor-agent`: audits shutdown capabilities against the four-level kill path spectrum and optional ISO `last_tested` recency.
10. `data-ops`
   - `schema-drift-detector-agent`: detects schema changes between versions and classifies drift severity.
   - `data-validator-agent`: validates data records against rules and reports violations.
11. `code-ops`
    - `code-reviewer-agent`: reviews code diffs for security, correctness, and style issues.
    - `pr-summary-agent`: summarizes PR changes for reviewers with risk assessment.
12. `observability-ops`
    - `log-analyzer-agent`: analyzes log entries for patterns and anomalies.
    - `slo-reporter-agent`: generates SLO compliance reports from service metrics and targets.
    - `change-correlation-agent`: correlates incident signal shifts with nearby deploy/config events.
    - `alert-tuner-agent`: suggests alert threshold tuning from historical noise patterns.
13. `eval-ops`
    - `benchmark-curator-agent`: deduplicates eval cases and surfaces benchmark coverage gaps.
    - `regression-score-agent`: compares baseline vs current eval metrics for regressions.
    - `quality-drift-reporter-agent`: summarizes quality trend and drift across time windows.
14. `experiment-ops`
    - `hypothesis-registration-agent`: registers and normalizes hypotheses with clarity checks.
    - `experiment-plan-agent`: generates bounded experiment plans from a hypothesis.
    - `result-adjudication-agent`: maps observed metrics to supports, inconclusive, or refutes verdicts.
15. `agent-incident-drill`
    - Scenario project that composes existing catalog agents into a measurable incident-response drill with governance, lineage, blast-radius, kill-path, rollback, and scorecard artifacts.

## Run Agents Locally

- `python3 scripts/run_agent.py --agent starter-kit.heartbeat-agent --input catalog/projects/starter-kit/agents/heartbeat-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent starter-kit.classifier-agent --input catalog/projects/starter-kit/agents/classifier-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent support-ops.triage-agent --input catalog/projects/support-ops/agents/triage-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent support-ops.reply-drafter-agent --input catalog/projects/support-ops/agents/reply-drafter-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent support-ops.summary-agent --input catalog/projects/support-ops/agents/summary-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent support-ops.handoff-agent --input catalog/projects/support-ops/agents/handoff-agent/examples/example-input.json --pretty`
- `python3 scripts/run_support_pipeline.py --input catalog/projects/support-ops/examples/pipeline-input.json --pretty`
- `python3 scripts/run_agent.py --agent planner-executor.planner-agent --input catalog/projects/planner-executor/agents/planner-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent planner-executor.executor-agent --input catalog/projects/planner-executor/agents/executor-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent research-ops.source-planner-agent --input catalog/projects/research-ops/agents/source-planner-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent research-ops.retrieval-agent --input catalog/projects/research-ops/agents/retrieval-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent research-ops.gap-detector-agent --input catalog/projects/research-ops/agents/gap-detector-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent research-ops.synthesis-agent --input catalog/projects/research-ops/agents/synthesis-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent knowledge-ops.evidence-ranker-agent --input catalog/projects/knowledge-ops/agents/evidence-ranker-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent knowledge-ops.claim-trace-agent --input catalog/projects/knowledge-ops/agents/claim-trace-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent knowledge-ops.memory-curator-agent --input catalog/projects/knowledge-ops/agents/memory-curator-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent knowledge-ops.temporal-watch-agent --input catalog/projects/knowledge-ops/agents/temporal-watch-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent qa-ops.test-case-generator-agent --input catalog/projects/qa-ops/agents/test-case-generator-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent qa-ops.regression-triage-agent --input catalog/projects/qa-ops/agents/regression-triage-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent eval-ops.benchmark-curator-agent --input catalog/projects/eval-ops/agents/benchmark-curator-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent eval-ops.regression-score-agent --input catalog/projects/eval-ops/agents/regression-score-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent eval-ops.quality-drift-reporter-agent --input catalog/projects/eval-ops/agents/quality-drift-reporter-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent experiment-ops.hypothesis-registration-agent --input catalog/projects/experiment-ops/agents/hypothesis-registration-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent experiment-ops.experiment-plan-agent --input catalog/projects/experiment-ops/agents/experiment-plan-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent experiment-ops.result-adjudication-agent --input catalog/projects/experiment-ops/agents/result-adjudication-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent workflow-ops.router-agent --input catalog/projects/workflow-ops/agents/router-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent workflow-ops.dependency-router-agent --input catalog/projects/workflow-ops/agents/dependency-router-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent workflow-ops.retry-policy-agent --input catalog/projects/workflow-ops/agents/retry-policy-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent workflow-ops.checkpoint-agent --input catalog/projects/workflow-ops/agents/checkpoint-agent/examples/example-input.json --pretty`
- `python3 scripts/run_planner_executor_pipeline.py --input catalog/projects/planner-executor/examples/pipeline-input.json --pretty`
- `python3 scripts/run_workflow_pipeline.py --input catalog/projects/workflow-ops/examples/pipeline-input.json --pretty`
- `python3 scripts/run_agent.py --agent control-ops.lineage-recorder-agent --input catalog/projects/control-ops/agents/lineage-recorder-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent control-ops.scope-validator-agent --input catalog/projects/control-ops/agents/scope-validator-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent control-ops.exception-policy-agent --input catalog/projects/control-ops/agents/exception-policy-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent control-ops.approval-memory-agent --input catalog/projects/control-ops/agents/approval-memory-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent control-ops.blast-radius-assessor-agent --input catalog/projects/control-ops/agents/blast-radius-assessor-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent control-ops.kill-path-auditor-agent --input catalog/projects/control-ops/agents/kill-path-auditor-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent data-ops.schema-drift-detector-agent --input catalog/projects/data-ops/agents/schema-drift-detector-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent data-ops.data-validator-agent --input catalog/projects/data-ops/agents/data-validator-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent code-ops.code-reviewer-agent --input catalog/projects/code-ops/agents/code-reviewer-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent code-ops.pr-summary-agent --input catalog/projects/code-ops/agents/pr-summary-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent observability-ops.log-analyzer-agent --input catalog/projects/observability-ops/agents/log-analyzer-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent observability-ops.slo-reporter-agent --input catalog/projects/observability-ops/agents/slo-reporter-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent observability-ops.change-correlation-agent --input catalog/projects/observability-ops/agents/change-correlation-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent observability-ops.alert-tuner-agent --input catalog/projects/observability-ops/agents/alert-tuner-agent/examples/example-input.json --pretty`
- `python3 scripts/run_governance_pipeline.py --input catalog/projects/control-ops/examples/governance-pipeline-input.json --pretty`
- `python3 scripts/run_resilience_pipeline.py --input catalog/projects/control-ops/examples/resilience-pipeline-input.json --pretty`
- `python3 scripts/run_incident_pipeline.py --input examples/incident-pipeline-input.json --pretty`
- `python3 scripts/run_agent_incident_drill.py --input catalog/projects/agent-incident-drill/examples/drill-input.json --pretty`
- `make compare-agent-incident-drill-scorecards-example` (diff scorecards from two drill runs)
- `python3 scripts/run_security_scan.py --target-path . --pretty`
- `python3 scripts/run_security_scan.py --target-path /path/to/other/catalog --rules custom-rules.json --pretty`
- `AGENT_MODE=llm python3 scripts/run_support_pipeline.py --input catalog/projects/support-ops/examples/pipeline-input.json --pretty`
- `make state-up` to start Redis for pipeline state persistence
- `make llm-up && make llm-pull` for a speed-first local model (`llama3.2:3b`)

See `/Users/macos-user/.projects/stack-research/agents/docs/local-usage.md` for full usage.

## End-to-End Story: Incident Day Walkthrough

A new engineer joins the on-call rotation. Mid-morning, support reports that some customers cannot log in after a release. Instead of jumping between tools and ad-hoc notes, the engineer uses the catalog as a structured agentic workflow.

The engineer starts by routing the task, then triaging the issue, generating QA scenarios, triaging an observed regression failure, producing a stakeholder-ready summary, and recording a checkpoint. The point is not replacing engineering judgment. The point is making the system legible, repeatable, and fast under pressure.

### 1) Route the incoming task

```bash
python3 scripts/run_agent.py \
  --agent workflow-ops.router-agent \
  --input catalog/projects/workflow-ops/agents/router-agent/examples/example-input.json \
  --pretty
```

Example output:

```json
{
  "priority": "p2",
  "rationale": "Support issue intent detected; route to triage.",
  "target_agent": "support-ops.triage-agent"
}
```

### 2) Triage the support issue

```bash
python3 scripts/run_agent.py \
  --agent support-ops.triage-agent \
  --input catalog/projects/support-ops/agents/triage-agent/examples/example-input.json \
  --pretty
```

Example output:

```json
{
  "category": "access",
  "next_action": "Escalate to auth on-call and collect user and timestamp details.",
  "priority": "p2"
}
```

### 3) Generate QA coverage for the suspected area

```bash
python3 scripts/run_agent.py \
  --agent qa-ops.test-case-generator-agent \
  --input catalog/projects/qa-ops/agents/test-case-generator-agent/examples/example-input.json \
  --pretty
```

Example output:

```json
{
  "risk_focus": "medium",
  "test_cases": [
    "Happy path: validate SSO login flow with Users can sign in with SAML",
    "Validation edge: reject invalid input for SSO login flow",
    "Boundary check: enforce limits and defaults for SSO login flow",
    "Failure path: verify clear error handling for SSO login flow",
    "Security check: block unauthorized access during SSO login flow"
  ]
}
```

### 4) Triage a regression failure signal

```bash
python3 scripts/run_agent.py \
  --agent qa-ops.regression-triage-agent \
  --input catalog/projects/qa-ops/agents/regression-triage-agent/examples/example-input.json \
  --pretty
```

Example output:

```json
{
  "probable_cause": "dependency",
  "recommended_actions": [
    "Reproduce failure with focused logs for: Production timeout after dependency version update",
    "Compare failure window with most recent merged changes",
    "Review changed components: auth-service, sdk-client"
  ],
  "severity": "sev2"
}
```

### 5) Synthesize findings for stakeholders

```bash
python3 scripts/run_agent.py \
  --agent research-ops.synthesis-agent \
  --input catalog/projects/research-ops/agents/synthesis-agent/examples/example-input.json \
  --pretty
```

Example output:

```json
{
  "headline": "Security Brief Summary",
  "next_actions": [
    "Validate highest-impact claim with one primary source",
    "Document assumptions and unresolved risks",
    "Share summary with stakeholders for review"
  ],
  "summary": "Key findings: Research objective: Summarize ASI09 mitigation guidance; Source note: enforce output contracts; Source note: require explicit human approval for sensitive actions"
}
```

### 6) Record a checkpoint in the workflow

```bash
python3 scripts/run_agent.py \
  --agent workflow-ops.checkpoint-agent \
  --input catalog/projects/workflow-ops/agents/checkpoint-agent/examples/example-input.json \
  --pretty
```

Example output:

```json
{
  "checkpoint_id": "release-2026-02-16:qa-validation:in_progress",
  "recorded": true,
  "summary": "Checkpoint recorded for workflow release-2026-02-16 at stage qa-validation with status in_progress. Notes: Integration tests running on staging."
}
```

This is the core advantage of a good agentic system for engineering teams: clear contracts, composable steps, and traceable state across the full lifecycle of work.

## Workflow-Ops Pipeline Example

For a fast orchestration-only path, run the composed workflow pipeline directly:

```bash
python3 scripts/run_workflow_pipeline.py \
  --input catalog/projects/workflow-ops/examples/pipeline-input.json \
  --pretty
```

This pipeline composes:

1. `workflow-ops.router-agent`
2. the routed target agent
3. `workflow-ops.checkpoint-agent`

and returns a single structured object with route decision, target output, checkpoint record, and `pipeline_status`.

## Governance Pipeline (`run_governance_pipeline.py`)

```
scope-validator -> [target agent] -> lineage-recorder -> checkpoint
```

- Validates action scope/permissions/reversibility **before** executing the target agent
- If scope validation returns `fail`, the pipeline **short-circuits**: records lineage ("blocked by governance gate") and a failed checkpoint, but never runs the target
- If `pass` or `review`, proceeds to execute the target, then records full decision lineage and a completion checkpoint
- Returns `pipeline_status`: `ok`, `blocked`, or `degraded`

```bash
python3 scripts/run_governance_pipeline.py \
  --input catalog/projects/control-ops/examples/governance-pipeline-input.json \
  --pretty
```

## Resilience Pipeline (`run_resilience_pipeline.py`)

```
blast-radius-assessor -> kill-path-auditor
```

- Assesses blast radius first (risk score, damage potential, detection/containment speeds)
- Then audits kill path coverage against the same system
- Computes a combined `resilience_verdict`:
  - **adequate**: full kill path coverage (4/4)
  - **partial**: moderate coverage
  - **at-risk**: high risk score + low coverage
  - **inadequate**: high risk score + very low coverage

Both follow the standard degraded-mode fallback pattern on validation failures. 10 new tests cover happy path, short-circuit blocking, degraded modes, and verdict logic.

```bash
python3 scripts/run_resilience_pipeline.py \
  --input catalog/projects/control-ops/examples/resilience-pipeline-input.json \
  --pretty
```

## Incident Pipeline (`run_incident_pipeline.py`)

```
router -> triage -> test-case-generator -> synthesis -> scope-validator -> checkpoint
```

Cross-domain orchestration that chains 6 agents from 5 different domains into a single incident response flow:

1. **Route** (workflow-ops): classifies the incident and selects a target agent
2. **Triage** (support-ops): assigns priority, category, and next action
3. **QA** (qa-ops): generates test cases for the affected feature area
4. **Synthesis** (research-ops): combines findings into a stakeholder summary
5. **Governance** (control-ops): validates the proposed response action against scope/permissions and stops on `review` or `fail`
6. **Checkpoint** (workflow-ops): records the pipeline outcome for traceability

If governance returns `verdict: fail`, the pipeline status is `blocked`. Validation failures at any stage produce `degraded` status with prior stage outputs preserved.

```bash
python3 scripts/run_incident_pipeline.py \
  --input examples/incident-pipeline-input.json \
  --pretty
```

## Pipeline State Persistence (Redis)

Pipelines can optionally persist intermediate stage outputs and final results to Redis. This enables multi-turn workflows, debugging, and auditing.

```bash
make state-up                    # start Redis
make state-down                  # stop Redis
```

Add `--state` to any pipeline runner to enable persistence:

```bash
python3 scripts/run_support_pipeline.py \
  --input catalog/projects/support-ops/examples/pipeline-input.json \
  --state --pretty
```

Optionally provide `--run-id` to set a custom run identifier; otherwise one is auto-generated.

State is stored with a 1-hour TTL and auto-expires. If Redis is unavailable, pipelines work exactly as before (stateless, single-shot).

## Test Suite

- `python3 -m unittest discover -s tests -v`
- `make test`
- `make verify-env` (policy check + deterministic tests, with deterministic security suite in non-dev environments)
- `make test-security` (ASI01+ASI02+ASI03+ASI04+ASI05+ASI06+ASI07+ASI08+ASI09+ASI10 adversarial checks + scanner tests)
- `make test-security-llm` (ASI01+ASI02+ASI03+ASI04+ASI05+ASI06+ASI07+ASI08+ASI09+ASI10 adversarial checks against local LLM)
- `make test-integration-llm` (optional LLM-backed checks)

The test suite currently includes:

- data-ops deterministic behavior tests (schema-drift-detector/data-validator).
- code-ops deterministic behavior tests (code-reviewer/pr-summary).
- observability-ops deterministic and LLM behavior tests (log-analyzer/slo-reporter/change-correlation/alert-tuner).
- knowledge-ops deterministic and LLM behavior tests (evidence-ranker/claim-trace/memory-curator/temporal-watch).
- control-ops deterministic and LLM behavior tests (lineage-recorder/scope-validator/exception-policy/approval-memory/blast-radius-assessor/kill-path-auditor).
- governance pipeline composition tests.
- resilience pipeline composition tests.
- behavior tests for local agent runtime logic.
- support-ops deterministic and LLM behavior tests (triage/reply/summary/handoff).
- pipeline composition tests.
- ASI01 goal-hijack adversarial regression tests.
- ASI01 goal-hijack LLM adversarial regression tests.
- ASI02 tool-misuse adversarial regression tests.
- ASI02 tool-misuse LLM adversarial regression tests.
- ASI03 identity/privilege-abuse adversarial regression tests.
- ASI03 identity/privilege-abuse LLM adversarial regression tests.
- ASI04 supply-chain/runtime-source adversarial regression tests.
- ASI04 supply-chain/runtime-source LLM adversarial regression tests.
- ASI05 unexpected-code-execution adversarial regression tests.
- ASI05 unexpected-code-execution LLM adversarial regression tests.
- ASI06 memory/context-poisoning adversarial regression tests.
- ASI06 memory/context-poisoning LLM adversarial regression tests.
- ASI07 inter-agent-communication adversarial regression tests.
- ASI07 inter-agent-communication LLM adversarial regression tests.
- ASI08 cascading-failure adversarial regression tests.
- ASI08 cascading-failure LLM adversarial regression tests.
- ASI09 human-agent-trust-exploitation adversarial regression tests.
- ASI09 human-agent-trust-exploitation LLM adversarial regression tests.
- ASI10 rogue-agent adversarial regression tests.
- ASI10 rogue-agent LLM adversarial regression tests.
- security scanner tests (glob discovery, custom rules, check operators, nested catalogs).
- state store unit tests (NoOp fallback, pipeline helpers, live Redis integration).
- `agent.yaml` JSON Schema validation (`schemas/agent.json`).
- benchmark/eval fixtures: 86 cases across 24 agents (`evals/cases.json` per agent).
- incident pipeline cross-domain composition tests.
- catalog structure checks for required per-agent files.
- optional integration tests against local Ollama.

## Policy Pack

Environment ASI control baselines live in:

- `policy/asi-control-baselines.json`

This policy pack defines required controls for `ASI01` through `ASI10` across:

- `dev`
- `staging`
- `prod`

Reference documentation:

- `docs/policy-pack.md`
- `python3 scripts/check_policy_pack.py --env dev --mode deterministic`
- `make check-policy-pack` and `make check-policy-pack-llm`

LLM-oriented `make` targets are policy-gated by environment (`POLICY_ENV`) and fail fast when policy disallows LLM mode.

## Add a New Agent

1. Create `catalog/projects/<project>/agents/<agent-name>/`.
2. Add `agent.yaml` with purpose, IO contract, and runtime assumptions (validated by `schemas/agent.json`).
3. Add prompt/workflow/example/test docs.
4. Add `evals/cases.json` with benchmark fixtures (validated by `schemas/eval-case.json`).
5. Update `catalog/projects/<project>/README.md`.
6. Update root `README.md`, **`catalog/README.md`** (canonical catalog index), and **`AGENTS.md`** if conventions or Update Rule change.

## Next Ideas

1. CI pipeline (GitHub Actions for `make test` and `make test-security`).
