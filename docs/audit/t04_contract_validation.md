# T04 modeling contracts validation

Implemented strict JSON/paths, twelve generated schemas, standalone synthetic
examples, cross-contract modeling checks, private workspace initialization,
revisioned state and append-only assumption events. No external project code was
copied. Original template and academic-figure assets are preserved.

Validation environment: Conda `test`, Python 3.12.13 on Windows. The suite reports
**73 passed, 1 skipped**; the skipped symlink-creation test requires a Windows
privilege unavailable to this process. Traversal, absolute/UNC/drive paths,
reserved Windows filenames and noncanonical paths are exercised without that
privilege. Python 3.11 and actual Windows junction behavior remain CI follow-up.

Meaningful regressions cover nonfinite/duplicate JSON, DAG cycles/self/unknown
edges, exact question coverage, high ambiguity, diagnostic-only baselines,
untriggered fallback, contradictory risk verdicts, input snapshots/tampering,
split/fit/target/time/group leakage, source/assumption/variable references,
rewritten question outputs, baseline split comparability, fake human attribution,
append-only supersession, concurrent state revision/locks, persistent retry limits,
and transitive stale detection on resume. Contract examples include an explicitly
unexecuted FAIL probe, preventing examples from claiming a scientific success.

Commands: `python -m pytest -q`, `python tools/build_contract_schemas.py --check`,
`python -m compileall -q mathmode tests tools`, and
`python tools/check_skill_parity.py`. The bundle CLI reports
`scope=modeling_contract_consistency`, `scientific_acceptance=NOT_RUN`.

Scope limits: T04 validates declared contracts, not source authenticity, actual
data membership, dimensions of arbitrary formula text, real probe measurements,
human-event authenticity or model correctness. These require T05–T08 runtime,
independent validation and role/evidence integration. Original-input read-only
flags and local locks do not constitute an OS sandbox. G0/G8 remain blocked by the
unverified default competition policy. Full project release remains incomplete.
