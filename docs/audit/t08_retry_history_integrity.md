# T08 retry history integrity checkpoint

Parent: `e4f65159dbca8d266d0c3548f79e4ec287c67c31`.
Branch: `feat/mathmode-v2-evidence-runtime`. T08 remains **IN PROGRESS**.

The runner previously selected retry predecessors from schema-valid manifests
without verifying their recorded execution controls. Rewriting both `attempt`
and `retry_of` could retain schema validity while resetting the budget. Modified
failure logs could likewise be consumed as historical records without detection.

Completed matching history now passes `verify_run(require_success=False,
current_sources=False)` before affecting execution. This compares the attempt
with the actual started record and verifies snapshot, log and control hashes.
Canonical code may change for repair; failed evidence remains FAIL and is not
overwritten. Inconsistent historical evidence blocks before a new run directory.

Validation in Conda `test` (Python 3.12):

- `pytest -q tests/test_runner.py tests/test_recovery.py tests/test_probes.py
  tests/test_workflow_fallback.py`: **38 passed in 127.63s**.
- New negatives rewrite a schema-valid attempt/predecessor pair and a failure
  log. The positive case executes a failing program, repairs the canonical code,
  succeeds on attempt two and verifies that the original manifest is unchanged.
- Runner tests retain actual subprocess execution, timeout and three-attempt
  exhaustion checks. Recovery and fallback tests cover their existing scopes;
  role provenance doubles do not establish real agent or historical acceptance.
- `compileall -q mathmode tests`, router/mirror sync (263 files per mirror) and
  `git diff --check`: PASS. Changed runtime/test/workflow files have no scanned
  credential/email/phone patterns or files over 5 MB. Protected assets unchanged.

An initial test version was rejected earlier by the existing schema check because
it changed only the attempt. The final negative changes both fields to model a
schema-valid rewrite and exercises the new historical verification.

This deliberately fails closed on damaged old snapshots and retains the existing
fallback authorization checks, even for historical verification. It is not an
authenticated append-only log: coordinated local rewriting or deletion of all
evidence is outside the trusted-host boundary. Cross-method retry budgets,
automatic failure classification/repair dispatch and diagnostic handling of
corrupted historical evidence still require implementation. No full-suite or CI
PASS is claimed for this checkpoint. T09 through T12, including the complete
historical contest and PR/CI acceptance, remain outstanding.

Fetched `origin/main` is `a179b49` and differs from the original base only through
research reports/index. It has not been merged or rebased into this branch.
