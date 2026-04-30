# Local Usage

## Prerequisites

- Python 3.10+ available as `python3`
- Docker Desktop (or compatible Docker runtime) for LLM mode

## Deterministic Mode (Default)

From repository root:

```bash
python3 scripts/run_agent.py \
  --agent starter-kit.heartbeat-agent \
  --input catalog/projects/starter-kit/agents/heartbeat-agent/examples/example-input.json \
  --pretty
```

Classifier example:

```bash
python3 scripts/run_agent.py \
  --agent starter-kit.classifier-agent \
  --input catalog/projects/starter-kit/agents/classifier-agent/examples/example-input.json \
  --pretty
```

Triage example:

```bash
python3 scripts/run_agent.py \
  --agent support-ops.triage-agent \
  --input catalog/projects/support-ops/agents/triage-agent/examples/example-input.json \
  --pretty
```

Reply drafter example:

```bash
python3 scripts/run_agent.py \
  --agent support-ops.reply-drafter-agent \
  --input catalog/projects/support-ops/agents/reply-drafter-agent/examples/example-input.json \
  --pretty
```

Weekly summary example:

```bash
python3 scripts/run_agent.py \
  --agent support-ops.summary-agent \
  --input catalog/projects/support-ops/agents/summary-agent/examples/example-input.json \
  --pretty
```

Handoff example:

```bash
python3 scripts/run_agent.py \
  --agent support-ops.handoff-agent \
  --input catalog/projects/support-ops/agents/handoff-agent/examples/example-input.json \
  --pretty
```

Planner example:

```bash
python3 scripts/run_agent.py \
  --agent planner-executor.planner-agent \
  --input catalog/projects/planner-executor/agents/planner-agent/examples/example-input.json \
  --pretty
```

Executor example:

```bash
python3 scripts/run_agent.py \
  --agent planner-executor.executor-agent \
  --input catalog/projects/planner-executor/agents/executor-agent/examples/example-input.json \
  --pretty
```

Source planner example:

```bash
python3 scripts/run_agent.py \
  --agent research-ops.source-planner-agent \
  --input catalog/projects/research-ops/agents/source-planner-agent/examples/example-input.json \
  --pretty
```

Retrieval example:

```bash
python3 scripts/run_agent.py \
  --agent research-ops.retrieval-agent \
  --input catalog/projects/research-ops/agents/retrieval-agent/examples/example-input.json \
  --pretty
```

Synthesis example:

```bash
python3 scripts/run_agent.py \
  --agent research-ops.synthesis-agent \
  --input catalog/projects/research-ops/agents/synthesis-agent/examples/example-input.json \
  --pretty
```

Gap detector example:

```bash
python3 scripts/run_agent.py \
  --agent research-ops.gap-detector-agent \
  --input catalog/projects/research-ops/agents/gap-detector-agent/examples/example-input.json \
  --pretty
```

Evidence ranker example:

```bash
python3 scripts/run_agent.py \
  --agent knowledge-ops.evidence-ranker-agent \
  --input catalog/projects/knowledge-ops/agents/evidence-ranker-agent/examples/example-input.json \
  --pretty
```

Claim trace example:

```bash
python3 scripts/run_agent.py \
  --agent knowledge-ops.claim-trace-agent \
  --input catalog/projects/knowledge-ops/agents/claim-trace-agent/examples/example-input.json \
  --pretty
```

Memory curator example:

```bash
python3 scripts/run_agent.py \
  --agent knowledge-ops.memory-curator-agent \
  --input catalog/projects/knowledge-ops/agents/memory-curator-agent/examples/example-input.json \
  --pretty
```

Temporal watch example:

```bash
python3 scripts/run_agent.py \
  --agent knowledge-ops.temporal-watch-agent \
  --input catalog/projects/knowledge-ops/agents/temporal-watch-agent/examples/example-input.json \
  --pretty
```

Test-case generator example:

```bash
python3 scripts/run_agent.py \
  --agent qa-ops.test-case-generator-agent \
  --input catalog/projects/qa-ops/agents/test-case-generator-agent/examples/example-input.json \
  --pretty
```

Regression triage example:

```bash
python3 scripts/run_agent.py \
  --agent qa-ops.regression-triage-agent \
  --input catalog/projects/qa-ops/agents/regression-triage-agent/examples/example-input.json \
  --pretty
```

Eval-ops (benchmark curation, regression scoring, quality drift):

```bash
python3 scripts/run_agent.py \
  --agent eval-ops.benchmark-curator-agent \
  --input catalog/projects/eval-ops/agents/benchmark-curator-agent/examples/example-input.json \
  --pretty
python3 scripts/run_agent.py \
  --agent eval-ops.regression-score-agent \
  --input catalog/projects/eval-ops/agents/regression-score-agent/examples/example-input.json \
  --pretty
python3 scripts/run_agent.py \
  --agent eval-ops.quality-drift-reporter-agent \
  --input catalog/projects/eval-ops/agents/quality-drift-reporter-agent/examples/example-input.json \
  --pretty
```

Experiment-ops (hypothesis registration, experiment plans, result adjudication):

```bash
python3 scripts/run_agent.py \
  --agent experiment-ops.hypothesis-registration-agent \
  --input catalog/projects/experiment-ops/agents/hypothesis-registration-agent/examples/example-input.json \
  --pretty
python3 scripts/run_agent.py \
  --agent experiment-ops.experiment-plan-agent \
  --input catalog/projects/experiment-ops/agents/experiment-plan-agent/examples/example-input.json \
  --pretty
python3 scripts/run_agent.py \
  --agent experiment-ops.result-adjudication-agent \
  --input catalog/projects/experiment-ops/agents/result-adjudication-agent/examples/example-input.json \
  --pretty
```

Artifact-ops (inventory, manifest, bundle seal):

```bash
python3 scripts/run_agent.py \
  --agent artifact-ops.artifact-inventory-agent \
  --input catalog/projects/artifact-ops/agents/artifact-inventory-agent/examples/example-input.json \
  --pretty
python3 scripts/run_agent.py \
  --agent artifact-ops.bundle-manifest-agent \
  --input catalog/projects/artifact-ops/agents/bundle-manifest-agent/examples/example-input.json \
  --pretty
python3 scripts/run_agent.py \
  --agent artifact-ops.bundle-seal-agent \
  --input catalog/projects/artifact-ops/agents/bundle-seal-agent/examples/example-input.json \
  --pretty
```

Router example:

```bash
python3 scripts/run_agent.py \
  --agent workflow-ops.router-agent \
  --input catalog/projects/workflow-ops/agents/router-agent/examples/example-input.json \
  --pretty
```

Dependency router example:

```bash
python3 scripts/run_agent.py \
  --agent workflow-ops.dependency-router-agent \
  --input catalog/projects/workflow-ops/agents/dependency-router-agent/examples/example-input.json \
  --pretty
```

Retry policy example:

```bash
python3 scripts/run_agent.py \
  --agent workflow-ops.retry-policy-agent \
  --input catalog/projects/workflow-ops/agents/retry-policy-agent/examples/example-input.json \
  --pretty
```

Checkpoint example:

```bash
python3 scripts/run_agent.py \
  --agent workflow-ops.checkpoint-agent \
  --input catalog/projects/workflow-ops/agents/checkpoint-agent/examples/example-input.json \
  --pretty
```

Lineage recorder example:

```bash
python3 scripts/run_agent.py \
  --agent control-ops.lineage-recorder-agent \
  --input catalog/projects/control-ops/agents/lineage-recorder-agent/examples/example-input.json \
  --pretty
```

Scope validator example:

```bash
python3 scripts/run_agent.py \
  --agent control-ops.scope-validator-agent \
  --input catalog/projects/control-ops/agents/scope-validator-agent/examples/example-input.json \
  --pretty
```

Exception policy example:

```bash
python3 scripts/run_agent.py \
  --agent control-ops.exception-policy-agent \
  --input catalog/projects/control-ops/agents/exception-policy-agent/examples/example-input.json \
  --pretty
```

Approval memory example:

```bash
python3 scripts/run_agent.py \
  --agent control-ops.approval-memory-agent \
  --input catalog/projects/control-ops/agents/approval-memory-agent/examples/example-input.json \
  --pretty
```

Blast radius assessor example:

```bash
python3 scripts/run_agent.py \
  --agent control-ops.blast-radius-assessor-agent \
  --input catalog/projects/control-ops/agents/blast-radius-assessor-agent/examples/example-input.json \
  --pretty
```

Kill path auditor example:

```bash
python3 scripts/run_agent.py \
  --agent control-ops.kill-path-auditor-agent \
  --input catalog/projects/control-ops/agents/kill-path-auditor-agent/examples/example-input.json \
  --pretty
```

Schema drift detector example:

```bash
python3 scripts/run_agent.py \
  --agent data-ops.schema-drift-detector-agent \
  --input catalog/projects/data-ops/agents/schema-drift-detector-agent/examples/example-input.json \
  --pretty
```

Data validator example:

```bash
python3 scripts/run_agent.py \
  --agent data-ops.data-validator-agent \
  --input catalog/projects/data-ops/agents/data-validator-agent/examples/example-input.json \
  --pretty
```

Code reviewer example:

```bash
python3 scripts/run_agent.py \
  --agent code-ops.code-reviewer-agent \
  --input catalog/projects/code-ops/agents/code-reviewer-agent/examples/example-input.json \
  --pretty
```

PR summary example:

```bash
python3 scripts/run_agent.py \
  --agent code-ops.pr-summary-agent \
  --input catalog/projects/code-ops/agents/pr-summary-agent/examples/example-input.json \
  --pretty
```

Log analyzer example:

```bash
python3 scripts/run_agent.py \
  --agent observability-ops.log-analyzer-agent \
  --input catalog/projects/observability-ops/agents/log-analyzer-agent/examples/example-input.json \
  --pretty
```

SLO reporter example:

```bash
python3 scripts/run_agent.py \
  --agent observability-ops.slo-reporter-agent \
  --input catalog/projects/observability-ops/agents/slo-reporter-agent/examples/example-input.json \
  --pretty
```

Change correlation example:

```bash
python3 scripts/run_agent.py \
  --agent observability-ops.change-correlation-agent \
  --input catalog/projects/observability-ops/agents/change-correlation-agent/examples/example-input.json \
  --pretty
```

Alert tuner example:

```bash
python3 scripts/run_agent.py \
  --agent observability-ops.alert-tuner-agent \
  --input catalog/projects/observability-ops/agents/alert-tuner-agent/examples/example-input.json \
  --pretty
```

Support pipeline example:

```bash
python3 scripts/run_support_pipeline.py \
  --input catalog/projects/support-ops/examples/pipeline-input.json \
  --pretty
```

Planner-executor pipeline example:

```bash
python3 scripts/run_planner_executor_pipeline.py \
  --input catalog/projects/planner-executor/examples/pipeline-input.json \
  --pretty
```

Workflow pipeline example:

```bash
python3 scripts/run_workflow_pipeline.py \
  --input catalog/projects/workflow-ops/examples/pipeline-input.json \
  --pretty
```

Governance pipeline example:

```bash
python3 scripts/run_governance_pipeline.py \
  --input catalog/projects/control-ops/examples/governance-pipeline-input.json \
  --pretty
```

Expected governance statuses:

- `ok`: target executed after governance pass
- `needs_review`: target skipped pending manual governance review
- `blocked`: target skipped because governance failed
- `degraded`: pipeline validation or orchestration failed

Resilience pipeline example:

```bash
python3 scripts/run_resilience_pipeline.py \
  --input catalog/projects/control-ops/examples/resilience-pipeline-input.json \
  --pretty
```

Agent incident drill example:

```bash
python3 scripts/run_agent_incident_drill.py \
  --input catalog/projects/agent-incident-drill/examples/drill-input.json \
  --pretty
```

Alternate drill inputs live under `catalog/projects/agent-incident-drill/examples/drill-input*.json`. Compare scorecards from two saved drill outputs:

```bash
python3 scripts/compare_agent_incident_drill_scorecards.py \
  --baseline /path/to/run-a.json --current /path/to/run-b.json --pretty
```

Or run two drills and diff in one step:

```bash
make compare-agent-incident-drill-scorecards-example
```

Security scan example:

```bash
python3 scripts/run_security_scan.py \
  --target-path . \
  --pretty
```

Policy pack example:

```bash
cat policy/asi-control-baselines.json
```

Policy enforcement check example:

```bash
python3 scripts/check_policy_pack.py --env dev --mode deterministic
```

Accepted `--agent` values:

- `starter-kit.heartbeat-agent` or `heartbeat-agent`
- `starter-kit.classifier-agent` or `classifier-agent`
- `support-ops.triage-agent` or `triage-agent`
- `support-ops.reply-drafter-agent` or `reply-drafter-agent`
- `support-ops.summary-agent` or `summary-agent`
- `support-ops.handoff-agent` or `handoff-agent`
- `planner-executor.planner-agent` or `planner-agent`
- `planner-executor.executor-agent` or `executor-agent`
- `research-ops.source-planner-agent` or `source-planner-agent`
- `research-ops.retrieval-agent` or `retrieval-agent`
- `research-ops.gap-detector-agent` or `gap-detector-agent`
- `research-ops.synthesis-agent` or `synthesis-agent`
- `knowledge-ops.evidence-ranker-agent` or `evidence-ranker-agent`
- `knowledge-ops.claim-trace-agent` or `claim-trace-agent`
- `knowledge-ops.memory-curator-agent` or `memory-curator-agent`
- `knowledge-ops.temporal-watch-agent` or `temporal-watch-agent`
- `qa-ops.test-case-generator-agent` or `test-case-generator-agent`
- `qa-ops.regression-triage-agent` or `regression-triage-agent`
- `eval-ops.benchmark-curator-agent` or `benchmark-curator-agent`
- `eval-ops.regression-score-agent` or `regression-score-agent`
- `eval-ops.quality-drift-reporter-agent` or `quality-drift-reporter-agent`
- `experiment-ops.hypothesis-registration-agent` or `hypothesis-registration-agent`
- `experiment-ops.experiment-plan-agent` or `experiment-plan-agent`
- `experiment-ops.result-adjudication-agent` or `result-adjudication-agent`
- `artifact-ops.artifact-inventory-agent` or `artifact-inventory-agent`
- `artifact-ops.bundle-manifest-agent` or `bundle-manifest-agent`
- `artifact-ops.bundle-seal-agent` or `bundle-seal-agent`
- `workflow-ops.router-agent` or `router-agent`
- `workflow-ops.dependency-router-agent` or `dependency-router-agent`
- `workflow-ops.retry-policy-agent` or `retry-policy-agent`
- `workflow-ops.checkpoint-agent` or `checkpoint-agent`
- `security-ops.agentic-security-scanner-agent` or `agentic-security-scanner-agent`
- `control-ops.lineage-recorder-agent` or `lineage-recorder-agent`
- `control-ops.scope-validator-agent` or `scope-validator-agent`
- `control-ops.exception-policy-agent` or `exception-policy-agent`
- `control-ops.approval-memory-agent` or `approval-memory-agent`
- `control-ops.blast-radius-assessor-agent` or `blast-radius-assessor-agent`
- `control-ops.kill-path-auditor-agent` or `kill-path-auditor-agent`
- `data-ops.schema-drift-detector-agent` or `schema-drift-detector-agent`
- `data-ops.data-validator-agent` or `data-validator-agent`
- `code-ops.code-reviewer-agent` or `code-reviewer-agent`
- `code-ops.pr-summary-agent` or `pr-summary-agent`
- `observability-ops.log-analyzer-agent` or `log-analyzer-agent`
- `observability-ops.slo-reporter-agent` or `slo-reporter-agent`
- `observability-ops.change-correlation-agent` or `change-correlation-agent`
- `observability-ops.alert-tuner-agent` or `alert-tuner-agent`

## Pipeline State Persistence (Redis)

Start Redis for optional state persistence:

```bash
make state-up
```

Run any pipeline with `--state` to persist intermediate stage outputs:

```bash
python3 scripts/run_support_pipeline.py \
  --input catalog/projects/support-ops/examples/pipeline-input.json \
  --state --pretty

python3 scripts/run_workflow_pipeline.py \
  --input catalog/projects/workflow-ops/examples/pipeline-input.json \
  --state --run-id my-custom-run --pretty
```

Optional flags:

- `--state` enables Redis state persistence (no-op if Redis is unavailable)
- `--run-id` sets a custom run identifier (auto-generated if omitted)

State keys use the pattern `pipeline:{run_id}:stage:{name}` and `pipeline:{run_id}:result` with a 1-hour TTL.

Stop Redis:

```bash
make state-down
```

## LLM Mode (Fast Local Model)

Start Ollama and pull fast model:

```bash
make llm-up
make llm-pull
```

This pulls `llama3.2:3b` for speed-first local runs.

Run pipeline in LLM mode:

```bash
AGENT_MODE=llm python3 scripts/run_support_pipeline.py \
  --input catalog/projects/support-ops/examples/pipeline-input.json \
  --pretty
```

Optional flags:

- `--model` (default: `llama3.2:3b`)
- `--base-url` (default: `http://localhost:11434`)

Stop Ollama:

```bash
make llm-down
```

## Test Suite

```bash
python3 -m unittest discover -s tests -v
```

Focused control-ops regression pass:

```bash
python3 -m unittest \
  tests/test_control_ops.py \
  tests/test_governance_pipeline.py \
  tests/test_resilience_pipeline.py \
  tests/test_incident_pipeline.py \
  tests/test_agent_incident_drill.py \
  tests/test_compare_agent_incident_drill_scorecards.py \
  tests/test_eval_ops.py \
  tests/test_experiment_ops.py \
  tests/test_artifact_ops.py
```

Experiment-ops LLM smoke (requires Ollama and `AGENT_MODE=llm`):

```bash
AGENT_MODE=llm python3 -m unittest tests.test_experiment_ops_llm -v
```

Artifact-ops LLM smoke (requires Ollama and `AGENT_MODE=llm`):

```bash
AGENT_MODE=llm python3 -m unittest tests.test_artifact_ops_llm -v
```

Or with Make targets:

```bash
make state-up
make state-down
make test
make verify-env
make test-security
make test-security-llm
make test-integration-llm
make check-policy-pack
make check-policy-pack-llm
make run-heartbeat-example
make run-classifier-example
make run-triage-example
make run-reply-drafter-example
make run-summary-example
make run-handoff-example
make run-planner-example
make run-executor-example
make run-retrieval-example
make run-synthesis-example
make run-test-case-generator-example
make run-regression-triage-example
make run-benchmark-curator-example
make run-regression-score-example
make run-quality-drift-reporter-example
make run-hypothesis-registration-example
make run-experiment-plan-example
make run-result-adjudication-example
make demo-experiment-ops
make run-router-example
make run-checkpoint-example
make run-schema-drift-detector-example
make run-data-validator-example
make run-code-reviewer-example
make run-pr-summary-example
make run-log-analyzer-example
make run-slo-reporter-example
make run-security-scan-example
make run-support-pipeline-example
make run-planner-executor-pipeline-example
make run-workflow-pipeline-example
make run-heartbeat-llm
make run-classifier-llm
make run-triage-llm
make run-reply-drafter-llm
make run-summary-llm
make run-handoff-llm
make run-planner-llm
make run-executor-llm
make run-retrieval-llm
make run-synthesis-llm
make run-test-case-generator-llm
make run-regression-triage-llm
make run-benchmark-curator-llm
make run-regression-score-llm
make run-quality-drift-reporter-llm
make run-hypothesis-registration-llm
make run-experiment-plan-llm
make run-result-adjudication-llm
make demo-experiment-ops-llm
make run-router-llm
make run-checkpoint-llm
make run-lineage-recorder-example
make run-scope-validator-example
make run-blast-radius-assessor-example
make run-kill-path-auditor-example
make run-lineage-recorder-llm
make run-scope-validator-llm
make run-blast-radius-assessor-llm
make run-kill-path-auditor-llm
make run-schema-drift-detector-llm
make run-data-validator-llm
make run-code-reviewer-llm
make run-pr-summary-llm
make run-log-analyzer-llm
make run-slo-reporter-llm
make run-governance-pipeline-example
make run-resilience-pipeline-example
make run-agent-incident-drill-example
make compare-agent-incident-drill-scorecards-example
make run-governance-pipeline-llm
make run-resilience-pipeline-llm
make run-support-pipeline-llm
make run-planner-executor-pipeline-llm
make run-workflow-pipeline-llm
```

Notes:

- `make test` runs deterministic unit tests and catalog structure checks.
- `make verify-env` runs policy precheck + deterministic tests and auto-runs deterministic security tests outside `dev`.
- `make test-security` runs ASI01+ASI02+ASI03+ASI04+ASI05+ASI06+ASI07+ASI08+ASI09+ASI10 adversarial regression tests and scanner tests.
- `make test-security-llm` runs ASI01+ASI02+ASI03+ASI04+ASI05+ASI06+ASI07+ASI08+ASI09+ASI10 adversarial tests against local Ollama.
- `make test-integration-llm` runs only LLM integration tests and skips automatically when Ollama is unavailable.
- `make check-policy-pack` validates runtime mode against selected policy environment (defaults: `POLICY_ENV=dev`, `AGENT_MODE=deterministic`).
- `make check-policy-pack-llm` validates LLM mode against selected policy environment (default `POLICY_ENV=dev`).
- All `*-llm` make targets run the LLM policy precheck first and will fail fast on disallowed environments (for example `POLICY_ENV=prod`).
- Security scanner currently supports deterministic mode only.
- ASI policy baselines by environment are defined in `policy/asi-control-baselines.json`.
- LLM runtime source is restricted to approved local host/model defaults to reduce supply-chain risk.
- Support pipeline returns `pipeline_status` (`ok` or `degraded`) and includes safe fallback output on validation failures to avoid cascade crashes.
- Planner-executor pipeline returns `pipeline_status` (`ok` or `degraded`) and includes safe fallback output on validation failures.
- `ASI09_STRICT_LLM=1 make test-security-llm` enables the slower direct-reply ASI09 LLM stress case; default runs skip it to avoid long-tail timeouts.
- `ASI10_STRICT_LLM=1 make test-security-llm` enables the slower direct-reply ASI10 LLM stress case; default runs skip it to keep full suites fast.
- ASI coverage is expanding incrementally from ASI01 to ASI10.
