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

## Freeze and stale propagation (T07)

Freeze requests list `frozen_number_id`, `claim_id`, source path, JSON Pointer,
unit and precision, plus actor/question/decision IDs. Values are read from actual
verified sources. Point checked metrics to `/measurements/<metric>` in the
validation summary, or declared main-output scalar fields to their JSON locators.

```powershell
python -m mathmode freeze --workspace ../competitions/case-id --request freeze_request.json --evidence evidence_gate.json
python -m mathmode verify-freeze --workspace ../competitions/case-id --question-id Q1
python -m mathmode thaw --workspace ../competitions/case-id --question-id Q1 --actor-id orchestrator --reason "Revise model parameters"
python -m mathmode refresh --workspace ../competitions/case-id
```

After thaw, rerun both models, revalidate, produce fresh evidence and freeze a new
version. Old immutable snapshots remain in `freezes/`; root `frozen_numbers.json`
is only the per-question index. Never manually edit snapshot numbers. Register
each derived figure/paper/package with its frozen artifact dependencies using
`ArtifactRegistry`; otherwise it is unregistered and cannot serve as V2 lineage.
V1 numbers/graphs have no automatically inferred provenance and need recomputation.

## T08 contract refinements (in progress)

Generated validation criteria and risk plans are pinned before execution through
`model_spec.validation_plan` and the runner's `contract_snapshots`; no original
manifest rewrite is necessary. Original imported criteria remain supported. Old
runs without these optional sidecars retain the older integrity checks; adding
criteria to an existing run is not migration and requires actual re-execution.

`upstream_freezes` and `fallback_authorization` are optional model-spec extensions.
They are enforced whenever present. A dependent question pins an active parent
freeze; a fallback needs a trigger card pinned before the measured probe. Legacy
files do not gain an implied upstream or fallback authorization.

T08 experimental agent results now require a hashed `bundle` and registered
transport provenance. Earlier smoke-call records remain historical evidence of
those actual calls, but cannot pass the new handoff verifier. Rerun the role to
obtain current provenance; do not backfill or fabricate a session/bundle record.
The successful early council smoke is not claimed to pass this newer verifier.

AGENTS/CLAUDE are generated thin routers from `docs/agent_router.md`, with shared
rules in `docs/runtime_rules.md`. Generate with `tools/sync_agent_assets.py` and
check using `--check`. Both complete figure skill trees are hash-checked without
copying or deleting assets. Historical full routers remain available in Git.

The new `reference_baseline` captures independent read-only copies of all five
pre-reference artifact groups. Existing `blind_reference_mode=true` values do not
authorize same-problem access. Use real framer/writer handoffs and a validated freeze
to seal the baseline before `admit-reference`. This is not a retroactive migration:
already recorded same-problem access prevents reconstructing an alleged blind run.
Method source records must reference supplied snapshots and prior explicit host
admission; arbitrary historic citations do not gain verified retrieval provenance.

New runtime requests record owner/process identities and runner request fingerprints.
Existing completed manifests remain readable; successful new local runs additionally
hash owner/process metadata as execution controls. Recovery records are separate
ABANDONED events, never backfilled run PASS/FAIL evidence. `recover-lock` can release
only a lock whose recorded owner has stopped. Old timestamp-only locks and interrupted
launches without process identities retain an explicit diagnostic blocker; do not
invent missing PID, process birth time, returncode or model session information.
Pre-launch interrupted requests can be distinguished by the absence of a persisted
launch marker. Post-recovery retries require the actual predecessor and retain the
original attempt count. Install the newly declared psutil dependency in the selected
runtime environment; the user's Conda test environment already contained psutil 7.2.2.

The new optional lifecycle coordinator adds `workflow_plan` and `workflow_progress`
to the catalog, now containing 34 schemas. Existing private workspaces remain usable through their
individual services; adopting the coordinator requires a plan naming actual
role-proven framing/spec/review artifacts for every question. No legacy file is
retroactively assigned reasoning provenance. The example plan under
`fixtures/agents/` contains paths/claim locators only, not invented run IDs or values.

Progress is an atomic resume index. The coordinator rechecks hashes and may adopt
actual matching prior runs/validation after pointer loss. Repaired successful runs
replace stale pointers and invalidate their old validation/evidence pointers.
After thaw, unchanged code still requires new main/baseline runs. Existing failed
runs require explicit repair/retry; do not edit their manifests to clear the failure.
The separate workflow lock has the same owner identity rules as the state lock;
`recover-lock --scope workflow` handles only a stopped coordinator. The default
`recover-lock` scope remains state, preserving existing CLI usage.

## Compatibility boundaries to finish in T08–T12

`reference_retrieval` and the optional `method_sources.sources[].retrieval` binding
connect actual HTTP receipts to source summaries. New HTTP method-source handoffs
require the receipt and original downloaded snapshot as task inputs; supplied
non-HTTP/local fixture sources retain their earlier admission checks. A historical
URL plus an arbitrary local file cannot be upgraded by inventing a download time
or response record. Use a real new retrieval to obtain current HTTP provenance.

Declare optional `workflow_plan.reference_requests` only in the trusted host plan;
role workers cannot publish that plan. Stable retrieval IDs allow later scheduled
tasks to reference downloaded snapshots and receipts before those files exist.
Old plans without requests remain unchanged. Failed/interrupted IDs are preserved
for diagnosis, never silently overwritten or retried. Both `references/` and
`reference_baselines/` at the template root are ignored; fixtures and schemas remain
tracked in their own directories. Real reference workspaces stay outside the public
template repository.

`method_decision.execution_role` now optionally distinguishes `main` from
`fallback`; existing records default to main and are not rewritten. To adopt a
fallback, append a real new decision citing the actual triggered main probe and
the fallback's own passing probe. The selected solution stays in `main_method_id`
and the plan's `main_spec` slot; its run is explicitly `role=fallback`. Update both
selected solution and baseline specs to that decision, obtain current independent
reviews, and execute them. A frozen prior solution requires explicit thaw first.
Never relabel an old main run or graft fallback authorization onto its manifest.

Existing `main_run` pointers and metric names are retained for reader compatibility
and refer to the selected production solution. The new workflow reports
`run-fallback`/`adopt-fallback` actions and preserves the actual manifest role.
Previously executed fallback runs can use the independent validator if they pass
their existing authorization/integrity checks; full workflow acceptance additionally
requires the actual decision, both screening reports and independent semantic
reviews. Missing old provenance must be obtained through real new work.

V1 visual/support/paper manifests will have explicit lineage adapters; no adapter
may invent successful execution, independent validation or a frozen value.
Historical figures and private competition workspaces must remain distinguishable
from engineering fixtures. Release notes will identify the final schema migration,
verified CLI sequence, actual historical run, tests and rollback commit.
