"""Check complete figure skill mirrors without copying or changing assets."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def snapshot(root: Path) -> dict[str, str]:
    if not root.is_dir():
        raise ValueError(f"Missing mirror: {root.name}")
    result = {}
    for path in sorted(root.rglob("*")):
        if any(part in {"__pycache__", ".pytest_cache"} for part in path.relative_to(root).parts):
            continue
        if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
            raise ValueError("Skill mirrors must be standalone, not symlinks/junctions")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def check(root: Path) -> dict:
    left = snapshot(root / ".agents/skills/academic-figure-skill")
    right = snapshot(root / ".claude/skills/academic-figure-skill")
    differences = sorted(name for name in left.keys() | right.keys() if left.get(name) != right.get(name))
    return {"status": "FAIL" if differences else "PASS", "files_per_mirror": len(left),
            "differences": differences}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = check(args.root.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
