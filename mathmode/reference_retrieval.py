"""Host-admitted HTTP retrieval with immutable, attributable response snapshots.

URLs/classifications are supplied by the trusted host, not inferred from pages.
No page scripts, cookies, ambient credentials or automatic redirects are executed.
"""
from __future__ import annotations

from datetime import datetime
import math
from pathlib import Path
import re
import stat
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit, urljoin
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler, Request
import uuid

from .contracts import validate
from .io import canonical_root, file_hash, now, object_hash, read_json, safe_path, write_json
from .lineage import ArtifactRegistry, artifact_id
from .processes import identity
from .reference_access import admit_reference
from .reference_baselines import verify_blind_admission
from .state import StateStore

REDIRECTS = {301, 302, 303, 307, 308}


def http_url(value: str) -> str:
    if not isinstance(value, str) or any(ord(char) < 33 or ord(char) == 127 for char in value):
        raise ValueError("Reference URL contains whitespace/control characters")
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username is not None or parts.password is not None:
        raise ValueError("Reference retrieval requires an HTTP(S) URL without embedded credentials")
    if parts.fragment or parts.port == 0:
        raise ValueError("Reference request URL must not contain a fragment or zero port")
    return value


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def retrieve_reference(root: Path, *, source: str, question_id: str, same_problem: bool,
                       baseline_id: str | None = None, timeout=30.0, max_bytes=20_000_000,
                       max_redirects=5, retrieval_id: str | None = None) -> dict:
    """Retrieve once; preserve failed attempts and admit every redirect before GET.

    Timeout bounds socket operations and is checked between response chunks. DNS
    resolution is owned by the OS and this is not a hard wall-clock process limit.
    Classification applies to the explicitly requested source and its redirects;
    actual scientific relevance/classification still needs host/role review.
    """
    root = canonical_root(root)
    source = http_url(source)
    if type(timeout) not in {int, float} or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Retrieval timeout must be finite and positive")
    if type(max_bytes) is not int or max_bytes < 1 or type(max_redirects) is not int or not 0 <= max_redirects <= 10:
        raise ValueError("Retrieval requires a positive byte limit and at most ten redirects")
    state = StateStore(root).load()
    retrieval_id = retrieval_id or "retrieval-" + uuid.uuid4().hex
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,100}", retrieval_id):
        raise ValueError("Retrieval ID must be a portable single path component")
    relative = "references/" + retrieval_id
    directory = safe_path(root, relative, exists=False)
    if directory.exists():
        raise ValueError("Retrieval ID already exists; verify its receipt or inspect the preserved failed/interrupted request")
    # Failed admission performs no network request and creates no alleged receipt.
    admission = admit_reference(root, source=source, question_id=question_id,
        same_problem=same_problem, baseline_id=baseline_id)["event"]
    directory.mkdir(parents=True)
    planned = {"retrieval_id": retrieval_id, "case_id": state["case_id"], "question_id": question_id,
        "source": source, "same_problem": same_problem, "baseline_id": baseline_id,
        "blind_reference_mode": admission["blind_reference_mode"],
        "started_at": now(), "timeout_seconds": timeout, "max_bytes": max_bytes, "max_redirects": max_redirects}
    write_json(directory / "planned.json", planned, exclusive=True)
    write_json(directory / "owner.json", {"owner": identity()}, exclusive=True)
    hops, snapshot, failure = [], None, None
    current = source
    deadline = time.monotonic() + timeout
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    seen = set()
    try:
        while True:
            if current in seen:
                raise ValueError("Redirect cycle")
            seen.add(current)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Retrieval budget exhausted")
            hop = {"url": current, "admission_sha256": object_hash(admission), "requested_at": now(),
                "responded_at": None, "status_code": None, "location": None,
                "content_type": None, "content_encoding": None, "content_length": None}
            hops.append(hop)
            write_json(directory / "trace.json", hops)
            request = Request(current, headers={"User-Agent": "MathMode-Reference/2.0", "Accept-Encoding": "identity"})
            try:
                response = opener.open(request, timeout=remaining)
            except HTTPError as error:
                response = error  # Record status/headers without silently following it.
            with response:
                hop.update(responded_at=now(), status_code=response.status,
                    location=response.headers.get("Location") or None, content_type=response.headers.get("Content-Type") or None,
                    content_encoding=response.headers.get("Content-Encoding") or None)
                length = response.headers.get("Content-Length")
                if length is not None:
                    observed_length = int(length)
                    if observed_length < 0:
                        raise ValueError("Invalid content length")
                    hop["content_length"] = observed_length
                write_json(directory / "trace.json", hops)
                if response.status in REDIRECTS:
                    if len(hops) > max_redirects or not hop["location"]:
                        raise ValueError("Redirect limit or missing destination")
                    target = http_url(urljoin(current, hop["location"]))
                    if urlsplit(current).scheme == "https" and urlsplit(target).scheme != "https":
                        raise ValueError("HTTPS reference cannot redirect to plaintext HTTP")
                    # Redirects inherit the host's explicit classification, which
                    # remains a host assertion rather than an automated content claim.
                    admission = admit_reference(root, source=target, question_id=question_id,
                        same_problem=same_problem, baseline_id=baseline_id)["event"]
                    current = target
                    continue
                if not 200 <= response.status < 300:
                    raise ValueError("HTTP response was not successful")
                if hop["content_length"] is not None and hop["content_length"] > max_bytes:
                    raise ValueError("Reference exceeds declared byte budget")
                size = 0
                partial = directory / "response.partial"
                with partial.open("xb") as output:
                    while True:
                        if time.monotonic() >= deadline:
                            raise TimeoutError("Retrieval budget exhausted")
                        chunk = response.read1(min(65536, max_bytes + 1 - size))
                        if time.monotonic() >= deadline:
                            raise TimeoutError("Retrieval budget exhausted")
                        if not chunk:
                            break
                        output.write(chunk)
                        size += len(chunk)
                        if size > max_bytes:
                            raise ValueError("Reference exceeds measured byte budget")
                if size == 0 or (hop["content_length"] is not None and size != hop["content_length"]):
                    raise ValueError("Reference response is empty or incomplete")
                body = directory / "body.bin"
                partial.rename(body)
                body.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
                snapshot = {"path": relative + "/body.bin", "sha256": file_hash(body), "size_bytes": size}
                break
    except Exception as error:
        # Exception messages may contain URLs/credentials or response fragments.
        # Preserve the actual exception type and HTTP trace, never a false receipt.
        failure = type(error).__name__
    write_json(directory / "trace.json", hops)
    controls = [{"path": relative + "/" + name, "sha256": file_hash(directory / name)}
                for name in ("planned.json", "owner.json", "trace.json")]
    receipt = {"schema_version": "2.0", **planned, "finished_at": now(),
        "status": "RETRIEVED" if snapshot is not None and failure is None else "FAILED",
        "failure_type": failure, "snapshot": snapshot, "requests": hops, "controls": controls,
        "timeout_scope": "socket_operations_and_between_chunks", "outside_host_blindness": "UNVERIFIABLE"}
    validate("reference_retrieval", receipt, root=root)
    write_json(directory / "retrieval.json", receipt, exclusive=True)
    for name in ("planned.json", "owner.json", "trace.json", "retrieval.json"):
        (directory / name).chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    registry = ArtifactRegistry(root)
    with registry.batch():
        dependencies = [registry.register(item["path"], producer="reference-http-service") for item in controls]
        if snapshot:
            dependencies.append(registry.register(snapshot["path"], producer="reference-http-service"))
        if baseline_id:
            dependencies.append(artifact_id(f"reference_baselines/{baseline_id}.json"))
        registry.register(relative + "/retrieval.json", producer="reference-http-service", dependencies=dependencies)
    return receipt


def verify_source_retrieval(root: Path, source: dict, *, question_id: str, supplied: dict, task_created_at: str) -> dict:
    """A model cannot assign a downloaded source URI to arbitrary supplied bytes."""
    reference = source.get("retrieval")
    if not reference or supplied.get(reference["path"]) != reference["sha256"]:
        raise ValueError("HTTP method sources require a verified retrieval receipt in the task input bundle")
    if file_hash(safe_path(root, reference["path"])) != reference["sha256"]:
        raise ValueError("Method-source retrieval receipt hash changed")
    receipt = verify_retrieval(root, reference["path"])
    if (receipt["question_id"], receipt["same_problem"]) != (question_id, source["same_problem"]):
        raise ValueError("Method source changed retrieval question/classification")
    if source["uri"] not in {receipt["source"], receipt["requests"][-1]["url"]}:
        raise ValueError("Method source URI differs from the actual HTTP retrieval")
    if (source["snapshot_path"], source["sha256"], source["accessed_at"]) != (
            receipt["snapshot"]["path"], receipt["snapshot"]["sha256"], receipt["finished_at"]):
        raise ValueError("Method source changed the retrieved bytes or observed access time")
    if datetime.fromisoformat(receipt["finished_at"]) > datetime.fromisoformat(task_created_at):
        raise ValueError("Method-source task began before reference retrieval completed")
    return receipt


def verify_retrieval(root: Path, receipt_relative: str) -> dict:
    """Verify stored host/network observations without fetching the source again."""
    root = canonical_root(root)
    receipt = validate("reference_retrieval", read_json(safe_path(root, receipt_relative)), root=root)
    expected_directory = "references/" + receipt["retrieval_id"]
    if receipt_relative != expected_directory + "/retrieval.json" or receipt["status"] != "RETRIEVED":
        raise ValueError("A failed, interrupted or misplaced retrieval cannot supply reference evidence")
    state = StateStore(root).load()
    if receipt["case_id"] != state["case_id"]:
        raise ValueError("Reference retrieval belongs to another workspace")
    registered = {item["path"]: item for item in state["artifacts"]}
    entry = registered.get(receipt_relative)
    freshness = StateStore(root).inspect_freshness()
    if not entry or entry["producer"] != "reference-http-service" or entry["artifact_id"] in freshness["stale"]:
        raise ValueError("Reference retrieval is unregistered or stale")
    if entry["sha256"] != file_hash(root / receipt_relative):
        raise ValueError("Reference receipt changed")
    dependencies = {artifact_id(item["path"]): item["sha256"] for item in [*receipt["controls"], receipt["snapshot"]]}
    if receipt["baseline_id"]:
        baseline_path = f"reference_baselines/{receipt['baseline_id']}.json"
        dependencies[artifact_id(baseline_path)] = file_hash(safe_path(root, baseline_path))
    if {item["artifact_id"]: item["sha256"] for item in entry["depends_on"]} != dependencies:
        raise ValueError("Reference receipt lost a required evidence dependency")
    controls = {item["path"]: item for item in receipt["controls"]}
    if set(controls) != {expected_directory + "/" + name for name in ("planned.json", "owner.json", "trace.json")}:
        raise ValueError("Reference receipt omits retrieval controls")
    for item in controls.values():
        if file_hash(safe_path(root, item["path"])) != item["sha256"]:
            raise ValueError("Reference retrieval controls changed")
    planned = read_json(root / expected_directory / "planned.json")
    if any(receipt.get(key) != value for key, value in planned.items()):
        raise ValueError("Reference receipt differs from its original request")
    if read_json(root / expected_directory / "trace.json") != receipt["requests"]:
        raise ValueError("Reference receipt differs from observed HTTP trace")
    accesses = {object_hash(event): event for event in state["reference_access"]}
    previous = None
    if len(receipt["requests"]) > receipt["max_redirects"] + 1:
        raise ValueError("Reference redirect count exceeds the declared budget")
    prior_time = datetime.fromisoformat(receipt["started_at"])
    finished = datetime.fromisoformat(receipt["finished_at"])
    for hop in receipt["requests"]:
        http_url(hop["url"])
        event = accesses.get(hop["admission_sha256"])
        if not event or (event["source"], event["question_id"], event["same_problem"], event["baseline_freeze_id"]) != (
                hop["url"], receipt["question_id"], receipt["same_problem"], receipt["baseline_id"]):
            raise ValueError("Reference request lacks its recorded host admission")
        if event.get("blind_reference_mode", True) != receipt.get("blind_reference_mode", True):
            raise ValueError("Reference receipt changed its admitted blindness mode")
        verify_blind_admission(root, event)
        if datetime.fromisoformat(event["at"]) > datetime.fromisoformat(hop["requested_at"]):
            raise ValueError("Reference was fetched before access admission")
        requested = datetime.fromisoformat(hop["requested_at"])
        responded = datetime.fromisoformat(hop["responded_at"]) if hop["responded_at"] else None
        if responded is None or not prior_time <= requested <= responded <= finished:
            raise ValueError("Reference HTTP observation times are inconsistent")
        prior_time = responded
        if previous is None:
            if hop["url"] != receipt["source"]:
                raise ValueError("Reference request starts at another source")
        elif previous["status_code"] not in REDIRECTS or urljoin(previous["url"], previous["location"] or "") != hop["url"]:
            raise ValueError("Reference redirect chain is discontinuous")
        if previous and urlsplit(previous["url"]).scheme == "https" and urlsplit(hop["url"]).scheme != "https":
            raise ValueError("Reference redirect downgraded HTTPS")
        previous = hop
    if previous is None or previous["status_code"] is None or not 200 <= previous["status_code"] < 300:
        raise ValueError("Reference has no completed successful response")
    snapshot = receipt["snapshot"]
    if not snapshot or snapshot["path"] != expected_directory + "/body.bin":
        raise ValueError("Reference response snapshot is missing or misplaced")
    path = safe_path(root, snapshot["path"])
    if path.stat().st_size != snapshot["size_bytes"] or file_hash(path) != snapshot["sha256"]:
        raise ValueError("Reference response snapshot changed")
    if snapshot["size_bytes"] > receipt["max_bytes"] or previous["content_length"] not in {None, snapshot["size_bytes"]}:
        raise ValueError("Reference response size differs from its declared observation")
    return receipt
