#!/usr/bin/env python3
"""Create a draft supporting-materials manifest for a Huawei Cup project."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def make_question(question_id: str, title: str) -> dict:
    entrypoint = f"求解/{title}/{title}.py"
    return {
        "question_id": question_id,
        "title": title,
        "status": "draft",
        "entrypoint": entrypoint,
        "run_command": f".venv\\Scripts\\python.exe {entrypoint}",
        "source_files": [
            {"path": entrypoint, "description": f"{title}唯一主入口，待补充本问全部依赖源码"}
        ],
        "run_verification": {
            "status": "pending",
            "command": f".venv\\Scripts\\python.exe {entrypoint}",
            "record_path": f"求解/{title}/结果/运行验证.json",
            "verified_at": ""
        },
        "supplementary_materials": [],
        "supplementary_materials_note": "待审查：正文未完整展示的大篇幅中间图表是否需要纳入支撑材料"
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project-title", required=True)
    parser.add_argument(
        "--question",
        action="append",
        required=True,
        metavar="ID:标题",
        help="Repeat once per question, for example --question q1:问题一",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite an existing draft")
    args = parser.parse_args()

    questions: list[dict] = []
    for raw in args.question:
        if ":" not in raw:
            raise SystemExit(f"Invalid --question value (expected ID:标题): {raw}")
        question_id, title = (part.strip() for part in raw.split(":", 1))
        if not question_id or not title:
            raise SystemExit(f"Invalid --question value: {raw}")
        questions.append(make_question(question_id, title))

    output = args.output.resolve()
    if output.exists() and not args.force:
        raise SystemExit(f"Refusing to overwrite existing manifest: {output}")
    manifest = {
        "schema_version": "1.0",
        "project_title": args.project_title,
        "package_status": "draft",
        "questions": questions,
        "external_data": [],
        "external_data_note": "待审查：是否使用了赛题官方原始数据之外的自主搜集、整理或爬取数据",
        "official_outputs": [],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "DRAFT_CREATED", "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
