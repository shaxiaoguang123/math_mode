"""Revisioned workspace state with exclusive writers and hash-based resume."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

from .contracts import validate
from .io import file_hash, now, read_json, safe_path, write_json, canonical_bytes, canonical_root


@contextmanager
def workspace_lock(root: Path):
    """A crashed writer leaves a visible lock; never silently steal it."""
    lock = root / ".mathmode.lock"
    try:
        handle = lock.open("x", encoding="utf-8")
    except FileExistsError as exc:
        raise ValueError(f"Workspace is locked; inspect interrupted writer: {lock}") from exc
    try:
        with handle:
            handle.write(now())
        yield
    finally:
        lock.unlink()


def initial_state(case_id: str, kind="competition", mode="autopilot", profile="lean") -> dict:
    stamp = now()
    return validate("workflow_state", {
        "schema_version": "2.0", "case_id": case_id, "revision": 0,
        "created_at": stamp, "updated_at": stamp, "workspace_kind": kind,
        "interaction_mode": mode, "rigor_profile": profile, "blind_reference_mode": True,
        "artifacts": [], "gates": [], "retry_history": [], "reference_access": []})


class StateStore:
    def __init__(self, root: Path):
        self.root = canonical_root(root)
        self.path = safe_path(self.root, "workflow_state.json", exists=False)

    def load(self) -> dict:
        return validate("workflow_state", read_json(self.path), root=self.root)

    def create(self, state: dict):
        validate("workflow_state", state, root=self.root)
        write_json(self.path, state, exclusive=True)

    def update(self, mutation, *, expected_revision: int) -> dict:
        with workspace_lock(self.root):
            previous = self.load()
            if previous["revision"] != expected_revision:
                raise ValueError("Concurrent state update: revision changed")
            state = deepcopy(previous)
            mutation(state)
            for field in ("case_id", "created_at", "workspace_kind"):
                if state[field] != previous[field]:
                    raise ValueError(f"Immutable state identity: {field}")
            for field in ("retry_history", "reference_access"):
                if state[field][:len(previous[field])] != previous[field]:
                    raise ValueError(f"Append-only state history: {field}")
            state["revision"] = previous["revision"] + 1
            state["updated_at"] = now()
            validate("workflow_state", state, root=self.root)
            write_json(self.path, state)
            return state

    def inspect_freshness(self) -> dict:
        state = self.load()
        artifacts = {item["artifact_id"]: item for item in state["artifacts"]}
        stale = set()
        reasons = {}
        for key, item in artifacts.items():
            try:
                path = safe_path(self.root, item["path"])
                if path.stat().st_size != item["size_bytes"] or file_hash(path) != item["sha256"]:
                    raise ValueError("content hash/size changed")
                if item["status"] in {"STALE", "FAILED", "DRAFT"}:
                    raise ValueError(f"artifact status {item['status']}")
                for dep in item["depends_on"]:
                    if artifacts[dep["artifact_id"]]["sha256"] != dep["sha256"]:
                        raise ValueError("dependency hash changed")
            except (ValueError, OSError) as exc:
                stale.add(key)
                reasons[key] = str(exc)
        while True:
            affected = {key for key, item in artifacts.items()
                        if any(dep["artifact_id"] in stale for dep in item["depends_on"])} - stale
            if not affected:
                break
            stale.update(affected)
            reasons.update({key: "upstream artifact is stale" for key in affected})
        return {"status": "BLOCKED" if stale else "PASS", "scope": "artifact_freshness",
                "revision": state["revision"], "stale": sorted(stale), "reasons": reasons}


def append_event(root: Path, relative: str, event: dict, *, contract: str):
    """Append without rewriting history; torn writes fail closed on next read."""
    from .contracts import read_ledger
    import os
    import tempfile

    validate(contract, event, root=root)
    path = safe_path(root, relative, exists=False)
    with workspace_lock(root):
        previous = path.read_bytes() if path.exists() else b""
        content = previous + canonical_bytes(event)
        # Validate complete event sequence before touching the canonical ledger.
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "ledger.jsonl"
            candidate.write_bytes(content)
            read_ledger(candidate, contract)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("ab") as handle:
            handle.write(canonical_bytes(event))
            handle.flush()
            os.fsync(handle.fileno())
