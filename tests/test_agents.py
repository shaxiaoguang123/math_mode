import json
from pathlib import Path

import pytest

from mathmode.agent_backends import AgentBackend, AgentExecution
from mathmode.agents import run_agent_task, validate_task, verify_agent_result
from mathmode.io import read_json, write_json, now
from mathmode.lineage import ArtifactRegistry
from mathmode.state import StateStore, initial_state


class FixtureBackend(AgentBackend):
    """Transport/permission test double, explicitly not a reasoning engine."""
    name = "fixture_transport"
    reasoning_backend = False

    def __init__(self, mutate=None):
        self.mutate = mutate

    def produce(self, directory, *, timeout):
        task = read_json(directory / "task.json")
        proposal = {"schema_version": "2.0", "proposal_id": "fixture-proposal", "actor_id": task["actor_id"],
            "question_id": "Q1", "view": "statistics", "applicable": False,
            "reason": "Transport fixture; no actual reasoning was performed.", "main_idea": None, "baseline_idea": None,
            "assumption_refs": [], "evidence_refs": [task["inputs"][0]["artifact_id"]], "risks": [], "validation_plan": []}
        response = {"schema_version": "2.0", "task_id": task["task_id"], "actor_id": task["actor_id"],
            "status": "PRODUCED", "rationale": "Only exercise the artifact transport contract.",
            "evidence_refs": [task["inputs"][0]["artifact_id"]], "blockers": [],
            "artifacts": [{"path": "methods/proposal.json", "content": json.dumps(proposal)}]}
        if self.mutate:
            self.mutate(response, directory)
        write_json(directory / "response.json", response)
        write_json(directory / "events.jsonl", {"type": "fixture.transport", "not_a_provider_call": True})
        (directory / "stderr.txt").write_text("", encoding="utf-8")
        return AgentExecution(0, False, 0.0, "test-double", "fixture", None)


@pytest.fixture
def task_root(tmp_path):
    StateStore(tmp_path).create(initial_state("agent-fixture", "fixture"))
    write_json(tmp_path / "problem.json", {"description": "Synthetic transport input, no contest claim"})
    registry = ArtifactRegistry(tmp_path)
    key = registry.register("problem.json", producer="fixture")
    source = registry.store.load()["artifacts"][0]
    task = {"schema_version": "2.0", "task_id": "task-fixture", "actor_id": "council-fixture", "role": "council",
        "question_id": "Q1", "instructions": "Exercise transport without pretending to perform mathematical reasoning.",
        "created_at": now(), "inputs": [{"artifact_id": key, "path": source["path"], "sha256": source["sha256"]}],
        "outputs": [{"path": "methods/proposal.json", "contract": "method_proposal", "format": "json"}],
        "reviewed_actor_id": None, "view": "statistics", "interaction_mode": "autopilot", "attempt": 1, "supersedes_task_id": None}
    return tmp_path, task


def test_scoped_publication_and_honest_fixture_provenance(task_root):
    root, task = task_root
    result = run_agent_task(root, task, FixtureBackend())
    assert result["status"] == "PRODUCED", result
    assert result["capabilities"]["reasoning_backend"] is False
    assert result["provider"] == "test-double"
    assert (root / "methods/proposal.json").is_file()
    usage = read_json(root / "ai_usage.jsonl")
    assert usage["human_postprocess"] is None
    assert usage["provider"] == "test-double"
    assert verify_agent_result(root, task["task_id"], require_reasoning=False)["status"] == "PRODUCED"
    with pytest.raises(ValueError, match="actual backend session"):
        verify_agent_result(root, task["task_id"])


def test_role_cannot_request_other_role_output(task_root):
    root, task = task_root
    task["outputs"][0].update(path="code/main.py", format="python", contract=None)
    with pytest.raises(ValueError, match="allowed directories"):
        run_agent_task(root, task, FixtureBackend())
    assert not (root / "agent_runs").exists()


def test_overscoped_model_output_is_preserved_only_as_failed_proposal(task_root):
    root, task = task_root
    backend = FixtureBackend(lambda response, _: response["artifacts"][0].update(path="workflow_state.json"))
    result = run_agent_task(root, task, backend)
    assert result["status"] == "FAILED"
    assert not (root / "methods/proposal.json").exists()
    assert StateStore(root).load()["case_id"] == "agent-fixture"


def test_invalid_contract_is_rejected_before_any_publication(task_root):
    root, task = task_root
    backend = FixtureBackend(lambda response, _: response["artifacts"][0].update(content='{"schema_version":"2.0"}'))
    result = run_agent_task(root, task, backend)
    assert result["status"] == "FAILED"
    assert not (root / "methods/proposal.json").exists()


def test_response_actor_and_evidence_identity_cannot_be_changed(task_root):
    root, task = task_root
    result = run_agent_task(root, task, FixtureBackend(lambda response, _: response.update(actor_id="someone-else")))
    assert result["status"] == "FAILED"
    assert "identity" in result["blockers"][0]


def test_review_cannot_approve_same_actor(task_root):
    _, task = task_root
    task.update(role="reviewer", view=None, reviewed_actor_id=task["actor_id"])
    task["outputs"] = [{"path": "reviews/review.json", "contract": "semantic_review", "format": "json"}]
    with pytest.raises(ValueError, match="different actual producer"):
        validate_task(task)


def test_raw_agent_api_cannot_impersonate_host_human_gate(task_root):
    _, task = task_root
    task.update(role="decision", view=None, interaction_mode="human_gate",
                outputs=[{"path": "decisions/choice.jsonl", "format": "jsonl", "contract": "method_decision"}])
    with pytest.raises(ValueError, match="actual host user event"):
        validate_task(task)


def test_model_response_cannot_publish_human_choice_even_with_an_event_id(task_root):
    root, task = task_root
    task.update(role="decision", view=None,
                outputs=[{"path": "decisions/choice.jsonl", "format": "jsonl", "contract": "method_decision"}])
    def forge(response, directory):
        decision = read_json(Path(__file__).resolve().parents[1] / "fixtures/contracts/method_decision.json")
        decision.update(actor_id=task["actor_id"], decided_by="human", human_event_id="human-claimed-by-model",
                        evidence_refs=[task["inputs"][0]["artifact_id"]])
        response["artifacts"] = [{"path": "decisions/choice.jsonl", "content": json.dumps(decision)}]
    result = run_agent_task(root, task, FixtureBackend(forge))
    assert result["status"] == "FAILED"
    assert not (root / "decisions/choice.jsonl").exists()


def test_raw_code_api_requires_real_human_decision_before_backend_execution(task_root):
    from mathmode.state import StateStore
    root, task = task_root
    store = StateStore(root)
    store.update(lambda state: state.update(interaction_mode="human_gate"), expected_revision=store.load()["revision"])
    task.update(role="code", view=None, interaction_mode="human_gate",
                outputs=[{"path": "code/main.py", "format": "python", "contract": None}])
    with pytest.raises(ValueError, match="actual host human decision"):
        run_agent_task(root, task, FixtureBackend())
    assert not (root / "agent_runs").exists()


@pytest.mark.parametrize("known_evidence", [True, False])
def test_decision_artifact_cannot_cite_unseen_probe_evidence(task_root, known_evidence):
    root, task = task_root
    path = "decisions/choice.jsonl"
    task.update(role="decision", view=None,
        outputs=[{"path": path, "format": "jsonl", "contract": "method_decision"}])
    def decision_response(response, directory):
        decision = read_json(Path(__file__).resolve().parents[1] / "fixtures/agents/fallback_decision.json")
        decision.update(actor_id=task["actor_id"], decided_at=now(),
            evidence_refs=[task["inputs"][0]["artifact_id"] if known_evidence else "invented-probe"])
        response["artifacts"] = [{"path": path, "content": json.dumps(decision)}]
    result = run_agent_task(root, task, FixtureBackend(decision_response))
    assert result["status"] == ("PRODUCED" if known_evidence else "FAILED")
    assert (root / path).exists() is known_evidence
    if known_evidence:
        # Valid scoped transport remains synthetic; it cannot establish screening.
        with pytest.raises(ValueError, match="actual backend session"):
            verify_agent_result(root, task["task_id"])
    else:
        assert "outside its input scope" in result["blockers"][0]


def test_backend_input_mutation_invalidates_response(task_root):
    root, task = task_root
    result = run_agent_task(root, task, FixtureBackend(lambda response, directory: (directory / "AGENTS.md").write_text("changed", encoding="utf-8")))
    assert result["status"] == "FAILED"
    assert "read-only" in result["blockers"][0]
    assert not (root / "methods/proposal.json").exists()


def test_codex_transport_schema_has_explicit_enum_types():
    from mathmode.agent_backends import CodexCliBackend
    from mathmode.schema_catalog import catalog
    schema = CodexCliBackend(command=["codex"]).response_schema(catalog()["agent_response"])
    assert schema["properties"]["schema_version"] == {"enum": ["2.0"], "type": "string"}
    assert schema["properties"]["status"]["type"] == "string"
    assert "const" in catalog()["agent_response"]["properties"]["schema_version"]
    assert "pattern" not in schema["properties"]["artifacts"]["items"]["properties"]["path"]
    assert "pattern" in catalog()["agent_response"]["properties"]["artifacts"]["items"]["properties"]["path"]


def test_codex_prompt_binds_contract_identity_to_task_actor(monkeypatch, tmp_path):
    from mathmode.agent_backends import CodexCliBackend
    from mathmode.execution import ExecutionResult

    write_json(tmp_path / "task.json", {"actor_id": "framer-codex-test"})
    captured = {}

    def fake_execute(self, argv, *, cwd, environment, timeout, stdout, stderr):
        captured["argv"] = argv
        stdout.write_text("", encoding="utf-8")
        stderr.write_text("", encoding="utf-8")
        return ExecutionResult(0, False, 0.0)

    monkeypatch.setattr("mathmode.agent_backends.LocalSubprocessBackend.execute", fake_execute)
    CodexCliBackend(command=["codex"]).produce(tmp_path, timeout=1)
    prompt = captured["argv"][-1]
    assert "task actor_id 'framer-codex-test'" in prompt
    assert "historical producer names" in prompt


def test_fresh_ids_and_actors_cannot_reset_failed_retry_budget(task_root):
    from copy import deepcopy
    root, task = task_root
    backend = FixtureBackend(lambda response, _: response.update(actor_id="wrong-actor"))
    for attempt in range(1, 4):
        current = deepcopy(task)
        current.update(task_id=f"failure-{attempt}", attempt=attempt,
                       supersedes_task_id=f"failure-{attempt - 1}" if attempt > 1 else None)
        assert run_agent_task(root, current, backend)["status"] == "FAILED"
    restarted = deepcopy(task)
    restarted.update(task_id="fresh-id", actor_id="fresh-actor")
    with pytest.raises(ValueError, match="reset.*retry budget"):
        run_agent_task(root, restarted, backend)
    assert not (root / "agent_runs/fresh-id").exists()


def test_backend_exception_is_a_recorded_failure_without_exception_secrets(task_root):
    class CrashingBackend(FixtureBackend):
        def produce(self, directory, *, timeout):
            raise RuntimeError("secret-test-value-must-not-be-recorded")
    root, task = task_root
    result = run_agent_task(root, task, CrashingBackend())
    assert result["status"] == "FAILED"
    assert result["returncode"] is None
    assert result["blockers"] == ["Backend exception: RuntimeError"]
    assert "secret-test-value" not in json.dumps(result)


@pytest.mark.parametrize("target", ["agent_result.json", "response.json", "events.jsonl", "AGENTS.md"])
def test_handoff_rejects_changed_transport_or_bundle(task_root, target):
    root, task = task_root
    run_agent_task(root, task, FixtureBackend())
    path = root / "agent_runs" / task["task_id"] / target
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="stale|changed"):
        verify_agent_result(root, task["task_id"], require_reasoning=False)


def test_cross_question_proposal_is_rejected(task_root):
    root, task = task_root
    def mutate(response, _):
        proposal = json.loads(response["artifacts"][0]["content"])
        proposal["question_id"] = "Q2"
        response["artifacts"][0]["content"] = json.dumps(proposal)
    result = run_agent_task(root, task, FixtureBackend(mutate))
    assert result["status"] == "FAILED"
    assert "question identity" in result["blockers"][0]


@pytest.mark.parametrize("admitted", [False, True])
def test_method_sources_require_prior_explicit_access_and_actual_snapshot(task_root, admitted):
    from mathmode.reference_access import admit_reference
    root, task = task_root
    if admitted:
        admit_reference(root, source="fixture://method-definition", question_id="Q1", same_problem=False)
    task.update(role="method_retriever", view=None, created_at=now(),
                outputs=[{"path": "methods/sources.json", "format": "json", "contract": "method_sources"}])
    def mutate(response, _):
        source = {"schema_version": "2.0", "actor_id": task["actor_id"], "question_id": "Q1",
            "sources": [{"source_id": "definition", "uri": "fixture://method-definition", "accessed_at": now(),
                "snapshot_path": task["inputs"][0]["path"], "sha256": task["inputs"][0]["sha256"],
                "same_problem": False, "contribution": "Transport fixture only", "limitations": "No actual literature search"}]}
        response["artifacts"] = [{"path": "methods/sources.json", "content": json.dumps(source)}]
    result = run_agent_task(root, task, FixtureBackend(mutate))
    assert result["status"] == ("PRODUCED" if admitted else "FAILED")
    if not admitted:
        assert "not explicitly admitted" in result["blockers"][0]


def test_successful_critic_proposals_cannot_loop_without_bound(task_root):
    root, task = task_root
    task.update(role="critic", view=None, reviewed_actor_id="proposal-producer",
                outputs=[{"path": "methods/card.json", "format": "json", "contract": "method_card"}])
    def card_response(response, _):
        card = read_json(Path(__file__).resolve().parents[1] / "fixtures/contracts/method_card.json")
        card["critic"]["actor_id"] = task["actor_id"]
        response["artifacts"] = [{"path": "methods/card.json", "content": json.dumps(card)}]
    for number in range(3):
        current = {**task, "task_id": f"critic-round-{number}"}
        assert run_agent_task(root, current, FixtureBackend(card_response))["status"] == "PRODUCED"
    with pytest.raises(ValueError, match="Critic round budget exhausted"):
        run_agent_task(root, {**task, "task_id": "new-round-id"}, FixtureBackend(card_response))
