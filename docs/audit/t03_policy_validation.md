# T03 — Competition policy implementation verification

Status: **PASS for policy implementation**, 2026-09-08. This is not G0/G8 official
compliance. Tests ran using Conda `test`, Python 3.12.13; `python-docx` 1.2.0 was
installed into that environment to verify the existing optional derivative.

Implemented strict policy schema/load and documentary hash/scope verification;
TeX/DOCX edition/TOC/cover options; separate identity-cover and anonymous-body
scopes; official page limits; nonblocking historical page recommendations; policy
CLI; migration notes and synchronized policy instructions in AGENTS/CLAUDE.
Fixed observed PDF regex and escaped-percent/brace errors. Kept original title
component and DOCX intact. DOCX table-cell anonymity is now included.

Evidence:

- `python -m pytest -q`: **21 passed**. Tests include new edition, required/optional/
  forbidden TOC, matching TeX and DOCX settings, missing rendered TOC, identity
  cover versus body leak (including nested TeX reuse and DOCX tables), immutable
  original DOCX, duplicate/NaN JSON rejection, changed source hash, incomplete
  official source scope, page-policy separation and PDF regex/abstract detection.
- `python -m compileall -q mathmode tests 华为杯_论文规范模板/tools`: passed.
- `python -m mathmode policy --workspace .`: expected **BLOCKED**, exit 1. Shipped
  draft has no verified official source snapshots, year or template provenance.
- `git diff --check`: passed. Protected `.agents`, `.claude`, original DOCX,
  `gmcm-title.sty` and `gmcmthesis.cls` have no differences from `d3b3f48`.

The tests use disposable engineering documents. They do not establish current
organizer rules, official-cover visual fidelity, full XeLaTeX rendering, Word COM
pagination or scientific evidence. Source and DOCX audits identify their limited
scope. PDF policy audit blocks unavailable official provenance and unknown required
page scope. A historical 45-page recommendation is explicitly nonblocking so it
cannot return as a disguised delivery requirement through warning exit handling.

Remaining stages: T04 contracts/workspace; T05 execution; T06 independent evidence;
T07 freeze/stale; T08 agent harness; T09 complete visual/paper lineage and legacy
migration; T10 CI/benchmark; T11 historical run; T12 final acceptance/PR. Source
authority and exact official cover rendering remain required for G0/G8 and are
not waived by this implementation-stage report.
