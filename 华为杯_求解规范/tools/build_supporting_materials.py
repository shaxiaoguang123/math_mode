#!/usr/bin/env python3
"""Build 提交附件/支撑材料 and its readme.md from a manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


SUPPORT_DIR_NAME = "支撑材料"
README_NAME = "readme.md"
BUILD_MANIFEST_NAME = "_支撑材料构建清单.json"
HASH_NAME = "SHA256SUMS.txt"
FORBIDDEN_PARTS = {".venv", "__pycache__", ".git", ".pytest_cache", "node_modules"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_path(project_root: Path, raw: str) -> Path:
    candidate = (project_root / raw).resolve()
    candidate.relative_to(project_root)
    if FORBIDDEN_PARTS.intersection(candidate.parts):
        raise ValueError(f"Path contains a forbidden environment/cache directory: {raw}")
    return candidate


def project_relative(project_root: Path, path: Path) -> Path:
    return path.resolve().relative_to(project_root)


def safe_rmtree(target: Path, managed_root: Path) -> None:
    target = target.resolve()
    managed_root = managed_root.resolve()
    target.relative_to(managed_root.parent)
    if target != managed_root or target.name != SUPPORT_DIR_NAME:
        raise ValueError(f"Refusing to remove unexpected directory: {target}")
    if target.exists():
        shutil.rmtree(target)


def copy_file(
    source: Path,
    source_relative: Path,
    destination: Path,
    output_root: Path,
    entries: list[dict],
    *,
    category: str,
    description: str,
    question_id: str | None = None,
    data_id: str | None = None,
) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Required supporting-material file does not exist: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    item = {
        "package_path": destination.relative_to(output_root).as_posix(),
        "source_path": source_relative.as_posix(),
        "category": category,
        "description": description,
        "size_bytes": destination.stat().st_size,
        "sha256": sha256(destination),
    }
    if question_id:
        item["question_id"] = question_id
    if data_id:
        item["data_id"] = data_id
    entries.append(item)


def ensure_unique_ids(items: list[dict], field: str) -> None:
    values = [item.get(field) for item in items]
    if any(not value for value in values) or len(values) != len(set(values)):
        raise ValueError(f"{field} values must be present and unique")


def validate_root_fields(manifest: dict) -> None:
    required = {
        "schema_version",
        "project_title",
        "package_status",
        "questions",
        "external_data",
        "external_data_note",
        "official_outputs",
    }
    missing = required - set(manifest)
    if missing:
        raise ValueError(f"Manifest is missing required fields: {sorted(missing)}")
    if manifest["schema_version"] != "1.0":
        raise ValueError(f"Unsupported schema version: {manifest['schema_version']}")
    ensure_unique_ids(manifest["questions"], "question_id")
    ensure_unique_ids(manifest["external_data"], "data_id")


def build_question(
    question: dict,
    project_root: Path,
    output_root: Path,
    support_root: Path,
    entries: list[dict],
) -> None:
    question_id = question["question_id"]
    source_paths = [item["path"] for item in question["source_files"]]
    if question["entrypoint"] not in source_paths:
        raise ValueError(f"{question_id}: entrypoint must also appear in source_files")

    question_root = support_root / question_id
    for item in question["source_files"]:
        source = project_path(project_root, item["path"])
        relative = project_relative(project_root, source)
        copy_file(
            source,
            relative,
            question_root / "源程序" / relative,
            output_root,
            entries,
            category="source_code",
            description=item["description"],
            question_id=question_id,
        )

    verification = question["run_verification"]
    record = project_path(project_root, verification["record_path"])
    copy_file(
        record,
        project_relative(project_root, record),
        question_root / "运行验证" / project_relative(project_root, record),
        output_root,
        entries,
        category="run_verification",
        description=f"{question['title']}源程序实际运行验证记录",
        question_id=question_id,
    )

    type_dir = {"figure": "图", "table": "表"}
    for item in question["supplementary_materials"]:
        source = project_path(project_root, item["path"])
        relative = project_relative(project_root, source)
        kind = item["material_type"]
        copy_file(
            source,
            relative,
            question_root / "补充图表" / type_dir[kind] / relative,
            output_root,
            entries,
            category=f"supplementary_{kind}",
            description=f"{item['description']}；纳入原因：{item['reason']}",
            question_id=question_id,
        )


def build_external_data(
    data: dict,
    project_root: Path,
    output_root: Path,
    support_root: Path,
    entries: list[dict],
) -> None:
    data_id = data["data_id"]
    data_root = support_root / "自主数据" / data_id
    for item in data["files"]:
        source = project_path(project_root, item["path"])
        relative = project_relative(project_root, source)
        copy_file(
            source,
            relative,
            data_root / "数据文件" / relative,
            output_root,
            entries,
            category="external_data",
            description=item["description"],
            data_id=data_id,
        )
    for item in data["collection_scripts"]:
        source = project_path(project_root, item["path"])
        relative = project_relative(project_root, source)
        copy_file(
            source,
            relative,
            data_root / "采集与整理程序" / relative,
            output_root,
            entries,
            category="external_data_script",
            description=item["description"],
            data_id=data_id,
        )
    provenance = project_path(project_root, data["provenance_file"])
    copy_file(
        provenance,
        project_relative(project_root, provenance),
        data_root / "来源记录" / project_relative(project_root, provenance),
        output_root,
        entries,
        category="external_data_provenance",
        description=f"{data['name']}的数据来源、获取日期、许可和处理记录",
        data_id=data_id,
    )


def official_rows(
    manifest: dict,
    project_root: Path,
    output_root: Path,
    support_root: Path,
    entries: list[dict],
) -> list[dict]:
    rows: list[dict] = []
    for item in manifest["official_outputs"]:
        path = project_path(project_root, item["path"])
        try:
            relative = path.relative_to(output_root).as_posix()
        except ValueError as exc:
            raise ValueError(f"Official output must be inside 提交附件: {item['path']}") from exc
        verification = project_path(project_root, item["verification_path"])
        verification_relative = project_relative(project_root, verification)
        verification_destination = support_root / "官方输出核验" / verification_relative
        copy_file(
            verification,
            verification_relative,
            verification_destination,
            output_root,
            entries,
            category="official_output_verification",
            description=f"{item['description']}的独立核验记录",
        )
        row = {
            "package_path": relative,
            "description": item["description"],
            "status": item["status"],
            "verification_path": verification_destination.relative_to(output_root).as_posix(),
            "exists": path.is_file(),
        }
        if path.is_file():
            row.update(size_bytes=path.stat().st_size, sha256=sha256(path))
        rows.append(row)
    return rows


def render_readme(
    manifest: dict,
    completed_questions: list[dict],
    included_data: list[dict],
    entries: list[dict],
    officials: list[dict],
    unregistered: list[str],
    built_at: str,
) -> str:
    lines = [
        f"# {manifest['project_title']}提交附件目录",
        "",
        f"- 构建时间：{built_at}",
        f"- 清单状态：`{manifest['package_status']}`",
        "- 本目录同时保存题面要求的官方输出和可复核的支撑材料。`支撑材料/` 是工具生成的快照，源文件仍以项目中的 `求解/`、`数据/` 为事实源。",
        "- 赛题官方原始数据不重复收录到自主数据；复运行时请按题面要求放回项目原约定路径。",
        "",
        "## 每问源程序与补充图表",
        "",
    ]
    by_question: dict[str, list[dict]] = {}
    for entry in entries:
        if entry.get("question_id"):
            by_question.setdefault(entry["question_id"], []).append(entry)
    if not completed_questions:
        lines.extend(["当前尚无标记为 `complete` 的问题。", ""])
    for question in completed_questions:
        qid = question["question_id"]
        lines.extend([
            f"### {question['title']}（{qid}）",
            "",
            f"- 主入口：`{question['entrypoint']}`",
            f"- 原项目运行命令：`{question['run_command']}`",
            f"- 补充图表审查说明：{question['supplementary_materials_note']}",
            "",
            "| 文件 | 类型 | 作用 |",
            "|---|---|---|",
        ])
        for entry in sorted(by_question.get(qid, []), key=lambda item: item["package_path"]):
            lines.append(f"| `{entry['package_path']}` | `{entry['category']}` | {entry['description']} |")
        lines.append("")

    lines.extend(["## 自主查阅、整理或爬取的数据", "", manifest["external_data_note"], ""])
    by_data: dict[str, list[dict]] = {}
    for entry in entries:
        if entry.get("data_id"):
            by_data.setdefault(entry["data_id"], []).append(entry)
    if not included_data:
        lines.extend(["本次未登记赛题官方原始数据之外的建模数据。", ""])
    for data in included_data:
        lines.extend([
            f"### {data['name']}（{data['data_id']}）",
            "",
            f"- 作用：{data['description']}",
            f"- 来源：{data['source']}",
            f"- 获取日期：{data['accessed_at']}",
            f"- 获取/整理方式：{data['collection_method']}",
            f"- 许可或使用条款：{data['license_or_terms']}",
            f"- 使用问题：{', '.join(data['used_by'])}",
            "",
            "| 文件 | 类型 | 作用 |",
            "|---|---|---|",
        ])
        for entry in sorted(by_data.get(data["data_id"], []), key=lambda item: item["package_path"]):
            lines.append(f"| `{entry['package_path']}` | `{entry['category']}` | {entry['description']} |")
        lines.append("")

    lines.extend(["## 官方提交文件", ""])
    if not officials:
        lines.extend(["题面未要求或当前尚未登记官方结果文件。", ""])
    else:
        lines.extend(["| 文件 | 状态 | 作用 | 核验记录 |", "|---|---|---|---|"])
        for item in officials:
            lines.append(
                f"| `{item['package_path']}` | `{item['status']}` | {item['description']} | `{item['verification_path']}` |"
            )
        lines.append("")

    lines.extend([
        "## 目录与完整性文件",
        "",
        f"- `{README_NAME}`：本目录，列出提交附件中的文件及其作用。",
        f"- `{BUILD_MANIFEST_NAME}`：机器可读的构建快照、来源路径、大小与 SHA-256。",
        f"- `{HASH_NAME}`：提交附件内文件的 SHA-256 校验值。",
        "",
    ])
    if unregistered:
        lines.extend([
            "## 尚未在清单中登记的文件",
            "",
            "以下文件已被列出，但用途尚未写入 `求解/支撑材料清单.json`；最终审计会失败：",
            "",
        ])
        lines.extend(f"- `{path}`" for path in unregistered)
        lines.append("")
    lines.extend([
        "## 复现说明",
        "",
        "1. 以项目根目录为工作目录，恢复题面官方数据到原路径；不要从本支撑材料反向覆盖事实源。",
        "2. 按 `requirements.txt`、`求解/环境与依赖.md` 和各问运行命令准备环境。",
        "3. 先运行每问唯一主入口，再读取对应运行验证记录；绘图脚本只读取已落盘结果。",
        "4. 最终提交前运行 `audit_supporting_materials.py`，确认文件、哈希、运行验证、外部数据溯源和本目录均通过。",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("提交附件"))
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    manifest_path = project_path(project_root, str(args.manifest))
    output_root = project_path(project_root, str(args.output))
    if output_root == project_root:
        raise SystemExit("Refusing to use the project root as the package output")
    support_root = output_root / SUPPORT_DIR_NAME

    manifest = load_json(manifest_path)
    validate_root_fields(manifest)
    completed_questions = [q for q in manifest["questions"] if q["status"] == "complete"]
    completed_ids = {q["question_id"] for q in completed_questions}
    included_data = [d for d in manifest["external_data"] if completed_ids.intersection(d["used_by"])]

    output_root.mkdir(parents=True, exist_ok=True)
    safe_rmtree(support_root, support_root)
    support_root.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    for question in completed_questions:
        build_question(question, project_root, output_root, support_root, entries)
    for data in included_data:
        build_external_data(data, project_root, output_root, support_root, entries)

    officials = official_rows(manifest, project_root, output_root, support_root, entries)
    registered_paths = {entry["package_path"] for entry in entries}
    registered_paths.update(item["package_path"] for item in officials)
    metadata_names = {README_NAME, BUILD_MANIFEST_NAME, HASH_NAME}
    existing_before_metadata = {
        path.relative_to(output_root).as_posix()
        for path in output_root.rglob("*")
        if path.is_file() and path.name not in metadata_names
    }
    unregistered = sorted(existing_before_metadata - registered_paths)

    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    build_manifest = {
        "schema_version": "1.0",
        "project_title": manifest["project_title"],
        "package_status": manifest["package_status"],
        "built_at": built_at,
        "source_manifest": manifest_path.relative_to(project_root).as_posix(),
        "source_manifest_sha256": sha256(manifest_path),
        "completed_questions": sorted(completed_ids),
        "entries": sorted(entries, key=lambda item: item["package_path"]),
        "official_outputs": officials,
        "unregistered_files": unregistered,
    }
    (output_root / BUILD_MANIFEST_NAME).write_text(
        json.dumps(build_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    readme = render_readme(
        manifest, completed_questions, included_data, entries, officials, unregistered, built_at
    )
    (output_root / README_NAME).write_text(readme, encoding="utf-8")

    hash_lines = []
    for path in sorted((p for p in output_root.rglob("*") if p.is_file() and p.name != HASH_NAME)):
        hash_lines.append(f"{sha256(path)}  {path.relative_to(output_root).as_posix()}")
    (output_root / HASH_NAME).write_text("\n".join(hash_lines) + "\n", encoding="utf-8")

    status = "BUILT" if not unregistered else "BUILT_WITH_UNREGISTERED_FILES"
    print(json.dumps({
        "status": status,
        "output": str(output_root),
        "completed_questions": sorted(completed_ids),
        "copied_files": len(entries),
        "unregistered_files": unregistered,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
