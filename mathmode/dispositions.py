"""Independently reviewed restrictions; warnings are never promoted to PASS."""
from __future__ import annotations

from pathlib import Path

from .contracts import validate, unique
from .io import canonical_root, file_hash, safe_path, object_hash
from .lineage import ArtifactRegistry, artifact_id


def pin(root, relative):
    return {"path": relative, "sha256": file_hash(safe_path(root, relative))}


def _contract(root, path, name):
    # Deferred import avoids the orchestrator/freeze cycle. This checks a real
    # successful role execution, not just a well-shaped authored JSON document.
    from .orchestrator import Orchestrator
    kind, value = Orchestrator(root, None)._kind(path)
    if kind != name:
        raise ValueError(f"Disposition requires a current {name} handoff: {path}")
    return value


def issues(source_kind, source, frame):
    """Stable locators are meaningful only together with the exact source hash."""
    questions = unique(frame["questions"], "question_id")
    result = {}
    if source_kind == "data_audit":
        if source["status"] != "WARN" or any(i["severity"] == "error" for i in source["issues"]):
            raise ValueError("Only warning audits admit limited continuation; errors require repair")
        for index, item in enumerate(source["issues"]):
            affected = {qid for qid, q in questions.items() if item["input_id"] in q["inputs"]}
            # Problem/rule attachments may constrain all questions without being
            # numerical inputs. Conservatively retain their limits case-wide.
            result[f"/issues/{index}"] = (item["message"], affected or set(questions))
    else:
        if source["verdict"] != "LIMITED" or any(i["severity"] == "error" for i in source["findings"]):
            raise ValueError("Only LIMITED reviews admit dispositions; BLOCKED/errors require repair")
        if source["question_id"] not in questions:
            raise ValueError("Disposition source references an unknown question")
        affected = {source["question_id"]}
        for index, finding in enumerate(source["findings"]):
            if finding["severity"] == "warning":
                result[f"/findings/{index}"] = (finding["issue"], affected)
        for index, limitation in enumerate(source["limitations"]):
            result[f"/limitations/{index}"] = (limitation, affected)
    if not result:
        raise ValueError("Disposition has no actual unresolved warnings or limitations")
    return result


def verify_disposition(root: Path, binding: dict, *, question_id=None, frame_path=None):
    """Return derived restrictions and dependencies from fresh independent work."""
    root = canonical_root(root)
    if set(binding) != {"source", "proposal", "review"}:
        raise ValueError("Disposition requires source, proposal and independent review")
    # Accept plan paths or immutable freeze pins; never silently refresh a pin.
    pins = {key: pin(root, value if isinstance(value, str) else value["path"]) for key, value in binding.items()}
    if any(not isinstance(binding[key], str) and binding[key] != value for key, value in pins.items()):
        raise ValueError("Disposition source/proposal/review hash changed")
    proposal = _contract(root, pins["proposal"]["path"], "issue_disposition")
    review = _contract(root, pins["review"]["path"], "disposition_review")
    if proposal["source"] != pins["source"] or review["proposal"] != pins["proposal"]:
        raise ValueError("Disposition does not pin its actual source/proposal")
    if frame_path is not None and proposal["frame"]["path"] != frame_path:
        raise ValueError("Disposition uses a different problem frame")
    if pin(root, proposal["frame"]["path"]) != proposal["frame"]:
        raise ValueError("Disposition problem frame hash changed")
    frame = _contract(root, proposal["frame"]["path"], "problem_frame")
    source = _contract(root, pins["source"]["path"], proposal["source_kind"])
    if proposal["source_kind"] == "data_audit" and pins["source"]["path"] != "framing/deterministic_data_audit.json":
        raise ValueError("Data disposition must bind the actual deterministic audit")
    expected_scope = None if proposal["source_kind"] == "data_audit" else source["question_id"]
    if proposal["question_id"] != expected_scope or review["question_id"] != expected_scope:
        raise ValueError("Disposition changed the source question scope")
    if review["reviewed_actor_id"] != proposal["actor_id"] or review["actor_id"] in {
            proposal["actor_id"], source["actor_id"], source.get("reviewed_actor_id")}:
        raise ValueError("Disposition needs an independent reviewer distinct from authors and original reviewer")
    if review["verdict"] != "LIMITED":
        raise ValueError("Independent disposition review blocks continuation")
    pending = issues(proposal["source_kind"], source, frame)
    entries = unique(proposal["items"], "locator")
    if entries.keys() != pending.keys():
        raise ValueError("Disposition must cover every warning/limitation exactly; no omitted or invented locators")
    known = {q["question_id"] for q in frame["questions"]}
    if question_id is not None and question_id not in known:
        raise ValueError("Disposition requested for an unknown question")
    restrictions = []
    refs = {artifact_id(p["path"]) for p in pins.values()} | {artifact_id(proposal["frame"]["path"])}
    required_review_refs = refs - {artifact_id(pins["review"]["path"])}
    if not required_review_refs <= set(review["evidence_refs"]):
        raise ValueError("Disposition review omits source, proposal or frame evidence")
    for locator, entry in entries.items():
        original, affected = pending[locator]
        declared = set(entry["question_ids"])
        if not affected <= declared or not declared <= known:
            raise ValueError("Disposition omits affected questions or invents question scope")
        if entry["action"] != "retain_with_limit":
            raise ValueError("Disposition still requires repair")
        refs.update(entry["evidence_refs"])
        for qid in sorted(declared):
            if question_id is None or qid == question_id:
                restrictions.append({"question_id": qid, "source": pins["source"], "locator": locator,
                                     "issue": original, "boundary": entry["boundary"]})
    refs.update(review["evidence_refs"])
    registry = ArtifactRegistry(root)
    records = {a["artifact_id"]: a for a in registry.store.load()["artifacts"]}
    if review["actor_id"] in {records[key]["producer"] for key in source.get("artifact_refs", []) if key in records}:
        raise ValueError("Disposition reviewer cannot be a producer of the original reviewed work")
    stale = set(registry.store.inspect_freshness()["stale"])
    if not refs <= records.keys() or refs & stale or any(records[key]["status"] not in {"VALID", "FROZEN"} for key in refs):
        raise ValueError("Disposition cites missing/stale evidence")
    return {"sources": pins, "restrictions": restrictions, "dependencies": sorted(refs)}


def qualify_source(root, source, bindings, *, frame_path=None, question_id=None):
    matches = [item for item in bindings if item["source"] == source]
    if len(matches) != 1:
        raise ValueError("Unresolved warning/LIMITED source needs exactly one reviewed disposition: " + source)
    return verify_disposition(root, matches[0], frame_path=frame_path, question_id=question_id)


def derive_qualifications(root, question_id, sources, runs):
    """Freeze callers provide pins, never approved wording or inherited claims."""
    from .freeze import verify_freeze
    restrictions, dependencies, inherited, direct = [], set(), {}, {}
    for binding in sources:
        result = verify_disposition(root, binding, question_id=question_id)
        key = result["sources"]["source"]["path"]
        if key in direct:
            raise ValueError("Duplicate qualification source")
        direct[key] = result["sources"]
        restrictions.extend(result["restrictions"])
        dependencies.update(result["dependencies"])
    for run in runs:
        for parent in run.get("upstream_freezes", []):
            snapshot = verify_freeze(root, parent["question_id"], refresh=False)
            reference = {"question_id": parent["question_id"], "freeze_id": snapshot["freeze_id"],
                         **pin(root, parent["source_path"])}
            if reference["freeze_id"] != parent["freeze_id"] or reference["sha256"] != parent["sha256"]:
                raise ValueError("Qualification parent differs from actual upstream run input")
            if snapshot.get("qualifications"):
                inherited[parent["question_id"]] = reference
                dependencies.add(snapshot["registry_artifact_id"])
                restrictions.extend(snapshot["qualifications"]["restrictions"])
    restrictions = {object_hash(item): item for item in restrictions}
    value = {"confidence": "limited", "sources": [direct[key] for key in sorted(direct)],
             "inherited_from": [inherited[key] for key in sorted(inherited)],
             "restrictions": [restrictions[key] for key in sorted(restrictions)]} if restrictions else None
    return value, sorted(dependencies)
