# Independent numerical evidence fixture

The regression solver reads original synthetic rows and fits ordinary least
squares or a training-mean baseline. `tests/test_validation.py` freezes criteria
before both runs, executes both, creates a separate validator input bundle and
runs the built-in evaluator. It generates real validation/evidence contracts in a
temporary workspace; no successful manifest is prefilled or published.

Changing predictions to zero leaves valid run outputs but fails independent
numerical validation. Other negatives cover self-validation, changed evidence,
stale solver code, fabricated graph edges/cost, linear infeasibility, conservation
failure, chronological leakage, dimensional errors and unresolved warnings.

Five adapter data protocols (all JSON):

| Kind | Original data | Final main/baseline output |
| --- | --- | --- |
| regression/time_series | `rows` with unique `id`, declared features/target; time series also ISO `time` | records with `id`, `prediction` covering exactly holdout |
| optimization | finite `c`, `bounds`, `A_ub`, `b_ub`, `A_eq`, `b_eq` for a continuous linear program | object with decision vector `x` and reported `objective` |
| mechanism | `initial_A`, nonnegative `rate`, unique nonnegative `times` for A→B first-order reaction | records with `time`, `A`, `B` |
| graph | unique `nodes`, directed nonnegative nonparallel `edges` (`from`, `to`, `weight`), `start`, `end` | object with simple node `path`, reported `cost` |

These are specific executable adapters, not universal solutions to contest
problems. The linear oracle uses SciPy HiGHS; graph checks use an independently
implemented shortest-path calculation; reaction checks use the analytic solution
and mass conservation. The numerical unit tests for these adapters are not yet
the full five-case pipeline benchmark required by T10.

Criteria include thresholds, source references, required/nonapplicable robustness
with reason, explicit symbol dimensions and optional bootstrap uncertainty settings.
Dimensional formulae use scalar Python syntax with one equality. Unsupported
TeX/matrix/fractional-dimensional forms fail closed pending reviewed reformulation.
