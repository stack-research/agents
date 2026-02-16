.PHONY: test test-verbose test-security test-security-llm test-integration-llm llm-up llm-pull llm-down check-policy-pack check-policy-pack-llm verify-env run-heartbeat-example run-classifier-example run-triage-example run-reply-drafter-example run-summary-example run-handoff-example run-planner-example run-executor-example run-retrieval-example run-synthesis-example run-test-case-generator-example run-regression-triage-example run-router-example run-checkpoint-example run-security-scan-example run-support-pipeline-example run-planner-executor-pipeline-example run-workflow-pipeline-example run-heartbeat-llm run-classifier-llm run-triage-llm run-reply-drafter-llm run-summary-llm run-handoff-llm run-planner-llm run-executor-llm run-retrieval-llm run-synthesis-llm run-test-case-generator-llm run-regression-triage-llm run-router-llm run-checkpoint-llm run-support-pipeline-llm run-planner-executor-pipeline-llm run-workflow-pipeline-llm

test:
	python3 -m unittest discover -s tests

test-verbose:
	python3 -m unittest discover -s tests -v

test-security:
	python3 -m unittest tests.test_asi01_goal_hijack tests.test_asi02_tool_misuse tests.test_asi03_identity_privilege_abuse tests.test_asi04_supply_chain tests.test_asi05_unexpected_code_execution tests.test_asi06_memory_context_poisoning tests.test_asi07_inter_agent_comm tests.test_asi08_cascading_failures tests.test_asi09_human_agent_trust_exploitation tests.test_asi10_rogue_agents tests.test_security_scanner -v

test-security-llm: check-policy-pack-llm
	AGENT_MODE=llm python3 -m unittest tests.test_asi01_goal_hijack_llm tests.test_asi02_tool_misuse_llm tests.test_asi03_identity_privilege_abuse_llm tests.test_asi04_supply_chain_llm tests.test_asi05_unexpected_code_execution_llm tests.test_asi06_memory_context_poisoning_llm tests.test_asi07_inter_agent_comm_llm tests.test_asi08_cascading_failures_llm tests.test_asi09_human_agent_trust_exploitation_llm tests.test_asi10_rogue_agents_llm -v

test-integration-llm: check-policy-pack-llm
	AGENT_MODE=llm python3 -m unittest tests.test_integration_llm -v

llm-up:
	docker compose up -d ollama

llm-pull:
	./scripts/pull_fast_model.sh

llm-down:
	docker compose down

check-policy-pack:
	python3 scripts/check_policy_pack.py --env $${POLICY_ENV:-dev} --mode $${AGENT_MODE:-deterministic}

check-policy-pack-llm:
	python3 scripts/check_policy_pack.py --env $${POLICY_ENV:-dev} --mode llm

verify-env:
	@echo "verify-env: POLICY_ENV=$${POLICY_ENV:-dev}, AGENT_MODE=$${AGENT_MODE:-deterministic}"
	$(MAKE) check-policy-pack POLICY_ENV=$${POLICY_ENV:-dev} AGENT_MODE=$${AGENT_MODE:-deterministic}
	$(MAKE) test
	@if [ "$${POLICY_ENV:-dev}" != "dev" ]; then \
		echo "Running deterministic security suite for $${POLICY_ENV:-dev}"; \
		$(MAKE) test-security; \
	else \
		echo "Skipping deterministic security suite in dev (run make test-security manually if needed)"; \
	fi

run-heartbeat-example:
	python3 scripts/run_agent.py --agent starter-kit.heartbeat-agent --input catalog/projects/starter-kit/agents/heartbeat-agent/examples/example-input.json --pretty

run-classifier-example:
	python3 scripts/run_agent.py --agent starter-kit.classifier-agent --input catalog/projects/starter-kit/agents/classifier-agent/examples/example-input.json --pretty

run-triage-example:
	python3 scripts/run_agent.py --agent support-ops.triage-agent --input catalog/projects/support-ops/agents/triage-agent/examples/example-input.json --pretty

run-reply-drafter-example:
	python3 scripts/run_agent.py --agent support-ops.reply-drafter-agent --input catalog/projects/support-ops/agents/reply-drafter-agent/examples/example-input.json --pretty

run-summary-example:
	python3 scripts/run_agent.py --agent support-ops.summary-agent --input catalog/projects/support-ops/agents/summary-agent/examples/example-input.json --pretty

run-handoff-example:
	python3 scripts/run_agent.py --agent support-ops.handoff-agent --input catalog/projects/support-ops/agents/handoff-agent/examples/example-input.json --pretty

run-planner-example:
	python3 scripts/run_agent.py --agent planner-executor.planner-agent --input catalog/projects/planner-executor/agents/planner-agent/examples/example-input.json --pretty

run-executor-example:
	python3 scripts/run_agent.py --agent planner-executor.executor-agent --input catalog/projects/planner-executor/agents/executor-agent/examples/example-input.json --pretty

run-retrieval-example:
	python3 scripts/run_agent.py --agent research-ops.retrieval-agent --input catalog/projects/research-ops/agents/retrieval-agent/examples/example-input.json --pretty

run-synthesis-example:
	python3 scripts/run_agent.py --agent research-ops.synthesis-agent --input catalog/projects/research-ops/agents/synthesis-agent/examples/example-input.json --pretty

run-test-case-generator-example:
	python3 scripts/run_agent.py --agent qa-ops.test-case-generator-agent --input catalog/projects/qa-ops/agents/test-case-generator-agent/examples/example-input.json --pretty

run-regression-triage-example:
	python3 scripts/run_agent.py --agent qa-ops.regression-triage-agent --input catalog/projects/qa-ops/agents/regression-triage-agent/examples/example-input.json --pretty

run-router-example:
	python3 scripts/run_agent.py --agent workflow-ops.router-agent --input catalog/projects/workflow-ops/agents/router-agent/examples/example-input.json --pretty

run-checkpoint-example:
	python3 scripts/run_agent.py --agent workflow-ops.checkpoint-agent --input catalog/projects/workflow-ops/agents/checkpoint-agent/examples/example-input.json --pretty

run-security-scan-example:
	python3 scripts/run_security_scan.py --target-path . --pretty

run-support-pipeline-example:
	python3 scripts/run_support_pipeline.py --input catalog/projects/support-ops/examples/pipeline-input.json --pretty

run-planner-executor-pipeline-example:
	python3 scripts/run_planner_executor_pipeline.py --input catalog/projects/planner-executor/examples/pipeline-input.json --pretty

run-workflow-pipeline-example:
	python3 scripts/run_workflow_pipeline.py --input catalog/projects/workflow-ops/examples/pipeline-input.json --pretty

run-heartbeat-llm: check-policy-pack-llm
	AGENT_MODE=llm python3 scripts/run_agent.py --agent starter-kit.heartbeat-agent --input catalog/projects/starter-kit/agents/heartbeat-agent/examples/example-input.json --pretty

run-classifier-llm: check-policy-pack-llm
	AGENT_MODE=llm python3 scripts/run_agent.py --agent starter-kit.classifier-agent --input catalog/projects/starter-kit/agents/classifier-agent/examples/example-input.json --pretty

run-triage-llm: check-policy-pack-llm
	AGENT_MODE=llm python3 scripts/run_agent.py --agent support-ops.triage-agent --input catalog/projects/support-ops/agents/triage-agent/examples/example-input.json --pretty

run-reply-drafter-llm: check-policy-pack-llm
	AGENT_MODE=llm python3 scripts/run_agent.py --agent support-ops.reply-drafter-agent --input catalog/projects/support-ops/agents/reply-drafter-agent/examples/example-input.json --pretty

run-summary-llm: check-policy-pack-llm
	AGENT_MODE=llm python3 scripts/run_agent.py --agent support-ops.summary-agent --input catalog/projects/support-ops/agents/summary-agent/examples/example-input.json --pretty

run-handoff-llm: check-policy-pack-llm
	AGENT_MODE=llm python3 scripts/run_agent.py --agent support-ops.handoff-agent --input catalog/projects/support-ops/agents/handoff-agent/examples/example-input.json --pretty

run-planner-llm: check-policy-pack-llm
	AGENT_MODE=llm python3 scripts/run_agent.py --agent planner-executor.planner-agent --input catalog/projects/planner-executor/agents/planner-agent/examples/example-input.json --pretty

run-executor-llm: check-policy-pack-llm
	AGENT_MODE=llm python3 scripts/run_agent.py --agent planner-executor.executor-agent --input catalog/projects/planner-executor/agents/executor-agent/examples/example-input.json --pretty

run-retrieval-llm: check-policy-pack-llm
	AGENT_MODE=llm python3 scripts/run_agent.py --agent research-ops.retrieval-agent --input catalog/projects/research-ops/agents/retrieval-agent/examples/example-input.json --pretty

run-synthesis-llm: check-policy-pack-llm
	AGENT_MODE=llm python3 scripts/run_agent.py --agent research-ops.synthesis-agent --input catalog/projects/research-ops/agents/synthesis-agent/examples/example-input.json --pretty

run-test-case-generator-llm: check-policy-pack-llm
	AGENT_MODE=llm python3 scripts/run_agent.py --agent qa-ops.test-case-generator-agent --input catalog/projects/qa-ops/agents/test-case-generator-agent/examples/example-input.json --pretty

run-regression-triage-llm: check-policy-pack-llm
	AGENT_MODE=llm python3 scripts/run_agent.py --agent qa-ops.regression-triage-agent --input catalog/projects/qa-ops/agents/regression-triage-agent/examples/example-input.json --pretty

run-router-llm: check-policy-pack-llm
	AGENT_MODE=llm python3 scripts/run_agent.py --agent workflow-ops.router-agent --input catalog/projects/workflow-ops/agents/router-agent/examples/example-input.json --pretty

run-checkpoint-llm: check-policy-pack-llm
	AGENT_MODE=llm python3 scripts/run_agent.py --agent workflow-ops.checkpoint-agent --input catalog/projects/workflow-ops/agents/checkpoint-agent/examples/example-input.json --pretty

run-support-pipeline-llm: check-policy-pack-llm
	AGENT_MODE=llm python3 scripts/run_support_pipeline.py --input catalog/projects/support-ops/examples/pipeline-input.json --pretty

run-planner-executor-pipeline-llm: check-policy-pack-llm
	AGENT_MODE=llm python3 scripts/run_planner_executor_pipeline.py --input catalog/projects/planner-executor/examples/pipeline-input.json --pretty

run-workflow-pipeline-llm: check-policy-pack-llm
	AGENT_MODE=llm python3 scripts/run_workflow_pipeline.py --input catalog/projects/workflow-ops/examples/pipeline-input.json --pretty
