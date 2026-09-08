# T07 immutable freeze and stale propagation

Implemented freeze request/snapshot/index/event schemas, exact finite JSON Pointer
reads, unit/precision checks, immutable per-question versions, an append-only
hash-linked change log, explicit thaw, new runs/validation before refreeze and
registered transitive dependency propagation. Root `frozen_numbers.json` is a
pointer index, not an editable table of numeric values.

Windows Conda `test`, Python 3.12.13: the complete regression suite reports
**119 passed, 1 skipped** in 142.19 seconds. A subsequent dependency-retention test
plus two targeted transaction/staleness regressions report **3 passed**. The one
skipped symlink-creation test still requires Windows privilege. Generated schemas,
compilation and both original figure-skill mirrors pass their checks.

The freeze fixtures actually execute regression main/baseline/independent
validation before freezing MSE from its source locator. Tests verify read-only
archives, version identity, refusal to overwrite an active freeze, downstream
paper/gate invalidation, fresh execution after thaw, preservation of previous
snapshot bytes, rejection of manually changed numbers/hash-chain events, wrong
units/unverified sources and invalid/bool/nonfinite numeric locators. Existing
upstream parameter/assumption dependencies survive run binding. Refreshing a broken
freeze does not bypass the explicit-thaw requirement.

Initial registration repeatedly reread the entire growing registry, causing 12
freeze tests to take 171.40 seconds. The registry now validates and publishes a
batch in one revision. Failed batches leave no partial state; targeted refreeze
and propagation tests passed after this change. Multi-file freeze publication is
not claimed to be a filesystem transaction: interrupted index/log/state writes
must fail verification, while immutable snapshots remain available for diagnosis.

Fixture figure/paper JSON files are dependency nodes only, explicitly not rendered
scientific artifacts. Real visual/paper/package adapters and automatic orchestrator
registration remain T08–T09. Local owner access can rewrite files; the chain is a
consistency/audit mechanism, not authentication against the workspace owner.
Official compliance and complete V2 release remain unfulfilled.
