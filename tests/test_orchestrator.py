from copy import deepcopy

import pytest

from test_runner import workspace
from test_validation import prepared
from test_agents import FixtureBackend
from mathmode.io import read_json, file_hash
from mathmode.orchestrator import Orchestrator, validate_schedule
from mathmode.state import StateStore


def schedule():
    return {"schema_version": "2.0", "case_id": "runner-fixture", "question_dag": None,
        "tasks": [{"task_id": "council-scheduled", "actor_id": "council-actor", "role": "council", "question_id": "Q1",
            "instructions": "Do not execute unless the actual phase prerequisites are present.",
            "inputs": ["input_manifest.json", "framing/deterministic_data_audit.json"],
            "outputs": [{"path": "methods/proposal.json", "format": "json", "contract": "method_proposal"}],
            "reviewed_actor_id": None, "view": "statistics", "depends_on": [], "attempt": 1, "supersedes_task_id": None}]}


def test_prepare_keeps_originals_and_is_stable_on_resume(workspace):
    before = file_hash(workspace / "input_manifest.json")
    orchestrator = Orchestrator(workspace, None)
    first = orchestrator.prepare_inputs()
    digest = file_hash(workspace / "framing/deterministic_data_audit.json")
    second = orchestrator.prepare_inputs()
    assert first == second
    assert first["status"] == "PASS"
    assert file_hash(workspace / "input_manifest.json") == before
    assert file_hash(workspace / "framing/deterministic_data_audit.json") == digest
    assert StateStore(workspace).inspect_freshness()["status"] == "PASS"


def test_council_cannot_bypass_framing_with_a_valid_schedule(workspace):
    orchestrator = Orchestrator(workspace, FixtureBackend())
    orchestrator.prepare_inputs()
    plan = schedule()
    assert validate_schedule(plan) == ["council-scheduled"]
    result = orchestrator.advance(plan)
    assert result["status"] == "BLOCKED"
    assert "phase prerequisites" in result["blocked"]["council-scheduled"][0]
    assert result["executed"] == []
    assert not (workspace / "agent_runs").exists()


def test_schedule_rejects_cycles_and_cross_workspace(workspace):
    plan = schedule()
    second = deepcopy(plan["tasks"][0])
    second.update(task_id="second", depends_on=["council-scheduled"])
    plan["tasks"][0]["depends_on"] = ["second"]
    plan["tasks"].append(second)
    with pytest.raises(ValueError, match="cycle"):
        validate_schedule(plan)
    plan = schedule()
    plan["case_id"] = "another-case"
    with pytest.raises(ValueError, match="another workspace"):
        Orchestrator(workspace, None).advance(plan)


def test_human_gate_never_dispatches_model_decision(workspace):
    state = StateStore(workspace)
    state.update(lambda current: current.update(interaction_mode="human_gate"), expected_revision=state.load()["revision"])
    orchestrator = Orchestrator(workspace, FixtureBackend())
    orchestrator.prepare_inputs()
    plan = schedule()
    plan["tasks"][0].update(role="decision", view=None,
        outputs=[{"path": "decisions/choice.jsonl", "format": "jsonl", "contract": "method_decision"}])
    result = orchestrator.advance(plan)
    assert "WAITING_HUMAN" in result["blocked"]["council-scheduled"][0]
    assert result["executed"] == []


def test_cli_data_audit_and_new_command_discovery(workspace, capsys):
    from mathmode.__main__ import main
    assert main(["data-audit", "--workspace", str(workspace)]) == 0
    assert '"status": "PASS"' in capsys.readouterr().out


def test_validator_can_use_repaired_outputs_but_not_stale_history(prepared, monkeypatch):
    import sys
    from mathmode.runner import execute_model
    from mathmode.lineage import artifact_id
    root = prepared
    old = execute_model(root, "main_spec.json", role="main", interpreter=sys.executable)
    code = root / "code/regression.py"
    code.write_text(code.read_text(encoding="utf-8") + "\n# Reviewed implementation revision\n", encoding="utf-8")
    current = execute_model(root, "main_spec.json", role="main", interpreter=sys.executable)
    service = Orchestrator(root, None)
    spec = read_json(root / "main_spec.json")
    criteria_path = spec["validation_plan"]["criteria"]["path"]
    dag = {"schema_version": "2.0", "nodes": [{"question_id": "Q1", "depends_on": []}]}
    # Mock only framed role provenance; execution integrity and the whitelist are real.
    contracts = {"main_spec.json": ("model_spec", spec),
        criteria_path: ("validation_criteria", read_json(root / criteria_path)),
        "framing/dag.json": ("problem_dag", dag)}
    monkeypatch.setattr(service, "_kind", lambda path: contracts.get(path, (None, None)))
    service.registry.register("main_spec.json", producer=spec["actor_id"])
    paths = [*contracts, current["outputs"][0]["path"]]
    task = {"role": "validator", "interaction_mode": "autopilot", "question_id": "Q1",
        "reviewed_actor_id": spec["actor_id"],
        "inputs": [{"path": path, "artifact_id": artifact_id(path)} for path in paths]}
    service._guard({}, task, {"question_dag": dag})
    task["inputs"].append({"path": old["outputs"][0]["path"], "artifact_id": "stale-output"})
    with pytest.raises(ValueError, match="unapproved inputs"):
        service._guard({}, task, {"question_dag": dag})
