from copy import deepcopy
from pathlib import Path
import stat

import pytest
from jsonschema import Draft202012Validator, ValidationError

from mathmode.contracts import validate, validate_modeling_bundle, topological_order, read_ledger
from mathmode.io import loads, read_json, safe_path, write_json, file_hash, now
from mathmode.schema_catalog import catalog
from mathmode.state import StateStore, initial_state, append_event, workspace_lock
from mathmode.workspace import initialize, REPO_ROOT
from tools.build_contract_schemas import build

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/contracts"


def sample(name):
    return read_json(FIXTURES / f"{name}.json")


@pytest.mark.parametrize("name", [name for name in catalog() if name not in {
    "run_manifest", "validation_criteria", "validation_summary", "evidence_gate",
    "freeze_request", "frozen_numbers", "freeze_event", "freeze_index"}])
def test_standalone_examples_and_schema_distribution(name):
    Draft202012Validator.check_schema(catalog()[name])
    validate(name, sample(name))
    assert build(REPO_ROOT / "华为杯_求解规范/schemas", check=True) == []


@pytest.mark.parametrize("payload", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":1e999}', '{"a":[-1e999]}'])
def test_strict_json_rejects_ambiguous_or_nonfinite_values(payload):
    with pytest.raises(ValueError):
        loads(payload)


@pytest.mark.parametrize("relative", ["../secret", "a/../../b", "C:/key", "//server/share", "/absolute",
    "a//b", "a/./b", "NUL.txt", "a/COM1", "file.", "file ", "a:stream"])
def test_confined_paths(tmp_path, relative):
    with pytest.raises(ValueError):
        safe_path(tmp_path, relative, exists=False)


def test_symlink_escape(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "workspace"
    root.mkdir()
    try:
        (root / "link").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Creating Windows symlinks requires Developer Mode or symlink privilege")
    with pytest.raises(ValueError, match="Symlink"):
        safe_path(root, "link/file.json", exists=False)


@pytest.mark.parametrize("nodes,reason", [({"Q1": ["Q1"]}, "Self"),
    ({"Q1": ["Q2"]}, "Unknown"), ({"Q1": ["Q2"], "Q2": ["Q1"]}, "cycle"),
    ({"Q1": [], "Q2": ["Q1", "Q1"]}, "Duplicate")])
def test_invalid_dags(nodes, reason):
    with pytest.raises(ValueError, match=reason):
        topological_order(nodes)


def test_topology_and_cross_contract_question_coverage():
    assert topological_order({"Q3": ["Q1", "Q2"], "Q2": [], "Q1": []}) == ["Q1", "Q2", "Q3"]
    bundle = sample("modeling_bundle")
    assert validate_modeling_bundle(bundle)["scientific_acceptance"] == "NOT_RUN"
    bundle["problem_dag"]["nodes"].append({"question_id": "Q2", "depends_on": []})
    with pytest.raises(ValueError, match="exactly"):
        validate_modeling_bundle(bundle)


def test_high_ambiguity_blocks_even_with_a_mitigation():
    bundle = sample("modeling_bundle")
    item = {"ambiguity_id": "unit-conflict", "severity": "high", "source": "problem:line1",
            "issue": "Conflicting units", "interpretations": ["m", "km"], "question_ids": ["Q1"],
            "status": "unresolved", "resolution": None, "evidence_refs": []}
    bundle["ambiguity_register"]["items"] = [item]
    with pytest.raises(ValueError, match="high-severity"):
        validate_modeling_bundle(bundle)
    item.update(status="mitigated", resolution="Compute both", evidence_refs=["source:line1"])
    with pytest.raises(ValueError, match="high-severity"):
        validate_modeling_bundle(bundle)
    item.update(status="resolved", resolution="Original source confirms m")
    validate_modeling_bundle(bundle)


@pytest.mark.parametrize("mutation,reason", [
    (lambda s: s["data_split"]["test_ids"].append("row1"), "leakage"),
    (lambda s: s["data_split"]["fit_ids"].append("row3"), "leakage"),
    (lambda s: s["data_split"]["features"].append("observed_y"), "Target leakage"),
    (lambda s: s.update(task_type="time_series"), "chronological"),
    (lambda s: s["formulae"][0].update(output_symbol="unknown"), "formula variable"),
    (lambda s: s["implementation"]["code_files"].append("validators/prediction.py"), "Independent validator"),
])
def test_model_spec_semantic_failures(mutation, reason):
    spec = sample("model_spec")
    mutation(spec)
    with pytest.raises(ValueError, match=reason):
        validate("model_spec", spec)


def test_missing_usable_baseline_and_untriggered_fallback():
    card = sample("method_card")
    card["methods"][1]["role"] = "diagnostic_reference"
    with pytest.raises(ValueError, match="usable_baseline"):
        validate("method_card", card)
    card = sample("method_card")
    fallback = deepcopy(card["methods"][0])
    fallback.update(method_id="fallback", role="conditional_fallback")
    card["methods"].append(fallback)
    with pytest.raises(ValueError, match="trigger"):
        validate("method_card", card)


def test_chronological_and_group_leakage():
    spec = sample("model_spec")
    spec["task_type"] = "time_series"
    split = spec["data_split"]
    split.update(strategy="time", sample_times={"row1": "2026-01-01T00:00:00Z",
        "row2": "2026-01-03T00:00:00Z", "row3": "2026-01-02T00:00:00Z"})
    with pytest.raises(ValueError, match="Chronological leakage"):
        validate("model_spec", spec)
    split["sample_times"]["row3"] = "2026-01-04T00:00:00Z"
    validate("model_spec", spec)
    spec["task_type"] = "regression"
    split.update(strategy="group", sample_groups={"row1": "siteA", "row2": "siteB", "row3": "siteA"})
    with pytest.raises(ValueError, match="Group leakage"):
        validate("model_spec", spec)


def test_assumption_references_and_comparable_baseline():
    bundle = sample("modeling_bundle")
    bundle["assumption_events"] = []
    with pytest.raises(ValueError, match="method assumption"):
        validate_modeling_bundle(bundle)
    bundle = sample("modeling_bundle")
    baseline = deepcopy(bundle["model_specs"][0])
    baseline["method_id"] = "mean-baseline"
    baseline["data_split"]["test_ids"] = ["row4"]
    bundle["model_specs"].append(baseline)
    with pytest.raises(ValueError, match="identical evaluation splits"):
        validate_modeling_bundle(bundle)


def test_probe_cannot_contradict_computed_checks():
    probe = sample("risk_probe")
    probe["verdict"] = "PASS"
    with pytest.raises(ValueError, match="contradicts"):
        validate("risk_probe", probe)
    probe = sample("risk_probe")
    probe["checks"][1] = deepcopy(probe["checks"][0])
    with pytest.raises(ValueError, match="Duplicate"):
        validate("risk_probe", probe)


def test_false_human_attribution_and_spec_changed_question():
    decision = sample("method_decision")
    decision["decided_by"] = "human"
    with pytest.raises(ValueError, match="Human attribution"):
        validate("method_decision", decision)
    bundle = sample("modeling_bundle")
    bundle["model_specs"][0]["outputs"][0]["precision"] = 1
    with pytest.raises(ValueError, match="changed official question"):
        validate_modeling_bundle(bundle)


def test_append_only_assumptions(tmp_path):
    event = sample("assumption_ledger")
    append_event(tmp_path, "assumptions.jsonl", event, contract="assumption_ledger")
    previous = (tmp_path / "assumptions.jsonl").read_bytes()
    update = {**event, "entry_id": "assumption-event2", "status": "accepted"}
    with pytest.raises(ValueError, match="supersede"):
        append_event(tmp_path, "assumptions.jsonl", update, contract="assumption_ledger")
    assert (tmp_path / "assumptions.jsonl").read_bytes() == previous
    update["supersedes"] = event["entry_id"]
    append_event(tmp_path, "assumptions.jsonl", update, contract="assumption_ledger")
    assert (tmp_path / "assumptions.jsonl").read_bytes().startswith(previous)
    assert len(read_ledger(tmp_path / "assumptions.jsonl")) == 2


def test_atomic_revision_and_lock(tmp_path):
    store = StateStore(tmp_path)
    store.create(initial_state("test-case", "fixture"))
    before = store.path.read_bytes()
    with pytest.raises(ValueError, match="revision"):
        store.update(lambda state: None, expected_revision=1)
    assert store.path.read_bytes() == before
    with workspace_lock(tmp_path):
        with pytest.raises(ValueError, match="locked"):
            store.update(lambda state: None, expected_revision=0)
    assert store.update(lambda state: state.update(rigor_profile="submission"), expected_revision=0)["revision"] == 1
    with pytest.raises(ValueError, match="identity"):
        store.update(lambda state: state.update(case_id="changed"), expected_revision=1)


def test_retry_budget_survives_resume(tmp_path):
    store = StateStore(tmp_path)
    store.create(initial_state("test-case", "fixture"))
    event = {"cause_id": "missing-input", "category": "DATA_FAILURE", "attempt": 1,
             "question_id": "Q1", "message": "Input missing", "changed_artifacts": [], "at": now()}
    for attempt in range(1, 4):
        store = StateStore(tmp_path)
        store.update(lambda state: state["retry_history"].append({**event, "attempt": attempt}), expected_revision=attempt - 1)
    with pytest.raises((ValueError, ValidationError)):
        store.update(lambda state: state["retry_history"].append({**event, "attempt": 4}), expected_revision=3)
    with pytest.raises(ValueError, match="Append-only"):
        store.update(lambda state: state.update(retry_history=[]), expected_revision=3)


def test_resume_detects_transitive_staleness(tmp_path):
    state = initial_state("test-case", "fixture")
    for key, deps in [("result", []), ("figure", ["result"]), ("paper", ["figure"])]:
        path = tmp_path / f"{key}.json"
        write_json(path, {"value": key})
        state["artifacts"].append({"artifact_id": key, "path": path.name, "sha256": file_hash(path),
            "size_bytes": path.stat().st_size, "created_at": now(), "producer": "test",
            "depends_on": [{"artifact_id": dep, "sha256": next(a["sha256"] for a in state["artifacts"] if a["artifact_id"] == dep)} for dep in deps], "status": "VALID"})
    store = StateStore(tmp_path)
    store.create(state)
    assert store.inspect_freshness()["status"] == "PASS"
    write_json(tmp_path / "result.json", {"value": "changed"})
    assert store.inspect_freshness()["stale"] == ["figure", "paper", "result"]


def test_workspace_snapshots_and_no_overwrite(tmp_path):
    original = tmp_path / "original.txt"
    original.write_text("A synthetic problem", encoding="utf-8")
    inputs = [{"input_id": "problem", "path": str(original), "role": "problem", "source": sample("input_manifest")["files"][0]["source"]}]
    destination = tmp_path / "private" / "case"
    root = initialize("test-case", inputs, destination=destination)
    manifest = read_json(root / "input_manifest.json")
    validate("input_manifest", manifest, root=root)
    copied = root / manifest["files"][0]["path"]
    assert not copied.stat().st_mode & 0o222
    assert original.stat().st_mode & 0o222
    with pytest.raises(ValueError, match="overwrite"):
        initialize("test-case", inputs, destination=destination)
    copied.chmod(stat.S_IRUSR | stat.S_IWUSR)
    copied.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        validate("input_manifest", manifest, root=root)


def test_workspace_preflight_does_not_create_destination(tmp_path):
    with pytest.raises(ValueError, match="public template"):
        initialize("private-case", [], destination=REPO_ROOT / "private-case")
    target = tmp_path / "destination"
    with pytest.raises(ValidationError):
        initialize("test-case", [], destination=target)
    assert not target.exists()
