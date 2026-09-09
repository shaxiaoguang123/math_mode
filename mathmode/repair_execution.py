"""Authorization binding for executing an independently reviewed repair."""
from __future__ import annotations

from .code_repairs import verify_code_repair
from .io import safe_path, file_hash


def validate_authorization(root, authorization, spec_relative, role, retry_of):
    if not isinstance(authorization, dict):
        raise ValueError("Execution authorization must be an object")
    for key in ("request", "review", "candidate_spec", "execution_role", "retry_of"):
        if key not in authorization:
            raise ValueError("Execution authorization is incomplete")
    if authorization["execution_role"] != role or authorization["retry_of"] != retry_of:
        raise ValueError("Execution authorization does not match the requested retry role/predecessor")
    request_path = authorization["request"]["path"]
    if file_hash(safe_path(root, request_path)) != authorization["request"]["sha256"]:
        raise ValueError("Execution authorization request hash mismatch")
    result = verify_code_repair(root, request_path)
    if result["review"] != authorization["review"]["path"] or result["candidate_spec"] != spec_relative:
        raise ValueError("Execution authorization does not bind the reviewed candidate")
    for key in ("review", "candidate_spec"):
        if file_hash(safe_path(root, authorization[key]["path"])) != authorization[key]["sha256"]:
            raise ValueError("Execution authorization artifact hash mismatch")
    return result
