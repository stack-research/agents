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

1. Add deterministic unit tests (default mode) under `tests/`.
2. Add LLM-mode tests for the same behavior/security path, with graceful skip when `AGENT_MODE!=llm` or Ollama is unavailable.
3. Add security regression tests for relevant OWASP ASI categories (current baseline: ASI01 through ASI10).
4. Ensure `make test` passes and update `make` targets when adding new security suites.
5. Update `docs/local-usage.md` with any new test commands.

**Full map of scripts, policy files, pipelines, and every `tests/test_*.py` file:** load the Agent Skill **`stack-research-agents-testing`** (directory **`.agents/skills/stack-research-agents-testing/`**, layout per [Where to scan](https://agentskills.io/client-implementation/adding-skills-support#where-to-scan) and format per [agentskills.io/specification](https://agentskills.io/specification.md)), or read its reference **[`.agents/skills/stack-research-agents-testing/references/repository-runtime-tests.md`](.agents/skills/stack-research-agents-testing/references/repository-runtime-tests.md)** directly. See also [`.agents/README.md`](.agents/README.md).

Contributor SOP:

- Canonical implementation workflow lives in `docs/contributor-sop.md`.
- Follow that SOP for scaffolding, runtime updates, deterministic+LLM tests, security regressions, and definition-of-done checks.

## Naming Conventions

- Project folder: `kebab-case` (example: `starter-kit`).
- Agent folder: `kebab-case` ending with `-agent`.
- Agent id in metadata: `<project>.<agent>`.

## Catalog index

The **canonical** list of projects and agents is **[`catalog/README.md`](catalog/README.md)** (human- and tool-readable; update it when the catalog changes). Do not duplicate the full index here.

## Update Rule

When adding or changing agents:

1. Update **`catalog/README.md`** (canonical catalog index).
2. Update root **`README.md`** current projects section.
3. Update the project-level **`catalog/projects/<project>/README.md`** affected by the change.
4. If runtime behavior changes, update tests under **`tests/`** and, when needed, the inventory in **`.agents/skills/stack-research-agents-testing/references/repository-runtime-tests.md`**.
5. Keep **`docs/local-usage.md`** in sync with run/test commands.
