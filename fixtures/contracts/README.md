# Synthetic contract examples

These repository-authored examples exercise schema and cross-contract consistency.
They contain no executed modeling result, actual human approval or provider call.
The illustrative risk probe deliberately reports FAIL. Contract validation PASS
does not authorize execution, freeze, scientific acceptance or official compliance.

Regenerate with `python tools/build_contract_examples.py`. The tracked problem
fixture is writable in a Git checkout; `input_manifest.json` illustrates the
read-only snapshot that workspace initialization creates. To verify input bytes and
read-only permissions, use an initialized workspace, not the fixture source folder.
