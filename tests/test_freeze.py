from copy import deepcopy
import stat
import sys

import pytest
from jsonschema import Draft202012Validator

from test_validation import prepared, runs  # Shared actual-run fixtures.
from mathmode.freeze import freeze_results, thaw, verify_freeze, freeze_events, json_pointer
from mathmode.io import read_json, write_json, file_hash
from mathmode.lineage import ArtifactRegistry
from mathmode.runner import execute_model
from mathmode.schema_catalog import catalog
from mathmode.state import StateStore
from mathmode.validation import independently_validate, audit_evidence


def make_evidence(root, main, baseline):
    summary = independently_validate(root, main, baseline, interpreter=sys.executable)
    summary_relative = f"validations/{summary['validation_id']}/validation_summary.json"
    report = audit_evidence(root, summary_relative)
    assert report["status"] == "PASS", report
    evidence_relative = f"validations/{summary['validation_id']}/evidence.json"
    write_json(root / evidence_relative, report)
    request = {"schema_version": "2.0", "actor_id": "freeze-service", "question_id": "Q1", "decision_id": "decision1",
        "numbers": [{"frozen_number_id": "Q1-MSE", "claim_id": "Q1-fit", "source_path": summary_relative,
            "locator": "/measurements/main_mse", "unit": "fixture-dimensionless", "precision": 6}]}
    return request, evidence_relative


@pytest.fixture
def frozen(runs):
    root, main, baseline = runs
    request, evidence = make_evidence(root, main, baseline)
    snapshot = freeze_results(root, request, evidence)
    return root, snapshot, request, evidence


def test_freeze_uses_real_locators_and_immutable_versions(frozen):
    root, snapshot, request, evidence = frozen
    assert snapshot["numbers"][0]["value"] == 0
    pointer = read_json(root / "frozen_numbers.json")["questions"]["Q1"]
    path = root / pointer["path"]
    assert not path.stat().st_mode & 0o222
    before = path.read_bytes()
    assert verify_freeze(root, "Q1")["freeze_id"] == snapshot["freeze_id"]
    with pytest.raises(ValueError, match="Thaw"):
        freeze_results(root, request, evidence)
    assert path.read_bytes() == before
    for name in ("freeze_request", "frozen_numbers", "freeze_event", "freeze_index"):
        Draft202012Validator.check_schema(catalog()[name])


def test_thaw_invalidates_all_consumers_and_preserves_old_bytes(frozen):
    root, snapshot, request, evidence = frozen
    registry = ArtifactRegistry(root)
    write_json(root / "figure.json", {"fixture": "render placeholder is not a final figure"})
    figure = registry.register("figure.json", producer="fixture-visual", dependencies=[snapshot["registry_artifact_id"]])
    write_json(root / "paper.json", {"fixture": "dependency node only"})
    paper = registry.register("paper.json", producer="fixture-writer", dependencies=[figure])
    store = StateStore(root)
    state = store.load()
    store.update(lambda s: s["gates"].append({"gate_id": "G7", "status": "PASS", "artifact_refs": [paper],
        "checked_at": snapshot["created_at"], "blockers": []}), expected_revision=state["revision"])
    pointer = read_json(root / "frozen_numbers.json")["questions"]["Q1"]
    original = (root / pointer["path"]).read_bytes()
    outcome = thaw(root, "Q1", actor_id="orchestrator", reason="Re-evaluate model parameters")
    assert {figure, paper} <= set(outcome["affected"])
    assert (root / pointer["path"]).read_bytes() == original
    state = store.load()
    assert state["gates"][0]["status"] == "BLOCKED"
    with pytest.raises(ValueError, match="active"):
        verify_freeze(root, "Q1")
    with pytest.raises(ValueError, match="new main/baseline"):
        freeze_results(root, request, evidence)


def test_refreeze_requires_actual_new_runs_and_validation(frozen):
    root, first, request, evidence = frozen
    old_pointer = read_json(root / "frozen_numbers.json")["questions"]["Q1"]
    old_hash = file_hash(root / old_pointer["path"])
    thaw(root, "Q1", actor_id="orchestrator", reason="Explicit independent repeat")
    main = execute_model(root, "main_spec.json", role="main", interpreter=sys.executable)
    baseline = execute_model(root, "baseline_spec.json", role="baseline", interpreter=sys.executable)
    request, evidence = make_evidence(root, f"runs/{main['run_id']}/run_manifest.json", f"runs/{baseline['run_id']}/run_manifest.json")
    second = freeze_results(root, request, evidence)
    assert second["version"] == 2 and second["freeze_id"] != first["freeze_id"]
    assert file_hash(root / old_pointer["path"]) == old_hash
    assert verify_freeze(root, "Q1")["freeze_id"] == second["freeze_id"]
    assert [event["kind"] for event in freeze_events(root)] == ["FREEZE", "THAW", "FREEZE"]


def test_canonical_change_propagates_to_freeze_and_paper(frozen):
    root, snapshot, request, evidence = frozen
    registry = ArtifactRegistry(root)
    write_json(root / "paper.json", {"fixture": "dependency node only"})
    paper = registry.register("paper.json", producer="fixture-writer", dependencies=[snapshot["registry_artifact_id"]])
    code = root / "code/regression.py"
    code.write_text(code.read_text(encoding="utf-8") + "\n# upstream change\n", encoding="utf-8")
    with pytest.raises(ValueError, match="thaw"):
        registry.register("code/regression.py", producer="modeler")
    report = registry.refresh()
    assert {snapshot["registry_artifact_id"], paper} <= set(report["stale"])
    with pytest.raises(ValueError, match="thaw"):
        registry.register("code/regression.py", producer="modeler")
    with pytest.raises(ValueError, match="stale"):
        verify_freeze(root, "Q1")


def test_manual_snapshot_and_log_mutation_are_rejected(frozen):
    root, snapshot, request, evidence = frozen
    pointer = read_json(root / "frozen_numbers.json")["questions"]["Q1"]
    path = root / pointer["path"]
    original = path.read_bytes()
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    altered = deepcopy(snapshot)
    altered["numbers"][0]["value"] = 999
    write_json(path, altered)
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_freeze(root, "Q1")
    path.write_bytes(original)
    thaw(root, "Q1", actor_id="orchestrator", reason="Test append-only history")
    log = root / "freeze_change_log.jsonl"
    lines = log.read_text(encoding="utf-8").splitlines()
    lines[0] = lines[0].replace("Computed evidence", "Altered evidence")
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash chain"):
        freeze_events(root)


@pytest.mark.parametrize("value,pointer", [({"a": True}, "/a"), ({"a": [1]}, "/a/01"),
    ({"a": [1]}, "/a/2"), ({"a": 1}, "/missing"), ({"a": 1}, "a"), ({"a": float('nan')}, "/a")])
def test_invalid_numeric_locators(value, pointer):
    with pytest.raises(ValueError):
        json_pointer(value, pointer)


def test_freeze_rejects_unverified_source_and_wrong_unit(runs):
    root, main, baseline = runs
    request, evidence = make_evidence(root, main, baseline)
    request["numbers"][0]["unit"] = "kg"
    with pytest.raises(ValueError, match="declared unit"):
        freeze_results(root, request, evidence)
    write_json(root / "unverified.json", {"value": 0})
    request["numbers"][0].update(source_path="unverified.json", locator="/value")
    with pytest.raises(ValueError, match="verified main outputs"):
        freeze_results(root, request, evidence)
    assert not (root / "frozen_numbers.json").exists()


def test_registry_batch_publishes_one_revision_or_nothing(tmp_path):
    from mathmode.state import initial_state
    store = StateStore(tmp_path)
    store.create(initial_state("batch-fixture", "fixture"))
    write_json(tmp_path / "source.json", {"value": 1})
    write_json(tmp_path / "derived.json", {"value": 2})
    registry = ArtifactRegistry(tmp_path)
    with pytest.raises(ValueError, match="unknown dependency"):
        with registry.batch():
            registry.register("source.json", producer="fixture")
            registry.register("derived.json", producer="fixture", dependencies=["missing"])
    assert store.load()["artifacts"] == []
    assert store.load()["revision"] == 0
    with registry.batch():
        source = registry.register("source.json", producer="fixture")
        registry.register("derived.json", producer="fixture", dependencies=[source])
    assert store.load()["revision"] == 1
    assert len(store.load()["artifacts"]) == 2


def test_binding_run_preserves_upstream_parameter_dependencies(runs):
    root, main, baseline = runs
    registry = ArtifactRegistry(root)
    write_json(root / "parameters.json", {"modeling_assumption": "affine response"})
    parameter = registry.register("parameters.json", producer="modeler")
    registry.register("main_spec.json", producer="modeler", dependencies=[parameter])
    request, evidence = make_evidence(root, main, baseline)
    snapshot = freeze_results(root, request, evidence)
    write_json(root / "parameters.json", {"modeling_assumption": "changed"})
    observation = registry.refresh()
    assert snapshot["registry_artifact_id"] in observation["stale"]
