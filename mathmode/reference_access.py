"""Explicit reference-blind baseline sealing and append-only access admission."""
from __future__ import annotations

from pathlib import Path
import stat
import uuid

from .agents import verify_agent_result
from .contracts import validate
from .freeze import verify_freeze
from .io import canonical_root, file_hash, now, read_json, safe_path, write_json, write_bytes
from .lineage import ArtifactRegistry
from .runner import verify_run
from .state import StateStore


def _role_artifacts(root, task_id, role):
    result = verify_agent_result(root, task_id)
    if result["role"] != role:
        raise ValueError("Blind baseline needs the actual designated producer")
    return {item["path"]: item for item in result["artifacts"]}


def seal_baseline(root: Path, question_id: str, *, framer_task: str, frame_path: str,
                  writer_task: str, paper_paths: list[str]) -> dict:
    """Freeze the pre-reference frame, executed models/code/results and draft paper.

    This is a blindness checkpoint, not final paper or official-policy approval.
    It cannot reconstruct whether a user read references outside this host.
    """
    root = canonical_root(root)
    store = StateStore(root)
    state = store.load()
    if not state["blind_reference_mode"] or any(event["same_problem"] and event["question_id"] == question_id
                                               for event in state["reference_access"]):
        raise ValueError("A pre-reference baseline cannot be reconstructed after reference admission")
    frame_outputs = _role_artifacts(root, framer_task, "framer")
    if frame_path not in frame_outputs:
        raise ValueError("Frame was not produced by the recorded framer")
    frame = validate("problem_frame", read_json(safe_path(root, frame_path)), root=root)
    if frame["case_id"] != state["case_id"] or question_id not in {q["question_id"] for q in frame["questions"]}:
        raise ValueError("Blind frame has a different case/question identity")
    papers = _role_artifacts(root, writer_task, "writer")
    writer = read_json(safe_path(root, f"agent_runs/{writer_task}/task.json"))
    if writer["question_id"] not in {None, question_id}:
        raise ValueError("Baseline paper belongs to another question")
    if not paper_paths or len(set(paper_paths)) != len(paper_paths) or set(paper_paths) - papers.keys():
        raise ValueError("Blind baseline needs actual writer-produced paper source")
    if any(not path.endswith(".tex") for path in paper_paths):
        raise ValueError("Baseline paper source must be TeX")
    freeze = verify_freeze(root, question_id)
    paths = {"frame": [frame_path], "models": [], "code": [], "results": [], "paper": paper_paths}
    for reference in (freeze["main_run"], freeze["baseline_run"]):
        record = verify_run(root, reference["path"])
        paths["models"].append(record["spec"]["source_path"])
        paths["code"].extend(item["source_path"] for item in record["code"])
        paths["results"].extend(item["path"] for item in record["outputs"])
        paths["results"].append(reference["path"])
    paths["results"].extend([freeze["validation"]["path"], f"freezes/{freeze['freeze_id']}/frozen_numbers.json"])
    baseline_id = "blind-" + uuid.uuid4().hex
    checkpoint = {"schema_version": "2.0", "baseline_id": baseline_id, "case_id": state["case_id"],
        "question_id": question_id, "freeze_id": freeze["freeze_id"], "created_at": now(),
        "framer_task": framer_task, "writer_task": writer_task,
        "artifacts": {group: [{"source_path": path, "path": f"reference_baselines/{baseline_id}/snapshot/{group}/{path}",
                               "sha256": file_hash(safe_path(root, path))} for path in sorted(set(values))]
                      for group, values in paths.items()},
        "scope": "host_observed_pre_reference_baseline", "paper_acceptance": "NOT_RUN"}
    validate("reference_baseline", checkpoint, root=root)
    relative = f"reference_baselines/{baseline_id}.json"
    registry = ArtifactRegistry(root)
    revision = store.load()["revision"]
    def publish(current):
        if not current["blind_reference_mode"] or any(event["same_problem"] and event["question_id"] == question_id
                                                      for event in current["reference_access"]):
            raise ValueError("Reference admission raced with baseline sealing")
        for items in checkpoint["artifacts"].values():
            for item in items:
                if file_hash(safe_path(root, item["source_path"])) != item["sha256"]:
                    raise ValueError("Baseline source changed during sealing")
        for items in checkpoint["artifacts"].values():
            for item in items:
                target = safe_path(root, item["path"], exists=False)
                write_bytes(target, safe_path(root, item["source_path"]).read_bytes(), exclusive=True)
                if file_hash(target) != item["sha256"]:
                    raise ValueError("Baseline changed during snapshot copy")
                target.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        destination = safe_path(root, relative, exists=False)
        write_json(destination, checkpoint, exclusive=True)
        destination.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    store.update(publish, expected_revision=revision)
    # Checkpoint integrity depends on immutable historical copies, so subsequent
    # reference-informed canonical revisions cannot erase the blind baseline.
    with registry.batch():
        dependencies = [registry.register(item["path"], producer="blind-baseline-service")
                        for items in checkpoint["artifacts"].values() for item in items]
        registry.register(relative, producer="blind-baseline-service", dependencies=dependencies)
    return checkpoint


def admit_reference(root: Path, *, source: str, question_id: str, same_problem: bool,
                    baseline_id: str | None = None) -> dict:
    """Record admission before the caller retrieves any same-problem content."""
    root = canonical_root(root)
    store = StateStore(root)
    state = store.load()
    if type(same_problem) is not bool or not isinstance(source, str) or not source.strip():
        raise ValueError("Reference admission requires an explicit source and classification")
    if same_problem:
        if not baseline_id:
            raise ValueError("Same-problem reference access requires a sealed blind baseline")
        relative = f"reference_baselines/{baseline_id}.json"
        baseline = validate("reference_baseline", read_json(safe_path(root, relative)), root=root)
        registered = {item["path"]: item for item in state["artifacts"]}
        entry = registered.get(relative)
        freshness = store.inspect_freshness()
        if not entry or entry["artifact_id"] in freshness["stale"] or entry["sha256"] != file_hash(root / relative):
            raise ValueError("Reference baseline is stale or unregistered")
        if (baseline["baseline_id"], baseline["question_id"], baseline["case_id"]) != (baseline_id, question_id, state["case_id"]):
            raise ValueError("Reference baseline identity differs from requested access")
        for items in baseline["artifacts"].values():
            for item in items:
                if file_hash(safe_path(root, item["path"])) != item["sha256"]:
                    raise ValueError("Immutable reference baseline snapshot changed")
    elif baseline_id is not None:
        raise ValueError("General method references do not claim a same-problem baseline")
    event = {"source": source, "question_id": question_id, "same_problem": same_problem,
             "at": now(), "baseline_freeze_id": baseline_id}
    store.update(lambda current: current["reference_access"].append(event), expected_revision=state["revision"])
    return {"status": "PASS", "scope": "reference_access_admission", "event": event,
            "external_read_performed": False, "outside_host_blindness": "UNVERIFIABLE"}
