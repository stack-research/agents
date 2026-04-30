# Agent catalog index

This file is the **canonical catalog index** for projects and agents under `catalog/projects/`. GitHub renders it when browsing the `catalog/` directory. Update it whenever you add or rename a project or agent (see [AGENTS.md](../AGENTS.md) Update Rule). For the testing/runtime file map Agent Skill, see [`../.agents/README.md`](../.agents/README.md).

Each project lives in `catalog/projects/<project>/` with agents in `agents/<agent-name>/`.

## Projects and agents

- `starter-kit`
  - `heartbeat-agent`: summarizes service heartbeat and emits a compact status report.
  - `classifier-agent`: maps short text to one intent label and confidence.
- `support-ops`
  - `triage-agent`: maps support requests to priority, category, and next action.
  - `reply-drafter-agent`: drafts customer-facing email subject/reply from triage fields.
  - `summary-agent`: summarizes weekly support ticket trends and recommended follow-up actions.
  - `handoff-agent`: generates shift-transition briefs from active incidents.
- `security-ops`
  - `agentic-security-scanner-agent`: scans repo controls and maps findings to OWASP ASI categories.
- `planner-executor`
  - `planner-agent`: generates bounded execution steps and a risk level from a goal.
  - `executor-agent`: reports execution status and summary from planned steps.
- `research-ops`
  - `source-planner-agent`: plans what evidence to fetch next from query and current evidence.
  - `retrieval-agent`: extracts bounded notes from a query and optional sources.
  - `gap-detector-agent`: finds unsupported assertions and recommends targeted evidence collection.
  - `synthesis-agent`: turns research notes into audience-specific summary/actions.
- `knowledge-ops`
  - `evidence-ranker-agent`: scores evidence quality for downstream decisions.
  - `claim-trace-agent`: maps assertions to support states and evidence references.
  - `memory-curator-agent`: curates reusable memory facts with confidence and expiry horizon.
  - `temporal-watch-agent`: compares snapshots over time and emits drift signals.
- `qa-ops`
  - `test-case-generator-agent`: turns feature requirements into bounded QA test scenarios.
  - `regression-triage-agent`: maps failures to probable cause, severity, and next actions.
- `eval-ops`
  - `benchmark-curator-agent`: deduplicates candidate eval cases and lists coverage gaps for a benchmark suite.
  - `regression-score-agent`: compares baseline and current eval scores to flag regressions with a verdict.
  - `quality-drift-reporter-agent`: summarizes metric drift and trend across ordered time windows.
- `experiment-ops`
  - `hypothesis-registration-agent`: normalizes and registers a hypothesis with stable id and ambiguity flags.
  - `experiment-plan-agent`: emits bounded variants, metrics, guardrails, and next steps from a hypothesis.
  - `result-adjudication-agent`: adjudicates observed metrics against optional explicit success criteria.
- `artifact-ops`
  - `artifact-inventory-agent`: normalizes run artifacts with roles and digests for reproducible bundles.
  - `bundle-manifest-agent`: emits canonical manifest entries and aggregate `bundle_root_sha256`.
  - `bundle-seal-agent`: seals bundle metadata with lineage attachment and verification checklist.
- `workflow-ops`
  - `router-agent`: routes incoming tasks to a best-fit agent with priority.
  - `dependency-router-agent`: routes tasks based on dependency readiness and missing prerequisites.
  - `retry-policy-agent`: decides retry, backoff, escalation, or stop on failed stages.
  - `checkpoint-agent`: records workflow progress with structured checkpoint summaries.
- `control-ops`
  - `lineage-recorder-agent`: structures decision events into append-only lineage records.
  - `scope-validator-agent`: validates proposed actions against governance requirements with pass/review/fail gating.
  - `exception-policy-agent`: evaluates controlled policy exceptions with owner/expiry constraints.
  - `approval-memory-agent`: records approval state with approver, timestamps, and expiration status.
  - `blast-radius-assessor-agent`: estimates blast radius from weighted permission, dependency, and resource-limit factors.
  - `kill-path-auditor-agent`: audits shutdown capabilities against the four-level kill path spectrum and optional ISO `last_tested` recency.
- `data-ops`
  - `schema-drift-detector-agent`: detects schema changes between versions and classifies drift severity.
  - `data-validator-agent`: validates data records against rules and reports violations.
- `code-ops`
  - `code-reviewer-agent`: reviews code diffs for security, correctness, and style issues.
  - `pr-summary-agent`: summarizes PR changes for reviewers with risk assessment.
- `observability-ops`
  - `log-analyzer-agent`: analyzes log entries for patterns and anomalies.
  - `slo-reporter-agent`: generates SLO compliance reports from service metrics and targets.
  - `change-correlation-agent`: correlates metric/log shifts with deploy and config events.
  - `alert-tuner-agent`: suggests threshold tuning from alert noise patterns.
- `agent-incident-drill`
  - Scenario project that composes existing agents into a measurable incident-response drill with governance, lineage, blast-radius, kill-path, rollback, and scorecard artifacts. Example inputs include support-export, data-corruption, auth-lockout, and supply-chain scenarios; `scripts/compare_agent_incident_drill_scorecards.py` diffs scorecards across saved runs.
