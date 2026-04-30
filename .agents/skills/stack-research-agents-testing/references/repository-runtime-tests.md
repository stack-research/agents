# Repository-level runtime and tests

Canonical inventory for the stack-research `agents` repo. Paths are relative to repository root.

## Scripts (pipelines and runners)

- `scripts/run_agent.py` — local runner for implemented agents.
- `scripts/run_support_pipeline.py` — support triage→reply pipeline runner.
- `scripts/run_planner_executor_pipeline.py` — planner→executor pipeline runner.
- `scripts/run_workflow_pipeline.py` — workflow router→target→checkpoint pipeline runner.
- `scripts/run_governance_pipeline.py` — governance scope-validator→target→lineage-recorder→checkpoint pipeline runner.
- `scripts/run_resilience_pipeline.py` — resilience blast-radius-assessor→kill-path-auditor pipeline runner.
- `scripts/run_security_scan.py` — security scanner runner.
- `scripts/check_policy_pack.py` — runtime policy-pack enforcement check.

## Policy and infrastructure

- `policy/asi-control-baselines.json` — environment ASI control baseline policy pack.
- `local_agents/state.py` — Redis state store with graceful NoOp fallback for pipeline state persistence.
- `docker-compose.yml` — local Ollama and Redis services for LLM testing and state persistence.

## Core and pipeline tests

- `tests/test_engine.py` — unit tests for deterministic runtime behavior.
- `tests/test_support_pipeline.py` — pipeline composition unit test.
- `tests/test_planner_executor_pipeline.py` — planner→executor pipeline composition test.
- `tests/test_workflow_pipeline.py` — workflow-ops pipeline composition test.

## OWASP ASI adversarial regression (deterministic + LLM)

- `tests/test_asi01_goal_hijack.py` / `tests/test_asi01_goal_hijack_llm.py` — ASI01.
- `tests/test_asi02_tool_misuse.py` / `tests/test_asi02_tool_misuse_llm.py` — ASI02.
- `tests/test_asi03_identity_privilege_abuse.py` / `tests/test_asi03_identity_privilege_abuse_llm.py` — ASI03.
- `tests/test_asi04_supply_chain.py` / `tests/test_asi04_supply_chain_llm.py` — ASI04.
- `tests/test_asi05_unexpected_code_execution.py` / `tests/test_asi05_unexpected_code_execution_llm.py` — ASI05.
- `tests/test_asi06_memory_context_poisoning.py` / `tests/test_asi06_memory_context_poisoning_llm.py` — ASI06.
- `tests/test_asi07_inter_agent_comm.py` / `tests/test_asi07_inter_agent_comm_llm.py` — ASI07.
- `tests/test_asi08_cascading_failures.py` / `tests/test_asi08_cascading_failures_llm.py` — ASI08.
- `tests/test_asi09_human_agent_trust_exploitation.py` / `tests/test_asi09_human_agent_trust_exploitation_llm.py` — ASI09.
- `tests/test_asi10_rogue_agents.py` / `tests/test_asi10_rogue_agents_llm.py` — ASI10.
- `tests/test_security_scanner.py` — security scanner unit tests.

## Domain and feature tests

- `tests/test_planner_executor.py` / `tests/test_planner_executor_llm.py` — planner/executor.
- `tests/test_research_ops.py` / `tests/test_research_ops_llm.py` — research-ops.
- `tests/test_knowledge_ops.py` / `tests/test_knowledge_ops_llm.py` — knowledge-ops.
- `tests/test_qa_ops.py` / `tests/test_qa_ops_llm.py` — QA-ops.
- `tests/test_workflow_ops.py` / `tests/test_workflow_ops_llm.py` / `tests/test_workflow_pipeline_llm.py` — workflow-ops.
- `tests/test_support_ops.py` / `tests/test_support_ops_llm.py` — support-ops.
- `tests/test_control_ops.py` / `tests/test_control_ops_llm.py` — control-ops.
- `tests/test_governance_pipeline.py` / `tests/test_resilience_pipeline.py` — governance and resilience pipelines.
- `tests/test_data_ops.py` — data-ops.
- `tests/test_code_ops.py` — code-ops.
- `tests/test_observability_ops.py` / `tests/test_observability_ops_llm.py` — observability-ops.
- `tests/test_eval_ops.py` / `tests/test_eval_ops_llm.py` — eval-ops.
- `tests/test_experiment_ops.py` / `tests/test_experiment_ops_llm.py` — experiment-ops.
- `tests/test_artifact_ops.py` / `tests/test_artifact_ops_llm.py` — artifact-ops.
- `tests/test_agent_incident_drill.py` / `tests/test_compare_agent_incident_drill_scorecards.py` — agent incident drill.

## Policy, schema, catalog, integration

- `tests/test_policy_pack.py` — policy pack structure and baseline presence.
- `tests/test_policy_enforcement.py` — runtime mode policy enforcement.
- `tests/test_agent_schema.py` — `agent.yaml` schema consistency.
- `tests/test_catalog_structure.py` — required files across catalog.
- `tests/test_state.py` — state store (NoOp, pipeline helpers, Redis).
- `tests/test_integration_llm.py` — optional integration tests for local Ollama.
