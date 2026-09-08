"""Recover observed stopped executions without fabricating completed run records."""
from __future__ import annotations

from pathlib import Path
import uuid

from .contracts import validate
from .io import canonical_root, file_hash, now, read_json, safe_path, write_json
from .processes import stopped
from .state import workspace_lock, LOCK_FILES


def recover_lock(root: Path, *, reason: str, scope="state") -> dict:
    root = canonical_root(root)
    if not reason.strip():
        raise ValueError("Recovery requires a diagnostic reason")
    if scope not in LOCK_FILES:
        raise ValueError("Unknown workspace lock scope")
    lock = safe_path(root, LOCK_FILES[scope])
    digest = file_hash(lock)
    try:
        ownership = read_json(lock)
    except ValueError as exc:
        raise ValueError("Legacy lock has no process identity; ownership cannot be inferred") from exc
    if not isinstance(ownership, dict) or "owner" not in ownership or not stopped(ownership["owner"]):
        raise ValueError("Cannot recover a lock whose owner is still running or unknown")
    relative = "recovery/lock-" + uuid.uuid4().hex + ".json"
    write_json(safe_path(root, relative, exists=False), {"recovered_at": now(), "reason": reason,
               "ownership": ownership, "lock_sha256": digest, "lock_scope": scope}, exclusive=True)
    if file_hash(lock) != digest:
        raise ValueError("Lock changed during recovery; archive preserved")
    lock.unlink()
    return {"status": "PASS", "scope": "stopped_writer_lock_recovery", "archive": relative}


def verify_recovery(root: Path, directory: str) -> dict:
    root = canonical_root(root)
    record = validate("recovery_event", read_json(safe_path(root, directory + "/recovery.json")), root=root)
    for reference in record["evidence"]:
        if file_hash(safe_path(root, reference["path"])) != reference["sha256"]:
            raise ValueError("Recovery evidence changed")
    return record


def recover_execution(root: Path, execution_id: str, *, kind: str, reason: str) -> dict:
    root = canonical_root(root)
    if kind not in {"run", "agent"} or not reason.strip():
        raise ValueError("Recovery requires a run/agent kind and a diagnostic reason")
    directory = ("runs/" if kind == "run" else "agent_runs/") + execution_id
    base = safe_path(root, directory, exists=False)
    finished = "run_manifest.json" if kind == "run" else "agent_result.json"
    if (base / finished).exists():
        raise ValueError("A terminal execution does not require interrupted recovery")
    request_name = "planned.json" if kind == "run" else "task.json"
    request = read_json(safe_path(root, directory + "/" + request_name))
    owner_path = safe_path(root, directory + "/owner.json")
    owner = read_json(owner_path)
    if not stopped(owner["owner"]):
        raise ValueError("Execution owner is still running")
    process_path = safe_path(root, directory + "/process.json", exists=False)
    started_name = "started.json" if kind == "run" else "backend_started.json"
    observation = "recorded_owner_and_child_stopped"
    if process_path.exists():
        process = read_json(process_path)
        if process["owner"] != owner["owner"] or not stopped(process["child"]):
            raise ValueError("Recorded execution process is still running or has a different owner")
        if any(not stopped(descendant) for descendant in process.get("descendants", [])):
            raise ValueError("A recorded descendant process is still running")
    elif (base / started_name).exists():
        raise ValueError("Launch began but process identity is missing; process exit cannot be inferred")
    else:
        observation = "owner_stopped_execution_not_started"
    expected_id = request.get("run_id" if kind == "run" else "task_id")
    if expected_id != execution_id:
        raise ValueError("Recovery request identity mismatch")
    names = [request_name, "owner.json"] + (["process.json"] if process_path.exists() else [])
    if (base / started_name).exists():
        names.append(started_name)
    evidence = [{"path": directory + "/" + name, "sha256": file_hash(safe_path(root, directory + "/" + name))}
                for name in names]
    event = {"schema_version": "2.0", "execution_id": execution_id, "kind": kind, "status": "ABANDONED",
        "recovered_at": now(), "reason": reason, "evidence": evidence, "attempt": request["attempt"],
        "returncode": None, "process_observation": observation,
        "descendant_quiescence": "NOT_PROVEN", "scientific_acceptance": "NOT_RUN"}
    validate("recovery_event", event, root=root)
    if (root / ".mathmode.lock").exists():
        recover_lock(root, reason=reason)
    with workspace_lock(root):
        if (base / finished).exists():
            raise ValueError("Execution became terminal during recovery")
        for reference in evidence:
            if file_hash(safe_path(root, reference["path"])) != reference["sha256"]:
                raise ValueError("Execution metadata changed during recovery")
        write_json(base / "recovery.json", event, exclusive=True)
    return event
