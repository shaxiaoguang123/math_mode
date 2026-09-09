"""Real code transport/execution; model approvals and reasoning are test doubles."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

from test_runner import workspace
from test_repairs import failure_case
from test_agents import FixtureBackend
from mathmode import code_repairs
from mathmode.agents import run_agent_task, verify_agent_result
from mathmode.contracts import validate
from mathmode.io import read_json, write_json, file_hash, now
from mathmode.lineage import artifact_id
from mathmode.orchestrator import validate_schedule
from mathmode.repairs import diagnose_failure
from mathmode.runner import execute_model, verify_run


@pytest.fixture
def repair_case(failure_case, monkeypatch):
    root, service, plan, job, failed, relative = failure_case
    service.agents.prepare_inputs()
    diagnosis = diagnose_failure(service, plan, job, relative)["diagnosis"]
    service.registry.register("model_spec.json", producer=failed["actor_id"])
    job.update(method_card="methods/card.json", decision="decisions/fixture.jsonl", probe_reports=["probes/report.json"])
    # These prerequisites are explicitly authored phase doubles. The existing
    # orchestrator tests cover real phase guards; this fixture exercises the
    # repair protocol, publication, lineage and actual repaired subprocess.
    for path in (job["method_card"], job["decision"], *job["probe_reports"]):
        write_json(root / path, {"fixture": "phase input double"})
        service.registry.register(path, producer="fixture-phase")
    original_contract = code_repairs._contract
    def contract(root, path, kind):
        if path in {"model_spec.json", "baseline_spec.json"} and kind == "model_spec":
            return validate(kind, read_json(root / path))
        return original_contract(root, path, kind)
    monkeypatch.setattr(code_repairs, "_contract", contract)
    monkeypatch.setattr(code_repairs, "verify_agent_result", lambda root, key: verify_agent_result(root, key, require_reasoning=False))
    schedules = []
    mutations = {}
    def advance(schedule):
        validate_schedule(schedule)
        schedules.append(deepcopy(schedule))
        blueprint = schedule["tasks"][0]
        task = {key: value for key, value in blueprint.items() if key not in {"depends_on", "inputs"}}
        task.update(schema_version="2.0", created_at=now(), interaction_mode="autopilot", inputs=[
            {"artifact_id": artifact_id(path), "path": path, "sha256": file_hash(root / path)} for path in blueprint["inputs"]])
        def response(value, directory):
            request_path = next(path for path in blueprint["inputs"] if path.startswith("repairs/") and path.endswith("/request.json"))
            request = read_json(root / request_path)
            if task["role"] == "reviewer":
                proposed = {"schema_version": "2.0", "review_id": "fixture-code-review", "question_id": "Q1",
                    "actor_id": task["actor_id"], "reviewed_actor_id": task["reviewed_actor_id"],
                    "artifact_refs": [item["artifact_id"] for item in task["inputs"]], "findings": [],
                    "verdict": "SUPPORTED", "limitations": [], "created_at": now()}
                if mutations.get("review"):
                    mutations["review"](proposed)
                artifacts = [{"path": request["review"], "content": json.dumps(proposed)}]
            else:
                spec = read_json(root / "model_spec.json")
                mapping = {item["source"]: item["candidate"] for item in request["code"]}
                spec["implementation"].update(entrypoint=mapping[spec["implementation"]["entrypoint"]],
                    code_files=[mapping[path] for path in spec["implementation"]["code_files"]])
                if mutations.get("spec"):
                    mutations["spec"](spec)
                content = (Path(__file__).resolve().parents[1] / "fixtures/runner/compute.py").read_text(encoding="utf-8")
                if mutations.get("no_change"):
                    content = (root / request["code"][0]["snapshot"]["path"]).read_text(encoding="utf-8")
                artifacts = [{"path": request["candidate_spec"], "content": json.dumps(spec)},
                             *[{"path": item["candidate"], "content": content} for item in request["code"]]]
                if mutations.get("spec_only"):
                    for item in request["code"]:
                        path = root / item["candidate"]
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text(content, encoding="utf-8")
                    artifacts = artifacts[:1]
            value.update(artifacts=artifacts, evidence_refs=[artifact_id(request_path)])
        if mutations.get("spec_only") and task["role"] != "reviewer":
            task["outputs"] = task["outputs"][:1]
        if mutations.get("omit_diagnosis") and task["role"] != "reviewer":
            task["inputs"] = [item for item in task["inputs"] if item["path"] != diagnosis]
        result = run_agent_task(root, task, FixtureBackend(response))
        return {"status": "PASS" if result["status"] == "PRODUCED" else "BLOCKED", "executed": [task["task_id"]],
                "scope": "fixture-transport", "blockers": result["blockers"]}
    monkeypatch.setattr(service.agents, "advance", advance)
    return root, service, plan, job, failed, relative, diagnosis, schedules, mutations


def test_staged_repair_is_reviewed_then_runs_without_changing_failed_sources(repair_case):
    root, service, plan, job, failed, relative, diagnosis, schedules, mutations = repair_case
    before = {path: file_hash(root / path) for path in (relative, "model_spec.json", "code/compute.py")}
    first = code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    assert first["status"] == "PASS" and first["action"] == "propose-code-repair", first
    with pytest.raises((ValueError, OSError)):
        code_repairs.verify_code_repair(root, first["request"])
    second = code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    assert second["action"] == "review-code-repair" and second["status"] == "PASS", second
    reviewed = code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    assert reviewed["scope"] == "independently_reviewed_code_repair" and not reviewed["executed"]
    assert reviewed["execution"] == "NOT_RUN" and len(schedules) == 2
    assert schedules[0]["tasks"][0]["actor_id"] != schedules[1]["tasks"][0]["actor_id"]
    assert all(file_hash(root / path) == digest for path, digest in before.items())
    # Explicit engineering execution, not yet a workflow activation adapter.
    repaired = execute_model(root, reviewed["candidate_spec"], retry_of=reviewed["retry_of"], interpreter=sys.executable)
    assert repaired["status"] == "PASS" and repaired["attempt"] == 2
    assert read_json(root / repaired["outputs"][0]["path"])["sum"] == 12
    verify_run(root, f"runs/{repaired['run_id']}/run_manifest.json")
    assert all(file_hash(root / path) == digest for path, digest in before.items())


@pytest.mark.parametrize("mutate", [lambda spec: spec.update(seed=77),
    lambda spec: spec["limits"].update(timeout_seconds=99),
    lambda spec: spec["objective"].update(metric="different"),
    lambda spec: spec["data_split"].update(test_ids=["row4"])])
def test_code_repair_cannot_change_scientific_model_or_controls(repair_case, mutate):
    root, service, plan, job, failed, relative, diagnosis, schedules, mutations = repair_case
    mutations["spec"] = mutate
    first = code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    with pytest.raises(ValueError, match="semantics|actual current"):
        code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    assert len(schedules) == 1


def test_identical_code_is_not_a_repair(repair_case):
    root, service, plan, job, failed, relative, diagnosis, schedules, mutations = repair_case
    mutations["no_change"] = True
    code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    with pytest.raises(ValueError, match="no actual code change"):
        code_repairs.prepare_code_repair(service, plan, job, diagnosis)


def test_review_limitations_do_not_authorize_repair(repair_case):
    root, service, plan, job, failed, relative, diagnosis, schedules, mutations = repair_case
    code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    mutations["review"] = lambda review: review.update(verdict="LIMITED", limitations=["Fixture unresolved import"])
    code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    with pytest.raises(ValueError, match="unresolved findings"):
        code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    assert len(list((root / "runs").iterdir())) == 1


def test_request_cannot_redirect_candidate_to_original_source(repair_case):
    root, service, plan, job, failed, relative, diagnosis, schedules, mutations = repair_case
    first = code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    request = read_json(root / first["request"])
    request["code"][0]["candidate"] = request["code"][0]["source"]
    write_json(root / first["request"], request)
    with pytest.raises(ValueError, match="differs from the verified"):
        code_repairs.verify_request(root, first["request"])


def test_spec_handoff_cannot_smuggle_unpublished_candidate_code(repair_case):
    root, service, plan, job, failed, relative, diagnosis, schedules, mutations = repair_case
    mutations["spec_only"] = True
    first = code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    with pytest.raises(ValueError, match="complete candidate bundle"):
        code_repairs.verify_candidate(root, first["request"])


def test_changed_original_code_invalidates_repair_request(repair_case):
    root, service, plan, job, failed, relative, diagnosis, schedules, mutations = repair_case
    first = code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    (root / "code/compute.py").write_text("print('changed outside repair')", encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        code_repairs.verify_request(root, first["request"])


def test_cli_reports_review_scope_without_running_candidate(repair_case, capsys):
    from mathmode.__main__ import main
    root, service, plan, job, failed, relative, diagnosis, schedules, mutations = repair_case
    first = code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    assert main(["verify-code-repair", "--workspace", str(root), "--request", first["request"]]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["scope"] == "independently_reviewed_code_repair"
    assert report["scientific_acceptance"] == report["execution"] == "NOT_RUN"
    assert len(list((root / "runs").iterdir())) == 1


def test_repair_does_not_target_a_replaced_workflow_model(repair_case):
    root, service, plan, job, failed, relative, diagnosis, schedules, mutations = repair_case
    job["main_spec"] = "models/new-selection.json"
    with pytest.raises(ValueError, match="selected workflow model"):
        code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    assert schedules == []


def test_code_review_receives_the_selected_model_pair(repair_case):
    root, service, plan, job, failed, relative, diagnosis, schedules, mutations = repair_case
    job.update(main_spec="model_spec.json", baseline_spec="baseline_spec.json")
    baseline = read_json(root / "model_spec.json")
    baseline.update(actor_id="fixture-baseline-author", implementation={"language": "python",
        "entrypoint": "code/baseline.py", "code_files": ["code/baseline.py"]})
    write_json(root / "baseline_spec.json", baseline)
    (root / "code/baseline.py").write_text("# Baseline input-scope fixture only\n", encoding="utf-8")
    for path, actor in (("baseline_spec.json", "fixture-baseline-author"), ("code/baseline.py", "fixture-baseline-author"),
                        ("code/compute.py", failed["actor_id"])):
        service.registry.register(path, producer=actor)
    code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    assert {"model_spec.json", "baseline_spec.json", "code/compute.py", "code/baseline.py"} <= set(schedules[-1]["tasks"][0]["inputs"])


def test_candidate_producer_must_receive_actual_diagnosis(repair_case):
    root, service, plan, job, failed, relative, diagnosis, schedules, mutations = repair_case
    mutations["omit_diagnosis"] = True
    first = code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    with pytest.raises(ValueError, match="complete candidate bundle"):
        code_repairs.verify_candidate(root, first["request"])


def test_execute_reviewed_repair_rejects_unreviewed_request(repair_case):
    root, service, plan, job, failed, relative, diagnosis, schedules, mutations = repair_case
    first = code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    with pytest.raises((ValueError, OSError)):
        from mathmode.repair_execution import execute_reviewed_repair
        execute_reviewed_repair(root, first["request"], interpreter=sys.executable)
    assert len(list((root / "runs").iterdir())) == 1


def test_authorized_repair_runs_once_and_cannot_be_relabeled(repair_case):
    from mathmode.repair_execution import execute_reviewed_repair
    root, service, plan, job, failed, relative, diagnosis, schedules, mutations = repair_case
    first = code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    run = execute_reviewed_repair(root, first["request"], interpreter=sys.executable)
    assert run["status"] == "PASS" and run["attempt"] == 2
    assert read_json(root / run["outputs"][0]["path"])["sum"] == 12
    assert execute_reviewed_repair(root, first["request"], interpreter=sys.executable)["run_id"] == run["run_id"]
    assert len(list((root / "runs").iterdir())) == 2
    manifest = root / f"runs/{run['run_id']}/run_manifest.json"
    run["execution_authorization"] = None
    write_json(manifest, run)
    with pytest.raises(ValueError, match="authorization contradicts"):
        verify_run(root, manifest.relative_to(root).as_posix())


@pytest.mark.parametrize("field", ["candidate_spec", "retry_of", "execution_role"])
def test_authorization_must_bind_exact_repair_identity(repair_case, field):
    from mathmode.repair_execution import validate_authorization
    root, service, plan, job, failed, relative, diagnosis, schedules, mutations = repair_case
    first = code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    reviewed = code_repairs.verify_code_repair(root, first["request"])
    auth = {key: {"path": path, "sha256": file_hash(root / path)} for key, path in
            (("request", first["request"]), ("review", reviewed["review"]), ("candidate_spec", reviewed["candidate_spec"]))}
    auth.update(execution_role="main", retry_of=failed["run_id"])
    if field == "candidate_spec":
        auth[field] = {"path": "model_spec.json", "sha256": file_hash(root / "model_spec.json")}
    else:
        auth[field] = "baseline" if field == "execution_role" else "run-unrelated"
    with pytest.raises(ValueError, match="actual role/predecessor|reviewed candidate"):
        validate_authorization(root, auth, reviewed["candidate_spec"], auth["execution_role"], auth["retry_of"])
    assert len(list((root / "runs").iterdir())) == 1


def test_ordinary_retry_cannot_be_adopted_as_authorized_repair(repair_case):
    from mathmode.repair_execution import execute_reviewed_repair
    from mathmode.repair_activation import activate_reviewed_repair
    root, service, plan, job, failed, relative, diagnosis, schedules, mutations = repair_case
    first = code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    reviewed = code_repairs.verify_code_repair(root, first["request"])
    ordinary = execute_model(root, reviewed["candidate_spec"], retry_of=reviewed["retry_of"], interpreter=sys.executable)
    assert ordinary["status"] == "PASS"
    with pytest.raises(ValueError, match="predecessor is no longer latest"):
        execute_reviewed_repair(root, first["request"], interpreter=sys.executable)
    with pytest.raises(ValueError, match="matching execution authorization"):
        activate_reviewed_repair(root, first["request"], f"runs/{ordinary['run_id']}/run_manifest.json")
    assert not (root / first["request"]).with_name("activation.json").exists()
    assert len(list((root / "runs").iterdir())) == 2


def test_activation_requires_successful_reviewed_run_and_is_idempotent(repair_case):
    from mathmode.repair_execution import execute_reviewed_repair
    from mathmode.repair_activation import activate_reviewed_repair, verify_activation, adopt_activation_in_progress
    root, service, plan, job, failed, relative, diagnosis, schedules, mutations = repair_case
    first = code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    code_repairs.prepare_code_repair(service, plan, job, diagnosis)
    run = execute_reviewed_repair(root, first["request"], interpreter=sys.executable)
    run_path = f"runs/{run['run_id']}/run_manifest.json"
    record = activate_reviewed_repair(root, first["request"], run_path)
    assert record["status"] == "ACTIVE"
    assert activate_reviewed_repair(root, first["request"], run_path) == record
    activation_path = first["request"].rsplit("/", 1)[0] + "/activation.json"
    assert verify_activation(root, activation_path) == record
    progress = {"schema_version": "2.0", "case_id": plan["case_id"], "questions": {
        job["question_id"]: {"main_run": relative, "baseline_run": None, "validation": None, "evidence": None}}}
    write_json(root / "workflow_progress.json", progress)
    original_progress_hash = file_hash(root / "workflow_progress.json")
    for field in ("request", "review", "candidate_spec", "run", "failed_predecessor"):
        forged = deepcopy(record)
        forged[field]["sha256"] = "0" * 64
        write_json(root / activation_path, forged)
        with pytest.raises(ValueError, match="differs from verified execution evidence"):
            adopt_activation_in_progress(root, "workflow_progress.json", activation_path, role="main")
        assert file_hash(root / "workflow_progress.json") == original_progress_hash
    write_json(root / activation_path, record)
    for role in ("baseline", "probe", "unrecognized"):
        with pytest.raises(ValueError, match="Adoption role"):
            adopt_activation_in_progress(root, "workflow_progress.json", activation_path, role=role)
        assert file_hash(root / "workflow_progress.json") == original_progress_hash
    adopted = adopt_activation_in_progress(root, "workflow_progress.json", activation_path, role="main")
    assert adopted["questions"][job["question_id"]]["effective_main_spec"] == record["candidate_spec"]["path"]
    assert adopted["questions"][job["question_id"]]["main_run"] == relative
