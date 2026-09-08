# T08 staged code repair checkpoint

Date: 2026-09-09. Parent: `adba84831a5217167bac6a9c50396c34a7c67f72`.
Branch: `feat/mathmode-v2-evidence-runtime`. T08 remains **IN PROGRESS**.

## Actual implementation

An existing independent CODE_FAILURE diagnosis with remaining numerical attempt
budget now dispatches a code-repair candidate task through workflow advance.
Failed probes use the probe role and its existing directory/phase restrictions;
production models use the code role and the actual screened decision, including
human-decision guards. Exhausted attempts return to the upstream modeling owner
without another code task. Other underlying failure classes retain their owners.

The host-generated `code_repair_request` (additive 2.0, catalog count 43) binds
the actual diagnosis, failed run, unchanged original spec and every original code
snapshot/hash. It derives fixed separate candidate spec/code and review paths.
Request verification recomputes the complete mapping and rejects redirection.
The current selected workflow model/probe must still be the failed source being
repaired. No original model or code is overwritten.

Candidate verification permits only implementation path relocation. The actor,
formulae, parameters, split, seed, inputs, criteria, outputs and resource controls
must remain exactly equal to the failed original spec. The complete candidate
spec/code set must be published by one actual verified code/probe handoff that
received the request, diagnosis and complete failed bundle. A spec pointing to
manually supplied code, or code produced without the actual diagnosis, is
insufficient. Identical code bytes do not constitute a repair.

A second task asks another reviewer, different from both the code author and
diagnostician, to inspect the implementation, original failure, current framing
and selected model pair when present. Required repair references must be cited.
Missing reviews, LIMITED/BLOCKED verdicts, unresolved findings or limitations
cannot produce an accepted code repair. Fixed identities preserve unsuccessful
proposals rather than repeatedly requesting a different verdict. The existing
agent scheduler handles unavailable backends, stale input and prior failed or
interrupted calls without fabricating a successful handoff.

`verify-code-repair` checks the request, full candidate provenance and independent
review. Its PASS scope is `independently_reviewed_code_repair`, with execution and
scientific_acceptance NOT_RUN. Workflow reports the runner as the next owner;
this adapter does not yet activate a new effective model or execute it.

## Verification and limits of the evidence

The positive fixture performs an actual initial failing subprocess, transports a
complete repaired Python implementation and spec, obtains a test-double review,
then explicitly executes the reviewed candidate as attempt two. The resulting
sum is actually 12 for the fixture inputs [2, 3, 7], the run verifies, and original
source/spec/failed-manifest hashes are unchanged. No stale result or authored
numerical output satisfies the repaired execution.

Role judgments, original model/phase provenance and the test scheduler are
explicit doubles. Candidate transport, publication, hashes, retry counting and
Python subprocess execution are real. These tests are not real provider code
generation/review or historical scientific acceptance. Previous real diagnostic
smokes remain separately scoped in t08_failure_diagnosis.md; they are not claimed
to exercise this new candidate adapter.

Negatives cover model/control changes, identical code, limited reviews, request
redirection, changed original code, a replaced workflow model, incomplete producer
output coverage and omitted diagnostic input. CLI checks retain NOT_RUN and do
not create another numerical run. The selected-pair test checks review input
coverage; its baseline is an explicit scope fixture, not a computed comparison.

An initial fixture lacked input registration and correctly failed the real agent
input gate; setup now calls the existing deterministic input preparation service.
No production guard was weakened to make that fixture pass.

Conda `test` validation:

- `tests/test_code_repairs.py tests/test_repairs.py tests/test_contracts.py
  tests/test_agents.py tests/test_orchestrator.py tests/test_workflow.py
  tests/test_workflow_fallback.py`: **126 passed, 1 skipped in 248.88s**. This began
  before the final selected-model/pair and producer-input refinements.
- Final-source `tests/test_code_repairs.py tests/test_repairs.py`: **29 passed in
  115.72s**, including those refinements and the actual sum assertion.
- Earlier focused checkpoints passed 8 tests and then 28 tests; the computed
  repaired-run check separately passed after adding its sum assertion. These
  are intermediate scopes, not replacements for the final checks above.
- Repository compileall, all 43 distributed schemas, both router entries and
  both full 263-file skill mirrors: PASS. Default git diff whitespace check PASS.
  The 18 changed files have no scanned credential/email/phone patterns, no files
  over 5 MB and no protected asset changes. These are pattern scans, not a proof
  of absence of all possible personal information.

The sole broader-suite skip is Windows symlink creation privilege. No tests are
represented as live human, real provider repair or historical contest acceptance.

## Outstanding integrations

Automatic workflow activation, latest-predecessor retry execution, refreshed
numerical/semantic/assumption evidence and refreeze are still required. The
separate candidate model must not be substituted into an old freeze or treated
as active merely because code review passed. Multi-file relocated imports are
the producer's responsibility and are reviewed, not mechanically rewritten.
The current proposal interface emits Python files; auxiliary non-Python bundle
assets need an explicit preservation adapter. Unresolved non-code root causes,
cross-method budgets, reviewed LIMITED repair continuation and full upstream
modeling escalation also remain work.

No full-suite or CI PASS is claimed for this checkpoint. T09 visual/paper/support
lineage, T10 final CI/benchmark, T11 the full historical contest and T12 release/PR
acceptance remain outstanding. Original protected templates and both complete
academic-figure-skill mirrors remain unchanged.
