"""Reproduce V1 audit gaps in a disposable workspace; never creates contest results.

Run only against the recorded V1 revision. Findings describe observed behavior,
not accepted outputs. V2 regression tests must instead reject these cases.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")


def run_probe(root: Path) -> dict:
    solving = root / "华为杯_求解规范" / "tools"
    paper = root / "华为杯_论文规范模板" / "tools"
    checks = []
    with tempfile.TemporaryDirectory(prefix="mathmode-v1-probe-") as raw:
        work = Path(raw).resolve()
        (work / "never_run.py").write_text('raise RuntimeError("MUST NOT EXECUTE")\n', encoding="utf-8")
        (work / "record.txt").write_text("This is a fabricated test record, not execution evidence.\n", encoding="utf-8")
        manifest = {
            "schema_version": "1.0", "project_title": "V1 audit negative probe",
            "package_status": "complete", "external_data": [],
            "external_data_note": "No external data is used in this isolated engineering probe.",
            "official_outputs": [], "questions": [{
                "question_id": "q1", "title": "probe", "status": "complete",
                "entrypoint": "never_run.py", "run_command": "python never_run.py",
                "source_files": [{"path": "never_run.py", "description": "Deliberately unexecuted failing source"}],
                "run_verification": {"status": "pass", "command": "python never_run.py",
                                     "record_path": "record.txt", "verified_at": "2026-09-08T00:00:00Z"},
                "supplementary_materials": [], "supplementary_materials_note": "No actual model or supplementary result exists in this negative probe.",
            }],
        }
        save(work / "manifest.json", manifest)
        build = subprocess.run([sys.executable, str(solving / "build_supporting_materials.py"),
                                "--manifest", "manifest.json", "--project-root", str(work),
                                "--output", "package"], cwd=work, capture_output=True, text=True, encoding="utf-8")
        if build.returncode:
            raise RuntimeError(build.stderr)
        result = module(solving / "audit_supporting_materials.py").audit(
            work / "manifest.json", work, work / "package", "final", None)
        checks.append({"id": "V1-EXECUTION-01", "observed_status": result["status"],
                       "unsafe_acceptance": result["status"] == "PASS",
                       "description": "Unexecuted raising code and fabricated plain-text record are accepted as complete."})
        categories = ["mechanism_geometry", "main_result", "independent_validation", "sensitivity_robustness"]
        evidence = [{"evidence_id": f"e{i}", "category": category, "question": "Probe question",
                     "applicability": "applicable" if i in (1, 2) else "not_needed",
                     "reason": "Engineering-only probe, no scientific claim or result.",
                     "data_shape": "single_value", "representation": "figure" if i in (1, 2) else "na",
                     "result_files": ["data.json"], "figure_ids": [f"f{i}"] if i in (1, 2) else []}
                    for i, category in enumerate(categories)]
        figures = []
        save(work / "data.json", {"placeholder": True})
        for i in (1, 2):
            for suffix in ("pdf", "png", "py"):
                (work / f"f{i}.{suffix}").write_text("This is not a real rendered figure.\n", encoding="utf-8")
            save(work / f"qa{i}.json", {"status": "FAIL"})
            figures.append({"figure_id": f"f{i}", "scope": "q1", "scientific_question": "negative probe",
                "claim_ids": ["c1"], "evidence_ids": [f"e{i}"], "archetype": "quantitative_grid",
                "layout": "1x1", "hero_panel": None,
                "panels": [{"panel_id": "a", "result_file": "data.json", "figure_family": "prediction_diagnostic"}],
                "script": f"f{i}.py", "outputs": {"vector": f"f{i}.pdf", "preview": f"f{i}.png"},
                "statistics_report": "data.json", "qa_report": f"qa{i}.json", "status": "qa_pass",
                "paper": {"label": f"fig:f{i}", "caption": "negative probe", "reference_context": "probe"}})
        plan = {"schema_version": "1.0", "project_title": "negative probe", "plan_status": "ready",
                "visual_encoding_path": "does_not_exist.md", "global_figures": [], "flowcharts": [],
                "problems": [{"problem_id": "q1", "complexity": "simple", "claims": [{"claim_id": "c1", "text": "placeholder"}],
                              "evidence_matrix": evidence, "figures": figures, "schematics": [], "low_figure_exception": None}]}
        save(work / "visual.json", plan)
        result = module(solving / "audit_visual_plan.py").audit(work / "visual.json", "render", work, None)
        checks.append({"id": "V1-VISUAL-01", "observed_status": result["status"],
                       "unsafe_acceptance": result["status"] == "PASS",
                       "description": "Invalid image bytes, placeholder data and QA status FAIL accepted from declared qa_pass; schema not enforced."})
        pdf_audit = module(paper / "audit_paper.py")
        checks.append({"id": "V1-PDF-REGEX-01", "reference_heading_matches": bool(pdf_audit.REFERENCE_RE.match("参考文献")),
                       "page_number_matches": bool(pdf_audit.PAGE_RE.fullmatch("12")),
                       "description": "Overescaped raw regex fails to recognize ordinary reference headings and page numbers."})
        tex_audit = module(paper / "audit_tex.py")
        checks.append({"id": "V1-TEX-COMMENT-01",
                       "balance_after_comment_removal": tex_audit.brace_balance(tex_audit.remove_comments(r"\text{95\%}")),
                       "description": "Escaped percent is mistaken for a TeX comment."})
    return {"purpose": "Engineering negative probes; not scientific evidence", "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_probe(args.root.resolve())
    save(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
