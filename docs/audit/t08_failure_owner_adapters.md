# Failure owner adapter routing

`CODE_FAILURE` continues through the independently reviewed code-repair path.
Other diagnosed classes now expose an explicit adapter name and a blocking
reason in the workflow response. The coordinator does not turn an environment,
data, model, validation or policy diagnosis into a generic retry. The named
owner must provide the class-specific evidence and repair handoff before any
new execution can be scheduled.

This is a routing boundary, not an implemented adapter. The adapters remain a
follow-up requirement and no non-code failure is presented as repaired or
scientifically accepted by this change.
