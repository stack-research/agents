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

Router example:

```bash
python3 scripts/run_agent.py \
  --agent workflow-ops.router-agent \
  --input catalog/projects/workflow-ops/agents/router-agent/examples/example-input.json \
  --pretty
```

Checkpoint example:

```bash
python3 scripts/run_agent.py \
  --agent workflow-ops.checkpoint-agent \
  --input catalog/projects/workflow-ops/agents/checkpoint-agent/examples/example-input.json \
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
- `research-ops.retrieval-agent` or `retrieval-agent`
- `research-ops.synthesis-agent` or `synthesis-agent`
- `qa-ops.test-case-generator-agent` or `test-case-generator-agent`
- `qa-ops.regression-triage-agent` or `regression-triage-agent`
- `workflow-ops.router-agent` or `router-agent`
- `workflow-ops.checkpoint-agent` or `checkpoint-agent`
- `security-ops.agentic-security-scanner-agent` or `agentic-security-scanner-agent`

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

Or with Make targets:

```bash
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
make run-router-example
make run-checkpoint-example
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
make run-router-llm
make run-checkpoint-llm
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
