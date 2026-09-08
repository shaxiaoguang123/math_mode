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

## Modeling contracts and private workspaces (T04)

V2 modeling contracts are additive; existing V1 paper/visual/support inputs retain
their entry points. Do not rename a V1 plan to a V2 spec or fill evidence fields
with invented PASS records. Start by explicitly framing the actual question,
registering inputs and reviewing assumptions.

Prepare an input declaration JSON array with `input_id`, absolute source `path`,
explicit `role` (`problem`, `data`, `template`, `rule`, `description`) and `source`
(`uri`, ISO `accessed_at`, `license`). At least one original problem is required.
Then run:

```powershell
python tools/init_competition_workspace.py --case-id case-id --inputs inputs.json
python -m mathmode validate input_manifest ../competitions/case-id/input_manifest.json --workspace ../competitions/case-id
python -m mathmode status --workspace ../competitions/case-id
```

The default destination is outside this public repository at
`../competitions/<case-id>`. Existing workspaces are never overwritten. Source
files stay unchanged; snapshots are hashed and made read-only. Invalid declarations
are rejected before destination creation. A publication failure may leave an
incomplete new destination for diagnosis; it never merges into existing content.
`--kind fixture` explicitly labels synthetic test workspaces. Initialization does
not verify official policy or run a scientific gate.

The 12 schemas, examples and cross-contract checks live in `mathmode/`,
`华为杯_求解规范/schemas/` and `fixtures/contracts/`. For JSONL assumptions and
decisions preserve every event; supersede instead of rewriting history. New split
contracts require explicit timestamps/groups when relevant. `.gitignore` protects
untracked private workspaces, root solve outputs, environments and secrets; it
does not remove already tracked template assets.

## Actual execution records (T05)

Solver entrypoints accept `--context <JSON path>`; context supplies the snapshot
input map, spec, output directory and seed. Copy the complete declared code bundle
into the private workspace and update `model_spec.implementation`. Outputs are flat
JSON objects/record arrays or CSV rows with declared field names/types/units.
XLSX/TXT require the later task-specific adapter; the runner rejects them for now.

```powershell
python -m mathmode run --workspace ../competitions/case-id --spec model_spec.json --role main --interpreter /path/to/python
python -m mathmode verify-run --workspace ../competitions/case-id --manifest runs/run-id/run_manifest.json
```

Replace `/path/to/python` with the actual interpreter or omit it to use the current
`sys.executable`. Every attempt creates a new directory. Preserve failed runs and
pass `--retry-of <latest-failed-run-id>` after a real repair; unchanged retries and
attempts beyond the three-attempt conservative bound are rejected. Original inputs
remain read-only snapshots. Logs, absolute local paths and package inventory stay
inside the private workspace. Run PASS and verify-run PASS remain execution
integrity findings, never independent scientific approval.

## Independent numerical validation (T06)

Create `validation_criteria.json` with an explicit supported adapter, source-backed
thresholds, symbol dimensions and robustness applicability. Register it as an
original rule input when initializing the workspace. Put its frozen path/hash in
both specs' `validation_plan.criteria` and include its input ID in `spec.inputs`.
Both specs must share question, target/split, outputs, objective and constraints.
Run main and usable baseline, then:

```powershell
python -m mathmode independent-validate --workspace ../competitions/case-id --main-run runs/main-run-id/run_manifest.json --baseline-run runs/baseline-run-id/run_manifest.json
python -m mathmode evidence --workspace ../competitions/case-id --validation validations/validation-id/validation_summary.json --report evidence_gate.json
```

The actual CLI reports generated IDs. Store the evidence report inside the private
workspace. Legacy run logs cannot replace these records. The built-in independent
validator reads original data and final outputs, not the solver's internal state.
It uses an explicit deterministic actor identity, not a fabricated human reviewer.
PASS covers computed adapter checks; model/source semantic review remains separate.
See `fixtures/validation/README.md` for exact data shapes and supported equations.

## Compatibility boundaries to finish in T07–T12

V1 visual/support/paper manifests will have explicit lineage adapters; no adapter
may invent successful execution, independent validation or a frozen value.
Historical figures and private competition workspaces must remain distinguishable
from engineering fixtures. Release notes will identify the final schema migration,
verified CLI sequence, actual historical run, tests and rollback commit.
