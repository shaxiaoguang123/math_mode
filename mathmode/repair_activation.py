"""Adopt an independently reviewed, successful repair without mutating canonical specs."""
from __future__ import annotations

from .code_repairs import verify_code_repair
from .contracts import validate
from .io import canonical_root, safe_path, read_json, write_json, file_hash, now
from .runner import verify_run
from .io import write_json


def activate_reviewed_repair(root, request_relative: str, run_relative: str):
    root = canonical_root(root)
    request = read_json(safe_path(root, request_relative))
    reviewed = verify_code_repair(root, request_relative)
    run = verify_run(root, run_relative, require_success=True)
    if run["spec"]["source_path"] != reviewed["candidate_spec"]:
        raise ValueError("Activation run does not execute the reviewed candidate")
    if run["role"] != request["execution_role"] or run.get("retry_of") != reviewed["retry_of"]:
        raise ValueError("Activation run is not the authorized repair retry")
    activation_id = "activation-" + request["repair_id"]
    relative = f"repairs/{request['repair_id']}/activation.json"
    record = validate("repair_activation", {"schema_version": "2.0", "activation_id": activation_id,
        "question_id": request["question_id"], "created_at": now(),
        "request": {"path": request_relative, "sha256": file_hash(safe_path(root, request_relative))},
        "review": {"path": reviewed["review"], "sha256": file_hash(safe_path(root, reviewed["review"]))},
        "candidate_spec": {"path": reviewed["candidate_spec"], "sha256": file_hash(safe_path(root, reviewed["candidate_spec"]))},
        "run": {"path": run_relative, "sha256": file_hash(safe_path(root, run_relative))},
        "failed_predecessor": {"path": request["failed_run"]["path"], "sha256": request["failed_run"]["sha256"]},
        "execution_role": request["execution_role"], "status": "ACTIVE"}, root=root)
    path = safe_path(root, relative, exists=False)
    if path.exists():
        existing = read_json(path)
        if {k: v for k, v in existing.items() if k != "created_at"} != {k: v for k, v in record.items() if k != "created_at"}:
            raise ValueError("Conflicting repair activation already exists")
        return existing
    else: write_json(path, record, exclusive=True)
    return record


def adopt_activation_in_progress(root, progress_relative: str, activation_relative: str, *, role: str):
    """Point progress at an ACTIVE candidate while preserving prior run lineage."""
    root = canonical_root(root)
    progress = read_json(safe_path(root, progress_relative))
    activation = validate("repair_activation", read_json(safe_path(root, activation_relative)), root=root)
    if activation["status"] != "ACTIVE":
        raise ValueError("Only ACTIVE repair activations can update workflow progress")
    question = progress["questions"].get(activation["question_id"])
    if question is None:
        raise ValueError("Repair activation belongs to an unknown workflow question")
    field = "effective_baseline_spec" if role == "baseline" else "effective_main_spec"
    question[field] = activation["candidate_spec"]["path"]
    question["repair_activation"] = activation_relative
    write_json(safe_path(root, progress_relative), progress)
    return progress
