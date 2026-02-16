# Contributor SOP

This SOP defines the standard workflow for adding or modifying agents in this repository.

## Scope

Use this SOP for:

- new agents
- runtime behavior changes
- security control changes
- new deterministic or LLM test suites

## 1) Scaffold and Catalog

1. Create agent directory:
   - `catalog/projects/<project>/agents/<agent-name>/`
2. Add required files:
   - `agent.yaml`
   - `prompts/system.md`
   - `workflows/runbook.md`
   - `examples/example-input.json`
   - `examples/example-output.json`
   - `tests/smoke.md`
3. Update catalog docs:
   - root `README.md`
   - `AGENTS.md`
   - project `README.md`

## 2) Runtime Implementation

1. Deterministic path:
   - add/modify logic in `local_agents/engine.py`
2. LLM path (if agent supports LLM mode):
   - add/modify logic in `local_agents/llm.py`
3. Exports/CLI:
   - update `local_agents/__init__.py` if needed
   - add/update scripts in `scripts/` if needed

## 3) Test Requirements (Mandatory)

For any new behavior/security change:

1. Add deterministic tests in `tests/`.
2. Add LLM-mode tests for equivalent behavior/security coverage.
3. LLM tests must gracefully skip when:
   - `AGENT_MODE != llm`, or
   - local Ollama endpoint is unavailable.
4. Add/extend OWASP ASI adversarial regression tests when relevant.
   - current baseline suites: ASI01 through ASI10.
5. If environment governance changes, update `policy/asi-control-baselines.json` and keep `tests/test_policy_pack.py` passing.

## 4) Security-Specific Requirements

1. Treat model and user-controlled text as untrusted.
2. Preserve strict output contracts (allowed keys/enums/limits).
3. Add regression tests for discovered security gaps before/with fixes.
4. For pipeline changes, include tests at component and composed pipeline level.

## 5) Validation Commands

Run from repository root:

```bash
make test
make test-security
```

If LLM behavior changed or new LLM tests were added:

```bash
make llm-up
make llm-pull
make test-integration-llm
make test-security-llm
```

Optional functional checks:

```bash
make run-support-pipeline-example
make run-support-pipeline-llm
make run-security-scan-example
```

## 6) Definition of Done

A change is done when:

1. deterministic suites pass
2. security suites pass
3. LLM suites pass (or are intentionally skipped only when unavailable)
4. docs are updated (`README.md`, `AGENTS.md`, `docs/local-usage.md` as applicable)
5. new commands are reflected in `Makefile` and docs
