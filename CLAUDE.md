# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

An **Agent Catalog** — a Python 3.10+ framework of composable AI agents organized by domain. 12 domain projects, 24 agents, 6 pipelines. Zero external Python dependencies for core runtime. Uses Ollama (local LLM) and Redis (optional state persistence) via Docker.

## Common Commands

```bash
# Testing
make test                      # All deterministic unit tests
make test-verbose              # Verbose output
make verify-env                # Policy check + deterministic tests (use before committing)
make test-security             # ASI01-ASI10 adversarial regression tests
make test-security-llm         # ASI tests against local LLM (requires Ollama)
make test-integration-llm      # Integration tests with LLM

# Run a single test file
python3 -m unittest tests/test_engine.py -v

# Run a single test method
python3 -m unittest tests.test_engine.TestEngine.test_triage_agent -v

# Run a single agent
python3 scripts/run_agent.py --agent support-ops.triage-agent \
  --input catalog/projects/support-ops/agents/triage-agent/examples/example-input.json --pretty

# Run with LLM mode
AGENT_MODE=llm python3 scripts/run_agent.py --agent <agent-id> --input <input.json> --pretty

# Run a pipeline
python3 scripts/run_support_pipeline.py --input catalog/projects/support-ops/examples/pipeline-input.json --pretty

# Infrastructure
make llm-up && make llm-pull   # Start Ollama + download llama3.2:3b
make state-up                  # Start Redis for state persistence
```

## Architecture

### Runtime Core (`local_agents/`)

- **`engine.py`**: Deterministic implementations for all 24 agents + `run_agent()` dispatcher. The central dispatch function maps agent IDs to handler functions.
- **`llm.py`**: LLM-backed implementations calling Ollama HTTP API (`/api/generate`). Each agent has a parallel LLM function.
- **`core.py`**: Shared validation, `sanitize_untrusted_text()` input sanitization, LLM source approval list.
- **`state.py`**: Minimal Redis client using raw RESP protocol (no dependencies). Graceful no-op fallback when Redis is unavailable.
- **`security_scanner.py`**: Repository control analysis engine.

### Dual Execution Model

Every agent has two implementations:
1. **Deterministic** (default): Rule-based logic in `engine.py`. Fast, no external calls.
2. **LLM**: Prompt-based in `llm.py`. Uses Ollama with structured JSON output validation.

Selected via `AGENT_MODE=llm` env var or `--mode llm` CLI arg.

### Agent Structure

Each agent lives at `catalog/projects/<domain>/agents/<agent-name>/` with:
- `agent.yaml` — schema definition (inputs, outputs, rules, constraints); validated against `schemas/agent.json`
- `prompts/system.md` — system prompt and behavior contract
- `workflows/runbook.md` — operating steps and failure handling
- `examples/` — `example-input.json` and `example-output.json`
- `evals/cases.json` — benchmark fixtures

Agents are still fundamentally constrained by their reasoning engine. They can chain actions impressively, but they don't truly "understand" failure modes the way a human operator does. They're brittle at the edges — novel situations outside their training distribution cause disproportionate breakdowns. And autonomy is a spectrum, not a binary; most production agents today are better described as "semi-autonomous with human checkpoints" than fully independent.

The real engineering challenge is making an agent that knows when not to take action.

### Pipelines (`scripts/run_*_pipeline.py`)

Compose agents in sequence. Return `pipeline_status`: `ok`, `degraded`, or `blocked`. Degraded pipelines return safe fallback outputs on validation failure. Six pipelines: support, planner-executor, workflow, governance, resilience, incident (cross-domain).

### State Persistence

Optional Redis-backed. Key pattern: `pipeline:{run_id}:stage:{stage}`. TTL: 1 hour. Enable with `--state --run-id <id>`.

## Adding a New Agent

1. Create directory tree under `catalog/projects/<domain>/agents/<name>/` with required files
2. Add deterministic handler in `engine.py` and LLM handler in `llm.py`
3. Register in the `run_agent()` dispatcher in `engine.py`
4. Export in `local_agents/__init__.py`
5. Add unit tests (deterministic + LLM) in `tests/`
6. Add eval cases in `evals/cases.json`
7. Update `AGENTS.md` and `docs/local-usage.md`
8. Run `make verify-env`

See `docs/contributor-sop.md` for the full checklist.

## Naming Conventions

- Projects: `kebab-case` (e.g., `support-ops`)
- Agents: `kebab-case` ending with `-agent` (e.g., `triage-agent`)
- Agent IDs: `<project>.<agent-name>` (e.g., `support-ops.triage-agent`)

## Security

- Input sanitization via `sanitize_untrusted_text()` strips injection patterns and credential leaks
- LLM calls restricted to approved models (`llama3.2:3b`) and localhost-only hosts
- ASI01–ASI10 adversarial test suites cover OWASP AI Security categories (goal hijacking, tool misuse, privilege abuse, supply chain, code execution, memory poisoning, inter-agent attacks, cascading failures, trust exploitation, rogue agents)
- Policy baselines in `policy/asi-control-baselines.json` define per-environment (dev/staging/prod) controls
