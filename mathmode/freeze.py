"""Immutable numerical snapshots, explicit thaw and fresh evidence lineage."""
from __future__ import annotations

from datetime import datetime
import math
from pathlib import Path
import stat
import uuid
from contextvars import ContextVar

from .contracts import validate, unique
from .io import canonical_bytes, canonical_root, file_hash, loads, now, object_hash, read_json, safe_path, write_json
from .lineage import ArtifactRegistry, artifact_id, descendants, mark_stale
from .runner import verify_run
from .state import StateStore
from .validation import audit_evidence, upstream_input_id

_VERIFY_STACK = ContextVar("mathmode_freeze_verification", default=())


def json_pointer(value, pointer: str):
    if not pointer.startswith("/"):
        raise ValueError("Frozen values require an explicit JSON Pointer")
    for token in pointer.split("/")[1:]:
        if "~" in token.replace("~0", "").replace("~1", ""):
            raise ValueError("Invalid JSON Pointer escape")
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not token.isdigit() or str(int(token)) != token:
                raise ValueError("Array locator must be a canonical nonnegative index")
            try:
                value = value[int(token)]
            except IndexError as exc:
                raise ValueError("Frozen locator is outside the source array") from exc
        elif isinstance(value, dict) and token in value:
            value = value[token]
        else:
            raise ValueError("Frozen locator does not resolve")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Frozen locator must resolve to a finite numerical value")
    return value


def freeze_events(root: Path) -> list[dict]:
    path = safe_path(root, "freeze_change_log.jsonl", exists=False)
    events = []
    if path.exists():
        previous = None
        states = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            event = validate("freeze_event", loads(line), root=root)
            if event["previous_event_sha256"] != previous:
                raise ValueError("Freeze event hash chain was rewritten")
            if event["kind"] == "FREEZE" and event["freeze_id"] in states:
                raise ValueError("Freeze ID cannot be reused")
            if event["kind"] == "THAW" and states.get(event["freeze_id"]) != "FREEZE":
                raise ValueError("THAW must follow an active freeze")
            states[event["freeze_id"]] = event["kind"]
            previous = object_hash(event)
            events.append(event)
        unique(events, "event_id")
    return events


def _index(root):
    path = safe_path(root, "frozen_numbers.json", exists=False)
    return validate("freeze_index", read_json(path), root=root) if path.exists() else {"schema_version": "2.0", "questions": {}}


def _append_event(root, event):
    import os
    with (root / "freeze_change_log.jsonl").open("ab") as handle:
        handle.write(canonical_bytes(event))
        handle.flush()
        os.fsync(handle.fileno())


def _register_run(registry, root, base, record, aliases=None):
    aliases = aliases or {}
    local = lambda relative: (base / relative).relative_to(root).as_posix()
    dependencies = []
    for item in [record["spec"], *record["inputs"], *record["code"], *record.get("contract_snapshots", []), *record.get("upstream_freezes", [])]:
        source = local(item["source_path"])
        source_id = registry.register(source, producer="runner", dependencies=aliases.get(source))
        dependencies.append(source_id)
        dependencies.append(registry.register(local(item["snapshot_path"]), producer="runner", dependencies=[source_id]))
    dependencies.append(registry.register(local("input_manifest.json"), producer="preflight"))
    for item in [*record["logs"].values(), *record["control_files"]]:
        dependencies.append(registry.register(local(item["path"]), producer="runner"))
    run_path = local(f"runs/{record['run_id']}/run_manifest.json")
    run_id = registry.register(run_path, producer="runner", dependencies=dependencies)
    outputs = {item["path"]: registry.register(local(item["path"]), producer="runner", dependencies=[run_id]) for item in record["outputs"]}
    return run_id, outputs


def _bind_evidence(registry, root, summary_relative, evidence_relative):
    with registry.batch():
        return _bind_evidence_records(registry, root, summary_relative, evidence_relative)


def _bind_evidence_records(registry, root, summary_relative, evidence_relative):
    summary = read_json(root / summary_relative)
    main = verify_run(root, summary["main_run"]["path"])
    baseline = verify_run(root, summary["baseline_run"]["path"])
    main_id, main_outputs = _register_run(registry, root, root, main)
    baseline_id, baseline_outputs = _register_run(registry, root, root, baseline)
    child = safe_path(root, summary["validator_workspace"], exists=False)
    child_record = verify_run(child, safe_path(root, summary["validator_run"]["path"]).relative_to(child).as_posix())
    criteria = read_json(root / summary["criteria"]["path"])
    original = unique(main["inputs"], "input_id")
    by_name = lambda record: unique(record["outputs"], "name")
    source_ids = {"raw-data": artifact_id(original[criteria["data_input_id"]]["source_path"]),
        "main-result": main_outputs[by_name(main)[criteria["main_output_name"]]["path"]],
        "baseline-result": baseline_outputs[by_name(baseline)[criteria["baseline_output_name"]]["path"]],
        "solver-spec": artifact_id(main["spec"]["source_path"]),
        "validation-criteria": artifact_id(summary["criteria"]["path"])}
    source_ids.update({upstream_input_id(item["question_id"]): artifact_id(item["source_path"])
                       for item in main.get("upstream_freezes", [])})
    aliases = {(child / item["source_path"]).relative_to(root).as_posix(): [source_ids[item["input_id"]]]
               for item in child_record["inputs"] if item["input_id"] in source_ids}
    aliases[(child / child_record["spec"]["source_path"]).relative_to(root).as_posix()] = [artifact_id(main["spec"]["source_path"])]
    validator_id, validator_outputs = _register_run(registry, root, child, child_record, aliases)
    summary_id = registry.register(summary_relative, producer="independent-validator",
        dependencies=[main_id, baseline_id, validator_id, *main_outputs.values(), *baseline_outputs.values(), *validator_outputs.values()])
    evidence_id = registry.register(evidence_relative, producer="evidence-auditor", dependencies=[summary_id])
    return summary, main, evidence_id, summary_id


def freeze_results(root: Path, request: dict, evidence_relative: str) -> dict:
    root = canonical_root(root)
    validate("freeze_request", request, root=root)
    unique(request["numbers"], "frozen_number_id")
    evidence = validate("evidence_gate", read_json(safe_path(root, evidence_relative)), root=root)
    if evidence["question_id"] != request["question_id"]:
        raise ValueError("Freeze evidence belongs to another question")
    summary_relative = evidence["validation"]["path"]
    if evidence["status"] != "PASS" or file_hash(safe_path(root, summary_relative)) != evidence["validation"]["sha256"]:
        raise ValueError("Freeze requires current passing evidence")
    fresh = audit_evidence(root, summary_relative)
    if fresh["status"] != "PASS":
        raise ValueError("Freeze evidence is stale or failed: " + "; ".join(fresh["blockers"]))
    index = _index(root)
    prior = index["questions"].get(request["question_id"])
    if prior and prior["status"] == "FROZEN":
        raise ValueError("Thaw the active question snapshot before refreezing")
    registry = ArtifactRegistry(root)
    summary = read_json(root / summary_relative)
    main = verify_run(root, summary["main_run"]["path"])
    spec = read_json(root / main["spec"]["snapshot_path"])
    if (request["question_id"], request["decision_id"]) != (summary["question_id"], spec["decision_id"]):
        raise ValueError("Freeze request changed question/decision identity")
    if prior:
        old = read_json(root / prior["path"])
        if summary["main_run"] == old["main_run"] or summary["baseline_run"] == old["baseline_run"] or summary_relative == old["validation"]["path"]:
            raise ValueError("Refreeze requires new main/baseline runs and independent validation")
        thaw = next(event for event in reversed(freeze_events(root)) if event["freeze_id"] == prior["freeze_id"] and event["kind"] == "THAW")
        for reference in (summary["main_run"], summary["baseline_run"]):
            if datetime.fromisoformat(read_json(root / reference["path"])["started_at"]) <= datetime.fromisoformat(thaw["timestamp"]):
                raise ValueError("Refreeze runs must occur after the explicit thaw")
    criteria = read_json(root / summary["criteria"]["path"])
    units = {check["metric"]: check["unit"] for check in criteria["checks"]}
    output_specs = unique(spec["outputs"], "name")
    source_specs = {item["path"]: output_specs[item["name"]] for item in main["outputs"]}
    numbers = []
    for item in request["numbers"]:
        source = safe_path(root, item["source_path"])
        value = json_pointer(read_json(source), item["locator"])
        if item["source_path"] == summary_relative:
            parts = item["locator"].split("/")
            if len(parts) != 3 or parts[1] != "measurements" or parts[2] not in units or item["unit"] != units[parts[2]]:
                raise ValueError("Freeze metric must bind a checked measurement and its declared unit")
        elif item["source_path"] in source_specs:
            output = source_specs[item["source_path"]]
            field = item["locator"].split("/")[-1].replace("~1", "/").replace("~0", "~")
            declarations = {f["name"]: f for f in output["fields"]}
            if field not in declarations or item["unit"] != declarations[field]["unit"] or item["precision"] > output["precision"]:
                raise ValueError("Frozen output unit/precision differs from declared output field")
        else:
            raise ValueError("Frozen numbers must come from verified main outputs or checked measurements")
        numbers.append({**item, "source_sha256": file_hash(source), "value": value})
    _, _, evidence_id, summary_id = _bind_evidence(registry, root, summary_relative, evidence_relative)
    from .dispositions import derive_qualifications
    baseline = verify_run(root, summary["baseline_run"]["path"])
    qualifications, qualification_dependencies = derive_qualifications(root, request["question_id"],
        request.get("qualification_sources", []), [main, baseline])
    from .assessments import bind_assessment_reports
    model_pins = {role: {"path": run["spec"]["source_path"], "sha256": run["spec"]["source_sha256"]}
                  for role, run in (("main", main), ("baseline", baseline))}
    assumption_dependencies = bind_assessment_reports(root, request.get("assumption_reports", []), request["question_id"], model_pins=model_pins)
    freeze_id = "freeze-" + uuid.uuid4().hex
    relative = f"freezes/{freeze_id}/frozen_numbers.json"
    key = artifact_id(relative)
    snapshot = {"schema_version": "2.0", "freeze_id": freeze_id, "version": prior["version"] + 1 if prior else 1,
        "question_id": request["question_id"], "decision_id": request["decision_id"], "actor_id": request["actor_id"],
        "created_at": now(), "evidence": {"path": evidence_relative, "sha256": file_hash(root / evidence_relative)},
        "validation": {"path": summary_relative, "sha256": file_hash(root / summary_relative)},
        "main_run": summary["main_run"], "baseline_run": summary["baseline_run"], "numbers": numbers, "registry_artifact_id": key}
    if qualifications:
        snapshot["qualifications"] = qualifications
    if request.get("assumption_reports"):
        snapshot["assumption_reports"] = request["assumption_reports"]
    validate("frozen_numbers", snapshot, root=root)
    state = registry.store.load()
    def publish(state):
        current = _index(root)
        if current != index:
            raise ValueError("Concurrent freeze changed the question index")
        if audit_evidence(root, summary_relative)["status"] != "PASS":
            raise ValueError("Evidence changed before freeze publication")
        current_qualifications, current_dependencies = derive_qualifications(root, request["question_id"],
            request.get("qualification_sources", []), [main, baseline])
        if current_qualifications != qualifications or current_dependencies != qualification_dependencies:
            raise ValueError("Reviewed qualifications changed before freeze publication")
        if bind_assessment_reports(root, request.get("assumption_reports", []), request["question_id"], model_pins=model_pins) != assumption_dependencies:
            raise ValueError("Assumption evidence changed before freeze publication")
        if {evidence_id, summary_id, *qualification_dependencies} & set(registry.store.inspect_freshness()["stale"]):
            raise ValueError("Registered evidence changed before freeze publication")
        for item in numbers:
            if file_hash(root / item["source_path"]) != item["source_sha256"]:
                raise ValueError("Frozen numerical source changed before publication")
        active_ids = set()
        for qid, pointer in current["questions"].items():
            if qid != request["question_id"] and pointer["status"] == "FROZEN":
                active_ids.update(item["frozen_number_id"] for item in read_json(root / pointer["path"])["numbers"])
        if active_ids & {item["frozen_number_id"] for item in numbers}:
            raise ValueError("Frozen number IDs must be unique across active questions")
        path = safe_path(root, relative, exists=False)
        write_json(path, snapshot, exclusive=True)
        path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        digest = file_hash(path)
        events = freeze_events(root)
        event = {"schema_version": "2.0", "event_id": "event-" + uuid.uuid4().hex, "freeze_id": freeze_id,
            "kind": "FREEZE", "actor_id": request["actor_id"], "timestamp": now(), "reason": "Computed evidence and numerical locators verified",
            "snapshot_path": relative, "snapshot_sha256": digest, "previous_event_sha256": object_hash(events[-1]) if events else None}
        _append_event(root, event)
        current["questions"][request["question_id"]] = {"freeze_id": freeze_id, "path": relative, "sha256": digest,
            "version": snapshot["version"], "status": "FROZEN"}
        write_json(root / "frozen_numbers.json", current)
        by_id = {a["artifact_id"]: a for a in state["artifacts"]}
        state["artifacts"].append({"artifact_id": key, "path": relative, "sha256": digest,
            "size_bytes": path.stat().st_size, "created_at": now(), "producer": "freeze-service", "status": "FROZEN",
            "depends_on": [{"artifact_id": dep, "sha256": by_id[dep]["sha256"]}
                           for dep in sorted({evidence_id, summary_id, *qualification_dependencies, *assumption_dependencies})]})
    registry.store.update(publish, expected_revision=state["revision"])
    return snapshot


def thaw(root: Path, question_id: str, *, actor_id: str, reason: str) -> dict:
    root = canonical_root(root)
    if not reason.strip():
        raise ValueError("Thaw requires an explicit reason")
    store = StateStore(root)
    state = store.load()
    outcome = {}
    def change(state):
        index = _index(root)
        pointer = index["questions"].get(question_id)
        if not pointer or pointer["status"] != "FROZEN":
            raise ValueError("Question has no active freeze to thaw")
        if file_hash(safe_path(root, pointer["path"])) != pointer["sha256"]:
            raise ValueError("Frozen snapshot was altered; preserve it for diagnosis")
        snapshot = read_json(root / pointer["path"])
        events = freeze_events(root)
        event = {"schema_version": "2.0", "event_id": "event-" + uuid.uuid4().hex, "freeze_id": pointer["freeze_id"],
            "kind": "THAW", "actor_id": actor_id, "timestamp": now(), "reason": reason,
            "snapshot_path": pointer["path"], "snapshot_sha256": pointer["sha256"],
            "previous_event_sha256": object_hash(events[-1]) if events else None}
        validate("freeze_event", event, root=root)
        _append_event(root, event)
        pointer["status"] = "THAWED"
        write_json(root / "frozen_numbers.json", index)
        affected = descendants(state["artifacts"], {snapshot["registry_artifact_id"]})
        mark_stale(state, affected, "Frozen result explicitly thawed: " + reason)
        outcome.update(status="THAWED", freeze_id=pointer["freeze_id"], affected=sorted(affected))
    store.update(change, expected_revision=state["revision"])
    return outcome


def verify_freeze(root: Path, question_id: str, *, refresh=True) -> dict:
    key = (str(canonical_root(root)), question_id)
    stack = _VERIFY_STACK.get()
    if key in stack:
        raise ValueError("Cyclic upstream freeze dependency")
    token = _VERIFY_STACK.set((*stack, key))
    try:
        return _verify_freeze(root, question_id, refresh=refresh)
    finally:
        _VERIFY_STACK.reset(token)


def _verify_freeze(root: Path, question_id: str, *, refresh=True) -> dict:
    root = canonical_root(root)
    pointer = _index(root)["questions"].get(question_id)
    if not pointer or pointer["status"] != "FROZEN":
        raise ValueError("Question has no current active freeze")
    path = safe_path(root, pointer["path"])
    if file_hash(path) != pointer["sha256"]:
        raise ValueError("Immutable freeze snapshot hash mismatch")
    snapshot = validate("frozen_numbers", read_json(path), root=root)
    if (snapshot["question_id"], snapshot["freeze_id"], snapshot["version"]) != (question_id, pointer["freeze_id"], pointer["version"]):
        raise ValueError("Freeze index and snapshot identities disagree")
    events = [event for event in freeze_events(root) if event["freeze_id"] == pointer["freeze_id"]]
    if not events or events[-1]["kind"] != "FREEZE" or events[-1]["snapshot_sha256"] != pointer["sha256"]:
        raise ValueError("Freeze history does not authorize this snapshot")
    registry = ArtifactRegistry(root)
    observation = registry.refresh() if refresh else registry.store.inspect_freshness()
    state = registry.store.load()
    registered = {a["artifact_id"]: a for a in state["artifacts"]}
    key = snapshot["registry_artifact_id"]
    if key not in registered or registered[key]["status"] != "FROZEN" or key in observation["stale"]:
        raise ValueError("Frozen snapshot is stale in the evidence graph")
    if audit_evidence(root, snapshot["validation"]["path"])["status"] != "PASS":
        raise ValueError("Frozen evidence no longer passes independent audit")
    for reference in (snapshot["evidence"], snapshot["validation"], snapshot["main_run"], snapshot["baseline_run"]):
        if file_hash(safe_path(root, reference["path"])) != reference["sha256"]:
            raise ValueError("Freeze dependency hash mismatch")
    for item in snapshot["numbers"]:
        source = safe_path(root, item["source_path"])
        if file_hash(source) != item["source_sha256"] or json_pointer(read_json(source), item["locator"]) != item["value"]:
            raise ValueError("Frozen number differs from its source locator")
    from .dispositions import derive_qualifications
    model_runs = {role: verify_run(root, snapshot[role + "_run"]["path"]) for role in ("main", "baseline")}
    qualifications, dependencies = derive_qualifications(root, question_id,
        snapshot.get("qualifications", {}).get("sources", []), list(model_runs.values()))
    if snapshot.get("qualifications") != qualifications:
        raise ValueError("Frozen qualifications differ from reviewed or inherited restrictions")
    if not set(dependencies) <= {dep["artifact_id"] for dep in registered[key]["depends_on"]}:
        raise ValueError("Freeze lineage omits qualification dependencies")
    from .assessments import bind_assessment_reports
    model_pins = {role: {"path": run["spec"]["source_path"], "sha256": run["spec"]["source_sha256"]} for role, run in model_runs.items()}
    dependencies = bind_assessment_reports(root, snapshot.get("assumption_reports", []), question_id, model_pins=model_pins)
    if not set(dependencies) <= {dep["artifact_id"] for dep in registered[key]["depends_on"]}:
        raise ValueError("Freeze lineage omits assumption evidence")
    return snapshot
