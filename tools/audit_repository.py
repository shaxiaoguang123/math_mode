"""Inventory a Git revision without importing or executing its model code.

Reads Git blobs, not historical README claims. This is an engineering inventory,
not a scientific correctness or official competition compliance certificate.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import re
import subprocess
import sys
import warnings
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

from jsonschema import Draft202012Validator


PATTERNS = {
    "absolute_windows_path": r"[A-Za-z]:[\\/][^\s\"'<>]+",
    "edition_literal": r"二十三|第二十三届|2026",
    "page_policy": r"required_body_pages|45\s*页|hard failure",
    "cover_anonymity_toc": r"maketitle|maketoc|anonym|匿名|封面|TOC",
    "shell_true": r"shell\s*=\s*True",
    "secret_pattern": r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "contact_pattern": r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|(?<!\d)1[3-9]\d{9}(?!\d)",
}


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True).stdout


def inventory(root: Path, revision: str) -> dict:
    commit = git(root, "rev-parse", f"{revision}^{{commit}}").decode().strip()
    tree = git(root, "ls-tree", "-rz", "--full-tree", commit).split(b"\0")
    files, errors, hashes = [], [], {}
    for record in tree:
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, kind, oid = metadata.decode().split()
        name = raw_path.decode("utf-8")
        if kind != "blob":
            errors.append({"path": name, "error": "non-blob entry requires separate review"})
            continue
        data = git(root, "cat-file", "blob", oid)
        digest = hashlib.sha256(data).hexdigest()
        hashes[name] = digest
        item = {"path": name, "mode": mode, "size_bytes": len(data), "sha256": digest,
                "suffix": Path(name).suffix.lower()}
        try:
            text = data.decode("utf-8-sig") if b"\0" not in data else None
        except UnicodeDecodeError:
            text = None
        item["utf8_text"] = text is not None
        if text is not None:
            item["lines"] = len(text.splitlines())
            item["review_locations"] = {
                key: [i for i, line in enumerate(text.splitlines(), 1) if re.search(pattern, line)]
                for key, pattern in PATTERNS.items()
            }
            item["review_locations"] = {k: v for k, v in item["review_locations"].items() if v}
            if name.endswith(".py"):
                try:
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter("always")
                        parsed = ast.parse(text, filename=name)
                        compile(parsed, name, "exec")
                    item["syntax"] = "PASS"
                    item["syntax_warnings"] = [str(w.message) for w in caught]
                    item["definitions"] = [{"name": n.name, "line": n.lineno}
                                           for n in ast.walk(parsed)
                                           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
                    item["imports"] = sorted({n.module or "" for n in ast.walk(parsed)
                                              if isinstance(n, ast.ImportFrom)} |
                                             {a.name for n in ast.walk(parsed)
                                              if isinstance(n, ast.Import) for a in n.names})
                except (SyntaxError, ValueError) as exc:
                    item["syntax"] = "FAIL"
                    errors.append({"path": name, "error": str(exc)})
            if name.endswith(".json"):
                try:
                    obj = json.loads(text)
                    item["json"] = "PASS"
                    if isinstance(obj, dict) and "$schema" in obj:
                        Draft202012Validator.check_schema(obj)
                        item["schema"] = "PASS"
                except Exception as exc:
                    errors.append({"path": name, "error": str(exc)})
        elif name.endswith(".docx"):
            with zipfile.ZipFile(io.BytesIO(data)) as package:
                item["docx_members"] = len(package.namelist())
                doc = ElementTree.fromstring(package.read("word/document.xml"))
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                # Only identify template features; do not publish identity values.
                plain = "".join(n.text or "" for n in doc.findall(".//w:t", ns))
                item["template_features"] = {word: word in plain for word in
                    ("学校", "参赛队号", "队员姓名", "摘要", "目录", "45", "身份", "第二十三届")}
                item["hidden_payload_members"] = [n for n in package.namelist()
                    if n.startswith(("customXml/", "word/embeddings/"))]
        files.append(item)
    prefix_a = ".agents/skills/academic-figure-skill/"
    prefix_b = ".claude/skills/academic-figure-skill/"
    a = {k[len(prefix_a):]: v for k, v in hashes.items() if k.startswith(prefix_a)}
    b = {k[len(prefix_b):]: v for k, v in hashes.items() if k.startswith(prefix_b)}
    mirror = {"only_agents": sorted(a.keys() - b.keys()), "only_claude": sorted(b.keys() - a.keys()),
              "different": sorted(k for k in a.keys() & b.keys() if a[k] != b[k])}
    return {
        "schema_version": "1.0", "revision": commit,
        "scope": "Every tracked blob at revision, UTF-8 text decoded; Python AST/syntax and JSON schemas checked; binary hashes and DOCX structure inspected. This does not run modeling code.",
        "python_version": sys.version.split()[0],
        "totals": {"files": len(files), "bytes": sum(f["size_bytes"] for f in files),
                   "extensions": dict(sorted(Counter(f["suffix"] for f in files).items()))},
        "test_entries": [f["path"] for f in files if Path(f["path"]).name.startswith("test_")],
        "ci_entries": [f["path"] for f in files if f["path"].startswith(".github/workflows/")],
        "skill_parity": mirror, "inspection_errors": errors, "files": files,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inventory(args.root.resolve(), args.revision)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("revision", "totals", "skill_parity", "inspection_errors")}, ensure_ascii=False))
    raise SystemExit(bool(result["inspection_errors"]))


if __name__ == "__main__":
    main()
