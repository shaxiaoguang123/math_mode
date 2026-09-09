# Repair activation authorization audit

The first activation implementation accepted an ordinary successful retry with
the same candidate path, role and predecessor. Its progress helper trusted an
ACTIVE contract without checking the pinned hashes. These were implementation
gaps, not scientific acceptance checks.

Activation now requires the successful run's matching execution authorization,
which run verification checks against the hashed pre-execution plan and actual
repair handoffs. It also requires the latest terminal run for the same question,
method and role. The activation reader rederives all five artifact pins and
identities, validates the timestamp/schema, and checks the canonical location.
Both activation publication and progress writes use the workflow lock.

Progress adoption verifies the record before writing, rejects unknown/probe or
mismatched production roles, and validates canonical progress before and after
the update. Failed checks leave progress bytes unchanged. Existing records retain
their timestamp on repeated activation.

Regression coverage uses actual Python subprocess repairs with fixture reasoning
handoffs. It checks ordinary retry rejection, all five forged SHA pins, role
mismatch rejection, idempotent activation and preservation of the old run pointer.
Fixtures are engineering evidence, not real-provider or historical-science proof.

Still required: bind adoption to the currently selected workflow plan/model,
consume effective spec pointers in workflow gates, preserve multiple activation
events, invalidate validation/assumption/freeze descendants, execute paired
main/baseline runs and generate new independent validation and freeze lineage.
The explicit pointer helper is not the completed workflow transition.
