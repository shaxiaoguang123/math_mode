"""Generate standalone contract schemas, or check distribution drift."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mathmode.schema_catalog import catalog


def build(root: Path, check: bool = False) -> list[str]:
    mismatches = []
    for name, definition in catalog().items():
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
                  "$id": f"https://mathmode.local/schemas/{name}.schema.json",
                  "title": f"MathMode {name} 2.0", **definition}
        content = json.dumps(schema, ensure_ascii=False, indent=2) + "\n"
        path = root / f"{name}.schema.json"
        if check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                mismatches.append(name)
        else:
            root.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    return mismatches


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "华为杯_求解规范" / "schemas"
    mismatches = build(root, args.check)
    print(json.dumps({"status": "FAIL" if mismatches else "PASS", "mismatches": mismatches,
                      "contracts": len(catalog())}))
    return bool(mismatches)


if __name__ == "__main__":
    raise SystemExit(main())
