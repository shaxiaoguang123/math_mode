from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time

import pytest

from test_agents import task_root, FixtureBackend
from test_reference_access import sealed_baseline, frozen, prepared, runs
from mathmode.agents import run_agent_task, verify_agent_result
from mathmode.io import read_json, file_hash, now
from mathmode.lineage import ArtifactRegistry
from mathmode.reference_retrieval import retrieve_reference, verify_retrieval
from mathmode.state import StateStore, initial_state

BODY = b"Synthetic reference: a median of pairwise slopes. This is a transport fixture, not literature evidence.\n"


@contextmanager
def server(root):
    observations = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            url = f"http://127.0.0.1:{self.server.server_port}{self.path}"
            events = StateStore(root).load()["reference_access"]
            observations.append({"path": self.path, "admitted_before_request": any(event["source"] == url for event in events)})
            if self.path in {"/redirect", "/cycle", "/file"}:
                self.send_response(302)
                self.send_header("Location", {"/redirect": "/method", "/cycle": "/cycle", "/file": "file:///private/local.txt"}[self.path])
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if self.path == "/slow":
                time.sleep(0.4)
            self.send_response(404 if self.path == "/error" else 200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            body = b"" if self.path == "/empty" else BODY
            lengths = {"/truncated": len(body) + 10, "/large": 100_000, "/negative": -1}
            if self.path != "/stream":
                self.send_header("Content-Length", str(lengths.get(self.path, len(body))))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}", observations
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=3)


@pytest.fixture
def reference_root(tmp_path):
    StateStore(tmp_path).create(initial_state("reference-http-fixture", "fixture"))
    yield tmp_path
    for path in tmp_path.rglob("*"):
        if path.is_file():
            path.chmod(0o600)


def test_http_snapshot_and_every_redirect_are_admitted_before_network(reference_root):
    root = reference_root
    with server(root) as (base, observations):
        receipt = retrieve_reference(root, source=base + "/redirect", question_id="Q1", same_problem=False,
            retrieval_id="method-reference")
        assert receipt["status"] == "RETRIEVED", receipt
        assert observations == [{"path": path, "admitted_before_request": True} for path in ("/redirect", "/method")]
        assert (root / receipt["snapshot"]["path"]).read_bytes() == BODY
        assert receipt["outside_host_blindness"] == "UNVERIFIABLE"
        relative = "references/method-reference/retrieval.json"
        assert verify_retrieval(root, relative) == receipt
        assert len(observations) == 2, "Verification must not silently fetch newer content"
        with pytest.raises(ValueError, match="already exists"):
            retrieve_reference(root, source=base + "/method", question_id="Q1", same_problem=False, retrieval_id="method-reference")
        assert len(observations) == 2
        path = root / receipt["snapshot"]["path"]
        path.chmod(0o600)
        path.write_bytes(b"Changed source")
        with pytest.raises(ValueError, match="stale"):
            verify_retrieval(root, relative)


def test_same_problem_requires_baseline_before_any_http_request(reference_root):
    with server(reference_root) as (base, observations):
        with pytest.raises(ValueError, match="sealed blind baseline"):
            retrieve_reference(reference_root, source=base + "/method", question_id="Q1", same_problem=True)
        assert observations == []
        assert not (reference_root / "references").exists()


def test_same_problem_http_receipt_preserves_and_depends_on_real_blind_checkpoint(sealed_baseline):
    root, baseline = sealed_baseline
    with server(root) as (base, observations):
        receipt = retrieve_reference(root, source=base + "/redirect", question_id="Q1", same_problem=True,
            baseline_id=baseline["baseline_id"])
        assert receipt["status"] == "RETRIEVED", receipt
        assert all(item["admitted_before_request"] for item in observations)
    relative = f"references/{receipt['retrieval_id']}/retrieval.json"
    assert verify_retrieval(root, relative)["baseline_id"] == baseline["baseline_id"]
    (root / "paper/draft.tex").write_text("Later reference-informed draft", encoding="utf-8")
    assert verify_retrieval(root, relative)["status"] == "RETRIEVED"
    frozen_paper = root / baseline["artifacts"]["paper"][0]["path"]
    frozen_paper.chmod(0o600)
    frozen_paper.write_text("Altered pre-reference checkpoint", encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        verify_retrieval(root, relative)


@pytest.mark.parametrize("route,options", [
    ("/empty", {}), ("/truncated", {}), ("/negative", {}), ("/error", {}),
    ("/large", {"max_bytes": 20}), ("/stream", {"max_bytes": 20}),
    ("/redirect", {"max_redirects": 0}), ("/cycle", {}), ("/file", {}), ("/slow", {"timeout": 0.1})])
def test_failed_downloads_preserve_evidence_without_usable_snapshot(reference_root, route, options):
    root = reference_root
    with server(root) as (base, observations):
        receipt = retrieve_reference(root, source=base + route, question_id="Q1", same_problem=False, **options)
        assert receipt["status"] == "FAILED", receipt
        assert receipt["snapshot"] is None and receipt["failure_type"]
        assert observations and all(item["admitted_before_request"] for item in observations)
        relative = f"references/{receipt['retrieval_id']}/retrieval.json"
        assert read_json(root / relative) == receipt
        with pytest.raises(ValueError, match="failed, interrupted"):
            verify_retrieval(root, relative)
        assert not list((root / "references").glob("*/body.bin"))


@pytest.mark.parametrize("uri", ["file:///private.txt", "https://user:password@example.org/file", "https://example.org/a#part", "https://example.org/\nheader"])
def test_non_http_or_credential_urls_are_rejected_before_admission(reference_root, uri):
    with pytest.raises(ValueError):
        retrieve_reference(reference_root, source=uri, question_id="Q1", same_problem=False)
    assert StateStore(reference_root).load()["reference_access"] == []


@pytest.mark.parametrize("mutation", [None, "uri", "time", "classification", "missing_receipt"])
def test_http_method_sources_bind_actual_receipt_and_snapshot(task_root, mutation):
    root, task = task_root
    with server(root) as (base, _):
        receipt = retrieve_reference(root, source=base + "/method", question_id="Q1", same_problem=False)
    relative = f"references/{receipt['retrieval_id']}/retrieval.json"
    artifacts = {item["path"]: item for item in ArtifactRegistry(root).store.load()["artifacts"]}
    task.update(role="method_retriever", view=None, created_at=now(),
        outputs=[{"path": "methods/sources.json", "format": "json", "contract": "method_sources"}])
    for path in (receipt["snapshot"]["path"], relative):
        item = artifacts[path]
        task["inputs"].append({key: item[key] for key in ("artifact_id", "path", "sha256")})
    source = {"source_id": "http-fixture", "uri": receipt["source"], "accessed_at": receipt["finished_at"],
        "snapshot_path": receipt["snapshot"]["path"], "sha256": receipt["snapshot"]["sha256"],
        "retrieval": {"path": relative, "sha256": file_hash(root / relative)}, "same_problem": False,
        "contribution": "Actual HTTP transport fixture", "limitations": "Synthetic content; no scientific literature claim"}
    if mutation == "uri":
        source["uri"] = base + "/different-unfetched-source"
    elif mutation == "time":
        source["accessed_at"] = now()
    elif mutation == "classification":
        source["same_problem"] = True
    elif mutation == "missing_receipt":
        source.pop("retrieval")
    def response(value, _):
        value["artifacts"] = [{"path": "methods/sources.json", "content": json.dumps({
            "schema_version": "2.0", "actor_id": task["actor_id"], "question_id": "Q1", "sources": [source]})}]
    result = run_agent_task(root, task, FixtureBackend(response))
    assert result["status"] == ("PRODUCED" if mutation is None else "FAILED"), result
    assert (root / "methods/sources.json").exists() is (mutation is None)
    if mutation is None:
        assert verify_agent_result(root, task["task_id"], require_reasoning=False)["status"] == "PRODUCED"


def test_cli_retrieval_and_verification_keep_scientific_acceptance_unrun(reference_root, capsys):
    from mathmode.__main__ import main
    with server(reference_root) as (base, _):
        assert main(["retrieve-reference", "--workspace", str(reference_root), "--question-id", "Q1",
                     "--source", base + "/method", "--classification", "general", "--retrieval-id", "cli-fixture"]) == 0
    assert json.loads(capsys.readouterr().out)["scientific_acceptance"] == "NOT_RUN"
    assert main(["verify-reference", "--workspace", str(reference_root), "--receipt", "references/cli-fixture/retrieval.json"]) == 0
    assert json.loads(capsys.readouterr().out)["scope"] == "reference_retrieval_integrity"
