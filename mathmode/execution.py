"""Explicit execution backends. Local subprocess execution is not an OS sandbox."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import os
from pathlib import Path
import signal
import subprocess
import time


@dataclass(frozen=True)
class ExecutionResult:
    returncode: int | None
    timed_out: bool
    duration_seconds: float
    startup_error: str | None = None


class ExecutionBackend(ABC):
    name: str
    capabilities: dict

    @abstractmethod
    def execute(self, argv: list[str], *, cwd: Path, environment: dict[str, str],
                timeout: float, stdout: Path, stderr: Path) -> ExecutionResult:
        """Execute an explicit argv and preserve real process observations."""


class LocalSubprocessBackend(ExecutionBackend):
    name = "local_subprocess"
    capabilities = {"os_sandbox": False, "network_isolation": False,
        "filesystem_isolation": False, "memory_limit": False, "cpu_limit": False,
        "timeout": True, "process_tree_termination": "best_effort"}

    def execute(self, argv, *, cwd, environment, timeout, stdout, stderr):
        started = time.monotonic()
        timed_out = False
        with stdout.open("xb") as out, stderr.open("xb") as err:
            try:
                process = subprocess.Popen(argv, cwd=cwd, env=environment, shell=False,
                    stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                    start_new_session=os.name != "nt",
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            except OSError as exc:
                return ExecutionResult(None, False, time.monotonic() - started, str(exc))
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                if os.name == "nt":
                    killer = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/taskkill.exe"
                    try:
                        subprocess.run([str(killer), "/PID", str(process.pid), "/T", "/F"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
                            shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
                    except (OSError, subprocess.TimeoutExpired):
                        pass
                else:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=10)
        return ExecutionResult(process.returncode, timed_out, time.monotonic() - started)
