"""Artifact registry and transitive invalidation shared by every downstream tool."""
from __future__ import annotations

import hashlib
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

from .io import canonical_root, file_hash, now, safe_path, read_json
from .state import StateStore


def artifact_id(relative: str) -> str:
    return "artifact-" + hashlib.sha256(relative.encode("utf-8")).hexdigest()[:24]


def descendants(artifacts: list[dict], roots: set[str]) -> set[str]:
    found = set(roots)
    while True:
        additional = {a["artifact_id"] for a in artifacts if any(d["artifact_id"] in found for d in a["depends_on"])} - found
        if not additional:
            return found
        found.update(additional)


def mark_stale(state: dict, affected: set[str], reason: str):
    for artifact in state["artifacts"]:
        if artifact["artifact_id"] in affected:
            artifact["status"] = "STALE"
    for gate in state["gates"]:
        if affected & set(gate["artifact_refs"]):
            gate.update(status="BLOCKED", blockers=[reason], checked_at=now())


class ArtifactRegistry:
    def __init__(self, root: Path):
        self.root = canonical_root(root)
        self.store = StateStore(self.root)
        self._pending = None
        self._pending_stale = set()

    @contextmanager
    def batch(self):
        """Validate and commit a whole evidence graph with one revision transaction."""
        if self._pending is not None:
            raise ValueError("Nested registry batches are not supported")
        original = self.store.load()
        self._pending = deepcopy(original)
        self._pending_stale = set(self.store.inspect_freshness()["stale"])
        try:
            yield self
            pending = self._pending
            def publish(state):
                state.clear()
                state.update(pending)
            self.store.update(publish, expected_revision=original["revision"])
        finally:
            self._pending = None
            self._pending_stale = set()

    def register(self, relative: str, *, producer: str, dependencies=None, status="VALID") -> str:
        if status not in {"DRAFT", "VALID"}:
            raise ValueError("Only freeze service may register frozen artifacts")
        path = safe_path(self.root, relative)
        relative = path.relative_to(self.root).as_posix()
        key = artifact_id(relative)
        state = self._pending if self._pending is not None else self.store.load()
        stale = self._pending_stale if self._pending is not None else set(self.store.inspect_freshness()["stale"])
        def change(state):
            registry = {a["artifact_id"]: a for a in state["artifacts"]}
            previous = registry.get(key)
            resolved_dependencies = list(dependencies) if dependencies is not None else (
                [dep["artifact_id"] for dep in previous["depends_on"]] if previous else [])
            if set(resolved_dependencies) - registry.keys():
                raise ValueError("Cannot register an unknown dependency")
            for dependency in resolved_dependencies:
                item = registry[dependency]
                actual = safe_path(self.root, item["path"])
                if dependency in stale or item["status"] not in {"VALID", "FROZEN"} or file_hash(actual) != item["sha256"]:
                    raise ValueError("Cannot consume a stale dependency")
            record = {"artifact_id": key, "path": relative, "sha256": file_hash(path),
                "size_bytes": path.stat().st_size, "created_at": now(), "producer": producer,
                "depends_on": [{"artifact_id": dep, "sha256": registry[dep]["sha256"]} for dep in sorted(set(resolved_dependencies))], "status": status}
            if previous:
                changed = previous["sha256"] != record["sha256"] or previous["depends_on"] != record["depends_on"]
                if not changed and previous["status"] in {"VALID", "FROZEN"}:
                    return
                affected = descendants(state["artifacts"], {key})
                active_freezes = set()
                index_path = safe_path(self.root, "frozen_numbers.json", exists=False)
                if index_path.exists():
                    from .contracts import validate
                    index = validate("freeze_index", read_json(index_path), root=self.root)
                    active_freezes = {artifact_id(pointer["path"]) for pointer in index["questions"].values() if pointer["status"] == "FROZEN"}
                if affected & active_freezes or any(a["status"] == "FROZEN" for a in state["artifacts"] if a["artifact_id"] in affected):
                    raise ValueError("A frozen consumer exists; thaw before canonical changes")
                mark_stale(state, affected, f"Canonical artifact changed: {key}")
                state["artifacts"] = [a for a in state["artifacts"] if a["artifact_id"] != key]
            state["artifacts"].append(record)
            stale.discard(key)
        if self._pending is not None:
            change(state)
        else:
            self.store.update(change, expected_revision=state["revision"])
        return key

    def refresh(self) -> dict:
        observation = self.store.inspect_freshness()
        if observation["stale"]:
            self.store.update(lambda state: mark_stale(state, set(observation["stale"]), "Upstream artifact is stale"),
                              expected_revision=observation["revision"])
        return observation

    def invalidate(self, keys: set[str], reason: str):
        state = self.store.load()
        available = {a["artifact_id"] for a in state["artifacts"]}
        if not keys <= available or not reason.strip():
            raise ValueError("Invalid invalidation roots/reason")
        affected = descendants(state["artifacts"], keys)
        self.store.update(lambda state: mark_stale(state, affected, reason), expected_revision=state["revision"])
        return affected
