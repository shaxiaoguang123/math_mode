"""Command entry point for deterministic MathMode services."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .policy import audit_policy, load_policy
from .io import read_json, write_json
from .contracts import validate, validate_modeling_bundle
from .schema_catalog import catalog
from .workspace import initialize
from .state import StateStore
from .runner import execute_model, verify_run
from .validation import independently_validate, audit_evidence
from .freeze import freeze_results, thaw, verify_freeze
from .lineage import ArtifactRegistry


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    policy = commands.add_parser("policy", help="Verify policy source snapshots and template hash")
    policy.add_argument("--policy", type=Path)
    policy.add_argument("--workspace", type=Path, required=True)
    policy.add_argument("--report", type=Path)
    check = commands.add_parser("validate", help="Validate contract syntax and semantics")
    check.add_argument("contract", choices=[*catalog(), "modeling_bundle"])
    check.add_argument("path", type=Path)
    check.add_argument("--workspace", type=Path)
    check.add_argument("--report", type=Path)
    init = commands.add_parser("init", help="Create a private workspace with original input snapshots")
    init.add_argument("--case-id", required=True)
    init.add_argument("--inputs", type=Path, required=True, help="JSON list of explicit input declarations")
    init.add_argument("--destination", type=Path)
    init.add_argument("--kind", choices=["competition", "fixture"], default="competition")
    init.add_argument("--mode", choices=["autopilot", "human_gate"], default="autopilot")
    init.add_argument("--profile", choices=["lean", "submission"], default="lean")
    init.add_argument("--blind-reference-mode", action=argparse.BooleanOptionalAction, default=True,
                      help="Fix reference blindness at workspace creation; disable explicitly for non-blind work")
    status = commands.add_parser("status", help="Recheck registered artifact hashes on resume")
    status.add_argument("--workspace", type=Path, required=True)
    status.add_argument("--report", type=Path)
    run = commands.add_parser("run", help="Execute a model spec with fresh snapshots and real process records")
    run.add_argument("--workspace", type=Path, required=True)
    run.add_argument("--spec", required=True, help="Workspace-relative model spec")
    run.add_argument("--role", choices=["main", "baseline", "probe", "validator", "fallback"], default="main")
    run.add_argument("--interpreter")
    run.add_argument("--retry-of")
    verify = commands.add_parser("verify-run", help="Recheck process record and all recorded artifact bytes")
    verify.add_argument("--workspace", type=Path, required=True)
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--report", type=Path)
    independent = commands.add_parser("independent-validate", help="Recompute evidence in a source-free validator workspace")
    independent.add_argument("--workspace", type=Path, required=True)
    independent.add_argument("--main-run", required=True)
    independent.add_argument("--baseline-run", required=True)
    independent.add_argument("--interpreter")
    evidence = commands.add_parser("evidence", help="Recheck independent computation and all upstream hashes")
    evidence.add_argument("--workspace", type=Path, required=True)
    evidence.add_argument("--validation", required=True)
    evidence.add_argument("--report", type=Path)
    freeze = commands.add_parser("freeze", help="Freeze numbers from verified source locators")
    freeze.add_argument("--workspace", type=Path, required=True)
    freeze.add_argument("--request", type=Path, required=True)
    freeze.add_argument("--evidence", required=True)
    unfreeze = commands.add_parser("thaw", help="Preserve a snapshot and invalidate its consumers")
    unfreeze.add_argument("--workspace", type=Path, required=True)
    unfreeze.add_argument("--question-id", required=True)
    unfreeze.add_argument("--actor-id", required=True)
    unfreeze.add_argument("--reason", required=True)
    frozen = commands.add_parser("verify-freeze", help="Recheck the active snapshot and evidence graph")
    frozen.add_argument("--workspace", type=Path, required=True)
    frozen.add_argument("--question-id", required=True)
    stale = commands.add_parser("refresh", help="Persist transitive STALE status and block affected gates")
    stale.add_argument("--workspace", type=Path, required=True)
    agent = commands.add_parser("agent", help="Execute a scoped role task through the configured Codex CLI")
    agent.add_argument("--workspace", type=Path, required=True)
    agent.add_argument("--task", type=Path, required=True)
    agent.add_argument("--timeout", type=float, default=300)
    agent_check = commands.add_parser("verify-agent", help="Recheck a real reasoning handoff and all recorded hashes")
    agent_check.add_argument("--workspace", type=Path, required=True)
    agent_check.add_argument("--task-id", required=True)
    schedule = commands.add_parser("advance-agents", help="Advance a role DAG with fresh phase prerequisites")
    schedule.add_argument("--workspace", type=Path, required=True)
    schedule.add_argument("--schedule", type=Path, required=True)
    schedule.add_argument("--max-tasks", type=int, default=1)
    schedule.add_argument("--timeout", type=float, default=300)
    human = commands.add_parser("human-decision", help="Read an actual terminal response to a prepared screened decision request")
    human.add_argument("--workspace", type=Path, required=True)
    human.add_argument("--request-id", required=True)
    human.add_argument("--actor-id", required=True, help="Local pseudonym for the user supplying this terminal response")
    human_check = commands.add_parser("verify-human-decision", help="Recheck the current decision against its actual host event")
    human_check.add_argument("--workspace", type=Path, required=True)
    human_check.add_argument("--decision", required=True)
    data = commands.add_parser("data-audit", help="Compute and register actual original-input statistics")
    data.add_argument("--workspace", type=Path, required=True)
    disposition = commands.add_parser("verify-disposition", help="Verify independently reviewed limited continuation and retained restrictions")
    disposition.add_argument("--workspace", type=Path, required=True)
    disposition.add_argument("--source", required=True)
    disposition.add_argument("--proposal", required=True)
    disposition.add_argument("--review", required=True)
    disposition.add_argument("--question-id")
    assessment = commands.add_parser("assess-assumptions", help="Execute predeclared perturbations and independently assess assumptions")
    assessment.add_argument("--workspace", type=Path, required=True)
    assessment.add_argument("--plan", required=True)
    assessment.add_argument("--interpreter")
    assessment_check = commands.add_parser("verify-assumptions", help="Recompute an assumption assessment from actual independent evidence")
    assessment_check.add_argument("--workspace", type=Path, required=True)
    assessment_check.add_argument("--assessment", required=True)
    diagnosis = commands.add_parser("verify-diagnosis", help="Verify independent terminal failure diagnosis; does not approve a repair")
    diagnosis.add_argument("--workspace", type=Path, required=True)
    diagnosis.add_argument("--diagnosis", required=True)
    code_repair = commands.add_parser("verify-code-repair", help="Verify a staged code repair and independent review; does not execute it")
    code_repair.add_argument("--workspace", type=Path, required=True)
    code_repair.add_argument("--request", required=True)
    repair_run = commands.add_parser("run-code-repair", help="Execute or adopt an independently reviewed repair with a preserved retry budget")
    repair_run.add_argument("--workspace", type=Path, required=True)
    repair_run.add_argument("--request", required=True)
    repair_run.add_argument("--interpreter")
    probe = commands.add_parser("probe-report", help="Compute risk verdicts from a predeclared plan and actual run")
    probe.add_argument("--workspace", type=Path, required=True)
    probe.add_argument("--manifest", required=True)
    probe.add_argument("--report", type=Path)
    baseline = commands.add_parser("seal-baseline", help="Seal actual frame/models/code/results/paper before same-problem references")
    baseline.add_argument("--workspace", type=Path, required=True)
    baseline.add_argument("--question-id", required=True)
    baseline.add_argument("--framer-task", required=True)
    baseline.add_argument("--frame", required=True)
    baseline.add_argument("--writer-task", required=True)
    baseline.add_argument("--paper", action="append", required=True)
    case_baseline = commands.add_parser("seal-case-baseline", help="Bind all framed question checkpoints before same-problem access")
    case_baseline.add_argument("--workspace", type=Path, required=True)
    case_baseline.add_argument("--baseline-id", action="append", required=True)
    baseline_check = commands.add_parser("verify-baseline", help="Check immutable question or whole-case baseline history")
    baseline_check.add_argument("--workspace", type=Path, required=True)
    baseline_check.add_argument("--baseline-id", required=True)
    reference = commands.add_parser("admit-reference", help="Record explicit reference classification before retrieval")
    reference.add_argument("--workspace", type=Path, required=True)
    reference.add_argument("--question-id", required=True)
    reference.add_argument("--source", required=True)
    reference.add_argument("--classification", choices=["general", "same-problem"], required=True)
    reference.add_argument("--baseline-id")
    retrieval = commands.add_parser("retrieve-reference", help="Admit HTTP requests and preserve verified reference response snapshots")
    retrieval.add_argument("--workspace", type=Path, required=True)
    retrieval.add_argument("--question-id", required=True)
    retrieval.add_argument("--source", required=True)
    retrieval.add_argument("--classification", choices=["general", "same-problem"], required=True)
    retrieval.add_argument("--baseline-id")
    retrieval.add_argument("--retrieval-id")
    retrieval.add_argument("--timeout", type=float, default=30)
    retrieval.add_argument("--max-bytes", type=int, default=20_000_000)
    retrieval.add_argument("--max-redirects", type=int, default=5)
    retrieval_check = commands.add_parser("verify-reference", help="Verify an actual reference receipt without fetching again")
    retrieval_check.add_argument("--workspace", type=Path, required=True)
    retrieval_check.add_argument("--receipt", required=True)
    recovery = commands.add_parser("recover", help="Archive an interrupted execution after observing stopped owner/child processes")
    recovery.add_argument("--workspace", type=Path, required=True)
    recovery.add_argument("--kind", choices=["run", "agent"], required=True)
    recovery.add_argument("--execution-id", required=True)
    recovery.add_argument("--reason", required=True)
    lock_recovery = commands.add_parser("recover-lock", help="Preserve and release a lock only after its recorded owner has stopped")
    lock_recovery.add_argument("--workspace", type=Path, required=True)
    lock_recovery.add_argument("--reason", required=True)
    lock_recovery.add_argument("--scope", choices=["state", "workflow"], default="state")
    workflow = commands.add_parser("workflow", help="Observe all evidence gates or advance one admissible numerical transition")
    workflow.add_argument("--workspace", type=Path, required=True)
    workflow.add_argument("--plan", type=Path, required=True)
    workflow.add_argument("--advance", action="store_true")
    workflow.add_argument("--no-agent", action="store_true", help="Run deterministic transitions and pause for missing role handoffs")
    workflow.add_argument("--interpreter")
    workflow.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "policy":
            result = audit_policy(load_policy(args.policy), args.workspace.resolve())
        elif args.command == "init":
            root = initialize(args.case_id, read_json(args.inputs), destination=args.destination,
                              kind=args.kind, mode=args.mode, profile=args.profile, blind_reference_mode=args.blind_reference_mode)
            result = {"status": "PASS", "scope": "workspace_initialization", "workspace": str(root),
                      "scientific_acceptance": "NOT_RUN", "official_compliance": "NOT_RUN"}
        elif args.command == "status":
            result = StateStore(args.workspace).inspect_freshness()
        elif args.command == "run":
            record = execute_model(args.workspace, args.spec, role=args.role, interpreter=args.interpreter, retry_of=args.retry_of)
            result = {"status": record["status"], "run_id": record["run_id"], "failure_class": record["failure_class"],
                      "failure_message": record["failure_message"], "scientific_acceptance": "NOT_RUN",
                      "manifest": f"runs/{record['run_id']}/run_manifest.json"}
        elif args.command == "verify-run":
            record = verify_run(args.workspace, args.manifest)
            result = {"status": "PASS", "scope": "execution_record_integrity", "run_id": record["run_id"],
                      "scientific_acceptance": "NOT_RUN"}
        elif args.command == "independent-validate":
            record = independently_validate(args.workspace, args.main_run, args.baseline_run, interpreter=args.interpreter)
            result = {"status": record["status"], "validation_id": record["validation_id"],
                      "summary": f"validations/{record['validation_id']}/validation_summary.json"}
        elif args.command == "evidence":
            result = audit_evidence(args.workspace, args.validation)
        elif args.command == "freeze":
            record = freeze_results(args.workspace, read_json(args.request), args.evidence)
            result = {"status": "PASS", "scope": "verified_numerical_freeze", "freeze_id": record["freeze_id"], "version": record["version"]}
            if record.get("qualifications"):
                result.update(status="LIMITED", qualifications=record["qualifications"])
        elif args.command == "thaw":
            result = {"status": "PASS", "scope": "thaw_completed", "outcome": thaw(args.workspace, args.question_id, actor_id=args.actor_id, reason=args.reason)}
        elif args.command == "verify-freeze":
            record = verify_freeze(args.workspace, args.question_id)
            result = {"status": "PASS", "scope": "freeze_integrity", "freeze_id": record["freeze_id"]}
            if record.get("qualifications"):
                result.update(status="LIMITED", qualifications=record["qualifications"])
        elif args.command == "refresh":
            result = ArtifactRegistry(args.workspace).refresh()
        elif args.command == "agent":
            from .agent_backends import CodexCliBackend
            from .agents import run_agent_task
            record = run_agent_task(args.workspace, read_json(args.task), CodexCliBackend(), timeout=args.timeout)
            result = {"status": "PASS" if record["status"] == "PRODUCED" else "BLOCKED",
                      "scope": "agent_transport", "task_id": record["task_id"], "blockers": record["blockers"],
                      "scientific_acceptance": "NOT_RUN"}
        elif args.command == "verify-agent":
            from .agents import verify_agent_result
            record = verify_agent_result(args.workspace, args.task_id)
            result = {"status": "PASS", "scope": "agent_handoff_integrity", "task_id": record["task_id"],
                      "scientific_acceptance": "NOT_RUN"}
        elif args.command == "advance-agents":
            from .agent_backends import CodexCliBackend
            from .orchestrator import Orchestrator
            result = Orchestrator(args.workspace, CodexCliBackend()).advance(read_json(args.schedule),
                        max_tasks=args.max_tasks, timeout=args.timeout)
        elif args.command == "human-decision":
            from .human_decisions import receive_terminal_decision
            result = receive_terminal_decision(args.workspace, args.request_id, actor_id=args.actor_id)
        elif args.command == "verify-human-decision":
            from .human_decisions import verify_human_decision
            decision = verify_human_decision(args.workspace, args.decision)
            result = {"status": "PASS", "scope": "human_decision_integrity", "decision_id": decision["decision_id"],
                      "scientific_acceptance": "NOT_RUN"}
        elif args.command == "data-audit":
            from .orchestrator import Orchestrator
            result = Orchestrator(args.workspace, None).prepare_inputs()
        elif args.command == "verify-disposition":
            from .dispositions import verify_disposition
            record = verify_disposition(args.workspace, {key: getattr(args, key) for key in ("source", "proposal", "review")},
                                        question_id=args.question_id)
            result = {"status": "LIMITED", "scope": "reviewed_bounded_continuation", **record}
        elif args.command == "assess-assumptions":
            from .assessments import assess_assumptions
            result = assess_assumptions(args.workspace, args.plan, interpreter=args.interpreter)
        elif args.command == "verify-assumptions":
            from .assessments import verify_assessment
            result = verify_assessment(args.workspace, args.assessment)
        elif args.command == "run-code-repair":
            from .repair_execution import execute_reviewed_repair
            record = execute_reviewed_repair(args.workspace, args.request, interpreter=args.interpreter)
            result = {"status": record["status"], "scope": "reviewed_repair_execution", "run_id": record["run_id"],
                      "attempt": record["attempt"], "scientific_acceptance": "NOT_RUN"}
        elif args.command == "verify-code-repair":
            from .code_repairs import verify_code_repair
            result = verify_code_repair(args.workspace, args.request)
        elif args.command == "verify-diagnosis":
            from .repairs import verify_diagnosis, OWNERS
            record = verify_diagnosis(args.workspace, args.diagnosis)
            result = {"status": "PASS", "scope": "independent_failure_diagnosis", "diagnosis": record,
                      "next_owner": OWNERS[record["failure_class"]], "scientific_acceptance": "NOT_RUN"}
        elif args.command == "probe-report":
            from .probes import measured_probe
            record = measured_probe(args.workspace, args.manifest)
            if args.report:
                write_json(args.report, record)
                args.report = None  # Keep the contract report distinct from the CLI envelope.
            result = {"status": record["verdict"], "scope": "measured_risk_probe", "probe": record}
        elif args.command == "seal-baseline":
            from .reference_access import seal_baseline
            record = seal_baseline(args.workspace, args.question_id, framer_task=args.framer_task,
                                   frame_path=args.frame, writer_task=args.writer_task, paper_paths=args.paper)
            result = {"status": "PASS", "scope": record["scope"], "baseline_id": record["baseline_id"],
                      "paper_acceptance": "NOT_RUN"}
        elif args.command in {"seal-case-baseline", "verify-baseline"}:
            from .reference_baselines import seal_case_baseline, verify_baseline
            record = (seal_case_baseline(args.workspace, args.baseline_id) if args.command == "seal-case-baseline"
                      else verify_baseline(args.workspace, args.baseline_id))
            result = {"status": "PASS", "scope": record["scope"], "baseline_id": record["baseline_id"],
                      "paper_acceptance": "NOT_RUN"}
        elif args.command == "admit-reference":
            from .reference_access import admit_reference
            result = admit_reference(args.workspace, source=args.source, question_id=args.question_id,
                                     same_problem=args.classification == "same-problem", baseline_id=args.baseline_id)
        elif args.command == "recover":
            from .recovery import recover_execution
            event = recover_execution(args.workspace, args.execution_id, kind=args.kind, reason=args.reason)
            result = {"status": "PASS", "scope": "interrupted_execution_recovery", "event": event,
                      "scientific_acceptance": "NOT_RUN"}
        elif args.command == "retrieve-reference":
            from .reference_retrieval import retrieve_reference
            receipt = retrieve_reference(args.workspace, source=args.source, question_id=args.question_id,
                same_problem=args.classification == "same-problem", baseline_id=args.baseline_id,
                retrieval_id=args.retrieval_id, timeout=args.timeout, max_bytes=args.max_bytes, max_redirects=args.max_redirects)
            result = {"status": "PASS" if receipt["status"] == "RETRIEVED" else "FAIL", "scope": "reference_http_retrieval",
                "receipt": receipt, "scientific_acceptance": "NOT_RUN"}
        elif args.command == "verify-reference":
            from .reference_retrieval import verify_retrieval
            receipt = verify_retrieval(args.workspace, args.receipt)
            result = {"status": "PASS", "scope": "reference_retrieval_integrity", "retrieval_id": receipt["retrieval_id"],
                "scientific_acceptance": "NOT_RUN"}
        elif args.command == "recover-lock":
            from .recovery import recover_lock
            result = recover_lock(args.workspace, reason=args.reason, scope=args.scope)
        elif args.command == "workflow":
            from .workflow import Workflow
            backend = None
            if args.advance and not args.no_agent:
                from .agent_backends import CodexCliBackend
                backend = CodexCliBackend()
            service = Workflow(args.workspace, backend)
            plan = read_json(args.plan)
            result = service.advance(plan, interpreter=args.interpreter) if args.advance else service.observe(plan)
        elif args.contract == "modeling_bundle":
            result = validate_modeling_bundle(read_json(args.path), root=args.workspace)
        else:
            validate(args.contract, read_json(args.path), root=args.workspace)
            result = {"status": "PASS", "scope": "contract_consistency", "scientific_acceptance": "NOT_RUN"}
    except (ValueError, OSError) as exc:
        result = {"status": "FAIL", "error": str(exc)}
    except Exception as exc:
        from jsonschema import ValidationError
        if not isinstance(exc, ValidationError):
            raise
        result = {"status": "FAIL", "error": exc.message, "path": list(exc.absolute_path)}
    content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if getattr(args, "report", None):
        write_json(args.report, result)
    print(content)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
