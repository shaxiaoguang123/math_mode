"""Adopt an independently reviewed, successful repair without mutating canonical specs."""
from __future__ import annotations

from .code_repairs import verify_code_repair
from .contracts import validate
from .io import canonical_root, safe_path, read_json, write_json, file_hash, now
from .runner import verify_run, _history
from .state import workspace_lock
from .lineage import artifact_id, ArtifactRegistry


def activate_reviewed_repair(root, request_relative: str, run_relative: str):
    root = canonical_root(root)
    with workspace_lock(root, scope="workflow"):
        record = _definition(root, request_relative, run_relative, now())
        relative = _location(record)
        path = safe_path(root, relative, exists=False)
        if path.exists():
            existing = verify_activation(root, relative)
            record["created_at"] = existing["created_at"]
            if existing != record:
                raise ValueError("Conflicting repair activation already exists")
            return existing
        write_json(path, record, exclusive=True)
        return record


def _location(record):
    return record["request"]["path"].rsplit("/", 1)[0] + "/activation.json"


def _definition(root, request_relative, run_relative, created_at):
    request = read_json(safe_path(root, request_relative))
    reviewed = verify_code_repair(root, request_relative)
    run = verify_run(root, run_relative, require_success=True)
    if run["spec"]["source_path"] != reviewed["candidate_spec"]:
        raise ValueError("Activation run does not execute the reviewed candidate")
    if run["role"] != request["execution_role"] or run.get("retry_of") != reviewed["retry_of"]:
        raise ValueError("Activation run is not the authorized repair retry")
    authorization = run.get("execution_authorization")
    if authorization is None or authorization["request"]["path"] != request_relative:
        raise ValueError("Activation requires the matching execution authorization")
    # verify_run rechecks authorization against the hashed pre-execution plan
    # and actual independent repair handoffs. A normal retry has no such grant.
    history = _history(root, run["question_id"], run["method_id"], run["role"])
    if not history or history[-1]["run_id"] != run["run_id"]:
        raise ValueError("Activation requires the latest terminal repair run")
    activation_id = "activation-" + request["repair_id"]
    return validate("repair_activation", {"schema_version": "2.0", "activation_id": activation_id,
        "question_id": request["question_id"], "created_at": created_at,
        "request": {"path": request_relative, "sha256": file_hash(safe_path(root, request_relative))},
        "review": {"path": reviewed["review"], "sha256": file_hash(safe_path(root, reviewed["review"]))},
        "candidate_spec": {"path": reviewed["candidate_spec"], "sha256": file_hash(safe_path(root, reviewed["candidate_spec"]))},
        "run": {"path": run_relative, "sha256": file_hash(safe_path(root, run_relative))},
        "failed_predecessor": {"path": request["failed_run"]["path"], "sha256": request["failed_run"]["sha256"]},
        "execution_role": request["execution_role"], "status": "ACTIVE"}, root=root)


def verify_activation(root, relative):
    """Rederive all pins and identities; a handwritten ACTIVE is not evidence."""
    root = canonical_root(root)
    record = validate("repair_activation", read_json(safe_path(root, relative)), root=root)
    if relative != _location(record):
        raise ValueError("Repair activation location differs from its request")
    expected = _definition(root, record["request"]["path"], record["run"]["path"], record["created_at"])
    if record != expected:
        raise ValueError("Repair activation differs from verified execution evidence")
    return record


def adopt_activation_in_progress(root, progress_relative: str, activation_relative: str, *, role: str):
    """Point progress at an ACTIVE candidate while preserving prior run lineage."""
    root = canonical_root(root)
    with workspace_lock(root, scope="workflow"):
        return _adopt(root, progress_relative, activation_relative, role)


def _adopt(root, progress_relative, activation_relative, role):
    if progress_relative != "workflow_progress.json":
        raise ValueError("Adoption requires canonical workflow progress")
    progress = validate("workflow_progress", read_json(safe_path(root, progress_relative)), root=root)
    activation = verify_activation(root, activation_relative)
    if role not in {"main", "baseline", "fallback"} or role != activation["execution_role"]:
        raise ValueError("Adoption role must match the production repair execution role")
    question = progress["questions"].get(activation["question_id"])
    if question is None:
        raise ValueError("Repair activation belongs to an unknown workflow question")
    field = "effective_baseline_spec" if role == "baseline" else "effective_main_spec"
    question[field] = activation["candidate_spec"]["path"]
    question["repair_activation"] = activation_relative
    validate("workflow_progress", progress, root=root)
    # Invalidate all registered descendants of the previous numerical evidence
    # before publishing the effective pointer. Historical files remain intact.
    roots = {artifact_id(path) for path in (question.get("validation"), question.get("evidence")) if path}
    registry = ArtifactRegistry(root)
    registered = {item["artifact_id"] for item in registry.store.load()["artifacts"]}
    roots &= registered
    if roots:
        registry.invalidate(roots, "Reviewed repair activation invalidated prior numerical evidence")
    write_json(safe_path(root, progress_relative), progress)
    return progress
