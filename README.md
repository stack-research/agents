# Agent Catalog

This repository is a growing catalog of reusable AI agents organized by project.

## Goals

- Keep each agent self-contained and easy to run.
- Reuse project-level patterns so new agents are quick to add.
- Document every agent clearly as the catalog scales.

## Repository Structure

- `AGENTS.md` - contribution and catalog conventions.
- `catalog/` - all projects and their agents.
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
3. `security-ops`
   - `agentic-security-scanner-agent`: scans repo controls and maps findings to OWASP ASI categories.

## Run Agents Locally

- `python3 scripts/run_agent.py --agent starter-kit.heartbeat-agent --input catalog/projects/starter-kit/agents/heartbeat-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent starter-kit.classifier-agent --input catalog/projects/starter-kit/agents/classifier-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent support-ops.triage-agent --input catalog/projects/support-ops/agents/triage-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent support-ops.reply-drafter-agent --input catalog/projects/support-ops/agents/reply-drafter-agent/examples/example-input.json --pretty`
- `python3 scripts/run_support_pipeline.py --input catalog/projects/support-ops/examples/pipeline-input.json --pretty`
- `python3 scripts/run_security_scan.py --target-path . --pretty`
- `AGENT_MODE=llm python3 scripts/run_support_pipeline.py --input catalog/projects/support-ops/examples/pipeline-input.json --pretty`
- `make llm-up && make llm-pull` for a speed-first local model (`llama3.2:3b`)

See `/Users/macos-user/.projects/stack-research/agents/docs/local-usage.md` for full usage.

## Test Suite

- `python3 -m unittest discover -s tests -v`
- `make test`
- `make test-security` (ASI01+ASI02 adversarial checks + scanner tests)
- `make test-security-llm` (ASI01+ASI02 adversarial checks against local LLM)
- `make test-integration-llm` (optional LLM-backed checks)

The test suite currently includes:

- behavior tests for local agent runtime logic.
- pipeline composition tests.
- ASI01 goal-hijack adversarial regression tests.
- ASI01 goal-hijack LLM adversarial regression tests.
- ASI02 tool-misuse adversarial regression tests.
- ASI02 tool-misuse LLM adversarial regression tests.
- security scanner tests.
- catalog structure checks for required per-agent files.
- optional integration tests against local Ollama.

## Add a New Agent

1. Create `catalog/projects/<project>/agents/<agent-name>/`.
2. Add `agent.yaml` with purpose, IO contract, and runtime assumptions.
3. Add prompt/workflow/example/test docs.
4. Update `catalog/projects/<project>/README.md`.
5. Update root `README.md` and `AGENTS.md` catalog sections.

## Next Ideas

- Add schema checks for `agent.yaml` files in CI.
- Add a `summary-agent` for support weekly trend rollups.
- Add a policy pack file for ASI control baselines by environment.
