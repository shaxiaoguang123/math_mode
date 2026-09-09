# T08 reviewed retry execution checkpoint

Parent: `db2fe8fcf43aa89cacaa158cd1e5be5b02d0c984`. T08 remains IN PROGRESS.

`run-code-repair` now verifies the independent review, constructs request/review/
candidate pins and executes the candidate using the exact failed predecessor and
execution role. The existing runner enforces the latest predecessor and total
attempt limit. A workflow lock serializes service calls. Resume adopts the latest
terminal run only if its recorded authorization exactly matches, and verifies its
current evidence before returning it. An ordinary retry or another intervening
run is not retroactively authorized. Interrupted reservations retain the existing
recovery requirement. No completed result is silently rerun to seek a better one.

This checkpoint fixes defects in the preceding authorization boundary: candidate
pin path, execution role and predecessor now match the actual reviewed request,
not only caller-supplied arguments. Malformed/extra fields are rejected. Run
verification compares authorization with the hashed pre-execution planned.json
and revalidates current review provenance when current_sources is true. Historical
verification retains recorded authorization equality without claiming that an old
review is current. The schema now actually makes execution_authorization optional,
as documented, so old manifests without this field remain readable.

The unfinished direct workflow invocation was removed during review: it executed
a candidate without adopting the effective model or updating progress, and did
not propagate the requested interpreter. The explicit execution service is usable
and tested, but automatic workflow activation, numerical/semantic/assumption
revalidation and freezing are still pending. Code execution PASS is not scientific
acceptance. No new historical contest or real-provider repair acceptance is claimed.

Tests use real failing and repaired subprocesses with explicit role/provenance
doubles inherited from the staged-repair fixtures. They check the actual repaired
sum, attempt two, identical run identity on resume, unchanged run count, missing
review rejection, altered authorization and exact identity binding. A separate
check covers legacy manifests and rejection of an ordinary retry as a reviewed
repair. Test results are recorded after completion below.

T09 visual/paper/support integration, T10 final CI/benchmark, T11 full historical
contest and T12 release/PR/CI remain outstanding. No merge is authorized.


Validation in Conda test (Python 3.12): runner/code-repair regression completed
43 passed in 207.80s. This run began before the two final added tests; those were
run separately and passed 2 in 14.18s, covering legacy authorization absence and
ordinary-retry rejection. Runtime code was unchanged between these runs. No
full-suite or CI PASS is claimed. Compileall for mathmode/tests, all 43 distributed
schemas, default diff whitespace and router/full 263-file mirror checks passed.
Tests use fresh external temporary directories under the outer workspace and
no pytest cache, avoiding old user-cache permission issues without changing ACLs.
