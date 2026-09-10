from test_validation import prepared
from test_workflow import case
from test_reference_retrieval import server
from pathlib import Path
from mathmode.io import read_json


def test_workflow_fetches_declared_general_source_once_and_preserves_blindness(case):
    root, workflow, plan = case
    with server(root) as (base, observations):
        general = read_json(Path(__file__).resolve().parents[1] / "fixtures/agents/reference_request.json")
        general["source"] = base + "/redirect"  # Unit integration uses its real local HTTP fixture.
        plan["reference_requests"] = [
            {"retrieval_id": "same-before-baseline", "source": base + "/same", "question_id": "Q1",
             "same_problem": True, "baseline_id": None},
            general]
        report = workflow.advance(plan)
        assert report["performed"] == {"action": "retrieve-reference", "retrieval_id": "general-method", "status": "RETRIEVED"}
        assert report["blockers"][0]["retrieval_id"] == "same-before-baseline"
        assert [item["path"] for item in observations] == ["/redirect", "/method"]
        assert len(list((root / "runs").glob("*/run_manifest.json"))) == 1, "Only the fixture's pre-existing probe ran"
        report = workflow.advance(plan)
        assert report["performed"]["action"] == "run-main", "Pending same-problem reference must not prevent constructing the blind baseline"
        assert len(observations) == 2, "Resume must verify, not refetch, the completed source"
        plan["reference_requests"][1]["source"] = base + "/changed"
        result = workflow._reference_requests(plan)
        assert result["performed"] is None
        assert "changed after retrieval" in result["blockers"][1]["reason"]
        assert len(observations) == 2
