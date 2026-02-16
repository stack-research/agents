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
4. `planner-executor`
   - `planner-agent`: converts a goal and constraints into a bounded execution plan.
   - `executor-agent`: summarizes progress and completion state from plan steps.
5. `research-ops`
   - `retrieval-agent`: extracts bounded notes from query + source hints.
   - `synthesis-agent`: converts notes into audience-aware summary and actions.
6. `qa-ops`
   - `test-case-generator-agent`: generates bounded QA scenarios from feature requirements.
   - `regression-triage-agent`: classifies regression cause/severity and proposes follow-up actions.
7. `workflow-ops`
   - `router-agent`: routes work items to the best-fit agent with a priority.
   - `checkpoint-agent`: records workflow stage/status checkpoints for traceability.

## Run Agents Locally

- `python3 scripts/run_agent.py --agent starter-kit.heartbeat-agent --input catalog/projects/starter-kit/agents/heartbeat-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent starter-kit.classifier-agent --input catalog/projects/starter-kit/agents/classifier-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent support-ops.triage-agent --input catalog/projects/support-ops/agents/triage-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent support-ops.reply-drafter-agent --input catalog/projects/support-ops/agents/reply-drafter-agent/examples/example-input.json --pretty`
- `python3 scripts/run_support_pipeline.py --input catalog/projects/support-ops/examples/pipeline-input.json --pretty`
- `python3 scripts/run_agent.py --agent planner-executor.planner-agent --input catalog/projects/planner-executor/agents/planner-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent planner-executor.executor-agent --input catalog/projects/planner-executor/agents/executor-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent research-ops.retrieval-agent --input catalog/projects/research-ops/agents/retrieval-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent research-ops.synthesis-agent --input catalog/projects/research-ops/agents/synthesis-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent qa-ops.test-case-generator-agent --input catalog/projects/qa-ops/agents/test-case-generator-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent qa-ops.regression-triage-agent --input catalog/projects/qa-ops/agents/regression-triage-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent workflow-ops.router-agent --input catalog/projects/workflow-ops/agents/router-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent workflow-ops.checkpoint-agent --input catalog/projects/workflow-ops/agents/checkpoint-agent/examples/example-input.json --pretty`
- `python3 scripts/run_planner_executor_pipeline.py --input catalog/projects/planner-executor/examples/pipeline-input.json --pretty`
- `python3 scripts/run_security_scan.py --target-path . --pretty`
- `AGENT_MODE=llm python3 scripts/run_support_pipeline.py --input catalog/projects/support-ops/examples/pipeline-input.json --pretty`
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

## Test Suite

- `python3 -m unittest discover -s tests -v`
- `make test`
- `make test-security` (ASI01+ASI02+ASI03+ASI04+ASI05+ASI06+ASI07+ASI08+ASI09+ASI10 adversarial checks + scanner tests)
- `make test-security-llm` (ASI01+ASI02+ASI03+ASI04+ASI05+ASI06+ASI07+ASI08+ASI09+ASI10 adversarial checks against local LLM)
- `make test-integration-llm` (optional LLM-backed checks)

The test suite currently includes:

- behavior tests for local agent runtime logic.
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
- security scanner tests.
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

## Add a New Agent

1. Create `catalog/projects/<project>/agents/<agent-name>/`.
2. Add `agent.yaml` with purpose, IO contract, and runtime assumptions.
3. Add prompt/workflow/example/test docs.
4. Update `catalog/projects/<project>/README.md`.
5. Update root `README.md` and `AGENTS.md` catalog sections.

## Next Ideas

- Add schema checks for `agent.yaml` files in CI.
- Add a `summary-agent` for support weekly trend rollups.
