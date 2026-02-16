# AGENTS.md

This file defines how to grow this repository as an agent catalog.

## Principles

- Prefer small, focused agents over broad multi-purpose agents.
- Keep each agent directory complete enough to understand in isolation.
- Use consistent file names and metadata to support tooling later.

## Required Agent Files

Each agent should include:

- `agent.yaml` - id, purpose, inputs, outputs, constraints.
- `prompts/system.md` - system prompt and behavior contract.
- `workflows/runbook.md` - operating steps and failure handling.
- `examples/` - sample inputs and outputs.
- `tests/` - smoke checks or evaluation notes.

## Testing Requirements

For any new agent behavior or security control:

1. Add deterministic unit tests (default mode) under `/Users/macos-user/.projects/stack-research/agents/tests/`.
2. Add LLM-mode tests for the same behavior/security path, with graceful skip when `AGENT_MODE!=llm` or Ollama is unavailable.
3. Add security regression tests for relevant OWASP ASI categories (current baseline: ASI01, ASI02, ASI03, ASI04, ASI05, ASI06, ASI07, ASI08, ASI09, and ASI10).
4. Ensure `make test` passes and update `make` targets when adding new security suites.
5. Update `/Users/macos-user/.projects/stack-research/agents/docs/local-usage.md` with any new test commands.

Contributor SOP:

- Canonical implementation workflow lives in `/Users/macos-user/.projects/stack-research/agents/docs/contributor-sop.md`.
- Follow that SOP for scaffolding, runtime updates, deterministic+LLM tests, security regressions, and definition-of-done checks.

Repository-level runtime and tests:

- `scripts/run_agent.py` - local runner for implemented agents.
- `scripts/run_support_pipeline.py` - support triage->reply pipeline runner.
- `scripts/run_planner_executor_pipeline.py` - planner->executor pipeline runner.
- `scripts/run_security_scan.py` - security scanner runner.
- `tests/test_engine.py` - unit tests for deterministic runtime behavior.
- `tests/test_support_pipeline.py` - pipeline composition unit test.
- `tests/test_planner_executor_pipeline.py` - planner->executor pipeline composition test.
- `tests/test_asi01_goal_hijack.py` - ASI01 adversarial regression tests (deterministic).
- `tests/test_asi01_goal_hijack_llm.py` - ASI01 adversarial checks in LLM mode.
- `tests/test_asi02_tool_misuse.py` - ASI02 tool-misuse checks (deterministic).
- `tests/test_asi02_tool_misuse_llm.py` - ASI02 tool-misuse checks in LLM mode.
- `tests/test_asi03_identity_privilege_abuse.py` - ASI03 identity/privilege-abuse checks (deterministic).
- `tests/test_asi03_identity_privilege_abuse_llm.py` - ASI03 identity/privilege-abuse checks in LLM mode.
- `tests/test_asi04_supply_chain.py` - ASI04 supply-chain/runtime-source checks (deterministic).
- `tests/test_asi04_supply_chain_llm.py` - ASI04 supply-chain/runtime-source checks in LLM mode.
- `tests/test_asi05_unexpected_code_execution.py` - ASI05 unexpected-code-execution checks (deterministic).
- `tests/test_asi05_unexpected_code_execution_llm.py` - ASI05 unexpected-code-execution checks in LLM mode.
- `tests/test_asi06_memory_context_poisoning.py` - ASI06 memory/context-poisoning checks (deterministic).
- `tests/test_asi06_memory_context_poisoning_llm.py` - ASI06 memory/context-poisoning checks in LLM mode.
- `tests/test_asi07_inter_agent_comm.py` - ASI07 inter-agent-communication checks (deterministic).
- `tests/test_asi07_inter_agent_comm_llm.py` - ASI07 inter-agent-communication checks in LLM mode.
- `tests/test_asi08_cascading_failures.py` - ASI08 cascading-failure checks (deterministic).
- `tests/test_asi08_cascading_failures_llm.py` - ASI08 cascading-failure checks in LLM mode.
- `tests/test_asi09_human_agent_trust_exploitation.py` - ASI09 human-agent-trust-exploitation checks (deterministic).
- `tests/test_asi09_human_agent_trust_exploitation_llm.py` - ASI09 human-agent-trust-exploitation checks in LLM mode.
- `tests/test_asi10_rogue_agents.py` - ASI10 rogue-agent checks (deterministic).
- `tests/test_asi10_rogue_agents_llm.py` - ASI10 rogue-agent checks in LLM mode.
- `tests/test_security_scanner.py` - security scanner unit tests.
- `tests/test_planner_executor.py` - deterministic planner/executor behavior tests.
- `tests/test_planner_executor_llm.py` - planner/executor checks in LLM mode.
- `tests/test_research_ops.py` - deterministic retrieval/synthesis behavior tests.
- `tests/test_research_ops_llm.py` - retrieval/synthesis checks in LLM mode.
- `tests/test_catalog_structure.py` - required file checks across catalog.
- `tests/test_integration_llm.py` - optional integration tests for local Ollama execution.
- `docker-compose.yml` - local Ollama service for speed-first LLM testing.

## Naming Conventions

- Project folder: `kebab-case` (example: `starter-kit`).
- Agent folder: `kebab-case` ending with `-agent`.
- Agent id in metadata: `<project>.<agent>`.

## Catalog Index

- `starter-kit`
  - `heartbeat-agent`: summarizes service heartbeat and emits a compact status report.
  - `classifier-agent`: maps short text to one intent label and confidence.
- `support-ops`
  - `triage-agent`: maps support requests to priority, category, and next action.
  - `reply-drafter-agent`: drafts customer-facing email subject/reply from triage fields.
- `security-ops`
  - `agentic-security-scanner-agent`: scans repo controls and maps findings to OWASP ASI categories.
- `planner-executor`
  - `planner-agent`: generates bounded execution steps and a risk level from a goal.
  - `executor-agent`: reports execution status and summary from planned steps.
- `research-ops`
  - `retrieval-agent`: extracts bounded notes from a query and optional sources.
  - `synthesis-agent`: turns research notes into audience-specific summary/actions.

## Update Rule

When adding or changing agents:

1. Update this `AGENTS.md` catalog index.
2. Update root `README.md` current projects section.
3. Update the project-level `README.md` affected by the change.
4. If runtime behavior changes, update tests in `/Users/macos-user/.projects/stack-research/agents/tests/`.
5. Keep `/Users/macos-user/.projects/stack-research/agents/docs/local-usage.md` in sync with run/test commands.
