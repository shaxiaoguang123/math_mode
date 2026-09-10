from pathlib import Path
import os
import subprocess
import sys
import time

import psutil
import pytest

from test_runner import workspace
from test_agents import task_root, FixtureBackend
from mathmode.agents import run_agent_task
from mathmode.io import read_json, write_json
from mathmode.processes import identity, stopped
from mathmode.recovery import recover_lock, recover_execution, verify_recovery
from mathmode.runner import execute_model
from mathmode.state import workspace_lock


def test_live_lock_and_legacy_lock_are_not_silently_stolen(tmp_path):
    with workspace_lock(tmp_path):
        assert read_json(tmp_path / ".mathmode.lock")["owner"] == identity()
        with pytest.raises(ValueError, match="still running"):
            recover_lock(tmp_path, reason="Test live owner refusal")
    (tmp_path / ".mathmode.lock").write_text("2026-09-08T00:00:00Z", encoding="utf-8")
    with pytest.raises(ValueError, match="Legacy lock"):
        recover_lock(tmp_path, reason="No identity in legacy lock")
    assert (tmp_path / ".mathmode.lock").exists()


def test_stopped_workflow_owner_requires_explicit_scoped_recovery(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    script = """import sys,time
from pathlib import Path
from mathmode.state import workspace_lock
from mathmode.io import write_json
root=Path(sys.argv[1])
with workspace_lock(root, scope='workflow'):
    write_json(root/'ready.json', {'ready':True})
    time.sleep(60)
"""
    process = subprocess.Popen([sys.executable, "-c", script, str(tmp_path)], cwd=repo,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    try:
        deadline = time.monotonic() + 15
        while not (tmp_path / "ready.json").exists() and time.monotonic() < deadline:
            assert process.poll() is None
            time.sleep(0.05)
        assert (tmp_path / "ready.json").exists()
        with pytest.raises(ValueError, match="still running"):
            recover_lock(tmp_path, scope="workflow", reason="Actual coordinator still alive")
        process.kill()
        process.wait(timeout=5)
        with pytest.raises(ValueError, match="Workspace is locked"):
            with workspace_lock(tmp_path, scope="workflow"):
                pytest.fail("Crash lock was silently stolen")
        result = recover_lock(tmp_path, scope="workflow", reason="Observed test coordinator exit")
        archive = read_json(tmp_path / result["archive"])
        assert archive["ownership"]["owner"]["pid"] == process.pid
        assert archive["lock_scope"] == "workflow"
        with workspace_lock(tmp_path, scope="workflow"):
            assert not (tmp_path / ".mathmode.lock").exists()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def test_real_interrupted_run_recovery_preserves_evidence_and_retry_budget(workspace):
    code = workspace / "code/compute.py"
    original = code.read_text(encoding="utf-8")
    code.write_text("import time, subprocess, sys, os\n"
                   "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], "
                   "creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)\n"
                   "time.sleep(60)\n" + original, encoding="utf-8")
    repo = Path(__file__).resolve().parents[1]
    script = "from pathlib import Path; from mathmode.runner import execute_model; import sys; execute_model(Path(sys.argv[1]), 'model_spec.json', interpreter=sys.executable)"
    process = subprocess.Popen([sys.executable, "-c", script, str(workspace)], cwd=repo,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    child = descendant = None
    try:
        deadline = time.monotonic() + 15
        observations = []
        while time.monotonic() < deadline:
            observations = list((workspace / "runs").glob("*/process.json"))
            if observations:
                for observed in read_json(observations[0]).get("descendants", []):
                    try:
                        candidate = psutil.Process(observed["pid"])
                        if "import time; time.sleep(60)" in candidate.cmdline():
                            descendant = candidate
                    except psutil.NoSuchProcess:
                        pass
                if descendant:
                    break
            if process.poll() is not None:
                pytest.fail("Runner unexpectedly terminated before interruption test")
            time.sleep(0.05)
        assert observations, "Runner did not record the actual child process"
        observation = read_json(observations[0])
        child = psutil.Process(observation["child"]["pid"])
        assert observation["descendants"], "Actual grandchild was not observed"
        assert descendant is not None, "The actual Python grandchild was not observed"
        run_id = observations[0].parent.name
        with pytest.raises(ValueError, match="owner is still running"):
            recover_execution(workspace, run_id, kind="run", reason="Owner alive")
        process.kill()
        process.wait(timeout=5)
        with pytest.raises(ValueError, match="process is still running"):
            recover_execution(workspace, run_id, kind="run", reason="Child still running")
        child.kill()
        try:
            child.wait(timeout=5)
        except psutil.TimeoutExpired:
            assert child.status() == psutil.STATUS_ZOMBIE
        with pytest.raises(ValueError, match="descendant process is still running"):
            recover_execution(workspace, run_id, kind="run", reason="Grandchild still running")
        descendant.kill()
        try:
            descendant.wait(timeout=5)
        except psutil.TimeoutExpired:
            assert descendant.status() == psutil.STATUS_ZOMBIE
        event = recover_execution(workspace, run_id, kind="run", reason="Actual owner and child terminated during crash test")
        assert event["status"] == "ABANDONED" and event["returncode"] is None
        assert not observations[0].with_name("run_manifest.json").exists()
        assert verify_recovery(workspace, f"runs/{run_id}") == event
        with pytest.raises(ValueError, match="explicit retry"):
            execute_model(workspace, "model_spec.json", interpreter=sys.executable)
        with pytest.raises(ValueError, match="recorded change"):
            execute_model(workspace, "model_spec.json", interpreter=sys.executable, retry_of=run_id)
        code.write_text(original, encoding="utf-8")
        rerun = execute_model(workspace, "model_spec.json", interpreter=sys.executable, retry_of=run_id)
        assert rerun["status"] == "PASS" and rerun["attempt"] == 2 and rerun["retry_of"] == run_id
        assert list((workspace / "recovery").glob("lock-*.json"))
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        for child in (child, descendant):
            if child is None:
                continue
            try:
                if child.is_running() and child.status() != psutil.STATUS_ZOMBIE:
                    child.kill()
                    child.wait(timeout=5)
            except psutil.NoSuchProcess:
                pass


def test_process_identity_does_not_treat_reused_pid_as_original_owner():
    actual = identity()
    assert not stopped(actual)
    assert stopped({**actual, "create_time": actual["create_time"] - 100})


def test_interrupted_agent_transport_recovery_keeps_attempt_history(task_root):
    root, task = task_root
    write_json(root / "task_request.json", task)
    script = '''
import sys
from pathlib import Path
from mathmode.agents import run_agent_task
from mathmode.agent_backends import AgentBackend
from mathmode.execution import LocalSubprocessBackend
from mathmode.runner import execution_environment
from mathmode.io import read_json
class WaitingTransport(AgentBackend):
    name = "interrupted-fixture-transport"
    reasoning_backend = False
    def produce(self, directory, *, timeout):
        LocalSubprocessBackend().execute([sys.executable, '-c', 'import time; time.sleep(60)'],
            cwd=directory, environment=execution_environment(0), timeout=60,
            stdout=directory/'events.jsonl', stderr=directory/'stderr.txt')
        raise RuntimeError('Interruption test did not interrupt')
root = Path(sys.argv[1])
run_agent_task(root, read_json(root/'task_request.json'), WaitingTransport())
'''
    parent = subprocess.Popen([sys.executable, "-c", script, str(root)], cwd=Path(__file__).resolve().parents[1],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    child = None
    path = root / "agent_runs" / task["task_id"] / "process.json"
    try:
        deadline = time.monotonic() + 15
        while not path.exists() and time.monotonic() < deadline:
            assert parent.poll() is None
            time.sleep(0.05)
        observed = read_json(path)
        child = psutil.Process(observed["child"]["pid"])
        parent.kill()
        parent.wait(timeout=5)
        child.kill()
        try:
            child.wait(timeout=5)
        except psutil.TimeoutExpired:
            assert child.status() == psutil.STATUS_ZOMBIE
        record = recover_execution(root, task["task_id"], kind="agent", reason="Interrupted actual fixture subprocess transport")
        assert record["status"] == "ABANDONED"
        assert not path.with_name("agent_result.json").exists()
        with pytest.raises(ValueError, match="reset.*retry budget"):
            run_agent_task(root, {**task, "task_id": "fresh-id"}, FixtureBackend())
        followup = {**task, "task_id": "recovered-retry", "attempt": 2, "supersedes_task_id": task["task_id"]}
        outcome = run_agent_task(root, followup, FixtureBackend())
        assert outcome["status"] == "PRODUCED", outcome
        assert not outcome["capabilities"]["reasoning_backend"]
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=5)
        if child:
            try:
                if child.is_running() and child.status() != psutil.STATUS_ZOMBIE:
                    child.kill()
                    child.wait(timeout=5)
            except psutil.NoSuchProcess:
                pass


def test_recovery_before_launch_differs_from_missing_identity_after_launch(task_root):
    root, task = task_root
    write_json(root / "task_request.json", task)
    script = "from pathlib import Path; import sys; from mathmode.agents import _reserve_task; from mathmode.io import read_json; root=Path(sys.argv[1]); _reserve_task(root, read_json(root/'task_request.json'))"
    completed = subprocess.run([sys.executable, "-c", script, str(root)], cwd=Path(__file__).resolve().parents[1],
                               capture_output=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    assert completed.returncode == 0
    folder = root / "agent_runs" / task["task_id"]
    # An observed launch with no PID is an ambiguous crash window, not stopped evidence.
    write_json(folder / "backend_started.json", {"at": "fixture launch marker"})
    with pytest.raises(ValueError, match="process exit cannot be inferred"):
        recover_execution(root, task["task_id"], kind="agent", reason="Ambiguous launch")
    (folder / "backend_started.json").unlink()
    event = recover_execution(root, task["task_id"], kind="agent", reason="Owner exited before backend dispatch")
    assert event["process_observation"] == "owner_stopped_execution_not_started"
