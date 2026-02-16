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

Support pipeline example:

```bash
python3 scripts/run_support_pipeline.py \
  --input catalog/projects/support-ops/examples/pipeline-input.json \
  --pretty
```

Security scan example:

```bash
python3 scripts/run_security_scan.py \
  --target-path . \
  --pretty
```

Accepted `--agent` values:

- `starter-kit.heartbeat-agent` or `heartbeat-agent`
- `starter-kit.classifier-agent` or `classifier-agent`
- `support-ops.triage-agent` or `triage-agent`
- `support-ops.reply-drafter-agent` or `reply-drafter-agent`
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
make test-security
make test-security-llm
make test-integration-llm
make run-heartbeat-example
make run-classifier-example
make run-triage-example
make run-reply-drafter-example
make run-security-scan-example
make run-support-pipeline-example
make run-heartbeat-llm
make run-classifier-llm
make run-triage-llm
make run-reply-drafter-llm
make run-support-pipeline-llm
```

Notes:

- `make test` runs deterministic unit tests and catalog structure checks.
- `make test-security` runs ASI01+ASI02+ASI03+ASI04+ASI05+ASI06+ASI07+ASI08 adversarial regression tests and scanner tests.
- `make test-security-llm` runs ASI01+ASI02+ASI03+ASI04+ASI05+ASI06+ASI07+ASI08 adversarial tests against local Ollama.
- `make test-integration-llm` runs only LLM integration tests and skips automatically when Ollama is unavailable.
- Security scanner currently supports deterministic mode only.
- LLM runtime source is restricted to approved local host/model defaults to reduce supply-chain risk.
- Support pipeline returns `pipeline_status` (`ok` or `degraded`) and includes safe fallback output on validation failures to avoid cascade crashes.
- ASI coverage is expanding incrementally from ASI01 to ASI10.
