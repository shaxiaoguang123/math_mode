"""Adopt an independently reviewed, successful repair without mutating canonical specs."""
from __future__ import annotations

from .code_repairs import verify_code_repair
from .contracts import validate
from .io import canonical_root, safe_path, read_json, write_json, file_hash, now
from .runner import verify_run


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
        if read_json(path) != record: raise ValueError("Conflicting repair activation already exists")
    else: write_json(path, record, exclusive=True)
    return record
