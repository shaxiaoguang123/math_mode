"""Policy configuration is separate from official-source verification.

Loading a valid JSON policy does not certify that its statements are official.
Final gates require reviewed source snapshots and matching template hashes.
"""
from __future__ import annotations

import re
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from .io import read_json, file_hash

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = REPO_ROOT / "华为杯_论文规范模板" / "competition_policy.json"
SCHEMA_PATH = REPO_ROOT / "华为杯_求解规范" / "schemas" / "competition_policy.schema.json"


def validate_policy(policy: dict) -> dict:
    schema = read_json(SCHEMA_PATH)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(policy)
    official = policy["official"]
    cover = official["cover_policy"]
    if (cover["mode"] == "identity_cover") != (cover["pages"] > 0):
        raise ValueError("Only an identity_cover can reserve physical cover pages")
    pages = official["page_policy"]
    ids = [source["source_id"] for source in policy["official_sources"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Official source IDs must be unique")
    if (pages["min_body_pages"] is not None and pages["max_total_pages"] is not None
            and pages["min_body_pages"] > pages["max_total_pages"]):
        raise ValueError("Body minimum exceeds total page maximum")
    return policy


def load_policy(path: Path | None = None) -> dict:
    return validate_policy(read_json(path or DEFAULT_POLICY))


def policy_file(root: Path, relative: str) -> Path:
    # Reject platform-independent absolute/traversal syntax before resolving.
    if (not relative or re.match(r"^[A-Za-z]:", relative)
            or relative.startswith(("/", "\\"))
            or ".." in relative.replace("\\", "/").split("/")):
        raise ValueError("Policy artifact must use a confined relative path")
    target = (root / relative).resolve()
    target.relative_to(root.resolve())
    if not target.is_file():
        raise ValueError(f"Policy artifact missing: {relative}")
    return target


def audit_policy(policy: dict, root: Path) -> dict:
    """Verify documentary provenance; never substitute heuristics for sources."""
    validate_policy(policy)
    issues = []
    if policy["verification"]["status"] != "verified":
        issues.append("Official rules have not been verified")
    if not policy["official_sources"]:
        issues.append("No reviewed official source snapshots")
    covered = {scope for source in policy["official_sources"] for scope in source["scope"]}
    required = {"competition", "year", "edition", "template", *policy["official"]}
    if required - covered:
        issues.append("Official source scope missing: " + ", ".join(sorted(required - covered)))
    if policy["year"] is None:
        issues.append("Competition year is not verified")
    for source in policy["official_sources"]:
        try:
            if file_hash(policy_file(root, source["snapshot_path"])) != source["sha256"]:
                issues.append(f"Official source hash mismatch: {source['source_id']}")
        except (OSError, ValueError) as exc:
            issues.append(str(exc))
    if not policy["official_template_path"] or not policy["official_template_sha256"]:
        issues.append("Official template provenance is missing")
    else:
        try:
            path = policy_file(root, policy["official_template_path"])
            if file_hash(path) != policy["official_template_sha256"]:
                issues.append("Official template hash mismatch")
        except (OSError, ValueError) as exc:
            issues.append(str(exc))
    return {"status": "BLOCKED" if issues else "PASS", "issues": issues,
            "scope": "Reviewed documentary provenance; not scientific validation"}


def toc_settings(policy: dict) -> tuple[bool, int]:
    toc = policy["official"]["toc_policy"]
    include = (toc["mode"] == "required" or
               (toc["mode"] == "optional" and policy["project_recommendations"]["include_toc"]))
    return include, toc["depth"]


def anonymous_records(records: list[dict], policy: dict) -> list[dict]:
    scope = policy["official"]["anonymity_policy"]["scope"]
    if scope == "none":
        return []
    cover_pages = policy["official"]["cover_policy"]["pages"] if scope == "after_cover" else 0
    return [record for record in records if record["physical_page"] > cover_pages]


def page_issues(body: dict, total: int, policy: dict, targets: dict) -> list[dict]:
    official = policy["official"]["page_policy"]
    issues = []
    minimum, maximum = official["min_body_pages"], official["max_total_pages"]
    if minimum is not None:
        if body.get("start") is None or body.get("end") is None:
            issues.append({"code": "official_body_scope_unknown", "severity": "error"})
        elif body["pages"] < minimum:
            issues.append({"code": "official_body_pages_below_minimum", "severity": "error",
                           "actual": body["pages"], "required": minimum})
    if maximum is not None and total > maximum:
        issues.append({"code": "official_total_pages_exceeded", "severity": "error",
                       "actual": total, "maximum": maximum})
    recommendation = targets.get("recommended_body_pages", targets.get("required_body_pages"))
    if recommendation is not None and body.get("start") is not None and body["pages"] < recommendation:
        issues.append({"code": "historical_body_page_recommendation", "severity": "warning",
                       "blocking": False,
                       "actual": body["pages"], "recommended": recommendation,
                       "message": "Historical heuristic only; improve evidence, never pad pages"})
    return issues
