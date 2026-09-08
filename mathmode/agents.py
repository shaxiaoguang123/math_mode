"""Role-scoped input snapshots and validated publication of real agent proposals."""
from __future__ import annotations

import ast
from pathlib import Path
import shutil
import stat
import uuid
import tempfile
import time
from jsonschema import ValidationError

from .agent_backends import AgentBackend, AgentExecution
from .contracts import validate, unique, read_ledger, topological_order
from .io import canonical_root, file_hash, loads, now, read_json, safe_path, write_json, object_hash
from .lineage import ArtifactRegistry
from .roles import COMMON_INSTRUCTION, ROLES
from .schema_catalog import catalog
from .state import append_event, workspace_lock


def validate_task(task):
    validate("agent_task", task)
    role = ROLES[task["role"]]
    if task["role"] == "decision" and task["interaction_mode"] == "human_gate":
        raise ValueError("Human-gated decisions must come from an actual host user event")
    unique(task["inputs"], "artifact_id")
    unique(task["outputs"], "path")
    if {item["path"] for item in task["inputs"]} & {item["path"] for item in task["outputs"]}:
        raise ValueError("Agent output cannot overwrite an input artifact")
    if task["role"] in {"critic", "validator", "reviewer"} and (
            not task["reviewed_actor_id"] or task["reviewed_actor_id"] == task["actor_id"]):
        raise ValueError("Review tasks require a different actual producer identity")
    if (task["role"] == "council") != (task["view"] is not None):
        raise ValueError("Only council tasks have an explicit modeling view")
    if (task["attempt"] == 1) != (task["supersedes_task_id"] is None):
        raise ValueError("Agent retries require a predecessor task")
    for output in task["outputs"]:
        if not output["path"].startswith(role.prefixes):
            raise ValueError("Role cannot publish outside its allowed directories")
        if output["format"] in {"json", "jsonl"}:
            if output["contract"] not in role.contracts or output["contract"] not in catalog():
                raise ValueError("Role cannot produce this contract")
            if output["format"] == "jsonl" and output["contract"] not in {"assumption_ledger", "method_decision"}:
                raise ValueError("Only append-only event contracts may use JSONL outputs")
        elif output["format"] == "python":
            if not role.may_write_code or output["contract"] is not None or not output["path"].endswith(".py"):
                raise ValueError("Role cannot produce executable code")
        elif task["role"] != "writer" or output["contract"] is not None or not output["path"].endswith(".tex"):
            raise ValueError("Only the writer may propose TeX source")
    return task


def _check_response(task, response, root=None):
    validate("agent_response", response)
    if (response["task_id"], response["actor_id"]) != (task["task_id"], task["actor_id"]):
        raise ValueError("Agent response changed task/actor identity")
    if set(response["evidence_refs"]) - {item["artifact_id"] for item in task["inputs"]}:
        raise ValueError("Agent response cites evidence outside its input scope")
    if response["status"] == "BLOCKED":
        if not response["blockers"] or response["artifacts"]:
            raise ValueError("A blocked proposal requires blockers and cannot publish artifacts")
        return []
    if response["blockers"]:
        raise ValueError("Produced response cannot hide unresolved blockers")
    outputs = unique(task["outputs"], "path")
    produced = unique(response["artifacts"], "path")
    if outputs.keys() != produced.keys():
        raise ValueError("Agent must produce exactly the allowed output set")
    result = []
    for path, artifact in produced.items():
        declaration = outputs[path]
        content = artifact["content"]
        if declaration["format"] == "python":
            ast.parse(content, filename=path)
        elif declaration["format"] in {"json", "jsonl"}:
            values = [loads(line) for line in content.splitlines()] if declaration["format"] == "jsonl" else [loads(content)]
            if not values:
                raise ValueError("An event proposal cannot be empty")
            for value in values:
                validate(declaration["contract"], value)
                if "question_id" in value and value["question_id"] != task["question_id"]:
                    raise ValueError("Produced contract changed question identity")
                for key in ("actor_id", "producer", "reviewed_by"):
                    if key in value and value[key] != task["actor_id"]:
                        raise ValueError("Produced contract misattributes its actor")
                if declaration["contract"] == "method_card" and value["critic"]["actor_id"] != task["actor_id"]:
                    raise ValueError("Method critic attribution mismatch")
                if declaration["contract"] == "method_decision":
                    if task["interaction_mode"] == "autopilot" and value["decided_by"] != "agent":
                        raise ValueError("Autopilot cannot impersonate a human decision")
                    if value["decided_by"] == "human":
                        raise ValueError("Human decisions must enter through an actual host user event")
                if declaration["contract"] in {"semantic_review", "disposition_review"} and value["reviewed_actor_id"] != task["reviewed_actor_id"]:
                    raise ValueError("Review changed the reviewed producer identity")
                if declaration["contract"] in {"semantic_review", "method_proposal", "method_decision", "issue_disposition", "disposition_review"}:
                    refs = value.get("artifact_refs", []) + value.get("evidence_refs", [])
                    for finding in value.get("findings", []):
                        refs.extend(finding["evidence_refs"])
                    for item in value.get("items", []):
                        refs.extend(item["evidence_refs"])
                    if set(refs) - {item["artifact_id"] for item in task["inputs"]}:
                        raise ValueError("Produced contract cites evidence outside its input scope")
                if declaration["contract"] in {"issue_disposition", "disposition_review"}:
                    supplied = {item["path"]: item["sha256"] for item in task["inputs"]}
                    keys = ("source", "frame") if declaration["contract"] == "issue_disposition" else ("proposal",)
                    if any(supplied.get(value[key]["path"]) != value[key]["sha256"] for key in keys):
                        raise ValueError("Disposition pins must match actual supplied input snapshots")
                if declaration["contract"] == "method_proposal" and value["view"] != task["view"]:
                    raise ValueError("Proposal changed its council view")
                if declaration["contract"] == "method_sources":
                    if root is None:
                        raise ValueError("Method sources require actual reference access provenance")
                    from datetime import datetime
                    access = ArtifactRegistry(root).store.load()["reference_access"]
                    supplied = {item["path"]: item["sha256"] for item in task["inputs"]}
                    for source in value["sources"]:
                        if supplied.get(source["snapshot_path"]) != source["sha256"]:
                            raise ValueError("Method source snapshot must be in the actual input bundle")
                        if file_hash(safe_path(root, source["snapshot_path"])) != source["sha256"]:
                            raise ValueError("Method source snapshot hash changed")
                        admitted = [event for event in access if event["source"] == source["uri"]
                            and event["question_id"] == task["question_id"] and event["same_problem"] == source["same_problem"]
                            and datetime.fromisoformat(event["at"]) <= datetime.fromisoformat(task["created_at"])
                            and datetime.fromisoformat(event["at"]) <= datetime.fromisoformat(source["accessed_at"])]
                        if not admitted:
                            raise ValueError("Reference was not explicitly admitted before retrieval/task dispatch")
                        from .reference_baselines import verify_blind_admission
                        verify_blind_admission(root, admitted[0])
                        from urllib.parse import urlsplit
                        if urlsplit(source["uri"]).scheme in {"http", "https"} or source["snapshot_path"].startswith("references/") or "retrieval" in source:
                            from .reference_retrieval import verify_source_retrieval
                            verify_source_retrieval(root, source, question_id=task["question_id"], supplied=supplied,
                                                    task_created_at=task["created_at"])
        result.append((declaration, content))
    return result


def _reserve_task(root, task):
    """A fresh identifier or actor cannot restart an unresolved logical task."""
    with workspace_lock(root):
        history = {}
        runs = safe_path(root, "agent_runs", exists=False)
        if runs.exists():
            for directory in runs.iterdir():
                prior = validate_task(read_json(safe_path(root, f"agent_runs/{directory.name}/task.json")))
                if (prior["role"], prior["question_id"], prior["view"]) == (task["role"], task["question_id"], task["view"]):
                    history[prior["task_id"]] = prior
        superseded = {prior["supersedes_task_id"] for prior in history.values()}
        if task["role"] == "critic":
            def framing_signature(item):
                return object_hash({source["path"]: source["sha256"] for source in item["inputs"]
                    if source["path"] == "input_manifest.json" or source["path"].startswith(("framing/", "inputs/"))})
            signature = framing_signature(task)
            if sum(framing_signature(previous) == signature for previous in history.values()) >= 3:
                raise ValueError("Critic round budget exhausted; return to framing/assumptions before another loop")
        unresolved = []
        for key in history.keys() - superseded:
            path = safe_path(root, f"agent_runs/{key}/agent_result.json", exists=False)
            if not path.exists():
                if not path.with_name("recovery.json").exists():
                    raise ValueError("Interrupted agent task requires explicit recovery")
                from .recovery import verify_recovery
                result = verify_recovery(root, f"agent_runs/{key}")
            else:
                result = validate("agent_result", read_json(path), root=root)
            if result["status"] != "PRODUCED":
                unresolved.append(history[key])
        if unresolved:
            if len(unresolved) != 1:
                raise ValueError("Ambiguous unresolved agent retry history")
            previous = unresolved[0]
            if task["supersedes_task_id"] != previous["task_id"] or task["attempt"] != previous["attempt"] + 1:
                raise ValueError("Fresh task IDs cannot reset the unresolved retry budget")
        elif task["supersedes_task_id"] is not None or task["attempt"] != 1:
            raise ValueError("Retry has no current unresolved predecessor")
        directory = safe_path(root, f"agent_runs/{task['task_id']}", exists=False)
        directory.mkdir(parents=True, exist_ok=False)
        write_json(directory / "task.json", task, exclusive=True)
        from .processes import identity
        write_json(directory / "owner.json", {"owner": identity()}, exclusive=True)
    return directory


def run_agent_task(root: Path, task: dict, backend: AgentBackend, *, timeout=300) -> dict:
    root = canonical_root(root)
    validate_task(task)
    registry = ArtifactRegistry(root)
    freshness = registry.refresh()
    state = registry.store.load()
    registered = {a["artifact_id"]: a for a in state["artifacts"]}
    if not backend.reasoning_backend and state["workspace_kind"] != "fixture":
        raise ValueError("Test-double backends are only permitted in fixture workspaces")
    if state["interaction_mode"] != task["interaction_mode"]:
        raise ValueError("Agent task interaction mode differs from workspace")
    if task["interaction_mode"] == "human_gate" and task["role"] == "code":
        from .human_decisions import verify_human_decision
        choices = [item["path"] for item in task["inputs"] if item["path"].startswith("decisions/") and item["path"].endswith(".jsonl")]
        if len(choices) != 1 or verify_human_decision(root, choices[0])["question_id"] != task["question_id"]:
            raise ValueError("Code task requires its actual host human decision")
    for item in task["inputs"]:
        entry = registered.get(item["artifact_id"])
        if not entry or entry["status"] not in {"VALID", "FROZEN"} or item["artifact_id"] in freshness["stale"]:
            raise ValueError("Agent task requires registered fresh input artifacts")
        if entry["path"] != item["path"] or entry["sha256"] != item["sha256"] or file_hash(safe_path(root, item["path"])) != item["sha256"]:
            raise ValueError("Agent input reference/hash mismatch")
    if task["supersedes_task_id"]:
        previous_root = safe_path(root, f"agent_runs/{task['supersedes_task_id']}", exists=False)
        previous = read_json(previous_root / "task.json")
        if (previous_root / "agent_result.json").exists():
            outcome = read_json(previous_root / "agent_result.json")
        else:
            from .recovery import verify_recovery
            outcome = verify_recovery(root, previous_root.relative_to(root).as_posix())
        if outcome["status"] not in {"FAILED", "BLOCKED", "ABANDONED"} or task["attempt"] != previous["attempt"] + 1:
            raise ValueError("Agent retry does not continue a failed predecessor")
        if (task["role"], task["question_id"], task["view"]) != (previous["role"], previous["question_id"], previous["view"]):
            raise ValueError("Retry changed its logical task")
    directory = _reserve_task(root, task)
    write_json(directory / "response.schema.json", backend.response_schema(catalog()["agent_response"]), exclusive=True)
    schema_paths = []
    for output in task["outputs"]:
        if output["contract"]:
            path = directory / "schemas" / f"{output['contract']}.json"
            if not path.exists():
                write_json(path, catalog()[output["contract"]], exclusive=True)
                schema_paths.append(path)
    (directory / "AGENTS.md").write_text(COMMON_INSTRUCTION + "\n" + ROLES[task["role"]].instruction + "\n", encoding="utf-8")
    input_dir = directory / "inputs"
    input_dir.mkdir()
    input_snapshots = []
    input_map = []
    for item in task["inputs"]:
        source = safe_path(root, item["path"])
        target = input_dir / (item["artifact_id"] + source.suffix)
        shutil.copyfile(source, target)
        target.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        if file_hash(target) != item["sha256"]:
            raise ValueError("Input changed while preparing the agent bundle")
        input_snapshots.append((target, item["sha256"]))
        input_map.append({**item, "bundle_path": target.relative_to(directory).as_posix()})
    write_json(directory / "input_map.json", input_map, exclusive=True)
    controls = {path: file_hash(path) for path in [directory / "task.json", directory / "response.schema.json", directory / "AGENTS.md", directory / "input_map.json", *schema_paths]}
    write_json(directory / "backend_started.json", {"at": now(), "owner": read_json(directory / "owner.json")["owner"]}, exclusive=True)
    controls[directory / "owner.json"] = file_hash(directory / "owner.json")
    controls[directory / "backend_started.json"] = file_hash(directory / "backend_started.json")
    started = time.monotonic()
    try:
        execution = backend.produce(directory, timeout=timeout)
    except Exception as exc:
        # Backend exception strings can contain credentials; retain the type only.
        execution = AgentExecution(None, False, time.monotonic() - started,
            "unreported-by-backend", None, None, "Backend exception: " + type(exc).__name__)
    for name in ("events.jsonl", "stderr.txt"):
        if not (directory / name).exists():
            (directory / name).write_bytes(b"")
    blockers, published = [], []
    response_reference = None
    status = "FAILED"
    try:
        if execution.returncode != 0 or execution.timed_out or execution.error:
            raise ValueError(execution.error or "Reasoning backend failed or timed out")
        for path, digest in [*controls.items(), *input_snapshots]:
            if file_hash(path) != digest:
                raise ValueError("Reasoning backend modified its read-only input/control bundle")
        response_path = directory / "response.json"
        response = read_json(response_path)
        response_reference = {"path": response_path.relative_to(root).as_posix(), "sha256": file_hash(response_path)}
        proposed = _check_response(task, response, root)
        for item in task["inputs"]:
            if file_hash(safe_path(root, item["path"])) != item["sha256"]:
                raise ValueError("Canonical inputs changed while the agent was reasoning")
        # Prevalidate all outputs and frozen-consumer constraints before publishing any file.
        from .lineage import descendants, artifact_id
        graph = registry.store.load()["artifacts"]
        proposed_graph = {a["artifact_id"]: [dep["artifact_id"] for dep in a["depends_on"]] for a in graph}
        for declaration, _ in proposed:
            proposed_graph[artifact_id(declaration["path"])] = [item["artifact_id"] for item in task["inputs"]]
        topological_order(proposed_graph)
        active_freezes = set()
        index_path = safe_path(root, "frozen_numbers.json", exists=False)
        if index_path.exists():
            index = validate("freeze_index", read_json(index_path), root=root)
            active_freezes = {artifact_id(pointer["path"]) for pointer in index["questions"].values() if pointer["status"] == "FROZEN"}
        for declaration, _ in proposed:
            output = safe_path(root, declaration["path"], exists=False)
            affected = descendants(graph, {artifact_id(declaration["path"])})
            if output.exists() and (affected & active_freezes or any(a["status"] == "FROZEN" for a in graph if a["artifact_id"] in affected)):
                raise ValueError("Agent output affects a frozen consumer; explicit thaw is required")
        for declaration, content in proposed:
            if declaration["format"] == "jsonl":
                path = safe_path(root, declaration["path"], exists=False)
                previous = path.read_text(encoding="utf-8-sig") if path.exists() else ""
                with tempfile.TemporaryDirectory() as temporary:
                    candidate = Path(temporary) / "events.jsonl"
                    candidate.write_text(previous + content.rstrip() + "\n", encoding="utf-8")
                    read_ledger(candidate, declaration["contract"])
        for declaration, content in proposed:
            output = safe_path(root, declaration["path"], exists=False)
            output.parent.mkdir(parents=True, exist_ok=True)
            if declaration["format"] == "jsonl":
                for line in content.splitlines():
                    append_event(root, declaration["path"], loads(line), contract=declaration["contract"])
            else:
                # Canonical artifact writes are atomic; graph publication occurs only after all validation.
                from .io import write_bytes
                write_bytes(output, content.encode("utf-8"))
        with registry.batch():
            for declaration, _ in proposed:
                key = registry.register(declaration["path"], producer=task["actor_id"], dependencies=[item["artifact_id"] for item in task["inputs"]])
                published.append({"artifact_id": key, "path": declaration["path"], "sha256": file_hash(root / declaration["path"])})
        status = response["status"]
        blockers = response["blockers"]
    except (ValueError, OSError, SyntaxError, ValidationError) as exc:
        blockers.append(str(exc))
    result = {"schema_version": "2.0", "task_id": task["task_id"], "actor_id": task["actor_id"], "role": task["role"],
        "created_at": now(), "backend": backend.name, "provider": execution.provider, "model": execution.model,
        "session_id": execution.session_id, "status": status, "request_sha256": controls[directory / "task.json"],
        "response": response_reference, "artifacts": published,
        "events": {"path": (directory / "events.jsonl").relative_to(root).as_posix(), "sha256": file_hash(directory / "events.jsonl")},
        "stderr": {"path": (directory / "stderr.txt").relative_to(root).as_posix(), "sha256": file_hash(directory / "stderr.txt")},
        "returncode": execution.returncode, "timed_out": execution.timed_out, "duration_seconds": execution.duration_seconds,
        "blockers": blockers, "capabilities": {"scoped_input_bundle": True, "validated_output_publication": True,
            "os_read_isolation": False, "reasoning_backend": backend.reasoning_backend}}
    result["bundle"] = [{"path": path.relative_to(root).as_posix(), "sha256": digest}
                        for path, digest in [*controls.items(), *input_snapshots]]
    validate("agent_result", result, root=root)
    write_json(directory / "agent_result.json", result, exclusive=True)
    # Register immutable transport evidence separately from canonical outputs.
    # Failed/tampered bundles remain inspectable but cannot satisfy a handoff.
    with registry.batch():
        proof_ids = [registry.register((directory / name).relative_to(root).as_posix(), producer="agent-runtime")
                     for name in ("task.json", "events.jsonl", "stderr.txt")]
        if response_reference:
            proof_ids.append(registry.register(response_reference["path"], producer="agent-runtime"))
        registry.register((directory / "agent_result.json").relative_to(root).as_posix(),
            producer="agent-runtime", dependencies=proof_ids)
    append_event(root, "ai_usage.jsonl", {"schema_version": "2.0", "event_id": "ai-" + uuid.uuid4().hex,
        "timestamp": now(), "provider": execution.provider, "model": execution.model or "unreported-by-backend",
        "version_date": None, "question_id": task["question_id"], "activity": ROLES[task["role"]].activity,
        "input_scope": [item["artifact_id"] for item in task["inputs"]], "output_used": status == "PRODUCED",
        "human_postprocess": None, "artifact_refs": [item["artifact_id"] for item in published], "actor_id": task["actor_id"]}, contract="ai_usage")
    return result


def verify_agent_result(root: Path, task_id: str, *, require_reasoning=True) -> dict:
    """Recheck a handoff against registered transport and current canonical inputs."""
    root = canonical_root(root)
    directory = safe_path(root, f"agent_runs/{task_id}", exists=False)
    result_path = (directory / "agent_result.json").relative_to(root).as_posix()
    result = validate("agent_result", read_json(root / result_path), root=root)
    task = validate_task(read_json(directory / "task.json"))
    if (result["task_id"], result["actor_id"], result["role"]) != (task_id, task["actor_id"], task["role"]):
        raise ValueError("Agent result identity differs from its task")
    if result["status"] != "PRODUCED" or result["returncode"] != 0 or result["timed_out"] or result["blockers"]:
        raise ValueError("Agent handoff requires a successfully produced result")
    if require_reasoning and (not result["capabilities"]["reasoning_backend"] or not result["session_id"]):
        raise ValueError("Reasoning handoff requires an actual backend session; test doubles cannot pass")
    if not result.get("bundle") or not result["response"]:
        raise ValueError("Agent handoff has no verifiable input/control bundle")
    registry = ArtifactRegistry(root)
    freshness = registry.store.inspect_freshness()
    registered = {a["path"]: a for a in registry.store.load()["artifacts"]}
    references = [{"path": result_path, "sha256": file_hash(root / result_path)},
                  {"path": (directory / "task.json").relative_to(root).as_posix(), "sha256": result["request_sha256"]},
                  result["response"], result["events"], result["stderr"], *task["inputs"], *result["artifacts"]]
    for reference in references:
        entry = registered.get(reference["path"])
        if not entry or entry["artifact_id"] in freshness["stale"] or entry["sha256"] != reference["sha256"]:
            raise ValueError("Agent handoff has stale or unregistered provenance")
        if file_hash(safe_path(root, reference["path"])) != reference["sha256"]:
            raise ValueError("Agent handoff hash mismatch")
    for reference in result["bundle"]:
        if file_hash(safe_path(root, reference["path"])) != reference["sha256"]:
            raise ValueError("Agent input/control bundle changed")
    response = read_json(root / result["response"]["path"])
    _check_response(task, response, root)
    if response["status"] != "PRODUCED" or {a["path"] for a in result["artifacts"]} != {a["path"] for a in response["artifacts"]}:
        raise ValueError("Agent result disagrees with its actual response")
    return result
