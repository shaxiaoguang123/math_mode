"""Initialize private competition workspaces from explicitly attributed inputs."""
from __future__ import annotations

import os
import re
import shutil
import stat
import tempfile
from pathlib import Path

from .contracts import validate
from .io import file_hash, now, write_json, canonical_root
from .state import StateStore, initial_state

REPO_ROOT = Path(__file__).resolve().parents[1]


def initialize(case_id: str, inputs: list[dict], *, destination: Path | None = None,
               kind="competition", mode="autopilot", profile="lean", producer="preflight", blind_reference_mode=True) -> Path:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,95}", case_id):
        raise ValueError("Case ID must be a portable contract identifier")
    target = (destination or REPO_ROOT.parent / "competitions" / case_id).absolute()
    for component in (target, *target.parents):
        if component.is_symlink() or getattr(component, "is_junction", lambda: False)():
            raise ValueError("Workspace destination cannot traverse a symlink/junction")
    target = canonical_root(target)
    public_root = canonical_root(REPO_ROOT)
    if kind == "competition" and (target == public_root or public_root in target.parents):
        raise ValueError("Formal competition workspace must stay outside the public template repository")
    if target.exists():
        raise ValueError("Refusing to overwrite an existing workspace")
    state = initial_state(case_id, kind, mode, profile, blind_reference_mode=blind_reference_mode)
    sources = []
    manifest = {"schema_version": "2.0", "case_id": case_id, "created_at": now(),
                "producer": producer, "frozen": True, "files": []}
    for item in inputs:
        if set(item) != {"input_id", "path", "role", "source"}:
            raise ValueError("Input declaration requires input_id, path, role and source only")
        raw_source = Path(item["path"]).absolute()
        if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (raw_source, *raw_source.parents)):
            raise ValueError("Original input source cannot traverse a symlink/junction")
        source = canonical_root(raw_source)
        if not source.is_file() or not source.stat().st_size:
            raise ValueError(f"Original input is missing/empty: {source.name}")
        relative = f"inputs/{item['input_id']}/{source.name}"
        manifest["files"].append({"input_id": item["input_id"], "path": relative,
            "role": item["role"], "source": item["source"], "sha256": file_hash(source),
            "size_bytes": source.stat().st_size, "readonly": True})
        sources.append(source)
    validate("input_manifest", manifest)
    # All declarations are valid before staging; never overwrite an existing workspace.
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{case_id}.init-", dir=target.parent))
    try:
        for source, record in zip(sources, manifest["files"]):
            output = staging / record["path"]
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, output)
            if file_hash(output) != record["sha256"]:
                raise ValueError("Input changed during snapshot copy")
            output.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        validate("input_manifest", manifest, root=staging)
        write_json(staging / "input_manifest.json", manifest, exclusive=True)
        StateStore(staging).create(state)
        (staging / "WORKSPACE.md").write_text(
            f"# {case_id}\n\nWorkspace kind: {kind}. Original input snapshots are read-only.\n"
            "Policy verification and scientific gates have NOT_RUN status.\n"
            "This directory contains private working material; do not publish it by default.\n", encoding="utf-8")
        # Reserve target before moving children, preventing POSIX rename over an empty workspace.
        target.mkdir()
        try:
            for child in staging.iterdir():
                os.rename(child, target / child.name)
        except BaseException:
            # Preserve partial destination for diagnosis; no existing user content is removed.
            raise
        return target
    finally:
        # Only clean the known temporary directory created by this call.
        if staging.exists():
            if staging.resolve().parent != target.parent.resolve() or not staging.name.startswith(f".{case_id}.init-"):
                raise ValueError("Refusing to clean an unexpected staging path")
            for path in staging.rglob("*"):
                if path.is_file():
                    path.chmod(stat.S_IRUSR | stat.S_IWUSR)
            shutil.rmtree(staging)
