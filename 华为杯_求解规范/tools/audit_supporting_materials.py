#!/usr/bin/env python3
"""Audit Huawei Cup supporting materials at per-question or final stage."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path


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
    return candidate


def is_placeholder(text: object) -> bool:
    value = str(text or "").strip()
    return not value or "待审查" in value or "待补充" in value or value == "待填写"


def local_python_dependencies(path: Path, project_root: Path) -> set[Path]:
    """Return directly imported Python files that resolve inside the project."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    except (OSError, SyntaxError, UnicodeError):
        return set()
    modules: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend((alias.name, 0) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append((node.module, node.level))

    dependencies: set[Path] = set()
    for module, level in modules:
        module_parts = module.split(".")
        bases: list[Path]
        if level:
            base = path.parent
            for _ in range(level - 1):
                base = base.parent
            bases = [base]
        else:
            bases = [path.parent, project_root, project_root / "求解" / "公共"]
        for base in bases:
            stem = base.joinpath(*module_parts)
            for candidate in (stem.with_suffix(".py"), stem / "__init__.py"):
                candidate = candidate.resolve()
                try:
                    candidate.relative_to(project_root)
                except ValueError:
                    continue
                if candidate.is_file() and candidate != path.resolve():
                    dependencies.add(candidate)
    return dependencies


def audit(
    manifest_path: Path,
    project_root: Path,
    output_root: Path,
    stage: str,
    question_id: str | None,
) -> dict:
    checks: list[dict] = []
    failures: list[dict] = []
    warnings: list[dict] = []

    def add(code: str, ok: bool, severity: str = "FAIL", **details) -> None:
        item = {"code": code, "ok": ok, "severity": "PASS" if ok else severity, **details}
        checks.append(item)
        if not ok:
            (failures if severity == "FAIL" else warnings).append(item)

    try:
        manifest = load_json(manifest_path)
    except Exception as exc:
        add("manifest_is_valid_json", False, error=str(exc))
        return {"status": "FAIL", "stage": stage, "checks": checks, "failures": failures, "warnings": warnings}

    required_root = {
        "schema_version", "project_title", "package_status", "questions",
        "external_data", "external_data_note", "official_outputs",
    }
    add("root_fields_present", required_root <= set(manifest), missing=sorted(required_root - set(manifest)))
    if failures:
        return {"status": "FAIL", "stage": stage, "checks": checks, "failures": failures, "warnings": warnings}
    add("schema_version_supported", manifest["schema_version"] == "1.0", actual=manifest["schema_version"])

    questions = manifest["questions"] if isinstance(manifest["questions"], list) else []
    qids = [q.get("question_id") for q in questions if isinstance(q, dict)]
    add("questions_present", bool(questions))
    add("question_ids_unique", len(qids) == len(set(qids)) and all(qids), values=qids)
    qmap = {q.get("question_id"): q for q in questions if isinstance(q, dict)}
    if stage == "question":
        add("question_id_provided", bool(question_id))
        add("question_id_known", question_id in qmap if question_id else False, question_id=question_id)
        target_questions = [qmap[question_id]] if question_id in qmap else []
    else:
        target_questions = questions
        add("package_marked_complete", manifest["package_status"] == "complete", actual=manifest["package_status"])

    for question in target_questions:
        qid = question.get("question_id", "unknown")
        required = {
            "question_id", "title", "status", "entrypoint", "run_command", "source_files",
            "run_verification", "supplementary_materials", "supplementary_materials_note",
        }
        add(f"{qid}_fields_present", required <= set(question), missing=sorted(required - set(question)))
        if not required <= set(question):
            continue
        add(f"{qid}_marked_complete", question["status"] == "complete", actual=question["status"])
        source_files = question["source_files"] if isinstance(question["source_files"], list) else []
        source_paths = [item.get("path") for item in source_files if isinstance(item, dict)]
        resolved_sources: set[Path] = set()
        add(f"{qid}_source_files_present", bool(source_files))
        add(f"{qid}_entrypoint_listed", question["entrypoint"] in source_paths, entrypoint=question["entrypoint"])
        add(f"{qid}_run_command_present", bool(str(question["run_command"]).strip()))
        for index, item in enumerate(source_files):
            raw = item.get("path", "") if isinstance(item, dict) else ""
            description = item.get("description", "") if isinstance(item, dict) else ""
            try:
                path = project_path(project_root, raw)
                allowed = not FORBIDDEN_PARTS.intersection(path.parts)
                exists = path.is_file()
                if exists:
                    resolved_sources.add(path.resolve())
            except Exception:
                allowed = False
                exists = False
            add(f"{qid}_source_{index}_safe", allowed, path=raw)
            add(f"{qid}_source_{index}_exists", exists, path=raw)
            add(f"{qid}_source_{index}_described", not is_placeholder(description), path=raw)

        missing_local_dependencies: list[str] = []
        for source in sorted(resolved_sources):
            if source.suffix.lower() != ".py":
                continue
            for dependency in local_python_dependencies(source, project_root):
                if dependency not in resolved_sources:
                    missing_local_dependencies.append(dependency.relative_to(project_root).as_posix())
        add(
            f"{qid}_direct_local_python_dependencies_listed",
            not missing_local_dependencies,
            missing=sorted(set(missing_local_dependencies)),
        )

        verification = question["run_verification"]
        add(f"{qid}_run_verified", verification.get("status") == "pass", actual=verification.get("status"))
        add(f"{qid}_verification_time_present", not is_placeholder(verification.get("verified_at")))
        try:
            record = project_path(project_root, verification.get("record_path", ""))
            record_exists = record.is_file() and record.stat().st_size > 0
        except Exception:
            record_exists = False
        add(f"{qid}_verification_record_exists", record_exists, path=verification.get("record_path"))
        add(
            f"{qid}_supplementary_reviewed",
            not is_placeholder(question["supplementary_materials_note"]),
            note=question["supplementary_materials_note"],
        )
        for index, item in enumerate(question["supplementary_materials"]):
            raw = item.get("path", "")
            try:
                path = project_path(project_root, raw)
                exists = path.is_file() and path.stat().st_size > 0
            except Exception:
                exists = False
            add(f"{qid}_supplementary_{index}_exists", exists, path=raw)
            add(
                f"{qid}_supplementary_{index}_described",
                not is_placeholder(item.get("description")) and not is_placeholder(item.get("reason")),
                path=raw,
            )

    external_data = manifest["external_data"] if isinstance(manifest["external_data"], list) else []
    data_ids = [item.get("data_id") for item in external_data if isinstance(item, dict)]
    add("external_data_ids_unique", len(data_ids) == len(set(data_ids)) and all(data_ids), values=data_ids)
    add("external_data_reviewed", not is_placeholder(manifest["external_data_note"]), note=manifest["external_data_note"])
    for data in external_data:
        data_id = data.get("data_id", "unknown")
        required = {
            "data_id", "name", "description", "source", "accessed_at", "collection_method",
            "license_or_terms", "used_by", "files", "collection_scripts", "provenance_file",
        }
        add(f"{data_id}_fields_present", required <= set(data), missing=sorted(required - set(data)))
        if not required <= set(data):
            continue
        add(f"{data_id}_used_by_known_questions", set(data["used_by"]) <= set(qids), used_by=data["used_by"])
        metadata_ok = all(not is_placeholder(data[field]) for field in (
            "name", "description", "source", "accessed_at", "collection_method", "license_or_terms"
        ))
        add(f"{data_id}_provenance_metadata_complete", metadata_ok)
        paths = list(data["files"]) + list(data["collection_scripts"])
        paths.append({"path": data["provenance_file"], "description": "provenance"})
        for index, item in enumerate(paths):
            raw = item.get("path", "")
            try:
                path = project_path(project_root, raw)
                rel = path.relative_to(project_root)
                official_raw = rel.parts[:1] == ("题目",) or rel.parts[:2] == ("数据", "原始")
                safe = not official_raw and not FORBIDDEN_PARTS.intersection(path.parts)
                exists = path.is_file() and path.stat().st_size > 0
            except Exception:
                safe = False
                exists = False
            add(f"{data_id}_file_{index}_not_official_raw", safe, path=raw)
            add(f"{data_id}_file_{index}_exists", exists, path=raw)

    officials = manifest["official_outputs"] if isinstance(manifest["official_outputs"], list) else []
    if stage == "final":
        for index, item in enumerate(officials):
            raw = item.get("path", "")
            try:
                path = project_path(project_root, raw)
                path.relative_to(output_root)
                exists = path.is_file() and path.stat().st_size > 0
                verification = project_path(project_root, item.get("verification_path", ""))
                verification_exists = verification.is_file() and verification.stat().st_size > 0
            except Exception:
                exists = False
                verification_exists = False
            add(f"official_{index}_exists", exists, path=raw)
            add(f"official_{index}_verified", item.get("status") == "pass", actual=item.get("status"))
            add(f"official_{index}_verification_record_exists", verification_exists, path=item.get("verification_path"))

    build_path = output_root / BUILD_MANIFEST_NAME
    readme_path = output_root / README_NAME
    hash_path = output_root / HASH_NAME
    add("build_manifest_exists", build_path.is_file())
    add("readme_exists", readme_path.is_file())
    add("hash_manifest_exists", hash_path.is_file())
    if build_path.is_file():
        try:
            build = load_json(build_path)
            build_valid = True
        except Exception as exc:
            build = {}
            build_valid = False
            add("build_manifest_valid_json", False, error=str(exc))
        if build_valid:
            add("build_manifest_valid_json", True)
            add(
                "package_rebuilt_after_manifest_change",
                build.get("source_manifest_sha256") == sha256(manifest_path),
                built=build.get("source_manifest_sha256"),
                current=sha256(manifest_path),
            )
            built_questions = set(build.get("completed_questions", []))
            expected_questions = {q.get("question_id") for q in target_questions if q.get("status") == "complete"}
            add("target_questions_packaged", expected_questions <= built_questions,
                expected=sorted(expected_questions), built=sorted(built_questions))
            if stage == "final":
                add("all_questions_packaged", set(qids) == built_questions,
                    expected=sorted(qids), built=sorted(built_questions))
                add("no_unregistered_files", not build.get("unregistered_files"),
                    files=build.get("unregistered_files", []))
            entries = build.get("entries", [])
            for index, entry in enumerate(entries):
                package_path = output_root / entry.get("package_path", "")
                exists = package_path.is_file()
                hash_ok = exists and sha256(package_path) == entry.get("sha256")
                try:
                    source_path = project_path(project_root, entry.get("source_path", ""))
                    source_matches = source_path.is_file() and sha256(source_path) == entry.get("sha256")
                except Exception:
                    source_matches = False
                add(f"packaged_entry_{index}_exists", exists, path=entry.get("package_path"))
                add(f"packaged_entry_{index}_hash_matches", hash_ok, path=entry.get("package_path"))
                add(
                    f"packaged_entry_{index}_source_matches_snapshot",
                    source_matches,
                    source_path=entry.get("source_path"),
                    package_path=entry.get("package_path"),
                )

            expected_support = {entry.get("package_path") for entry in entries}
            actual_support = {
                path.relative_to(output_root).as_posix()
                for path in (output_root / "支撑材料").rglob("*")
                if path.is_file()
            } if (output_root / "支撑材料").is_dir() else set()
            add("support_directory_matches_build_manifest", expected_support == actual_support,
                missing=sorted(expected_support - actual_support), extra=sorted(actual_support - expected_support))

    if readme_path.is_file():
        readme = readme_path.read_text(encoding="utf-8-sig")
        package_files = {
            path.relative_to(output_root).as_posix()
            for path in output_root.rglob("*")
            if path.is_file()
        }
        missing_from_readme = sorted(
            path for path in package_files
            if path != README_NAME and path not in readme and Path(path).name not in {BUILD_MANIFEST_NAME, HASH_NAME}
        )
        add("readme_lists_all_material_files", not missing_from_readme, missing=missing_from_readme)
        add("readme_has_required_sections", all(title in readme for title in (
            "每问源程序与补充图表", "自主查阅、整理或爬取的数据", "官方提交文件", "复现说明"
        )))

    if hash_path.is_file():
        hash_records: dict[str, str] = {}
        malformed: list[str] = []
        for line in hash_path.read_text(encoding="utf-8-sig").splitlines():
            if "  " not in line:
                malformed.append(line)
                continue
            digest, relative = line.split("  ", 1)
            hash_records[relative] = digest
        add("hash_manifest_well_formed", not malformed, malformed=malformed)
        files_to_hash = {
            path.relative_to(output_root).as_posix(): path
            for path in output_root.rglob("*")
            if path.is_file() and path.name != HASH_NAME
        }
        add("hash_manifest_file_set_complete", set(hash_records) == set(files_to_hash),
            missing=sorted(set(files_to_hash) - set(hash_records)), extra=sorted(set(hash_records) - set(files_to_hash)))
        bad_hashes = sorted(
            relative for relative, path in files_to_hash.items()
            if hash_records.get(relative) != sha256(path)
        )
        add("hash_manifest_values_match", not bad_hashes, files=bad_hashes)

    return {
        "status": "PASS" if not failures else "FAIL",
        "stage": stage,
        "question_id": question_id,
        "checks": checks,
        "failures": failures,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--stage", choices=("question", "final"), required=True)
    parser.add_argument("--question-id")
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("提交附件"))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    if args.stage == "question" and not args.question_id:
        raise SystemExit("--question-id is required for --stage question")
    if args.stage == "final" and args.question_id:
        raise SystemExit("--question-id is only valid for --stage question")

    project_root = args.project_root.resolve()
    manifest_path = project_path(project_root, str(args.manifest))
    output_root = project_path(project_root, str(args.output))
    report = audit(manifest_path, project_root, output_root, args.stage, args.question_id)
    if args.report:
        report_path = project_path(project_root, str(args.report))
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
