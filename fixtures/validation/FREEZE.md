# Computed freeze fixtures

`tests/test_freeze.py` reuses the actual regression main/baseline/validator runs.
It creates a freeze request pointing to the checked `/measurements/main_mse`, then
lets the service read its value. No frozen numerical value is manually supplied.
All freeze/index/change-log examples are generated during those executions.

The fixture graph's `figure.json` and `paper.json` are explicitly dependency nodes,
not scientific plots or rendered papers. Their purpose is to verify propagation
and blocked gate observations; they never serve as final visual/paper evidence.

Tests cover immutable versions, source locators/units, explicit thaw, downstream
staleness, new runs before refreeze, old-byte preservation, manual snapshot/log
mutation, dependency retention and one-revision registry batches. The latest
question index is `frozen_numbers.json`; numerical snapshots live under `freezes/`.
