"""Stage diagnosed code repairs and obtain independent review before execution."""
from __future__ import annotations

from copy import deepcopy
from jsonschema import ValidationError

from .agents import verify_agent_result
from .contracts import validate
from .io import read_json, write_json, safe_path, file_hash, now
from .lineage import artifact_id
from .repairs import verify_diagnosis, evidence_paths
from .runner import verify_run


def _pin(root, relative):
    return {"path": relative, "sha256": file_hash(safe_path(root, relative))}


def _definition(root, diagnosis_path, created_at):
    diagnosis = verify_diagnosis(root, diagnosis_path)
    if diagnosis["failure_class"] != "CODE_FAILURE":
        raise ValueError("Code repair requires an independent CODE_FAILURE diagnosis")
    failed = verify_run(root, diagnosis["failure_source"]["path"], require_success=False)
    if failed["status"] != "FAIL":
        raise ValueError("Code repair requires a terminal failure")
    if failed["attempt"] >= 3:
        raise ValueError("Run budget exhausted; return to the upstream modeling owner")
    if failed["role"] not in {"main", "baseline", "fallback", "probe"}:
        raise ValueError("This code repair adapter does not handle validator executions")
    key = "repair-" + failed["run_id"]
    prefix = ("probes" if failed["role"] == "probe" else "code") + "/repairs/" + key
    spec_prefix = "probes" if failed["role"] == "probe" else "models"
    return validate("code_repair_request", {"schema_version": "2.0", "repair_id": key,
        "question_id": failed["question_id"], "created_at": created_at,
        "diagnosis": _pin(root, diagnosis_path), "failed_run": diagnosis["failure_source"],
        "original_spec": _pin(root, failed["spec"]["source_path"]), "execution_role": failed["role"],
        "candidate_spec": f"{spec_prefix}/repairs/{key}/model_spec.json",
        "review": f"reviews/{key}-code.json",
        "code": [{"source": item["source_path"], "snapshot": {"path": item["snapshot_path"], "sha256": item["sha256"]},
                  "candidate": f"{prefix}/{item['source_path']}"} for item in failed["code"]]}, root=root)


def verify_request(root, relative):
    request = validate("code_repair_request", read_json(safe_path(root, relative)), root=root)
    if relative != f"repairs/{request['repair_id']}/request.json":
        raise ValueError("Code repair request location differs from its identity")
    expected = _definition(root, request["diagnosis"]["path"], request["created_at"])
    if request != expected:
        raise ValueError("Code repair request differs from the verified failed execution")
    return request


def _contract(root, path, kind):
    from .orchestrator import Orchestrator
    actual_kind, value = Orchestrator(root, None)._kind(path)
    if actual_kind != kind:
        raise ValueError(f"Code repair requires an actual current {kind} handoff: {path}")
    return value


def verify_candidate(root, relative):
    request = verify_request(root, relative)
    candidate = _contract(root, request["candidate_spec"], "model_spec")
    expected = deepcopy(read_json(safe_path(root, request["original_spec"]["path"])))
    mapping = {item["source"]: item["candidate"] for item in request["code"]}
    expected["implementation"] = {**expected["implementation"],
        "entrypoint": mapping[expected["implementation"]["entrypoint"]],
        "code_files": [mapping[path] for path in expected["implementation"]["code_files"]]}
    if candidate != expected:
        raise ValueError("Code repair changed model semantics, actor, criteria or declared execution controls")
    required_outputs = {request["candidate_spec"], *[item["candidate"] for item in request["code"]]}
    failure = read_json(safe_path(root, request["failed_run"]["path"]))
    required_inputs = {relative, request["diagnosis"]["path"], request["failed_run"]["path"],
                       request["original_spec"]["path"], *evidence_paths(failure)}
    producer_found = False
    for task_path in (root / "agent_runs").glob("*/task.json"):
        task = read_json(safe_path(root, task_path.relative_to(root).as_posix()))
        if (task["actor_id"] != candidate["actor_id"] or task["role"] not in {"code", "probe"}
                or {item["path"] for item in task["outputs"]} != required_outputs
                or not required_inputs <= {item["path"] for item in task["inputs"]}):
            continue
        try:
            verify_agent_result(root, task["task_id"])
        except (ValueError, OSError, ValidationError):
            continue
        producer_found = True
        break
    if not producer_found:
        raise ValueError("Code repair requires one actual producer handoff for the complete candidate bundle")
    if all(file_hash(safe_path(root, item["candidate"])) == item["snapshot"]["sha256"] for item in request["code"]):
        raise ValueError("Code repair contains no actual code change")
    return request, candidate


def verify_code_repair(root, relative):
    request, candidate = verify_candidate(root, relative)
    review = _contract(root, request["review"], "semantic_review")
    diagnosis = verify_diagnosis(root, request["diagnosis"]["path"])
    if (review["question_id"] != request["question_id"] or review["reviewed_actor_id"] != candidate["actor_id"]
            or review["actor_id"] in {candidate["actor_id"], diagnosis["actor_id"]}):
        raise ValueError("Code repair review requires a separate reviewer of the actual repaired producer")
    required = {relative, request["diagnosis"]["path"], request["failed_run"]["path"],
                request["original_spec"]["path"], request["candidate_spec"], *[item["candidate"] for item in request["code"]]}
    if {artifact_id(path) for path in required} - set(review["artifact_refs"]):
        raise ValueError("Code repair review omits required repair evidence")
    if review["verdict"] != "SUPPORTED" or any(item["severity"] in {"warning", "error"} for item in review["findings"]) or review["limitations"]:
        raise ValueError("Code repair review has unresolved findings or limitations")
    return {"status": "PASS", "scope": "independently_reviewed_code_repair", "request": relative,
            "candidate_spec": request["candidate_spec"], "review": request["review"],
            "retry_of": request["failed_run"]["path"].split("/")[1],
            "scientific_acceptance": "NOT_RUN", "execution": "NOT_RUN"}


def prepare_code_repair(workflow, plan, job, diagnosis_path):
    """Advance one fixed repair-generation or review task; preserve rejected work."""
    root = workflow.root
    definition = _definition(root, diagnosis_path, now())
    relative = f"repairs/{definition['repair_id']}/request.json"
    path = safe_path(root, relative, exists=False)
    if not path.exists():
        write_json(path, definition, exclusive=True)
    request = verify_request(root, relative)
    if request["question_id"] != job["question_id"]:
        raise ValueError("Repair request belongs to another workflow question")
    slot = "baseline_spec" if request["execution_role"] == "baseline" else "main_spec"
    if request["execution_role"] == "probe":
        if job.get("probe_specs") and request["original_spec"]["path"] not in job["probe_specs"]:
            raise ValueError("Repair no longer targets a selected workflow probe")
    elif job.get(slot) and job[slot] != request["original_spec"]["path"]:
        raise ValueError("Repair no longer targets the selected workflow model")
    failed = verify_run(root, request["failed_run"]["path"], require_success=False)
    inputs = {diagnosis_path, request["failed_run"]["path"], request["original_spec"]["path"], *evidence_paths(failed)}
    with workflow.registry.batch():
        registered = {item["path"]: item for item in workflow.registry.store.load()["artifacts"]}
        # Diagnosis already registered historical evidence. The current spec is
        # an actual code handoff, never silently reattributed by this service.
        _contract(root, request["original_spec"]["path"], "model_spec")
        if request["original_spec"]["path"] not in registered:
            raise ValueError("Repair requires a registered original model spec")
        workflow.registry.register(relative, producer="code-repair-service", dependencies=[artifact_id(p) for p in inputs])
    inputs.add(relative)
    inputs.add("input_manifest.json")
    inputs.update(path for key, path in plan["framing"].items() if key != "review")
    inputs.update(item["path"] for item in read_json(root / "input_manifest.json")["files"])
    inputs.add(job["method_card"])
    if request["execution_role"] != "probe":
        inputs.add(job["decision"])
        inputs.update(job["probe_reports"])
    for binding in plan.get("dispositions", []):
        inputs.update(binding.values())
    original = read_json(root / request["original_spec"]["path"])
    candidate_exists = safe_path(root, request["candidate_spec"], exists=False).exists()
    if candidate_exists:
        verify_candidate(root, relative)
        if safe_path(root, request["review"], exists=False).exists():
            return {**verify_code_repair(root, relative), "executed": []}
        inputs.update([request["candidate_spec"], *[item["candidate"] for item in request["code"]]])
        if request["execution_role"] != "probe":
            for field in ("main_spec", "baseline_spec"):
                if job.get(field):
                    paired = _contract(root, job[field], "model_spec")
                    inputs.add(job[field])
                    inputs.update(paired["implementation"]["code_files"])
                    criteria = paired["validation_plan"].get("criteria")
                    if criteria:
                        inputs.add(criteria["path"])
        role, key, actor = "reviewer", request["repair_id"] + "-review", request["repair_id"] + "-reviewer"
        outputs = [{"path": request["review"], "contract": "semantic_review", "format": "json"}]
        instructions = "Independently review the diagnosed code repair, the original requirements/model and all proposed code. Compare with the immutable failed snapshots and logs. Check the diagnosis is addressed without changing model semantics, criteria, split, seed, outputs or resources. Check relocated imports and completeness of the runnable code bundle. Cite the request, diagnosis, failed manifest, original and candidate specs and every candidate code file in artifact_refs. Report actual findings/limitations; do not approve an incomplete repair or claim a rerun. Your review cannot establish numerical or scientific acceptance."
    else:
        role = "probe" if request["execution_role"] == "probe" else "code"
        key, actor = request["repair_id"] + "-code", original["actor_id"]
        outputs = [{"path": request["candidate_spec"], "contract": "model_spec", "format": "json"},
                   *[{"path": item["candidate"], "contract": None, "format": "python"} for item in request["code"]]]
        instructions = "Implement the independently diagnosed CODE_FAILURE using the supplied original requirements, approved model, failure evidence and code_repair_request. Produce the exact allowed candidate spec and complete Python code bundle. Copy the original model spec exactly except implementation.entrypoint and implementation.code_files, which must use the source-to-candidate mapping in the request, in the same order. Preserve actor_id, formulas, parameters, seed, inputs, splits, validation criteria, output contracts and limits. Fix imports for the relocated complete bundle without depending on undeclared original solver modules. Do not write original code, run the model, invent outputs or approve the repair. Return BLOCKED if the diagnosis requires changing the model rather than its implementation."
    task = {"task_id": key, "actor_id": actor, "role": role, "question_id": job["question_id"],
        "instructions": instructions, "inputs": sorted(inputs), "outputs": outputs,
        "reviewed_actor_id": original["actor_id"] if role == "reviewer" else None,
        "view": None, "depends_on": [], "attempt": 1, "supersedes_task_id": None}
    result = workflow.agents.advance({"schema_version": "2.0", "case_id": plan["case_id"],
        "question_dag": workflow._contract(plan["framing"]["problem_dag"], "problem_dag"), "tasks": [task]})
    return {**result, "request": relative, "action": "review-code-repair" if candidate_exists else "propose-code-repair",
            "scientific_acceptance": "NOT_RUN", "execution": "NOT_RUN"}
