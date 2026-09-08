"""Real fallback lifecycle with explicit test doubles only for role provenance."""
from copy import deepcopy
import sys

import pytest

from test_validation import prepared
from test_workflow import case, review
from mathmode.io import read_json, write_json, file_hash, now
from mathmode.lineage import artifact_id
from mathmode.probes import measured_probe, screening_options, verify_screened_decision
from mathmode.runner import execute_model, verify_run
from mathmode.freeze import verify_freeze
from mathmode.state import append_event


@pytest.fixture
def fallback_case(case):
    root, service, plan = case
    job = plan["questions"][0]
    card = read_json(root / job["method_card"])
    fallback = deepcopy(card["methods"][0])
    fallback.update(method_id="median-slope-fallback", role="conditional_fallback",
        idea="Median pairwise training slope for this synthetic affine fixture",
        fallback_trigger={"metric": "degeneracy.degeneracy", "operator": "lt", "threshold": 100})
    card["methods"][0]["assumption_ids"].append("main-wide-spread")
    card["methods"].append(fallback)
    write_json(root / job["method_card"], card)
    probe_plan = read_json(root / "probes/plan.json")
    # Deliberately strict main screening threshold produces a measured rejection.
    # This tests routing, not a claim that the main algorithm is scientifically wrong.
    for check in probe_plan["checks"]:
        if check["category"] == "degeneracy":
            check["measurements"][0]["threshold"] = 100
    write_json(root / "probes/plan.json", probe_plan)
    spec = read_json(root / "probes/spec.json")
    spec["validation_plan"].update(
        probe={"path": "probes/plan.json", "sha256": file_hash(root / "probes/plan.json")},
        screening_card={"path": job["method_card"], "sha256": file_hash(root / job["method_card"])})
    write_json(root / "probes/spec.json", spec)
    main_probe = execute_model(root, "probes/spec.json", role="probe", interpreter=sys.executable)
    main_run_path = f"runs/{main_probe['run_id']}/run_manifest.json"
    write_json(root / "probes/report.json", measured_probe(root, main_run_path))
    append_event(root, plan["framing"]["assumption_ledger"], {
        "schema_version": "2.0", "entry_id": "main-spread-rejected", "assumption_id": "main-wide-spread",
        "supersedes": None, "content": "Main screening requires input variance at least 100 in this synthetic routing test.",
        "kind": "simplifying", "source_refs": ["problem:1"], "question_ids": ["Q1"],
        "formula_ids": ["unselected-main-spread-formula"], "validation_method": "Actual predeclared main variance probe",
        "sensitivity_status": "not_applicable", "status": "rejected", "created_at": now(), "producer": "fixture-auditor"
    }, contract="assumption_ledger")
    own_plan = deepcopy(probe_plan)
    own_plan["method_id"] = fallback["method_id"]
    for check in own_plan["checks"]:
        if check["category"] == "degeneracy":
            check["measurements"][0]["threshold"] = 1
    write_json(root / "probes/fallback-plan.json", own_plan)
    own_spec = deepcopy(spec)
    own_spec["method_id"] = fallback["method_id"]
    own_spec["validation_plan"]["probe"] = {"path": "probes/fallback-plan.json", "sha256": file_hash(root / "probes/fallback-plan.json")}
    write_json(root / "probes/fallback-spec.json", own_spec)
    own_run = execute_model(root, "probes/fallback-spec.json", role="probe", interpreter=sys.executable)
    write_json(root / "probes/fallback-report.json", measured_probe(root, f"runs/{own_run['run_id']}/run_manifest.json"))
    job["probe_reports"].append("probes/fallback-report.json")
    job["probe_specs"].append("probes/fallback-spec.json")
    decision = read_json(root / job["decision"])
    decision.update(decision_id="fallback-decision", main_method_id=fallback["method_id"],
        execution_role="fallback", decided_at=now(), rationale="Measured main screening threshold failed; the predeclared fallback trigger is active and its own probe passes.",
        evidence_refs=[artifact_id(path) for path in job["probe_reports"]])
    append_event(root, job["decision"], decision, contract="method_decision")
    code = '''import json,sys,statistics,itertools
from pathlib import Path
c=json.loads(Path(sys.argv[sys.argv.index('--context')+1]).read_text())
s=json.loads(Path(c['spec']).read_text())
rows={r['id']:r for r in json.loads(Path(c['inputs']['data']).read_text())['rows']}
train=[rows[k] for k in s['data_split']['train_ids']]
slopes=[(b['observed_y']-a['observed_y'])/(b['x']-a['x'])
        for a,b in itertools.combinations(train,2) if b['x']!=a['x']]
slope=statistics.median(slopes)
intercept=statistics.median(r['observed_y']-slope*r['x'] for r in train)
out=[{'id':k,'prediction':slope*rows[k]['x']+intercept} for k in s['data_split']['test_ids']]
(Path(c['output_dir'])/'predictions.json').write_text(json.dumps(out))
'''
    (root / "code/fallback.py").write_text(code, encoding="utf-8")
    solution = read_json(root / "main_spec.json")
    solution.update(method_id=fallback["method_id"], decision_id=decision["decision_id"],
        implementation={"entrypoint": "code/fallback.py", "code_files": ["code/fallback.py"], "language": "python"},
        fallback_authorization={field: {"path": path, "sha256": file_hash(root / path)} for field, path in
            (("card", job["method_card"]), ("probe_report", "probes/report.json"), ("probe_run", main_run_path))})
    job["main_spec"] = "fallback_spec.json"
    write_json(root / job["main_spec"], solution)
    baseline = read_json(root / job["baseline_spec"])
    baseline["decision_id"] = decision["decision_id"]
    write_json(root / job["baseline_spec"], baseline)
    review(root, job["code_review"], solution["actor_id"], [job["main_spec"], job["baseline_spec"],
        "code/fallback.py", "code/regression.py", solution["validation_plan"]["criteria"]["path"],
        job["method_card"], job["decision"], *job["probe_reports"]])
    return root, service, plan, decision


def test_triggered_fallback_is_reviewed_executed_independently_validated_and_frozen(fallback_case, monkeypatch):
    root, service, plan, decision = fallback_case
    job = plan["questions"][0]
    assert read_json(root / "probes/report.json")["verdict"] == "FAIL"
    assert read_json(root / "probes/fallback-report.json")["verdict"] == "PASS"
    report = service.observe(plan)
    assert report["questions"]["Q1"]["next_action"] == "run-fallback", report
    for action in ("run-fallback", "run-baseline", "independent-validate"):
        report = service.advance(plan, interpreter=sys.executable)
        assert report["performed"]["action"] == action, report
    assert report["questions"]["Q1"]["next_action"] == "review-validation"
    progress = read_json(root / "workflow_progress.json")["questions"]["Q1"]
    run = verify_run(root, progress["main_run"])
    assert run["role"] == "fallback" and run["method_id"] == decision["main_method_id"]
    summary = read_json(root / progress["validation"])
    assert summary["measurements"]["main_mse"] == 0
    assert summary["measurements"]["baseline_mse"] == 26
    child_spec = read_json(root / summary["validator_workspace"] / "model_spec.json")
    assert "fallback_authorization" not in child_spec
    assert all(path.startswith("validator/") for path in child_spec["implementation"]["code_files"])
    captured = []
    service.agents.backend = object()
    def capture(schedule):
        captured.append(schedule)
        return {"executed": []}
    monkeypatch.setattr(service.agents, "advance", capture)
    assert service.advance(plan)["performed"] is None
    supplied = set(captured[0]["tasks"][0]["inputs"])
    assert {job["method_card"], job["decision"], *job["probe_reports"]} <= supplied
    assert not {"code/fallback.py", "code/regression.py"} & supplied
    service.agents.backend = None
    solution = read_json(root / job["main_spec"])
    review(root, job["validation_review"], solution["actor_id"], [job["main_spec"], job["baseline_spec"],
        progress["validation"], progress["evidence"], solution["validation_plan"]["criteria"]["path"],
        job["method_card"], job["decision"], *job["probe_reports"]])
    assert service.advance(plan)["performed"]["action"] == "freeze"
    frozen = verify_freeze(root, "Q1")
    assert frozen["decision_id"] == decision["decision_id"]
    assert service.observe(plan)["gates"]["G6"]["status"] == "PASS"
    assert service.observe(plan)["gates"]["G7"]["status"] == "BLOCKED"
    # A lost index adopts the same actual fallback, without relabeling or rerunning it.
    before = len(list((root / "runs").glob("*/run_manifest.json")))
    (root / "workflow_progress.json").unlink()
    assert service.advance(plan)["performed"]["action"] == "adopt-fallback"
    assert len(list((root / "runs").glob("*/run_manifest.json"))) == before
    # The authorization remains part of downstream integrity after freezing.
    changed = read_json(root / "probes/report.json")
    changed["checks"][0]["metrics"]["executability"] = 42
    write_json(root / "probes/report.json", changed)
    with pytest.raises(ValueError):
        verify_freeze(root, "Q1")


def test_fallback_requires_own_probe_role_and_complete_decision_evidence(fallback_case):
    root, service, plan, decision = fallback_case
    job = plan["questions"][0]
    with pytest.raises(ValueError, match="No screened production method"):
        screening_options(root, job["method_card"], ["probes/report.json"])
    screening = screening_options(root, job["method_card"], job["probe_reports"])
    assert set(screening["options"]) == {"fallback"}
    wrong_role = {**decision, "execution_role": "main"}
    with pytest.raises(ValueError, match="eligible screened"):
        verify_screened_decision(wrong_role, screening, job["probe_reports"])
    omitted = {**decision, "evidence_refs": [artifact_id("probes/report.json")]}
    with pytest.raises(ValueError, match="omits"):
        verify_screened_decision(omitted, screening, job["probe_reports"])
    with pytest.raises(ValueError, match="one declared current probe"):
        screening_options(root, job["method_card"], [*job["probe_reports"], "probes/report.json"])
    # The lower-level runner rejects disguising the authorized fallback as main.
    with pytest.raises(ValueError, match="only be consumed by a fallback"):
        execute_model(root, job["main_spec"], role="main", interpreter=sys.executable)
    bundle, assumptions = service._framing(plan)
    card = read_json(root / job["method_card"])
    bad_card = deepcopy(card)
    next(method for method in bad_card["methods"] if method["role"] == "conditional_fallback")["assumption_ids"].append("main-wide-spread")
    reused = deepcopy(assumptions)
    next(item for item in reused if item["assumption_id"] == "main-wide-spread")["formula_ids"] = ["affine"]
    with pytest.raises(ValueError, match="rejected assumption"):
        service._code(job, bundle, reused, bad_card, decision)
    typo = deepcopy(assumptions)
    next(item for item in typo if item["assumption_id"] == "linearity")["formula_ids"] = ["missing-active-formula"]
    with pytest.raises(ValueError, match="assumption formula"):
        service._code(job, bundle, typo, card, decision)
    solution = read_json(root / job["main_spec"])
    solution.pop("fallback_authorization")
    write_json(root / job["main_spec"], solution)
    report = service.observe(plan)
    assert "must carry measured authorization" in report["questions"]["Q1"]["gates"]["G4"]["blockers"][0]


def test_structural_fallback_decision_is_not_a_runtime_admission():
    from pathlib import Path
    from mathmode.contracts import validate
    path = Path(__file__).resolve().parents[1] / "fixtures/agents/fallback_decision.json"
    decision = validate("method_decision", read_json(path))
    assert decision["execution_role"] == "fallback"
    with pytest.raises(ValueError, match="eligible screened"):
        verify_screened_decision(decision, {"card": {"question_id": "Q1", "methods": [
            {"role": "usable_baseline", "method_id": "mean-baseline"}]}, "options": {}}, [])


def test_fallback_validator_guard_requires_selection_evidence_and_excludes_code(fallback_case, monkeypatch):
    root, service, plan, decision = fallback_case
    job = plan["questions"][0]
    spec = read_json(root / job["main_spec"])
    criteria = spec["validation_plan"]["criteria"]["path"]
    dag_path = plan["framing"]["problem_dag"]
    contracts = {job["main_spec"]: ("model_spec", spec),
        job["baseline_spec"]: ("model_spec", read_json(root / job["baseline_spec"])),
        criteria: ("validation_criteria", read_json(root / criteria)),
        job["method_card"]: ("method_card", read_json(root / job["method_card"])),
        job["decision"]: ("method_decision", decision),
        dag_path: ("problem_dag", read_json(root / dag_path))}
    contracts.update({path: ("risk_probe", read_json(root / path)) for path in job["probe_reports"]})
    # Role authorship is the same explicit fixture double used by the lifecycle;
    # the scheduler's actual screening verification and input whitelist remain real.
    monkeypatch.setattr(service.agents, "_kind", lambda path: contracts.get(path, (None, None)))
    service.registry.register(job["main_spec"], producer=spec["actor_id"])
    task = {"role": "validator", "question_id": "Q1", "interaction_mode": "autopilot",
        "reviewed_actor_id": spec["actor_id"],
        "inputs": [{"path": path, "artifact_id": artifact_id(path)} for path in contracts]}
    schedule = {"question_dag": contracts[dag_path][1]}
    service.agents._guard({}, task, schedule)
    missing_decision = {**task, "inputs": [item for item in task["inputs"] if item["path"] != job["decision"]]}
    with pytest.raises(ValueError, match="requires its actual decision"):
        service.agents._guard({}, missing_decision, schedule)
    missing_probe = {**task, "inputs": [item for item in task["inputs"] if item["path"] != "probes/fallback-report.json"]}
    with pytest.raises(ValueError, match="No screened production method"):
        service.agents._guard({}, missing_probe, schedule)
    task["inputs"].append({"path": "code/fallback.py", "artifact_id": "solver-code"})
    with pytest.raises(ValueError, match="unapproved inputs"):
        service.agents._guard({}, task, schedule)
