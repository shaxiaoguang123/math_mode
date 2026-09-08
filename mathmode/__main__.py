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
