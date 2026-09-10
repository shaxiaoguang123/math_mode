# Real execution fixture

`compute.py` actually reads synthetic original input, computes its sum and a seeded
random draw, and reports the interpreter and environment observations. Tests
initialize a disposable workspace and generate a real `run_manifest` by running
the selected interpreter. No prefilled successful run manifest is checked in.

The test suite also executes raising code, no-output code, a NaN writer, a timeout,
snapshot tampering and changed-code retries. These are intentionally failing
executions; a console string saying PASS cannot change the runner verdict.

Contract: solver receives `--context <absolute JSON path>` containing `inputs`,
`spec`, `output_dir`, `seed`, `entrypoint` and `code_root`. Use only those declared
inputs and write declared final files below `output_dir`. Temporary work belongs
in the fresh process working directory. Main solver and validator must be separate
implementations; the runner itself does not establish their scientific independence.
