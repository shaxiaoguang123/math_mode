# Windows DOCX replacement regression

During T08 full regression, `test_docx_derived_toc_and_edition_match_policy[False]`
failed with `PermissionError: [WinError 5]` when replacing `derived.docx.cleaning`
over `derived.docx`. The full run had 211 passing tests and one existing Windows
symlink-privilege skip. The same policy test failed again in a focused run, then
passed unchanged in an isolated run (2.28s). Both retained packages were writable.
Inspection confirms the scrubber's source/destination ZIP contexts close before
replacement; no evidence identifies the external holder of the transient denial.

`scrub_package` now retries only Windows permission/sharing/lock errors 5, 32 and
33, with at most three attempts and delays of 0.1s and 0.2s. It does not delete the
destination, alter permissions or touch the original template. Persistent denial
raises the error and preserves both the old generated package and completed
cleaned package for diagnosis. Other permission errors are not retried. This does
not turn an unsuccessful cleanup into a successful build.

The regression tests generate real disposable DOCX packages, explicitly inject
Windows replacement errors, verify bounded attempts/delays and preserved original
bytes, then read the actual successful cleaned DOCX and check removal of author
metadata while retaining body text. Persistent-error tests confirm both packages
remain readable. The transient tests retain the actual short waits because this
Windows host can independently deny the real replacement after injected errors.

Verification after the fix: `tests/test_docx_io.py` and `tests/test_policy.py`
passed **26/26** in 2.99s in Conda test. This is a narrow build reliability repair,
not T09 paper integration or official-format acceptance. Original DOCX, class/sty
and figure assets remain unchanged.
