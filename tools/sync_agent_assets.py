"""Generate runtime routers from one source and verify complete skill mirrors."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from check_skill_parity import check


def synchronize(root: Path, *, check_only=False) -> dict:
    source = (root / "docs/agent_router.md").read_text(encoding="utf-8")
    mismatches = []
    for filename, runtime, skill in (
        ("AGENTS.md", "Codex", ".agents/skills/academic-figure-skill"),
        ("CLAUDE.md", "Claude Code", ".claude/skills/academic-figure-skill"),
    ):
        expected = source.replace("{{runtime}}", runtime).replace("{{skill_path}}", skill)
        path = root / filename
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            if check_only:
                mismatches.append(filename)
            else:
                path.write_text(expected, encoding="utf-8", newline="\n")
    parity = check(root)
    return {"status": "FAIL" if mismatches or parity["status"] != "PASS" else "PASS",
            "router_mismatches": mismatches, "skill_mirrors": parity}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = synchronize(args.root.resolve(), check_only=args.check)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
