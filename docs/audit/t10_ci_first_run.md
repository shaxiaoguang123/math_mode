# First Windows matrix execution

GitHub Actions run 34315045775 tested commit
`3ee5f14a4eecf5c77e7ee3dd0f6f8e08e4a939ac` on Windows:

- Python 3.11: 277 passed, 1 failed (672.51 seconds).
- Python 3.12: 276 passed, 2 failed (682.53 seconds).

Both versions failed `test_failed_production_is_dispatched_to_diagnosis_on_resume`.
The non-code routing change read the planned diagnosis output before a blocked
agent had published it. The diagnosis service now supplies the failure class
only after verification of a completed handoff. Workflow leaves incomplete
diagnosis with the failure reviewer, without opening its planned output or
claiming that a repair adapter is ready.

Python 3.12 also failed the `/slow` HTTP test because its 0.1-second retrieval
budget could expire before the server observed a request. The fixture now
holds the response until cleanup, with a bounded server wait, and allows a
two-second client budget for actual transport setup. It still requires server
observation of prior admission, a failed receipt, and no usable snapshot.
Production timeout behavior is unchanged.

This records a failed CI run and its fixes, not a full-goal acceptance result.
T08 remaining repair integration, T09, historical evaluation and release audits
are still required even if a subsequent CI run succeeds.
