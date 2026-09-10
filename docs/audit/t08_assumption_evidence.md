# T08 predeclared assumption evidence checkpoint

Date: 2026-09-08. Parent: `dce1134e0f415dd7905fab26a00b4c6f96650f95`.
Branch: `feat/mathmode-v2-evidence-runtime`. T08 remains **IN PROGRESS**.

## Observed gap

The workflow checked accepted/rejected assumption events and their question/formula
scope, but did not require measured sensitivity evidence. A hand-authored `tested`
flag could coexist with no experiment, while the semantic review alone permitted
G5. The generic risk probe's assumptions/perturbation categories execute real code,
but do not independently establish production-model sensitivity for every selected
assumption. Those are separate evidence obligations.

## Implemented boundary

An independent reviewer now produces `assumption_plan`, pinning the accepted ledger
and actual main/fallback plus baseline specs. The actor must differ from both solver
authors. It assigns exact assumption IDs to predeclared parameter/seed perturbations
or an explicit NOT_APPLICABLE rationale. The planner consumes those actual hashes;
authored fixtures cannot replace a real role handoff. The catalog has 41 contracts.

The deterministic service creates derived experiment specs and pins the plan into
each run's contract snapshots before execution. Only the declared main-model
parameter or seed changes; the original data, code, split, constraints, criteria
and baseline remain fixed. Duplicate/no-op perturbations, unknown parameters,
incorrect units, missing criteria, incompatible models and invented scenario IDs
are refused. Each actual control/perturbed output is independently recomputed by
the existing source-free numerical validator. Reports preserve observed values,
absolute changes, predeclared limits and failures. Thresholds cannot be retrofitted
onto a completed run. A reported TESTED state is derived from those measurements,
not from the assumption ledger flag. N/A produces no invented experiment.

G5 requires current successful evidence covering exactly the assumptions used by
the selected production and baseline methods. It ignores unselected candidate-only
assumptions. The semantic reviewer must cite the actual plan and report and still
judge applicability. A failed independent check or exceeded sensitivity threshold
blocks assumption acceptance and freezing. Freeze requests/snapshots bind current
assessment report hashes; report or upstream changes invalidate the snapshot.
Every scenario must reuse the actual control baseline execution. Freeze publication
and verification additionally require the report's production-model pins to match
the exact source specs of the main/fallback and baseline runs being frozen; a
different model for the same question cannot donate its assumption assessment.
Old optional-field-free numerical snapshots remain readable but cannot satisfy
new workflow obligations without actual evidence and the normal thaw/recompute
sequence. CLI commands are `assess-assumptions` and `verify-assumptions`.

The workflow lock serializes assessment execution. Resume adopts actual successful
model runs and completed validation summaries. Validation requests are written
before dispatch: a prior request without a completed summary requires diagnosis,
not an automatic fresh validator ID. If report publication succeeded but registry
publication was interrupted, the service recomputes the saved report before
registering it. Failed/stale runs and changed plans are preserved, not overwritten.

## Validation and limitations

Tests execute actual parameter and random-seed changes on a synthetic affine
fixture with small declared noise. The independent numerical checks verify
observed held-out error changes; a separately predeclared strict sensitivity limit
produces FAIL even though the numerical validation itself passes. Other cases
exercise no-report blocking despite a `tested` flag, semantic review requirements,
frozen evidence tampering, current input scope, invalid plans, adoption after an
actual completed validation followed by interruption, interrupted report registry
publication, and refusal to repeat an unfinished validation request.

Positive engineering cases explicitly double only role provenance/judgment. They
do not claim actual independent scientific approval or a live historical contest
run. Existing routing/human/fallback fixtures now supply explicit N/A judgment
doubles for their analytically constructed affine law; these are labeled test
judgments, not fabricated sensitivity measurements. The new perturbation tests
separately exercise the actual measured path. No real user terminal or provider
review acceptance is inferred from these doubles.

Initial targeted checks: **68 passed, 1 skipped** in 223.73s in Conda `test`, before
the additional interruption-recovery negatives. The skip is Windows symlink
privilege. The broad regression completed with **232 passed, 1 skipped** in
987.42s. It began before the final fixed-baseline and production-model binding
guards were added. The final source was then checked with
`tests/test_assessments.py tests/test_freeze.py tests/test_dispositions.py`:
**24 passed** in 306.15s, covering both new association guards, actual experiments,
recovery, freeze integrity and reviewed-limit inheritance. These results have
different scopes; the broad run is not claimed to have exercised the later guards.
Full-repository
compileall, all 41 distributed schemas, both complete 263-file skill mirrors and
diff whitespace checks pass. Changed-file privacy patterns found no credential,
email or phone matches; protected DOCX/class/sty/PDF/figure assets are unchanged.

The present numerical adapter perturbs the main model's parameter or seed while
keeping the baseline fixed. It does not implement input noise/missingness,
baseline perturbations, structural alternative-model experiments, a universal
assumption theorem prover or automatic plan generation/repair routing. Such cases
need appropriate reviewed adapters; an unrelated experiment is not scientific
support merely because the schema and numerical checker pass. Local filesystem
and reviewer identity remain trusted-host boundaries, not OS isolation or person
authentication. An unfinished validator request still needs explicit diagnosis
and repair; no automatic failure recovery result is invented.

T08 live multi-question role chains, remaining source discovery/repair integrations,
T09 visual/paper/support lineage, T10 final CI/benchmark matrix, T11 a complete
public historical contest and T12 release/PR/CI acceptance remain outstanding.
G7/G8 and unverified official policy continue to block final acceptance. This is
a feature checkpoint, not T08 PASS, CI PASS, a merge or MathMode V2 READY.
