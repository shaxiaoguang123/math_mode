import stat

from mathmode.data_audit import audit_inputs
from mathmode.workspace import initialize


def test_actual_missingness_and_duplicates_do_not_become_pass(tmp_path):
    problem = tmp_path / "problem.txt"
    problem.write_text("Synthetic tabular input audit fixture", encoding="utf-8")
    data = tmp_path / "data.csv"
    data.write_text("id,value\na,\na,\n", encoding="utf-8")
    source = {"uri": "fixture://input-audit", "accessed_at": "2026-09-08T00:00:00Z", "license": "Repository-authored fixture"}
    root = initialize("data-audit-fixture", [{"input_id": key, "path": str(path), "role": key, "source": source}
        for key, path in [("problem", problem), ("data", data)]], destination=tmp_path / "workspace", kind="fixture")
    result = audit_inputs(root)
    assert result["status"] == "WARN"
    record = next(item for item in result["files"] if item["input_id"] == "data")
    assert record["rows"] == 2 and record["missing_values"] == 2 and record["duplicate_rows"] == 1
    for path in root.rglob("*"):
        if path.is_file():
            path.chmod(stat.S_IRUSR | stat.S_IWUSR)
