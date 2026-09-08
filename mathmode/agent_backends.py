"""Reasoning backends produce proposals; the parent owns canonical publication."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from copy import deepcopy
import os
from pathlib import Path
import shutil

from .execution import LocalSubprocessBackend
from .io import loads
from .runner import execution_environment


@dataclass(frozen=True)
class AgentExecution:
    returncode: int | None
    timed_out: bool
    duration_seconds: float
    provider: str
    model: str | None
    session_id: str | None
    error: str | None = None


class AgentBackend(ABC):
    name: str
    reasoning_backend = True

    def response_schema(self, definition: dict) -> dict:
        return definition

    @abstractmethod
    def produce(self, directory: Path, *, timeout: float) -> AgentExecution:
        """Read task/bundle and write response.json, events.jsonl, stderr.txt."""


def codex_command() -> list[str]:
    executable = shutil.which("codex")
    if not executable:
        raise ValueError("Codex CLI is not installed or not on PATH")
    path = Path(executable)
    if os.name == "nt" and path.suffix.lower() in {".cmd", ".bat", ".ps1"}:
        launcher = path.parent / "node_modules/@openai/codex/bin/codex.js"
        node = shutil.which("node")
        if not node or not launcher.is_file():
            raise ValueError("Use an explicit native Codex executable; shell wrappers are not executed")
        return [node, str(launcher)]
    return [str(path)]


class CodexCliBackend(AgentBackend):
    name = "codex_cli"

    def __init__(self, command=None, model=None):
        self.command = command or codex_command()
        self.model = model

    def response_schema(self, definition):
        result = deepcopy(definition)
        def typed(node):
            if isinstance(node, dict):
                # Provider regex/array subsets differ from full Draft 2020-12.
                # Canonical parent validation still enforces these restrictions.
                node.pop("pattern", None)
                node.pop("uniqueItems", None)
                if "const" in node:
                    node["enum"] = [node.pop("const")]
                if "enum" in node and "type" not in node:
                    values = node["enum"]
                    if all(isinstance(value, str) for value in values):
                        node["type"] = "string"
                    elif all(isinstance(value, bool) for value in values):
                        node["type"] = "boolean"
                    else:
                        raise ValueError("Provider schema enum requires an explicit supported type")
                for value in node.values():
                    typed(value)
            elif isinstance(node, list):
                for value in node:
                    typed(value)
        typed(result)
        return result

    def produce(self, directory, *, timeout):
        # Preserve explicit user CLI configuration/authentication; no provider token is logged.
        environment = execution_environment(0)
        for key in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "CODEX_HOME", "CODEX_API_KEY"):
            if key in os.environ:
                environment[key] = os.environ[key]
        argv = [*self.command, "exec", "--json", "--ephemeral", "--sandbox", "read-only",
            "--skip-git-repo-check", "--color", "never", "--cd", str(directory),
            "--output-schema", str(directory / "response.schema.json"),
            "--output-last-message", str(directory / "response.json")]
        if self.model:
            argv.extend(["--model", self.model])
        argv.append("Read AGENTS.md, task.json and input_map.json together; then batch-read only the supplied input snapshots and required schemas. Explicitly supplied historical log snapshots are evidence. Return the structured proposal. Do not read this task's own execution logs/transcripts, modify files or invoke other agents.")
        execution = LocalSubprocessBackend().execute(argv, cwd=directory, environment=environment,
            timeout=timeout, stdout=directory / "events.jsonl", stderr=directory / "stderr.txt")
        session_id = None
        error = execution.startup_error
        if (directory / "events.jsonl").exists():
            for line in (directory / "events.jsonl").read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    event = loads(line)
                except ValueError:
                    continue
                if event.get("type") == "thread.started":
                    session_id = event.get("thread_id")
                if event.get("type") == "turn.failed":
                    error = str(event.get("error", {}).get("message", "Codex turn failed"))
        return AgentExecution(execution.returncode, execution.timed_out, execution.duration_seconds,
            "codex-configured-provider", self.model, session_id, error)
