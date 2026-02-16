.PHONY: test test-verbose test-security test-security-llm test-integration-llm llm-up llm-pull llm-down run-heartbeat-example run-classifier-example run-triage-example run-reply-drafter-example run-security-scan-example run-support-pipeline-example run-heartbeat-llm run-classifier-llm run-triage-llm run-reply-drafter-llm run-support-pipeline-llm

test:
	python3 -m unittest discover -s tests

test-verbose:
	python3 -m unittest discover -s tests -v

test-security:
	python3 -m unittest tests.test_asi01_goal_hijack tests.test_asi02_tool_misuse tests.test_asi03_identity_privilege_abuse tests.test_asi04_supply_chain tests.test_asi05_unexpected_code_execution tests.test_asi06_memory_context_poisoning tests.test_asi07_inter_agent_comm tests.test_asi08_cascading_failures tests.test_security_scanner -v

test-security-llm:
	AGENT_MODE=llm python3 -m unittest tests.test_asi01_goal_hijack_llm tests.test_asi02_tool_misuse_llm tests.test_asi03_identity_privilege_abuse_llm tests.test_asi04_supply_chain_llm tests.test_asi05_unexpected_code_execution_llm tests.test_asi06_memory_context_poisoning_llm tests.test_asi07_inter_agent_comm_llm tests.test_asi08_cascading_failures_llm -v

test-integration-llm:
	AGENT_MODE=llm python3 -m unittest tests.test_integration_llm -v

llm-up:
	docker compose up -d ollama

llm-pull:
	./scripts/pull_fast_model.sh

llm-down:
	docker compose down

run-heartbeat-example:
	python3 scripts/run_agent.py --agent starter-kit.heartbeat-agent --input catalog/projects/starter-kit/agents/heartbeat-agent/examples/example-input.json --pretty

run-classifier-example:
	python3 scripts/run_agent.py --agent starter-kit.classifier-agent --input catalog/projects/starter-kit/agents/classifier-agent/examples/example-input.json --pretty

run-triage-example:
	python3 scripts/run_agent.py --agent support-ops.triage-agent --input catalog/projects/support-ops/agents/triage-agent/examples/example-input.json --pretty

run-reply-drafter-example:
	python3 scripts/run_agent.py --agent support-ops.reply-drafter-agent --input catalog/projects/support-ops/agents/reply-drafter-agent/examples/example-input.json --pretty

run-security-scan-example:
	python3 scripts/run_security_scan.py --target-path . --pretty

run-support-pipeline-example:
	python3 scripts/run_support_pipeline.py --input catalog/projects/support-ops/examples/pipeline-input.json --pretty

run-heartbeat-llm:
	AGENT_MODE=llm python3 scripts/run_agent.py --agent starter-kit.heartbeat-agent --input catalog/projects/starter-kit/agents/heartbeat-agent/examples/example-input.json --pretty

run-classifier-llm:
	AGENT_MODE=llm python3 scripts/run_agent.py --agent starter-kit.classifier-agent --input catalog/projects/starter-kit/agents/classifier-agent/examples/example-input.json --pretty

run-triage-llm:
	AGENT_MODE=llm python3 scripts/run_agent.py --agent support-ops.triage-agent --input catalog/projects/support-ops/agents/triage-agent/examples/example-input.json --pretty

run-reply-drafter-llm:
	AGENT_MODE=llm python3 scripts/run_agent.py --agent support-ops.reply-drafter-agent --input catalog/projects/support-ops/agents/reply-drafter-agent/examples/example-input.json --pretty

run-support-pipeline-llm:
	AGENT_MODE=llm python3 scripts/run_support_pipeline.py --input catalog/projects/support-ops/examples/pipeline-input.json --pretty
