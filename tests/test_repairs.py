"""Real failing subprocesses with explicitly doubled diagnostic reasoning."""
import json

import pytest
from jsonschema import ValidationError

from test_runner import workspace, run
from test_agents import FixtureBackend
from mathmode import orchestrator
from mathmode.agents import verify_agent_result
from mathmode.contracts import validate
from mathmode.io import read_json, write_json, file_hash, now
from mathmode.lineage import artifact_id
from mathmode.repairs import diagnose_failure, validate_diagnosis, verify_diagnosis, latest_failure, evidence_paths
from mathmode.workflow import Workflow


def diagnosis(root, relative, actor):
    return {"schema_version": "2.0", "diagnosis_id": "fixture-diagnosis", "actor_id": actor,
        "question_id": "Q1", "failure_source": {"path": relative, "sha256": file_hash(root / relative)},
        "created_at": now(), "failure_class": "CODE_FAILURE", "cause_id": "fixture-explicit-exception",
        "rationale": "Explicit test judgment for a program containing only a raised RuntimeError; not actual scientific reasoning.",
        "evidence_refs": [artifact_id(relative)], "repair_steps": ["Replace the intentional fixture exception with the approved computation."]}


@pytest.fixture
def failure_case(workspace, monkeypatch):
    root = workspace
    (root / "code/compute.py").write_text("raise RuntimeError('diagnostic fixture')", encoding="utf-8")
    failed = run(root)
    relative = f"runs/{failed['run_id']}/run_manifest.json"
    dag_path = "framing/problem_dag.json"
    write_json(root / dag_path, {"schema_version": "2.0", "nodes": [{"question_id": "Q1", "depends_on": []}]})
    def response(value, directory):
        task = read_json(directory / "task.json")
        value["artifacts"] = [{"path": task["outputs"][0]["path"],
                               "content": json.dumps(diagnosis(root, relative, task["actor_id"]))}]
        value["evidence_refs"] = [artifact_id(relative)]
    service = Workflow(root, FixtureBackend(response))
    service.registry.register(dag_path, producer="fixture-framer")
    original_kind = orchestrator.Orchestrator._kind
    def fixture_kind(self, path):
        if path == dag_path:
            return "problem_dag", validate("problem_dag", read_json(self.root / path))
        return original_kind(self, path)
    monkeypatch.setattr(orchestrator.Orchestrator, "_kind", fixture_kind)
    # Only source DAG provenance and reasoning provenance are doubled. Complete
    # input transport, hashes, publication, permissions and failed run are real.
    monkeypatch.setattr(orchestrator, "verify_agent_result",
                        lambda root, key: verify_agent_result(root, key, require_reasoning=False))
    plan = {"case_id": "runner-fixture", "framing": {"problem_dag": dag_path}}
    return root, service, plan, {"question_id": "Q1"}, failed, relative


def test_failed_subprocess_dispatches_once_and_routes_diagnosis(failure_case):
    root, service, plan, job, failed, relative = failure_case
    before = file_hash(root / relative)
    result = diagnose_failure(service, plan, job, relative)
    assert result["status"] == "PASS" and len(result["executed"]) == 1, result
    key = result["executed"][0]
    task = read_json(root / f"agent_runs/{key}/task.json")
    assert set(evidence_paths(failed)) <= {item["path"] for item in task["inputs"]}
    assert "code/compute.py" not in {item["path"] for item in task["inputs"]}
    assert task["reviewed_actor_id"] == failed["actor_id"] != task["actor_id"]
    again = diagnose_failure(service, plan, job, relative)
    assert again["status"] == "DIAGNOSED" and again["executed"] == []
    assert again["next_owner"] == "code" and again["retry_budget_remaining"] == 2
    assert again["failure_class"] == "CODE_FAILURE"
    assert file_hash(root / relative) == before
    assert len(list((root / "runs").iterdir())) == 1
    with pytest.raises(ValueError, match="actual backend session"):
        verify_agent_result(root, key)
    # Repairing canonical code does not erase the historical diagnosis.
    (root / "code/compute.py").write_text("print('changed')", encoding="utf-8")
    assert verify_diagnosis(root, result["diagnosis"])["cause_id"] == "fixture-explicit-exception"
    assert latest_failure(root, "model_spec.json", "main") == relative


def test_authored_diagnosis_cannot_replace_a_handoff(failure_case):
    root, service, plan, job, failed, relative = failure_case
    path = f"reviews/failure-diagnosis-{failed['run_id']}.json"
    write_json(root / path, diagnosis(root, relative, "fixture-independent"))
    with pytest.raises(ValueError, match="actual independent role handoff"):
        diagnose_failure(service, plan, job, relative)
    assert not (root / "agent_runs").exists()


def test_corrupted_failed_log_blocks_diagnosis(failure_case):
    root, service, plan, job, failed, relative = failure_case
    (root / failed["logs"]["stderr"]["path"]).write_text("rewritten", encoding="utf-8")
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        diagnose_failure(service, plan, job, relative)
    assert not (root / "agent_runs").exists()


@pytest.mark.parametrize("mutation,reason", [
    (lambda value, failed: value.update(actor_id=failed["actor_id"]), "independent actor"),
    (lambda value, failed: value.update(question_id="Q2"), "same question"),
    (lambda value, failed: value["failure_source"].update(sha256="0" * 64), "source hash"),
    (lambda value, failed: value.update(evidence_refs=["unrelated"]), "must cite"),
])
def test_diagnosis_rejects_false_attribution_and_pins(failure_case, mutation, reason):
    root, service, plan, job, failed, relative = failure_case
    value = diagnosis(root, relative, "fixture-independent")
    mutation(value, failed)
    with pytest.raises(ValueError, match=reason):
        validate_diagnosis(root, value)


def test_diagnosis_requires_complete_historical_input_bundle(failure_case):
    root, service, plan, job, failed, relative = failure_case
    value = diagnosis(root, relative, "fixture-independent")
    task = {"reviewed_actor_id": failed["actor_id"], "inputs": [
        {"path": relative, "sha256": file_hash(root / relative)}]}
    with pytest.raises(ValueError, match="complete verified execution bundle"):
        validate_diagnosis(root, value, task=task)


def test_workflow_failure_hook_returns_diagnosis_without_retrying(failure_case, monkeypatch):
    root, service, plan, job, failed, relative = failure_case
    monkeypatch.setattr(service, "observe", lambda plan: {"status": "BLOCKED"})
    result = service._failure(plan, job, "model_spec.json", "main")
    assert result["performed"]["action"] == "diagnose-failure", result
    from mathmode import code_repairs
    calls = []
    def capture(workflow, plan, job, diagnosis_path):
        calls.append(diagnosis_path)
        return {"status": "BLOCKED", "executed": [], "scope": "fixture-capture"}
    monkeypatch.setattr(code_repairs, "prepare_code_repair", capture)
    assert service._failure(plan, job, "model_spec.json", "main")["next_owner"] == "code-repair"
    assert len(calls) == 1
    assert len(list((root / "runs").iterdir())) == 1


def test_verify_diagnosis_cli_reports_only_diagnostic_scope(failure_case, capsys):
    from mathmode.__main__ import main
    root, service, plan, job, failed, relative = failure_case
    result = diagnose_failure(service, plan, job, relative)
    assert main(["verify-diagnosis", "--workspace", str(root), "--diagnosis", result["diagnosis"]]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["scope"] == "independent_failure_diagnosis"
    assert report["scientific_acceptance"] == "NOT_RUN"
    assert read_json(root / relative)["status"] == "FAIL"


def test_failed_diagnostic_proposal_is_preserved_without_resolicitation(failure_case):
    root, service, plan, job, failed, relative = failure_case
    original = service.agents.backend.mutate
    calls = []
    def corrupt(response, directory):
        calls.append(directory)
        original(response, directory)
        content = json.loads(response["artifacts"][0]["content"])
        content["failure_source"]["sha256"] = "0" * 64
        response["artifacts"][0]["content"] = json.dumps(content)
    service.agents.backend.mutate = corrupt
    first = diagnose_failure(service, plan, job, relative)
    assert first["status"] == "BLOCKED" and len(first["executed"]) == 1
    second = diagnose_failure(service, plan, job, relative)
    assert second["status"] == "BLOCKED" and not second["executed"]
    assert len(calls) == 1 and len(list((root / "agent_runs").iterdir())) == 1
    assert not (root / first["diagnosis"]).exists()
    # An explicit repaired diagnostic attempt may supersede the failed call,
    # preserving its record and the numerical run's separate attempt budget.
    previous = first["executed"][0]
    task = read_json(root / "agent_runs" / previous / "task.json")
    old_hash = file_hash(root / "agent_runs" / previous / "agent_result.json")
    blueprint = {key: value for key, value in task.items()
                 if key not in {"schema_version", "created_at", "interaction_mode", "inputs"}}
    blueprint.update(task_id=previous + "-retry", attempt=2, supersedes_task_id=previous,
                     inputs=[item["path"] for item in task["inputs"]], depends_on=[])
    service.agents.backend.mutate = original
    result = service.agents.advance({"schema_version": "2.0", "case_id": plan["case_id"],
        "question_dag": read_json(root / plan["framing"]["problem_dag"]), "tasks": [blueprint]})
    assert result["status"] == "PASS", result
    assert file_hash(root / "agent_runs" / previous / "agent_result.json") == old_hash
    assert diagnose_failure(service, plan, job, relative)["status"] == "DIAGNOSED"
    assert read_json(root / relative)["attempt"] == 1


def test_missing_backend_waits_without_inventing_diagnosis(failure_case):
    root, service, plan, job, failed, relative = failure_case
    service.agents.backend = None
    result = diagnose_failure(service, plan, job, relative)
    assert result["status"] == "BLOCKED" and not result["executed"]
    assert any("WAITING_AGENT" in reason for reasons in result["blocked"].values() for reason in reasons)
    assert not (root / result["diagnosis"]).exists()


def test_wrong_workflow_question_blocks_before_dispatch(failure_case):
    root, service, plan, job, failed, relative = failure_case
    with pytest.raises(ValueError, match="another workflow question"):
        diagnose_failure(service, plan, {"question_id": "Q2"}, relative)
    assert not (root / "agent_runs").exists()


def test_historical_snapshots_cannot_impersonate_current_role_contracts(failure_case):
    root, service, plan, job, failed, relative = failure_case
    assert service.agents._kind(failed["spec"]["snapshot_path"]) == (None, None)
    assert service.agents._kind(relative)[0] == "run_manifest"


def test_diagnosis_source_must_be_manifest_not_code(failure_case):
    root, service, plan, job, failed, relative = failure_case
    value = diagnosis(root, relative, "fixture-independent")
    value["failure_source"] = {"path": failed["code"][0]["snapshot_path"], "sha256": failed["code"][0]["sha256"]}
    with pytest.raises(ValidationError, match="does not match"):
        validate_diagnosis(root, value)
