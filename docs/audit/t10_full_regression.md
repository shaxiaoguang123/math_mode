# T10 full regression evidence

The complete repository regression was executed in the Conda `test` environment
from the feature branch head `05d23054aa5f7dfcf15ebd65b5371dd75c5e2c9b`:

```text
conda run -n test python -m pytest -q
278 passed, 1 skipped in 1250.20s
```

The single skipped test is the Windows symlink contract, which requires
Developer Mode or symlink privilege. This is an environment capability check,
not a test failure. The run covers the repository's unit, negative fixture,
workflow, evidence, repair, and schema tests. It does not constitute the T11
historical contest dry run or scientific acceptance.
