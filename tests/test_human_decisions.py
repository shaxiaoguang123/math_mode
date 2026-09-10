"""Real numerical evidence and host code; terminal/framer authorship are explicit doubles."""
from copy import deepcopy
import io
import sys

import pytest
from jsonschema import ValidationError

from test_validation import prepared
from test_workflow import case, review, na_assumptions
from test_workflow_fallback import fallback_case
from mathmode.contracts import read_ledger
from mathmode.freeze import _register_run, verify_freeze
from mathmode.human_decisions import prepare_request, receive_terminal_decision, verify_human_decision, verify_request
from mathmode.io import file_hash, now, read_json, write_json
from mathmode.lineage import ArtifactRegistry, artifact_id
from mathmode.orchestrator import Orchestrator
from mathmode.runner import verify_run
from mathmode.state import StateStore


class TerminalDouble(io.StringIO):
    """In-memory terminal simulation, not evidence that a real person interacted."""
    def isatty(self):
        return True


def terminal(monkeypatch, text):
    input_stream, output_stream = TerminalDouble(text), TerminalDouble()
    monkeypatch.setattr(sys, "stdin", input_stream)
    monkeypatch.setattr(sys, "stdout", output_stream)
    return output_stream


def configure(root, plan, monkeypatch):
    store = StateStore(root)
    store.update(lambda value: value.update(interaction_mode="human_gate"), expected_revision=store.load()["revision"])
    registry = ArtifactRegistry(root)
    job = plan["questions"][0]
    paths = [job["method_card"], *job["probe_reports"], plan["framing"]["problem_frame"]]
    for path in paths:
        registry.register(path, producer="fixture-critic")
    for path in job["probe_reports"]:
        report = read_json(root / path)
        run = verify_run(root, f"runs/{report['run_id']}/run_manifest.json")
        with registry.batch():
            run_id, _ = _register_run(registry, root, root, run)
            registry.register(path, producer="probe-service", dependencies=[run_id])
    original_kind = Orchestrator._kind
    def fixture_kind(self, path):
        if path == job["method_card"]:
            return "method_card", read_json(root / path)
        if path == plan["framing"]["problem_frame"]:
            return "problem_frame", read_json(root / path)
        return original_kind(self, path)
    monkeypatch.setattr(Orchestrator, "_kind", fixture_kind)
    blueprint = {"task_id": "human-choice", "actor_id": "scheduled-role", "role": "decision", "question_id": "Q1",
        "instructions": "Choose using the synthetic probe evidence. This test does not claim real human or scientific review.",
        "inputs": paths, "outputs": [{"path": job["decision"], "format": "jsonl", "contract": "method_decision"}],
        "reviewed_actor_id": None, "view": None, "depends_on": [], "attempt": 1, "supersedes_task_id": None}
    schedule = {"schema_version": "2.0", "case_id": store.load()["case_id"], "question_dag": None, "tasks": [blueprint]}
    scheduler = Orchestrator(root, None)
    result = scheduler.advance(schedule)
    assert result["executed"] == [] and result["completed"] == []
    assert "WAITING_HUMAN" in result["blocked"]["human-choice"][0], result
    request_id = result["human_requests"][0]["request_id"]
    assert scheduler.advance(schedule)["human_requests"][0]["request_id"] == request_id
    return job, scheduler, schedule, request_id


def test_terminal_event_resumes_schedule_and_binds_real_execution(case, monkeypatch):
    root, workflow, plan = case
    legacy = root / plan["questions"][0]["decision"]
    legacy.write_bytes(legacy.read_bytes().rstrip(b"\n"))
    job, scheduler, schedule, request_id = configure(root, plan, monkeypatch)
    write_json(root / "host_schedule.json", schedule)
    plan["agent_schedule"] = "host_schedule.json"
    assert workflow.advance(plan)["agent_schedule"]["human_requests"][0]["request_id"] == request_id
    previous = (root / job["decision"]).read_bytes()
    with monkeypatch.context() as streams:
        display = terminal(streams, "main\nMeasured six-category probe supports this fixture choice.\nSUBMIT\n")
        response = receive_terminal_decision(root, request_id, actor_id="fixture-terminal-user")
        assert "measured_probes" in display.getvalue()
    assert response["status"] == "PASS"
    decision = verify_human_decision(root, job["decision"])
    assert decision["decided_by"] == "human" and decision["actor_id"] == "fixture-terminal-user"
    assert (root / job["decision"]).read_bytes().startswith(previous)
    assert len(read_ledger(root / job["decision"], "method_decision")) == 2
    result = scheduler.advance(schedule)
    assert result["status"] == "PASS" and result["completed"] == ["human-choice"] and result["executed"] == []
    assert receive_terminal_decision(root, request_id, actor_id="unused-on-resume") == response
    assert not (root / "agent_runs/human-choice").exists() and not (root / "ai_usage.jsonl").exists()
    changed = deepcopy(schedule)
    changed["tasks"][0]["instructions"] = "Alter the already received request"
    assert "different scheduled task" in scheduler.advance(changed)["blocked"]["human-choice"][0]
    # Real production specs are tied to the actual host decision; only their role
    # authorship and later semantic-review content are test doubles.
    for path in (job["main_spec"], job["baseline_spec"]):
        spec = read_json(root / path)
        spec["decision_id"] = decision["decision_id"]
        write_json(root / path, spec)
        ArtifactRegistry(root).register(path, producer=spec["actor_id"], dependencies=[artifact_id(job["decision"])])
    na_assumptions(root, workflow, plan)
    for action in ("run-main", "run-baseline", "independent-validate"):
        result = workflow.advance(plan, interpreter=sys.executable)
        assert result["performed"]["action"] == action, result
    progress = read_json(root / "workflow_progress.json")["questions"]["Q1"]
    summary = read_json(root / progress["validation"])
    assert summary["measurements"]["main_mse"] == 0 and summary["measurements"]["baseline_mse"] == 26
    spec = read_json(root / job["main_spec"])
    review(root, job["validation_review"], spec["actor_id"], [job["main_spec"], job["baseline_spec"],
        progress["validation"], progress["evidence"], spec["validation_plan"]["criteria"]["path"]])
    assert workflow.advance(plan, interpreter=sys.executable)["performed"]["action"] == "freeze"
    frozen = verify_freeze(root, "Q1")
    # A new explicit host task may ask for reconsideration, but cannot overwrite
    # a decision that still has an active frozen numerical consumer.
    reconsider = deepcopy(schedule)
    reconsider["tasks"][0]["task_id"] = "human-reconsider"
    next_request = scheduler.advance(reconsider)["human_requests"][0]["request_id"]
    before_reconsider = file_hash(root / job["decision"])
    with monkeypatch.context() as streams:
        terminal(streams, "main\nRecord a deliberate new choice after reconsideration.\nSUBMIT\n")
        with pytest.raises(ValueError, match="Thaw"):
            receive_terminal_decision(root, next_request, actor_id="fixture-terminal-user")
    assert file_hash(root / job["decision"]) == before_reconsider
    event_path = root / f"human_events/{decision['human_event_id']}.json"
    event_path.chmod(0o600)
    event_path.write_text("{}", encoding="utf-8")
    assert frozen["registry_artifact_id"] in StateStore(root).inspect_freshness()["stale"]
    with pytest.raises((ValueError, ValidationError)):
        verify_human_decision(root, job["decision"])
    with pytest.raises(ValueError):
        verify_freeze(root, "Q1")


def test_pipes_defer_and_cancel_never_publish_a_method_choice(case, monkeypatch):
    root, _, plan = case
    job, scheduler, schedule, request_id = configure(root, plan, monkeypatch)
    before = file_hash(root / job["decision"])
    with monkeypatch.context() as streams:
        streams.setattr(sys, "stdin", io.StringIO("main\nPretend human\nSUBMIT\n"))
        streams.setattr(sys, "stdout", TerminalDouble())
        with pytest.raises(ValueError, match="interactive"):
            receive_terminal_decision(root, request_id, actor_id="fixture-terminal-user")
    assert not (root / "human_events").exists()
    with monkeypatch.context() as streams:
        terminal(streams, "main\nUnconfirmed response\nCANCEL\n")
        assert receive_terminal_decision(root, request_id, actor_id="fixture-terminal-user")["status"] == "BLOCKED"
    assert not (root / "human_events").exists()
    with monkeypatch.context() as streams:
        terminal(streams, "defer\nNeed to inspect the model assumptions.\nSUBMIT\n")
        result = receive_terminal_decision(root, request_id, actor_id="fixture-terminal-user")
    assert result["status"] == "BLOCKED" and len(list((root / "human_events").glob("*.json"))) == 1
    assert file_hash(root / job["decision"]) == before
    assert scheduler.advance(schedule)["completed"] == []


def test_changed_evidence_while_waiting_preserves_event_but_refuses_publication(case, monkeypatch):
    root, _, plan = case
    job, _, _, request_id = configure(root, plan, monkeypatch)
    before = file_hash(root / job["decision"])
    class ChangingTerminal(TerminalDouble):
        def readline(self, *args):
            value = super().readline(*args)
            if value.startswith("SUBMIT"):
                card = read_json(root / job["method_card"])
                card["critic"]["findings"].append("Changed while the terminal was awaiting a choice")
                write_json(root / job["method_card"], card)
            return value
    with monkeypatch.context() as streams:
        streams.setattr(sys, "stdin", ChangingTerminal("main\nSelect measured method.\nSUBMIT\n"))
        streams.setattr(sys, "stdout", TerminalDouble())
        with pytest.raises(ValueError, match="stale"):
            receive_terminal_decision(root, request_id, actor_id="fixture-terminal-user")
    assert file_hash(root / job["decision"]) == before
    assert len(list((root / "human_events").glob("*.json"))) == 1, "Keep the actual observed test response for diagnosis"


def test_human_can_only_choose_a_triggered_and_measured_fallback(fallback_case, monkeypatch):
    root, _, plan, _ = fallback_case
    job, scheduler, schedule, request_id = configure(root, plan, monkeypatch)
    request, _, _ = verify_request(root, request_id)
    assert [item["role"] for item in request["choices"]] == ["fallback"]
    before = file_hash(root / job["decision"])
    with monkeypatch.context() as streams:
        terminal(streams, "main\nOverride a failed probe\nSUBMIT\n")
        with pytest.raises(ValueError, match="eligible choice"):
            receive_terminal_decision(root, request_id, actor_id="fixture-terminal-user")
    assert file_hash(root / job["decision"]) == before
    with monkeypatch.context() as streams:
        terminal(streams, "fallback\nThe pinned trigger and the fallback probe support this choice.\nSUBMIT\n")
        result = receive_terminal_decision(root, request_id, actor_id="fixture-terminal-user")
    assert result["decision"]["execution_role"] == "fallback"
    assert scheduler.advance(schedule)["completed"] == ["human-choice"]
    forged = deepcopy(result["decision"])
    forged["rationale"] = "Rewrite the received rationale"
    write_json(root / job["decision"], forged)
    with pytest.raises(ValueError, match="actual received event"):
        verify_human_decision(root, job["decision"])


def test_interrupted_publication_reuses_observed_choice_without_another_prompt(case, monkeypatch):
    root, _, plan = case
    # An existing, empty JSONL initialization also has a real byte hash.
    (root / plan["questions"][0]["decision"]).write_text("", encoding="utf-8")
    job, _, _, request_id = configure(root, plan, monkeypatch)
    before = file_hash(root / job["decision"])
    def interrupted(*args):
        raise OSError("Synthetic interruption after the terminal event was recorded")
    with monkeypatch.context() as interruption:
        terminal(interruption, "main\nUse the measured option.\nSUBMIT\n")
        interruption.setattr("mathmode.human_decisions._publish", interrupted)
        with pytest.raises(OSError, match="Synthetic interruption"):
            receive_terminal_decision(root, request_id, actor_id="fixture-terminal-user")
    assert file_hash(root / job["decision"]) == before
    assert len(list((root / "human_events").glob("*.json"))) == 1
    result = receive_terminal_decision(root, request_id, actor_id="unused-on-resume")
    assert result["status"] == "PASS"
    assert result["decision"]["actor_id"] == "fixture-terminal-user"
    assert len(read_ledger(root / job["decision"], "method_decision")) == 1
    assert len(list((root / "human_events").glob("*.json"))) == 1


def test_new_task_requires_new_response_after_context_changes(case, monkeypatch):
    root, _, plan = case
    job, scheduler, schedule, request_id = configure(root, plan, monkeypatch)
    with monkeypatch.context() as streams:
        terminal(streams, "main\nChoose against the original fixture context.\nSUBMIT\n")
        first = receive_terminal_decision(root, request_id, actor_id="fixture-terminal-user")["decision"]
    path = plan["framing"]["problem_frame"]
    frame = read_json(root / path)
    frame["questions"][0]["title"] += " with revised framing context"
    write_json(root / path, frame)
    ArtifactRegistry(root).register(path, producer="fixture-framer")
    assert scheduler.advance(schedule)["completed"] == []
    schedule["tasks"][0]["task_id"] = "human-revised-context"
    result = scheduler.advance(schedule)
    assert result["completed"] == [] and result["executed"] == []
    next_request = result["human_requests"][0]["request_id"]
    assert next_request != request_id
    with monkeypatch.context() as streams:
        terminal(streams, "main\nChoose after reading the revised context.\nSUBMIT\n")
        second = receive_terminal_decision(root, next_request, actor_id="fixture-terminal-user")["decision"]
    assert second["human_event_id"] != first["human_event_id"]
    assert verify_human_decision(root, job["decision"]) == second
    assert len(read_ledger(root / job["decision"], "method_decision")) == 3
