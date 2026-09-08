from pathlib import Path
import json
import stat
import sys

import pytest
from jsonschema import Draft202012Validator

from mathmode.contracts import validate
from mathmode.execution import LocalSubprocessBackend
from mathmode.io import file_hash, read_json, write_json
from mathmode.runner import execute_model, verify_run, validate_output
from mathmode.schema_catalog import catalog
from mathmode.workspace import initialize

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture
def workspace(tmp_path):
    problem = tmp_path / "problem.txt"
    problem.write_text("Synthetic execution contract fixture", encoding="utf-8")
    data = tmp_path / "data.json"
    write_json(data, {"values": [2, 3, 7]})
    source = {"uri": "fixture://runner", "accessed_at": "2026-09-08T00:00:00Z", "license": "Repository-authored fixture"}
    root = initialize("runner-fixture", [{"input_id": key, "path": str(path), "role": key, "source": source}
        for key, path in [("problem", problem), ("data", data)]], destination=tmp_path / "workspace", kind="fixture")
    (root / "code").mkdir()
    (root / "code/compute.py").write_bytes((FIXTURES / "runner/compute.py").read_bytes())
    spec = read_json(FIXTURES / "contracts/model_spec.json")
    spec.update(inputs=["data"], implementation={"entrypoint": "code/compute.py", "code_files": ["code/compute.py"], "language": "python"})
    spec["outputs"] = [{"name": "result", "path": "results/result.json", "format": "json",
        "fields": [{"name": "sum", "type": "number", "unit": "1"}], "precision": 6}]
    write_json(root / "model_spec.json", spec)
    yield root
    for path in root.rglob("*"):
        if path.is_file():
            path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def run(root, **kwargs):
    return execute_model(root, "model_spec.json", interpreter=sys.executable, **kwargs)


def test_real_run_seed_environment_and_hashes(workspace, monkeypatch):
    monkeypatch.setenv("MATHMODE_TEST_SECRET", "fixture-not-a-real-secret")
    first, second = run(workspace), run(workspace)
    assert first["status"] == second["status"] == "PASS"
    assert first["scientific_acceptance"] == "NOT_RUN"
    assert first["run_id"] != second["run_id"]
    a = read_json(workspace / first["outputs"][0]["path"])
    b = read_json(workspace / second["outputs"][0]["path"])
    assert a == b
    assert a["sum"] == 12
    assert a["hash_seed"] == "42"
    assert not a["secret_forwarded"]
    assert Path(a["interpreter"]).resolve() == Path(sys.executable).resolve()
    for item in first["outputs"]:
        assert file_hash(workspace / item["path"]) == item["sha256"]
    assert first["capabilities"]["os_sandbox"] is False
    Draft202012Validator.check_schema(catalog()["run_manifest"])
    validate("run_manifest", first, root=workspace)
    verify_run(workspace, f"runs/{first['run_id']}/run_manifest.json")


@pytest.mark.parametrize("code,reason", [
    ("raise RuntimeError('deliberate failure')", "CODE_FAILURE"),
    ("print('PASS')", "VALIDATION_FAILURE"),
    ("import sys; print('PASS'); sys.exit(7)", "CODE_FAILURE"),
    ("import argparse,json,pathlib; p=argparse.ArgumentParser();p.add_argument('--context');c=json.loads(pathlib.Path(p.parse_args().context).read_text()); (pathlib.Path(c['output_dir'])/'results/result.json').write_text('{\"sum\":NaN}')", "VALIDATION_FAILURE"),
])
def test_exit_or_text_claims_do_not_establish_artifacts(workspace, code, reason):
    (workspace / "code/compute.py").write_text(code, encoding="utf-8")
    record = run(workspace)
    assert record["status"] == "FAIL"
    assert record["failure_class"] == reason
    assert (workspace / record["logs"]["stderr"]["path"]).exists()


def test_old_output_cannot_satisfy_a_fresh_run(workspace):
    first = run(workspace)
    (workspace / "code/compute.py").write_text("print('no output')", encoding="utf-8")
    second = run(workspace)
    assert first["status"] == "PASS" and second["status"] == "FAIL"
    assert second["outputs"] == []
    assert (workspace / first["outputs"][0]["path"]).is_file()


def test_timeout_is_recorded_with_real_returncode(workspace):
    (workspace / "code/compute.py").write_text("import time; time.sleep(30)", encoding="utf-8")
    spec = read_json(workspace / "model_spec.json")
    spec["limits"]["timeout_seconds"] = 0.5
    write_json(workspace / "model_spec.json", spec)
    record = run(workspace)
    assert record["timed_out"] and record["status"] == "FAIL"
    assert record["returncode"] != 0
    assert record["cause_id"] == "execution-timeout"
    assert record["duration_seconds"] < 15


def test_retries_require_changed_code_and_stop_at_three(workspace):
    (workspace / "code/compute.py").write_text("raise RuntimeError('failure 1')", encoding="utf-8")
    first = run(workspace)
    with pytest.raises(ValueError, match="explicit retry"):
        run(workspace)
    with pytest.raises(ValueError, match="recorded change"):
        run(workspace, retry_of=first["run_id"])
    previous = first
    for attempt in (2, 3):
        (workspace / "code/compute.py").write_text(f"raise RuntimeError('failure {attempt}')", encoding="utf-8")
        previous = run(workspace, retry_of=previous["run_id"])
        assert previous["attempt"] == attempt
    (workspace / "code/compute.py").write_text("raise RuntimeError('failure 4')", encoding="utf-8")
    with pytest.raises(ValueError, match="budget exhausted"):
        run(workspace, retry_of=previous["run_id"])


def test_input_snapshot_modification_is_detected(workspace):
    code = """import argparse,json,pathlib,stat
p=argparse.ArgumentParser();p.add_argument('--context')
c=json.loads(pathlib.Path(p.parse_args().context).read_text())
data=pathlib.Path(c['inputs']['data']);data.chmod(stat.S_IWRITE);data.write_text('{}')
(pathlib.Path(c['output_dir'])/'results/result.json').write_text('{"sum":12}')
"""
    (workspace / "code/compute.py").write_text(code, encoding="utf-8")
    record = run(workspace)
    assert record["status"] == "FAIL"
    assert "changed during execution" in record["failure_message"]


def test_unsupported_memory_limit_is_not_silently_ignored(workspace):
    spec = read_json(workspace / "model_spec.json")
    spec["limits"]["memory_mb"] = 256
    write_json(workspace / "model_spec.json", spec)
    with pytest.raises(ValueError, match="memory"):
        run(workspace)
    assert not (workspace / "runs").exists()


def test_no_shell_expansion_in_backend(tmp_path):
    result = LocalSubprocessBackend().execute([sys.executable, "-c", "import sys;print(sys.argv[1])", "$(echo should-not-run)"],
        cwd=tmp_path, environment={}, timeout=5, stdout=tmp_path / "stdout.txt", stderr=tmp_path / "stderr.txt")
    assert result.returncode == 0
    assert (tmp_path / "stdout.txt").read_text().strip() == "$(echo should-not-run)"


def test_verify_rejects_tampering_and_stale_code(workspace):
    record = run(workspace)
    relative = f"runs/{record['run_id']}/run_manifest.json"
    code = workspace / "code/compute.py"
    previous = code.read_bytes()
    code.write_bytes(previous + b"\n# modification\n")
    with pytest.raises(ValueError, match="stale"):
        verify_run(workspace, relative)
    code.write_bytes(previous)
    output = workspace / record["outputs"][0]["path"]
    output.write_text('{"sum":999}', encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_run(workspace, relative)


def test_verify_rejects_rewritten_success_claim(workspace):
    (workspace / "code/compute.py").write_text("raise RuntimeError('failure')", encoding="utf-8")
    record = run(workspace)
    relative = f"runs/{record['run_id']}/run_manifest.json"
    record["status"] = "PASS"
    write_json(workspace / relative, record)
    with pytest.raises(ValueError, match="contradicts"):
        verify_run(workspace, relative)


def test_interrupted_run_cannot_be_silently_skipped(workspace):
    pending = workspace / "runs/run-interrupted"
    pending.mkdir(parents=True)
    write_json(pending / "planned.json", {"run_id": "run-interrupted", "question_id": "Q1", "method_id": "affine-main", "role": "main"})
    with pytest.raises(ValueError, match="Interrupted run"):
        run(workspace)


@pytest.mark.parametrize("content,kind", [('{"sum":"wrong"}', "json"), ('{}', "json"),
    ('[]', "json"), ('sum\nNaN\n', "csv"), ('sum,sum\n1,2\n', "csv"), ('sum\n', "csv")])
def test_output_contract_rejects_wrong_shape_or_nonfinite(tmp_path, content, kind):
    path = tmp_path / f"result.{kind}"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        validate_output(path, {"format": kind, "fields": [{"name": "sum", "type": "number", "unit": "1"}]})
