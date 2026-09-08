#!/usr/bin/env python3
r"""Audit the TeX-only paper source and its generated ``\input`` chain."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mathmode.policy import load_policy, toc_settings, validate_policy

INPUT_RE = re.compile(r"\\input\s*\{([^{}]+)\}")
GRAPHICS_RE = re.compile(r"\\includegraphics(?:\[[^]]*\])?\s*\{([^{}]+)\}")
BEGIN_RE = re.compile(r"\\begin\s*\{([^{}]+)\}")
END_RE = re.compile(r"\\end\s*\{([^{}]+)\}")
LABEL_RE = re.compile(r"\\label\s*\{([^{}]+)\}")
REF_RE = re.compile(r"\\(?:ref|eqref|autoref|pageref)\s*\{([^{}]+)\}")
TOC_DEPTH_RE = re.compile(r"\\setcounter\s*\{tocdepth\}\s*\{\s*(\d+)\s*\}")
FORBIDDEN_UNICODE_MATH = set("ᐟ¹²³⁴⁵⁶⁷⁸⁹⁰⁻⁺Σ∑∫√∈∉≤≥≈μσπγδελρτφω̃ᵀĉŷ")


def read_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def inside(root: Path, raw: str) -> Path:
    path = (root / raw).resolve()
    path.relative_to(root.resolve())
    return path


def remove_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        escaped = False
        for index, char in enumerate(line):
            if char == "%" and not escaped:
                line = line[:index]
                break
            escaped = not escaped if char == "\\" else False
        lines.append(line)
    return "\n".join(lines)


def brace_balance(text: str) -> int:
    balance = 0
    escaped = False
    for char in text:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
        elif char == "{":
            balance += 1
        elif char == "}":
            balance -= 1
            if balance < 0:
                return -1
    return balance


def expand_tex_inputs(root: Path, roots: list[Path]) -> tuple[list[Path], list[str]]:
    """Return manifest fragments plus every nested TeX input exactly once."""
    ordered: list[Path] = []
    errors: list[str] = []
    visited: set[Path] = set()

    def visit(path: Path) -> None:
        resolved = path.resolve()
        if resolved in visited:
            return
        visited.add(resolved)
        ordered.append(resolved)
        text = resolved.read_text(encoding="utf-8-sig")
        for raw in INPUT_RE.findall(remove_comments(text)):
            candidates = [(root / raw).resolve(), (resolved.parent / raw).resolve()]
            nested = next((item for item in candidates if item.is_file()), candidates[0])
            try:
                nested.relative_to(root.resolve())
            except (ValueError, OSError):
                errors.append(f"{resolved}: nested input escapes paper root: {raw}")
                continue
            if nested.suffix.lower() != ".tex":
                errors.append(f"{resolved}: nested input is not .tex: {raw}")
            elif not nested.is_file():
                errors.append(f"{resolved}: nested input does not exist: {raw}")
            else:
                visit(nested)

    for path in roots:
        visit(path)
    return ordered, errors


def audit(manifest_path: Path, main_path: Path, policy: dict | None = None,
          cover_tex_path: str | None = None, stage: str = "source") -> dict:
    policy = validate_policy(policy) if policy is not None else load_policy()
    include_toc, toc_depth = toc_settings(policy)
    root = manifest_path.parent.resolve()
    project_root = root.parent
    manifest = read_manifest(manifest_path)
    checks: list[dict] = []
    failures: list[dict] = []

    def add(code: str, ok: bool, **details) -> None:
        item = {"code": code, "ok": ok, **details}
        checks.append(item)
        if not ok:
            failures.append(item)

    main_text = main_path.read_text(encoding="utf-8-sig") if main_path.is_file() else ""
    add("main_exists", main_path.is_file(), path=str(main_path))
    if not main_path.is_file():
        return {"status": "FAIL", "manifest": str(manifest_path), "checks": checks, "failures": failures}

    expected = [str(manifest["abstract_tex_path"]).replace("\\", "/")]
    for chapter in manifest.get("chapters", []):
        expected.append(str(chapter["tex_path"]).replace("\\", "/"))
    cover_mode = policy["official"]["cover_policy"]["mode"]
    add("cover_policy", bool(cover_tex_path) == (cover_mode == "identity_cover"))
    if cover_tex_path:
        add("cover_is_distinct", cover_tex_path not in expected)
        expected.insert(0, cover_tex_path)
    actual = INPUT_RE.findall(remove_comments(main_text))
    add("input_order_matches_manifest", actual == expected, expected=expected, actual=actual)
    add("main_has_no_markdown_input", not any(path.lower().endswith(".md") for path in actual), actual=actual)

    # The TOC is a production contract: it must follow the complete
    # abstract/keywords block and precede the first body input.
    clean_main = remove_comments(main_text)
    toc_match = re.search(r"\\maketoc\b", clean_main)
    abstract_end = clean_main.find(r"\end{abstract}")
    after_abstract = clean_main[abstract_end + len(r"\end{abstract}"):] if abstract_end >= 0 else ""
    first_input_match = re.search(r"\\input\s*\{", after_abstract)
    first_input_pos = abstract_end + len(r"\end{abstract}") + first_input_match.start() if abstract_end >= 0 and first_input_match else -1
    toc_order_ok = bool(toc_match and abstract_end >= 0 and first_input_pos >= 0 and abstract_end < toc_match.start() < first_input_pos)
    add("toc_command_order", toc_order_ok if include_toc else toc_match is None, maketoc_position=toc_match.start() if toc_match else None,
        abstract_end=abstract_end, first_body_input=first_input_pos)
    depth_values = [int(value) for value in TOC_DEPTH_RE.findall(clean_main)]
    add("toc_depth_matches_policy", depth_values == ([toc_depth] if include_toc else []), values=depth_values)
    add("toc_hyperlinks_enabled", bool(re.search(r"\\hypersetup\s*\{[^}]*hidelinks", clean_main, re.S)),
        message="hyperref is configured for linked TOC/bookmarks")

    fragment_paths: list[Path] = []
    fragment_errors: list[str] = []
    for raw in expected:
        try:
            path = inside(root, raw)
        except (ValueError, OSError) as exc:
            fragment_errors.append(f"{raw}: {exc}")
            continue
        if path.suffix.lower() != ".tex":
            fragment_errors.append(f"{raw}: suffix is not .tex")
        elif not path.is_file():
            fragment_errors.append(f"{raw}: file does not exist")
        else:
            fragment_paths.append(path)
    add("all_manifest_fragments_exist_and_are_tex", not fragment_errors, errors=fragment_errors)

    audit_paths, nested_input_errors = expand_tex_inputs(root, fragment_paths)
    add("nested_tex_inputs_resolve", not nested_input_errors, errors=nested_input_errors,
        count=max(0, len(audit_paths) - len(fragment_paths)))

    markdown_residue: list[str] = []
    document_commands: list[str] = []
    unbalanced: list[str] = []
    environment_errors: list[str] = []
    all_text = main_text
    for path in audit_paths:
        text = path.read_text(encoding="utf-8-sig")
        all_text += "\n" + text
        if re.search(r"(?m)^\s*#{1,6}\s", text) or re.search(r"(?m)^\s*\|[^|]+\|", text) or "![" in text or chr(96) * 3 in text:
            markdown_residue.append(str(path))
        for command in ("\\documentclass", "\\begin{document}", "\\end{document}"):
            if command in text:
                document_commands.append(f"{path}: {command}")
        if brace_balance(remove_comments(text)) != 0:
            unbalanced.append(str(path))
        stack: list[str] = []
        cleaned = remove_comments(text)
        for match in re.finditer(r"\\begin\s*\{([^{}]+)\}|\\end\s*\{([^{}]+)\}", cleaned):
            begin, end = match.groups()
            if begin:
                stack.append(begin)
            elif not stack or stack.pop() != end:
                environment_errors.append(f"{path}: mismatched \\end{{{end}}}")
        environment_errors.extend(f"{path}: unclosed {env}" for env in stack)
    add("fragments_are_real_latex", not markdown_residue and not document_commands, markdown_residue=markdown_residue, document_commands=document_commands)
    add("fragment_braces_balanced", not unbalanced, files=unbalanced)
    add("fragment_environments_balanced", not environment_errors, errors=environment_errors)

    # After XeLaTeX, inspect the generated auxiliary file when it exists.  A
    # pre-compilation audit remains useful and reports this check as pending
    # rather than manufacturing a failure from a missing build artifact.
    toc_path = main_path.with_suffix(".toc")
    if include_toc and stage == "render" and toc_path.is_file():
        toc_text = toc_path.read_text(encoding="utf-8", errors="replace")
        toc_levels = {
            level: bool(re.search(rf"\\contentsline\s*\{{{level}\}}", toc_text))
            for level in ("section", "subsection", "subsubsection")[:toc_depth]
        }
        expected_levels = {
            level: bool(re.search(rf"\\{level}\*?\s*(?:\[[^]]*\])?\s*\{{", remove_comments(all_text)))
            for level in toc_levels
        }
        toc_content_ok = all((not expected_levels[level]) or toc_levels[level] for level in toc_levels)
        add("toc_auxiliary_content", toc_content_ok, path=str(toc_path), expected=expected_levels, found=toc_levels)
    elif include_toc and stage == "render":
        add("toc_auxiliary_content", False, available=False, path=str(toc_path),
            message=".toc missing for rendered audit")
    else:
        checks.append({"code": "toc_auxiliary_content", "ok": None, "status": "NOT_RUN",
                       "message": "Source-only audit or TOC disabled by policy"})

    missing_graphics: list[str] = []
    for raw in GRAPHICS_RE.findall(all_text):
        try:
            # The paper source may reference real result figures stored in
            # the sibling 求解/ tree.  Inputs remain confined to 论文/;
            # graphics are allowed anywhere inside the project root.
            path = (root / raw).resolve()
            path.relative_to(project_root.resolve())
        except (ValueError, OSError):
            missing_graphics.append(raw)
            continue
        if not path.is_file():
            missing_graphics.append(raw)
    add("graphics_paths_exist", not missing_graphics, missing=missing_graphics)

    anonymous_text = all_text
    anonymity_scope = policy["official"]["anonymity_policy"]["scope"]
    if anonymity_scope == "none":
        anonymous_text = ""
    elif anonymity_scope == "after_cover" and cover_tex_path:
        cover_path = inside(root, cover_tex_path)
        # Reconstruct scope; replacing the cover's text could also remove an
        # identical identity leak in the anonymous body.
        anonymous_text = main_text + "\n" + "\n".join(
            path.read_text(encoding="utf-8-sig") for path in audit_paths if path != cover_path)
        nested_cover = False
        for path in audit_paths:
            if path == cover_path:
                continue
            for raw in INPUT_RE.findall(remove_comments(path.read_text(encoding="utf-8-sig"))):
                if any(candidate.resolve() == cover_path for candidate in (root / raw, path.parent / raw)):
                    nested_cover = True
        add("cover_not_reused_in_body", not nested_cover)
    identity_hits = sorted(set(re.findall(r"学校|学院|实验室|参赛队号|队员姓名|指导教师|学号|邮箱|C:\\Users\\", anonymous_text, re.I)))
    identity_hits += [term for term in policy["official"]["anonymity_policy"]["identity_terms"] if term in anonymous_text]
    add("anonymous_source", not identity_hits, matches=identity_hits)
    add("no_markdown_chapter_sources", not any(path.suffix.lower() == ".md" for path in audit_paths), files=[str(path) for path in audit_paths if path.suffix.lower() == ".md"])

    labels = LABEL_RE.findall(remove_comments(all_text))
    duplicate_labels = sorted({label for label in labels if labels.count(label) > 1})
    references = REF_RE.findall(remove_comments(all_text))
    missing_labels = sorted(set(references) - set(labels))
    add("labels_are_unique", not duplicate_labels, duplicates=duplicate_labels)
    add("references_resolve", not missing_labels, missing=missing_labels)

    unicode_math_hits = sorted(set(all_text) & FORBIDDEN_UNICODE_MATH)
    add(
        "math_uses_latex_commands",
        not unicode_math_hits,
        characters=unicode_math_hits,
        message="Unicode 上下标/运算符易落入西文字体并造成缺字；请改用 LaTeX 数学命令。",
    )

    italic_commands = sorted(set(re.findall(r"\\(?:itshape|textit|emph)\b", remove_comments(all_text))))
    add("no_explicit_body_italic", not italic_commands, commands=italic_commands)

    return {"status": "PASS" if not failures else "FAIL", "scope": f"TeX {stage} checks only; policy/PDF/evidence gates are separate",
            "manifest": str(manifest_path), "main": str(main_path), "checks": checks, "failures": failures}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--main", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--cover-tex")
    parser.add_argument("--stage", choices=["source", "render"], default="source")
    args = parser.parse_args()
    result = audit(args.manifest.resolve(), args.main.resolve(), load_policy(args.policy), args.cover_tex, args.stage)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
