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
    args = parser.parse_args(argv)
    try:
        if args.command == "policy":
            result = audit_policy(load_policy(args.policy), args.workspace.resolve())
        elif args.command == "init":
            root = initialize(args.case_id, read_json(args.inputs), destination=args.destination,
                              kind=args.kind, mode=args.mode, profile=args.profile)
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
        elif args.command == "thaw":
            result = {"status": "PASS", "scope": "thaw_completed", "outcome": thaw(args.workspace, args.question_id, actor_id=args.actor_id, reason=args.reason)}
        elif args.command == "verify-freeze":
            record = verify_freeze(args.workspace, args.question_id)
            result = {"status": "PASS", "scope": "freeze_integrity", "freeze_id": record["freeze_id"]}
        elif args.command == "refresh":
            result = ArtifactRegistry(args.workspace).refresh()
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
