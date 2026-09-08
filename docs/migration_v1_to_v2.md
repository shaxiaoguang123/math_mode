# V1 → V2 migration

Implementation is staged. T03 adds policy and corrects page/cover/TOC behavior;
later runtime and evidence migrations must extend this document before release.
Preserve original inputs, templates and the existing figure skill. Old audit
reports do not become V2 evidence merely because their `status` says PASS.

## Competition policy (T03)

The shipped `华为杯_论文规范模板/competition_policy.json` is an **unverified draft**
based on the existing template edition. It deliberately contains no invented
official source URL, contest year, template hash or page requirement. Its valid
schema allows draft building; official policy audit returns BLOCKED.

Copy this configuration into the private contest workspace, verify the actual
edition's organizer rules, retain source snapshots and their SHA-256, and record
which policy sections each source supports. Fill the official template path/hash
relative to that workspace. A review event needs real actor/time attribution.
An accessible URL or a filename containing an edition does not establish official
authority; the curator must read the organizer material. The automated policy
gate checks recorded scope and hashes, not the authenticity of an arbitrary URL.

```powershell
python -m pip install -r requirements.txt
python -m mathmode policy --workspace ../competitions/case-id --policy ../competitions/case-id/competition_policy.json
```

All paper tools accept `--policy <path>`. Pass the same file to build and audit.
`build_latex.py` and `build_docx.py` accept `--cover-tex cover.tex` only when the
policy selects `identity_cover`. The fragment lives inside the paper directory
and is distinct from abstract/body sources. DOCX remains a limited derivative
of the same TeX, and its source boundary marker is not proof of physical pagination.
Inspect the rendered cover and its page count before final PDF audit.

`cover_policy.pages` reserves only separate identity-cover pages; title-only and
no-cover modes reserve zero. `anonymity_policy.scope` is `all`, `after_cover` or
`none`. Known identities may be supplied as `identity_terms` in the private
configuration. Do not publish these terms or filled covers in this template repo.

`toc_policy.mode` is `required`, `optional` or `forbidden`, with depth 1–3.
Optional TOC uses `project_recommendations.include_toc`; the default draft omits
it. Source audit uses `audit_tex.py --stage source`; after rendering use
`--stage render`, which checks the auxiliary TOC if enabled. A missing rendered
TOC cannot silently pass. PDF audit should receive `--source` and
`--project-root` alongside the policy to verify TOC choice and source snapshots.

`page_targets.json` version 2 renames `required_body_pages` to
`recommended_body_pages`. Legacy target files remain readable, but their old
minimum is interpreted as a warning only. Calibration no longer manufactures an
official minimum. Actual limits are `official.page_policy.min_body_pages` and
`max_total_pages`; use null when there is no verified requirement. Unknown body
boundaries cannot satisfy an official body-page limit. PDF warnings report WARN,
errors FAIL (exit 1), completed checks PASS (exit 0). Unresolved audit warnings use
exit 2. Historical page advisories explicitly carry `blocking=false` and do not
block delivery or cause a nonzero exit on their own; they still appear as WARN,
never as a completed scientific check. `delivery_blocked` distinguishes these
recommendations from required audit work.

The original template filename remains unchanged. The builders read the edition
from policy; `gmcm-title.sty` visual parameters and original DOCX bytes are preserved.
No example PDF, past page count or original router claim proves official compliance.

## Compatibility boundaries to finish in T04–T12

V1 visual/support/paper manifests will have explicit lineage adapters; no adapter
may invent successful execution, independent validation or a frozen value.
Historical figures and private competition workspaces must remain distinguishable
from engineering fixtures. Release notes will identify the final schema migration,
verified CLI sequence, actual historical run, tests and rollback commit.
