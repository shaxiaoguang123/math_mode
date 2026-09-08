"""Command entry point for deterministic MathMode services."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .policy import audit_policy, load_policy


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    policy = commands.add_parser("policy", help="Verify policy source snapshots and template hash")
    policy.add_argument("--policy", type=Path)
    policy.add_argument("--workspace", type=Path, required=True)
    policy.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = audit_policy(load_policy(args.policy), args.workspace.resolve())
    content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(content, encoding="utf-8")
    print(content)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
