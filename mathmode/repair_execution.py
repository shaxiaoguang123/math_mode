"""Authorization binding for executing an independently reviewed repair."""
from __future__ import annotations

from .code_repairs import verify_code_repair
from .io import safe_path, file_hash, read_json, canonical_root
from .runner import execute_model, verify_run, _history
from .state import workspace_lock


def validate_authorization(root, authorization, spec_relative, role, retry_of):
    if not isinstance(authorization, dict):
        raise ValueError("Execution authorization must be an object")
    if set(authorization) != {"request", "review", "candidate_spec", "execution_role", "retry_of"}:
        raise ValueError("Execution authorization is incomplete or has unknown fields")
    for key in ("request", "review", "candidate_spec"):
        pin = authorization[key]
        if not isinstance(pin, dict) or set(pin) != {"path", "sha256"} or not all(isinstance(v, str) for v in pin.values()):
            raise ValueError("Execution authorization has a malformed pin")
    if authorization["execution_role"] != role or authorization["retry_of"] != retry_of:
        raise ValueError("Execution authorization does not match the requested retry role/predecessor")
    request_path = authorization["request"]["path"]
    if file_hash(safe_path(root, request_path)) != authorization["request"]["sha256"]:
        raise ValueError("Execution authorization request hash mismatch")
    result = verify_code_repair(root, request_path)
    request = read_json(safe_path(root, request_path))
    if request["execution_role"] != role or result["retry_of"] != retry_of:
        raise ValueError("Execution authorization differs from the repair's actual role/predecessor")
    if (result["review"] != authorization["review"]["path"] or
            result["candidate_spec"] != spec_relative or authorization["candidate_spec"]["path"] != spec_relative):
        raise ValueError("Execution authorization does not bind the reviewed candidate")
    for key in ("review", "candidate_spec"):
        if file_hash(safe_path(root, authorization[key]["path"])) != authorization[key]["sha256"]:
            raise ValueError("Execution authorization artifact hash mismatch")
    return result


def execute_reviewed_repair(root, request_relative, *, interpreter=None):
    """Execute once or adopt the matching terminal retry, including FAIL."""
    root = canonical_root(root)
    with workspace_lock(root, scope="workflow"):
        return _execute_reviewed_repair(root, request_relative, interpreter=interpreter)


def _execute_reviewed_repair(root, request_relative, *, interpreter=None):
    request = read_json(safe_path(root, request_relative))
    reviewed = verify_code_repair(root, request_relative)
    authorization = {
        "request": {"path": request_relative, "sha256": file_hash(safe_path(root, request_relative))},
        "review": {"path": reviewed["review"], "sha256": file_hash(safe_path(root, reviewed["review"]))},
        "candidate_spec": {"path": reviewed["candidate_spec"], "sha256": file_hash(safe_path(root, reviewed["candidate_spec"]))},
        "execution_role": request["execution_role"], "retry_of": reviewed["retry_of"]}
    candidate = read_json(safe_path(root, reviewed["candidate_spec"]))
    history = _history(root, candidate["question_id"], candidate["method_id"], request["execution_role"])
    if history and history[-1]["run_id"] != reviewed["retry_of"]:
        latest = history[-1]
        if latest.get("execution_authorization") != authorization:
            raise ValueError("Repair predecessor is no longer latest; explicit diagnosis is required")
        return verify_run(root, f"runs/{latest['run_id']}/run_manifest.json", require_success=False)
    return execute_model(root, reviewed["candidate_spec"], role=request["execution_role"],
                         interpreter=interpreter, retry_of=reviewed["retry_of"],
                         execution_authorization=authorization)
