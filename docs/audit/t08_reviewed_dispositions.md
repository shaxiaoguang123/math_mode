# T08 reviewed warning and LIMITED disposition checkpoint

Date: 2026-09-08. Parent: `c7a10de5f7067b7259f53cf7caf4cc6899e859c7`.
Branch: `feat/mathmode-v2-evidence-runtime`. T08 remains **IN PROGRESS**.

## Observed defect and resulting behavior

The actual generic input auditor counts missingness across all tabular fields,
including unused notes. Its canonical handoff previously rejected every non-PASS
report, so a framer could not even read the warning and reason about its relevance.
The workflow also rejected every LIMITED semantic review without an explicit
reviewed-disposition path. Simply changing these checks to accept WARN/LIMITED
would erase the distinction between numerical execution and justified use.

`Orchestrator._kind` now admits only exactly recomputed audit bytes to inspection,
preserving the original status. Modeling dispatch independently recomputes the
audit and still blocks FAIL. WARN needs a source/proposal/independent-review bundle
with actual role provenance and cited evidence in the task inputs.

The new `issue_disposition` and `disposition_review` contracts bind exact hashes,
question scope, each actual warning/limitation locator, retained use boundaries
and actual input evidence. The checker refuses source errors/BLOCKED, omitted or
invented issues/questions, repair requests, self-approval, approval by the original
reviewer/producer, stale context and missing evidence. A changed source/frame
cannot reuse the old approval. No approved disposition rewrites the source report.

Workflow G2 and affected downstream numerical phases retain LIMITED. Freezing
derives restrictions from independently verified bindings and actual upstream
main/baseline freeze inputs, checks them again under the writer lock and binds
the complete evidence dependencies. Verification recomputes the qualifications.
Changed approvals invalidate the numerical snapshot and downstream consumers.
Bare numerical freezes cannot satisfy a workflow with missing required limits.

`verify-disposition` exposes the restrictions and source/proposal/review pins.
Restricted `freeze`/`verify-freeze` responses explicitly expose LIMITED. Existing
CLI convention is preserved: exit zero means PASS; approved limited use exits one.
Old optional-field-free contracts and numerical snapshots remain readable without
invented approvals or rewriting their history.

## Evidence and boundaries

`tests/test_dispositions.py` uses real synthetic regression/probe/main/baseline
subprocesses, independent numerical validation, immutable freezes and Q1→Q2 inputs.
The extra note field is introduced before workspace initialization; original
snapshots/manifests are not rewritten to construct the warning case. The audit
keeps identical WARN bytes after all qualified transitions. The measured main MSE
is zero; this is an analytically constructed engineering fixture, not a contest
or real-world performance result.

Role provenance is explicitly doubled in the positive engineering cases. Without
that double, the authored proposal/review files cannot satisfy actual handoff
verification. No actual external reasoning approval for a limited historical
scientific claim has been asserted. Tests also cover input-scope/hash rejection
before agent publication, inspection versus modeling admission, errors and repair
refusal, independently limited numerical review, inherited restrictions, explicit
CLI LIMITED status, and both freezes becoming stale after approval tampering.

Initial targeted regression: **66 passed, 1 skipped** in 93.29 seconds in Conda
`test` (Python 3.12.13). The skip is Windows symlink privilege. Final full regression
after the CLI and additional negative checks: **223 passed, 1 skipped** in 859.19
seconds. This includes existing human/fallback/recovery/reference workflows and
the new reviewed-restriction lifecycle. The skip remains Windows symlink privilege.

The 39 schema distributions and both complete 263-file academic-figure-skill
mirrors pass their actual checkers. `git diff --check` passes. No original DOCX,
class/sty, PDF, template figure or skill asset changed.
Full-repository compileall passes. Changed/untracked-file privacy patterns found
no credential, email or phone matches across the 28 intended files; no file exceeds
one megabyte. Actual numerical test workspaces remain outside the template tree.

## Remaining work

This checkpoint provides accounted limited use through explicit role schedules and
host plan bindings. It does not implement automatic disposition-task generation,
data cleaning/preprocessing, measured assumption-sensitivity adapters, automatic
failure repair routing or complete live multi-question role chains. In particular,
an accepted assumption's `sensitivity_status` flag is not measured proof.

T09 visual/paper/support lineage, T10 final CI/benchmark matrix, T11 one complete
public historical contest run and T12 release/PR/CI acceptance remain required.
G7/G8 and unverified official policy still block final acceptance. No PR, CI PASS,
merge, historical dry-run completion or MathMode V2 READY is claimed here.
