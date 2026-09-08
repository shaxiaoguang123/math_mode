"""Screened decisions from a trusted interactive terminal, never model responses.

This is an application host boundary, not person authentication or OS isolation.
The agent subprocess has no path that submits a JSON 'human' decision to it.
"""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import stat
import sys
import uuid

from .contracts import read_ledger, validate, validate_events
from .io import canonical_bytes, canonical_root, file_hash, now, object_hash, read_json, safe_path, write_bytes, write_json
from .lineage import ArtifactRegistry, artifact_id, descendants
from .probes import screening_options, verify_screened_decision
from .state import StateStore


def task_signature(task):
    return object_hash({key: value for key, value in task.items() if key != "created_at"})


def _readonly_json(root, relative, value):
    path = safe_path(root, relative, exists=False)
    write_json(path, value, exclusive=True)
    path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    return {"path": relative, "sha256": file_hash(path)}


def _fresh(root, reference, *, producer=None, dependencies=None):
    store = StateStore(root)
    state, freshness = store.load(), store.inspect_freshness()
    entry = next((item for item in state["artifacts"] if item["path"] == reference["path"]), None)
    if (not entry or entry["artifact_id"] in freshness["stale"] or entry["sha256"] != reference["sha256"]
            or file_hash(safe_path(root, reference["path"])) != reference["sha256"]
            or (producer is not None and entry["producer"] != producer)):
        raise ValueError("Human decision has stale or unregistered host evidence")
    if dependencies is not None and {item["artifact_id"]: item["sha256"] for item in entry["depends_on"]} != dependencies:
        raise ValueError("Human decision lost a required evidence dependency")


def _check_task(root, task):
    from .agents import validate_task
    from .orchestrator import Orchestrator
    validate_task(dict(task, interaction_mode="autopilot"))  # Reuse role/output validation; never dispatch it.
    if task["role"] != "decision" or task["interaction_mode"] != "human_gate":
        raise ValueError("Human requests require a decision task in human_gate mode")
    if StateStore(root).load()["interaction_mode"] != "human_gate":
        raise ValueError("Human decisions require the workspace's explicit human_gate mode")
    if len(task["outputs"]) != 1 or task["outputs"][0]["format"] != "jsonl":
        raise ValueError("Human decisions require one append-only method_decision output")
    for item in task["inputs"]:
        _fresh(root, item)
    service = Orchestrator(root, None)
    service._guard({}, task, {"question_dag": None}, allow_human_request=True)
    kinds = [(item["path"], *service._kind(item["path"])) for item in task["inputs"]]
    card = next(path for path, kind, _ in kinds if kind == "method_card")
    probes = [path for path, kind, _ in kinds if kind == "risk_probe"]
    frames = [value for _, kind, value in kinds if kind == "problem_frame"]
    questions = [question for frame in frames for question in frame["questions"] if question["question_id"] == task["question_id"]]
    if len(frames) != 1 or len(questions) != 1:
        raise ValueError("Human decision needs one actual framed question in its input scope")
    screening = screening_options(root, card, probes)
    screening["question"] = questions[0]
    return card, probes, screening


def _display(task, screening, probes):
    return {"question_id": task["question_id"], "question": screening["question"], "instructions": task["instructions"],
        "methods": screening["card"]["methods"], "critic": screening["card"]["critic"],
        "measured_probes": probes, "eligible_choices": {role: item["method_id"] for role, item in screening["options"].items()},
        "input_files": [item["path"] for item in task["inputs"]],
        "decision_scope": "Method choice only; scientific validation and official acceptance remain separate."}


def prepare_request(root: Path, task: dict) -> dict:
    """Prepare reviewable evidence; no user decision or agent result is invented."""
    root = canonical_root(root)
    card, probes, screening = _check_task(root, task)
    signature = task_signature(task)
    request_id = "human-request-" + signature[:40]
    relative = f"human_requests/{request_id}/request.json"
    if safe_path(root, relative, exists=False).exists():
        return verify_request(root, request_id)[0]
    directory = safe_path(root, f"human_requests/{request_id}", exists=False)
    directory.mkdir(parents=True, exist_ok=False)
    task_ref = _readonly_json(root, f"human_requests/{request_id}/task.json", task)
    display = _display(task, screening, [read_json(safe_path(root, path)) for path in probes])
    display_ref = _readonly_json(root, f"human_requests/{request_id}/display.json", display)
    output = safe_path(root, task["outputs"][0]["path"], exists=False)
    if output.exists():
        read_ledger(output, "method_decision")
    request = {"schema_version": "2.0", "request_id": request_id, "case_id": StateStore(root).load()["case_id"],
        "question_id": task["question_id"], "created_at": now(), "task_signature": signature,
        "task": task_ref, "display": display_ref, "card_path": card, "probe_paths": probes,
        "decision_path": task["outputs"][0]["path"], "previous_ledger_sha256": file_hash(output) if output.exists() else None,
        "choices": [{"role": role, "method_id": item["method_id"]} for role, item in sorted(screening["options"].items())]}
    validate("human_decision_request", request, root=root)
    _readonly_json(root, relative, request)
    registry = ArtifactRegistry(root)
    with registry.batch():
        controls = [registry.register(item["path"], producer="human-decision-host") for item in (task_ref, display_ref)]
        registry.register(relative, producer="human-decision-host", dependencies=controls + [item["artifact_id"] for item in task["inputs"]])
    verify_request(root, request_id)
    return request


def verify_request(root: Path, request_id: str):
    root = canonical_root(root)
    relative = f"human_requests/{request_id}/request.json"
    request = validate("human_decision_request", read_json(safe_path(root, relative)), root=root)
    if request["request_id"] != request_id or request["case_id"] != StateStore(root).load()["case_id"]:
        raise ValueError("Human request belongs to another case or ID")
    task = validate("agent_task", read_json(safe_path(root, request["task"]["path"])), root=root)
    for item, name in ((request["task"], "task.json"), (request["display"], "display.json")):
        if item["path"] != f"human_requests/{request_id}/{name}":
            raise ValueError("Human request control is misplaced")
        _fresh(root, item, producer="human-decision-host")
    dependencies = {artifact_id(item["path"]): item["sha256"] for item in [request["task"], request["display"], *task["inputs"]]}
    _fresh(root, {"path": relative, "sha256": file_hash(safe_path(root, relative))},
           producer="human-decision-host", dependencies=dependencies)
    card, probes, screening = _check_task(root, task)
    if (task_signature(task) != request["task_signature"] or task["question_id"] != request["question_id"]
            or task["outputs"][0]["path"] != request["decision_path"] or (card, probes) != (request["card_path"], request["probe_paths"])):
        raise ValueError("Human request changed its screened task")
    choices = [{"role": role, "method_id": item["method_id"]} for role, item in sorted(screening["options"].items())]
    if request["choices"] != choices or read_json(safe_path(root, request["display"]["path"])) != _display(
            task, screening, [read_json(safe_path(root, path)) for path in probes]):
        raise ValueError("Human request display differs from current measured evidence")
    return request, task, screening


def _event(root, event_id):
    relative = f"human_events/{event_id}.json"
    event = validate("human_decision_event", read_json(safe_path(root, relative)), root=root)
    if event["event_id"] != event_id:
        raise ValueError("Human event identity differs")
    _fresh(root, {"path": relative, "sha256": file_hash(safe_path(root, relative))}, producer="human-decision-host",
           dependencies={artifact_id(event["request"]["path"]): event["request"]["sha256"]})
    request_raw = read_json(safe_path(root, event["request"]["path"]))
    request, task, screening = verify_request(root, request_raw["request_id"])
    if event["request"]["path"] != f"human_requests/{request['request_id']}/request.json":
        raise ValueError("Human event request is misplaced")
    if datetime.fromisoformat(event["received_at"]) < datetime.fromisoformat(request["created_at"]):
        raise ValueError("Human event predates the displayed request")
    return event, request, task, screening


def _decision(event, request, screening):
    if event["choice"] not in screening["options"]:
        raise ValueError("Human event does not choose an eligible screened method")
    decision = {"schema_version": "2.0", "decision_id": "decision-" + event["event_id"],
        "question_id": request["question_id"], "main_method_id": screening["options"][event["choice"]]["method_id"],
        "baseline_method_id": next(item["method_id"] for item in screening["card"]["methods"] if item["role"] == "usable_baseline"),
        "rationale": event["rationale"], "evidence_refs": sorted({artifact_id(path) for path in
            [request["card_path"], *request["probe_paths"], event["request"]["path"], f"human_events/{event['event_id']}.json"]}),
        "decided_by": "human", "actor_id": event["actor_id"], "decided_at": event["received_at"],
        "human_event_id": event["event_id"], "execution_role": event["choice"]}
    verify_screened_decision(decision, screening, request["probe_paths"])
    return decision


def verify_human_decision(root: Path, relative: str, *, task=None) -> dict:
    root = canonical_root(root)
    decisions = read_ledger(safe_path(root, relative), "method_decision")
    if not decisions or decisions[-1]["decided_by"] != "human":
        raise ValueError("Missing actual human decision event")
    decision = decisions[-1]
    event, request, recorded_task, screening = _event(root, decision["human_event_id"])
    if request["decision_path"] != relative or decision != _decision(event, request, screening):
        raise ValueError("Human decision differs from the actual received event")
    if task is not None and task_signature(task) != task_signature(recorded_task):
        raise ValueError("Human decision belongs to a different scheduled task or input scope")
    suffix = canonical_bytes(decision)
    content = safe_path(root, relative).read_bytes()
    prefix = content[:-len(suffix)]
    import hashlib
    previous_hash = hashlib.sha256(prefix).hexdigest() if prefix or request["previous_ledger_sha256"] is not None else None
    matches_history = previous_hash == request["previous_ledger_sha256"]
    # A legacy final line may lack its separator. Adding one preserves every old
    # byte and its recorded hash; it must not concatenate two JSON objects.
    if prefix.endswith(b"\n") and request["previous_ledger_sha256"] is not None:
        matches_history |= hashlib.sha256(prefix[:-1]).hexdigest() == request["previous_ledger_sha256"]
    if not content.endswith(suffix) or not matches_history:
        raise ValueError("Human decision changed its prior append-only history")
    required = [event["request"]["path"], f"human_events/{event['event_id']}.json"]
    _fresh(root, {"path": relative, "sha256": file_hash(safe_path(root, relative))}, producer=event["actor_id"],
           dependencies={artifact_id(path): file_hash(safe_path(root, path)) for path in required})
    return decision


def _publish(root, event_id):
    event, request, _, screening = _event(root, event_id)
    decision = _decision(event, request, screening)
    store = StateStore(root)
    state = store.load()
    relative = request["decision_path"]
    output = safe_path(root, relative, exists=False)
    current = read_ledger(output, "method_decision") if output.exists() else []
    already_appended = bool(current and current[-1] == decision)
    if not already_appended:
        if (file_hash(output) if output.exists() else None) != request["previous_ledger_sha256"]:
            raise ValueError("Decision history changed while waiting; prepare a new task")
        validate_events([*current, decision], "method_decision")
        prefix = output.read_bytes() if output.exists() else b""
        def publish(current_state):
            # Recheck while holding the writer lock, after the human's wait.
            _event(root, event_id)
            affected = descendants(current_state["artifacts"], {artifact_id(relative)})
            index_path = safe_path(root, "frozen_numbers.json", exists=False)
            active = set()
            if index_path.exists():
                index = validate("freeze_index", read_json(index_path), root=root)
                active = {artifact_id(item["path"]) for item in index["questions"].values() if item["status"] == "FROZEN"}
            if affected & active or any(item["artifact_id"] in affected and item["status"] == "FROZEN" for item in current_state["artifacts"]):
                raise ValueError("Thaw frozen consumers before changing the human decision")
            if (file_hash(output) if output.exists() else None) != request["previous_ledger_sha256"]:
                raise ValueError("Decision history changed during publication")
            separator = b"\n" if prefix and not prefix.endswith(b"\n") else b""
            write_bytes(output, prefix + separator + canonical_bytes(decision))
        store.update(publish, expected_revision=state["revision"])
    ArtifactRegistry(root).register(relative, producer=event["actor_id"],
        dependencies=[artifact_id(event["request"]["path"]), artifact_id(f"human_events/{event_id}.json")])
    return verify_human_decision(root, relative)


def decision_matches_task(root: Path, relative: str, task: dict) -> bool:
    """A new explicit task may request reconsideration; an old task cannot change scope."""
    root = canonical_root(root)
    decision = read_ledger(safe_path(root, relative), "method_decision")[-1]
    registered = {item["path"]: item for item in StateStore(root).load()["artifacts"]}
    def history(path, expected=None, producer="human-decision-host"):
        entry = registered.get(path)
        if (not entry or entry["producer"] != producer or entry["sha256"] != file_hash(safe_path(root, path))
                or (expected is not None and entry["sha256"] != expected)):
            raise ValueError("Previous human decision history was changed or unregistered")
        return read_json(safe_path(root, path))
    history_path = f"human_events/{decision['human_event_id']}.json"
    event = validate("human_decision_event", history(history_path), root=root)
    request = validate("human_decision_request", history(event["request"]["path"], event["request"]["sha256"]), root=root)
    history(request["task"]["path"], request["task"]["sha256"])
    recorded = read_json(safe_path(root, request["task"]["path"]))
    if recorded["task_id"] != task["task_id"]:
        # Old input dependencies may legitimately be stale. Their immutable bytes
        # must still exist, but a new task will obtain a new independently checked
        # request and a new terminal response instead of adopting the old choice.
        ledger = registered.get(relative)
        if not ledger or ledger["producer"] != event["actor_id"] or ledger["sha256"] != file_hash(safe_path(root, relative)):
            raise ValueError("Previous human decision ledger was changed or unregistered")
        return False
    verify_human_decision(root, relative)
    if task_signature(task) != task_signature(recorded):
        raise ValueError("Human decision belongs to a different scheduled task or input scope")
    return True


def receive_terminal_decision(root: Path, request_id: str, *, actor_id: str) -> dict:
    """Display the concrete choice, read the terminal, then recheck before publication.

    No CLI argument, model response, file upload or piped stdin supplies the choice.
    Tests replace terminal streams explicitly and do not claim a live human session.
    """
    root = canonical_root(root)
    request, _, _ = verify_request(root, request_id)
    reference = {"path": f"human_requests/{request_id}/request.json",
                 "sha256": file_hash(safe_path(root, f"human_requests/{request_id}/request.json"))}
    output = safe_path(root, request["decision_path"], exists=False)
    if output.exists():
        ledger = read_ledger(output, "method_decision")
        if ledger and ledger[-1]["decided_by"] == "human":
            current_id = ledger[-1]["human_event_id"]
            current_event = read_json(safe_path(root, f"human_events/{current_id}.json"))
            if current_event["request"] == reference:
                return {"status": "PASS", "scope": "human_decision_admission", "decision": _publish(root, current_id)}
    # A completed choice resumes without asking again. Interrupted unregistered
    # host observations remain diagnostic; they are never converted into a choice.
    events_dir = safe_path(root, "human_events", exists=False)
    pending = []
    for path in sorted(events_dir.glob("*.json")) if events_dir.exists() else []:
        prior = validate("human_decision_event", read_json(path), root=root)
        if prior["request"] == reference and prior["choice"] != "defer":
            pending.append(prior["event_id"])
    if len(pending) > 1:
        raise ValueError("Multiple pending terminal responses require explicit host reconciliation")
    if pending:
        return {"status": "PASS", "scope": "human_decision_admission", "decision": _publish(root, pending[0])}
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError("Human decision requires an interactive input/output terminal; piped/model input is not admitted")
    print(json.dumps(read_json(safe_path(root, request["display"]["path"])), ensure_ascii=False, indent=2))
    print("Choose one eligible role, or defer. A method choice does not approve scientific results.")
    choice = input("Choice: ").strip()
    if choice not in {item["role"] for item in request["choices"]} | {"defer"}:
        raise ValueError("No eligible choice was received")
    rationale = input("Reason: ").strip()
    if not rationale:
        raise ValueError("An actual decision rationale is required")
    if input("Type SUBMIT to record this response: ").strip() != "SUBMIT":
        return {"status": "BLOCKED", "scope": "human_decision_admission", "reason": "Response was not submitted"}
    event_id = "human-" + uuid.uuid4().hex
    event = {"schema_version": "2.0", "event_id": event_id, "request": reference, "actor_id": actor_id,
        "received_at": now(), "choice": choice, "rationale": rationale, "source": "terminal_stdin",
        "input_tty": True, "output_tty": True, "confirmation": "SUBMIT",
        "identity_scope": "host_terminal_not_person_authentication"}
    validate("human_decision_event", event, root=root)
    _readonly_json(root, f"human_events/{event_id}.json", event)
    verify_request(root, request_id)  # A changed model/probe while waiting cannot gain approval.
    ArtifactRegistry(root).register(f"human_events/{event_id}.json", producer="human-decision-host",
                                   dependencies=[artifact_id(reference["path"])])
    if choice == "defer":
        return {"status": "BLOCKED", "scope": "human_decision_admission", "event_id": event_id,
                "reason": "User deferred; no method decision published"}
    return {"status": "PASS", "scope": "human_decision_admission", "decision": _publish(root, event_id)}
