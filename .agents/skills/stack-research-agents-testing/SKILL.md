---
name: stack-research-agents-testing
description: Maps scripts, policy packs, pipelines, and tests for the stack-research agents catalog repo. Use when adding or changing agents, pipelines, Makefile or verify-env targets, OWASP ASI regression tests, policy enforcement, catalog schema checks, Ollama/Redis test wiring, or docs/local-usage.md test commands. Keywords: run_agent, ASI01-ASI10, test_engine, pipeline, security scanner, contributor-sop.
license: Repository default
metadata:
  repository: stack-research/agents
---

# Stack-research agents — testing and runtime map

## When to use this skill

- You are touching **`local_agents/`** (engine, LLM, state) or **pipelines** under `scripts/run_*`.
- You add a **new catalog project** or agent and need the matching **`tests/test_*`** and optional **`tests/test_*_llm.py`** pattern.
- You extend **ASI** coverage, **policy pack**, or **Makefile** `test` / `test-security` targets.
- You must keep **`docs/local-usage.md`** aligned with new unittest or `make` commands.

## Workflow (short)

1. Read **[references/repository-runtime-tests.md](references/repository-runtime-tests.md)** for the full file inventory (scripts, `tests/*.py`, policy, docker).
2. Follow **`docs/contributor-sop.md`** for scaffolding, deterministic + LLM tests, and definition of done.
3. For a new **domain** project mirroring existing ops: add `tests/test_<domain>_ops.py` and `tests/test_<domain>_ops_llm.py` (skip when `AGENT_MODE!=llm` or Ollama unavailable), wire **`run_agent`** / **`llm.py`**, and document commands in **`docs/local-usage.md`**.
4. Run **`make test`** (and **`make verify-env`** before commit if that is the team norm).

## Progressive disclosure

- Full enumerated paths and descriptions: **[references/repository-runtime-tests.md](references/repository-runtime-tests.md)**.
- Catalog of agents (projects and agent names): repo root **`catalog/README.md`**.

## Validation (optional)

To validate this skill directory against the Agent Skills format:

```bash
skills-ref validate ./.agents/skills/stack-research-agents-testing
```

Install or use [agentskills skills-ref](https://github.com/agentskills/agentskills/tree/main/skills-ref) as documented upstream.
