# T06 independent validation and deterministic evidence

Implemented three strict schemas (criteria/summary/evidence), criteria pinned before
execution, separate validator input/code bundles, actual validator subprocess runs,
threshold recomputation, source/run freshness checks, scalar dimensional algebra
and explicit adapters for regression, time series, continuous linear optimization,
first-order reaction and nonnegative directed shortest paths.

Conda `test`, Python 3.12.13, Windows: full regression suite **104 passed, 1 skipped**,
followed by **2 additional passing tests** for mandatory coverage/robustness criteria
and unresolved-warning rejection. The skipped symlink creation test still needs a
Windows privilege; the five numerical adapter tests and complete regression
main→baseline→independent-validator→evidence path actually execute. They are not
yet the full five-case pipeline benchmark scheduled for T10.

The complete regression path independently computes main MSE 0 and training-mean
baseline MSE 26 from the synthetic original rows. Replacing predictions with zero
still passes process/output structure, then fails numerical validation/evidence.
The suite also rejects changed measurements, stale source, self-validation,
infeasible linear decisions, reported objective/cost errors, invented graph edges,
mass imbalance, real-data chronological leakage, incompatible dimensions and
unresolved stderr warnings. Bootstrap bounds are sampled from actual holdout errors.

Integration exposed Windows MAX_PATH failures in nested validator snapshots.
Shared canonical roots now use Windows extended paths; the failing nested tests
were rerun successfully alongside workspace/runner tests. No registry/OS settings
were changed. Standalone generated schemas and existing figure mirrors pass drift
checks, and all new modules compile.

Scope limits: adapters implement explicit data/model protocols, not arbitrary
contest models. Dimensional algebra supports scalar Python equalities and fails
closed on unsupported TeX/matrix forms. The linear certificate is for continuous
linear programs only. Criteria/source authenticity, assumptions, semantic quality,
custom validators and real agent/human provenance remain T08 integration work.
Deterministic actor separation is honest tool attribution, not a claim that an
independent human or LLM reviewed the result. Evidence scope is computed model
checks; official compliance remains NOT_RUN and default G0/G8 remain blocked.
