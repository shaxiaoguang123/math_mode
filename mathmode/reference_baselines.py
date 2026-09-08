"""Historical question checkpoints and a complete-case blind reference boundary."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import stat
import uuid

from .contracts import validate
from .freeze import verify_freeze
from .io import canonical_root, file_hash, now, read_json, safe_path, write_json
from .lineage import ArtifactRegistry, artifact_id
from .state import StateStore


def baseline_path(baseline_id):
    if not isinstance(baseline_id, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,95}", baseline_id):
        raise ValueError("Invalid reference baseline identifier")
    return f"reference_baselines/{baseline_id}.json"


def _registered(root, relative, state, freshness, dependencies):
    entry = next((item for item in state["artifacts"] if item["path"] == relative), None)
    if (not entry or entry["producer"] != "blind-baseline-service"
            or entry["artifact_id"] in freshness["stale"]
            or entry["sha256"] != file_hash(safe_path(root, relative))):
        raise ValueError("Reference baseline is stale or unregistered")
    if {item["artifact_id"]: item["sha256"] for item in entry["depends_on"]} != dependencies:
        raise ValueError("Reference baseline lost required snapshot dependencies")


def _question(root, baseline_id, state, freshness):
    relative = baseline_path(baseline_id)
    value = validate("reference_baseline", read_json(safe_path(root, relative)), root=root)
    if (value["baseline_id"], value["case_id"]) != (baseline_id, state["case_id"]):
        raise ValueError("Reference baseline identity differs from workspace")
    items = [item for group in value["artifacts"].values() for item in group]
    _registered(root, relative, state, freshness, {artifact_id(item["path"]): item["sha256"] for item in items})
    for group, records in value["artifacts"].items():
        if len({item["source_path"] for item in records}) != len(records):
            raise ValueError("Reference baseline has duplicate source snapshots")
        for item in records:
            if item["path"] != f"reference_baselines/{baseline_id}/snapshot/{group}/{item['source_path']}":
                raise ValueError("Reference baseline snapshot is misplaced")
            if file_hash(safe_path(root, item["path"])) != item["sha256"]:
                raise ValueError("Immutable reference baseline snapshot changed")
    if len(value["artifacts"]["frame"]) != 1:
        raise ValueError("Reference baseline requires exactly one complete frame")
    frame_item = value["artifacts"]["frame"][0]
    frame = validate("problem_frame", read_json(safe_path(root, frame_item["path"])), root=root)
    questions = {item["question_id"] for item in frame["questions"]}
    if frame["case_id"] != value["case_id"] or value["question_id"] not in questions:
        raise ValueError("Reference baseline frame has a different case/question identity")
    results = {item["source_path"]: item for item in value["artifacts"]["results"]}
    frozen_item = results.get(f"freezes/{value['freeze_id']}/frozen_numbers.json")
    if not frozen_item:
        raise ValueError("Reference baseline has no frozen result snapshot")
    frozen = validate("frozen_numbers", read_json(safe_path(root, frozen_item["path"])), root=root)
    if (frozen["freeze_id"], frozen["question_id"]) != (value["freeze_id"], value["question_id"]):
        raise ValueError("Reference baseline frozen question differs")
    originals = set()
    for ref, roles in ((frozen["main_run"], {"main", "fallback"}), (frozen["baseline_run"], {"baseline"})):
        item = results.get(ref["path"])
        if not item or item["sha256"] != ref["sha256"]:
            raise ValueError("Reference baseline lost a frozen execution")
        run = validate("run_manifest", read_json(safe_path(root, item["path"])), root=root)
        if run["question_id"] != value["question_id"] or run["role"] not in roles or run["status"] != "PASS":
            raise ValueError("Reference baseline execution identity differs")
        originals.add(run["input_manifest_sha256"])
    if len(originals) != 1:
        raise ValueError("Reference baseline executions used different original inputs")
    return value, {"questions": questions, "frame": frame_item, "input_manifest_sha256": originals.pop()}


def verify_baseline(root: Path, baseline_id: str) -> dict:
    """Check immutable history, without requiring reference-informed sources to stay unchanged.

    Question checkpoints remain readable for historical diagnosis; admission uses
    verify_blind_admission to require complete coverage before using one.
    """
    root = canonical_root(root)
    store = StateStore(root)
    state, freshness = store.load(), store.inspect_freshness()
    relative = baseline_path(baseline_id)
    value = read_json(safe_path(root, relative))
    if value.get("scope") != "host_observed_all_question_pre_reference_baseline":
        return _question(root, baseline_id, state, freshness)[0]
    validate("reference_case_baseline", value, root=root)
    if (value["baseline_id"], value["case_id"]) != (baseline_id, state["case_id"]):
        raise ValueError("Reference case baseline identity differs from workspace")
    _registered(root, relative, state, freshness,
        {artifact_id(item["path"]): item["sha256"] for item in value["baselines"]})
    for ref in value["baselines"]:
        if ref["path"] != baseline_path(ref["baseline_id"]) or file_hash(safe_path(root, ref["path"])) != ref["sha256"]:
            raise ValueError("Reference case baseline changed a question checkpoint")
        checkpoint, info = _question(root, ref["baseline_id"], state, freshness)
        if (checkpoint["question_id"], checkpoint["freeze_id"]) != (ref["question_id"], ref["freeze_id"]):
            raise ValueError("Reference case baseline changed a question/freeze identity")
        if (info["questions"] != set(value["question_ids"]) or info["frame"]["sha256"] != value["frame_sha256"]
                or info["input_manifest_sha256"] != value["input_manifest_sha256"]):
            raise ValueError("Case baseline mixes different frames or original inputs")
        if datetime.fromisoformat(checkpoint["created_at"]) > datetime.fromisoformat(value["created_at"]):
            raise ValueError("Case checkpoint predates its question baseline")
    return value


def seal_case_baseline(root: Path, baseline_ids: list[str]) -> dict:
    """Bind every framed question's actual blind checkpoint before any case exposure."""
    root = canonical_root(root)
    store = StateStore(root)
    state, freshness = store.load(), store.inspect_freshness()
    if not state["blind_reference_mode"] or any(event["same_problem"] for event in state["reference_access"]):
        raise ValueError("A pre-reference baseline cannot be reconstructed after reference admission")
    if not baseline_ids or len(set(baseline_ids)) != len(baseline_ids):
        raise ValueError("Case baseline needs unique question checkpoint IDs")
    checkpoints = [_question(root, key, state, freshness) for key in baseline_ids]
    first = checkpoints[0][1]
    questions = [item[0]["question_id"] for item in checkpoints]
    if len(set(questions)) != len(questions) or set(questions) != first["questions"]:
        raise ValueError("Case baseline must cover exactly all framed questions")
    for checkpoint, info in checkpoints:
        if (info["questions"] != first["questions"] or info["frame"]["sha256"] != first["frame"]["sha256"]
                or info["input_manifest_sha256"] != first["input_manifest_sha256"]):
            raise ValueError("Case baseline mixes different frames or original inputs")
        if verify_freeze(root, checkpoint["question_id"])["freeze_id"] != checkpoint["freeze_id"]:
            raise ValueError("Case baseline must seal current independent question freezes")
    if (file_hash(safe_path(root, first["frame"]["source_path"])) != first["frame"]["sha256"]
            or file_hash(safe_path(root, "input_manifest.json")) != first["input_manifest_sha256"]):
        raise ValueError("Case baseline frame or original inputs changed before sealing")
    baseline_id = "blind-case-" + uuid.uuid4().hex
    value = {"schema_version": "2.0", "baseline_id": baseline_id, "case_id": state["case_id"], "created_at": now(),
        "question_ids": sorted(questions), "frame_sha256": first["frame"]["sha256"],
        "input_manifest_sha256": first["input_manifest_sha256"],
        "baselines": [{"question_id": item["question_id"], "baseline_id": item["baseline_id"],
            "freeze_id": item["freeze_id"], "path": baseline_path(item["baseline_id"]),
            "sha256": file_hash(safe_path(root, baseline_path(item["baseline_id"])))}
            for item, _ in sorted(checkpoints, key=lambda pair: pair[0]["question_id"])],
        "scope": "host_observed_all_question_pre_reference_baseline", "paper_acceptance": "NOT_RUN"}
    validate("reference_case_baseline", value, root=root)
    relative = baseline_path(baseline_id)
    def publish(current):
        if any(event["same_problem"] for event in current["reference_access"]):
            raise ValueError("Reference admission raced with case baseline sealing")
        write_json(safe_path(root, relative, exists=False), value, exclusive=True)
        safe_path(root, relative).chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    store.update(publish, expected_revision=state["revision"])
    ArtifactRegistry(root).register(relative, producer="blind-baseline-service",
        dependencies=[artifact_id(item["path"]) for item in value["baselines"]])
    verify_baseline(root, baseline_id)
    return value


def verify_blind_admission(root: Path, event: dict) -> dict | None:
    """Revalidate both HTTP and local-source admission; old partial cases fail closed."""
    root = canonical_root(root)
    store = StateStore(root)
    state = store.load()
    if event.get("blind_reference_mode", True) != state["blind_reference_mode"]:
        raise ValueError("Reference admission mode differs from the workspace")
    required = event["same_problem"] and state["blind_reference_mode"]
    baseline_id = event["baseline_freeze_id"]
    if not required:
        if baseline_id is not None:
            raise ValueError("General or non-blind references cannot claim a blind baseline")
        return None
    if not baseline_id:
        raise ValueError("Same-problem reference access requires a sealed blind baseline")
    value = verify_baseline(root, baseline_id)
    if "baselines" in value:
        questions = set(value["question_ids"])
    else:
        _, info = _question(root, baseline_id, state, store.inspect_freshness())
        questions = info["questions"]
        if questions != {value["question_id"]}:
            raise ValueError("Same-problem access requires an all-question case baseline")
    if event["question_id"] not in questions:
        raise ValueError("Reference baseline identity differs from requested access")
    if not any(item["same_problem"] for item in state["reference_access"]):
        checkpoint_id = value["baselines"][0]["baseline_id"] if "baselines" in value else baseline_id
        _, info = _question(root, checkpoint_id, state, store.inspect_freshness())
        if (file_hash(safe_path(root, info["frame"]["source_path"])) != info["frame"]["sha256"]
                or file_hash(safe_path(root, "input_manifest.json")) != info["input_manifest_sha256"]):
            raise ValueError("Blind admission frame or original inputs changed since checkpoint")
    # Any admitted same-case content may expose all questions. Historical partial
    # admissions cannot be followed by a new checkpoint claiming restored blindness.
    first_access = min([event["at"], *[item["at"] for item in state["reference_access"] if item["same_problem"]]],
                       key=datetime.fromisoformat)
    if datetime.fromisoformat(value["created_at"]) > datetime.fromisoformat(first_access):
        raise ValueError("Blind baseline was created after case reference exposure")
    return value
