# T11 2024 C execution status

The external blind workspace at `F:\project\math_mode\T11_2024_C\blind_workspace`
now contains draft Q1鈥換5 outputs and `outputs/evidence_index.json`. The index
records SHA-256 and byte size for 13 output artifacts, with
`blind_reference_mode=true`, `reference_papers_read=0`, and status `DRAFT`.

Q1/Q4 output-only structural checks passed, but these were host-authored checks,
not independent scientific verification. Q5 checks covered finite values and
deduplication only, not provenance or Pareto correctness against all candidates.
Q2 grouped validation and Q3 descriptive factor checks are recorded.
The output attachment copy preserves the official filename and contains 80 Q1
class entries and 400 Q4 predictions; the original input snapshot is unchanged.

No artifact is frozen. Remaining gates are semantic equation/unit review,
independent numerical validation, sensitivity evidence, complete run manifests,
reference admission only after a sealed blind baseline, paper/figure lineage,
and final audit. Draft metrics must not be described as contest results.

## Input-mapping correction

Direct script inspection subsequently identified material errors in those drafts:

- Q1 used offset 5 for attachment II, dropping the first of 1,024 samples.
- Q4 reused training metadata indices on attachment III, treating sample ID as
  temperature, temperature as frequency and material as waveform. Its training
  holdout scores therefore do not establish correctness of test-set predictions.
- The corrected Q4 rerun now explicitly encodes material from worksheet names (training) and the test material column; its metrics are newly generated and downstream artifacts are stale until rebuilt.
- Q5 ranks observed losses against frequency times peak-to-peak flux, while the
  task requires the Q4 model and peak flux. It also exports only 50 of the
  computed frontier entries. The existing artifact is not a completed Q5 solution.

The external workspace preserves prior output bytes under
`history/input-layout-correction` and records their hashes in
`preflight/input_layout_correction.json`. Q1/Q4 metadata indexing was corrected
and a direct feature-function check verified equal features for equivalent
training/test records and rejection of truncated waveforms. Corrected executions
and downstream revalidation remain required; none of the old PASS labels or
output hashes authorize freezing, paper claims or reference admission.

## Corrected attachment verification

The private `source_project/build_attachment_checked.py` replaces the legacy
builder, whose `source_unchanged` compared a hash with itself. The new builder
checks the original against `input_manifest.json`, pins both prediction files,
verifies sequential ID formulas, stages the result, then reopens it and compares
every cell with the template or the corresponding prediction. Q4 display uses
`0.0`; untouched cells retain their template values. Prior attachment bytes are
archived before replacement.

The actual rebuild passed with 80 Q1 and 400 Q4 entries. Negative checks rejected
a changed Q4 value, an extra classification beyond sample 80, a changed ID formula
and a duplicate prediction ID. The new `attachment4_cell_validation.json` report
is scoped to `host_attachment_cell_consistency`, scientific acceptance `NOT_RUN`.
It supersedes the old attachment report and does not validate either model.

## Q1 runner checkpoint

The private workspace completed a real MathMode runner execution for Q1
(`rf-waveform-runner`). Run `run-d6da348346564069809ec0941c658383` returned
code 0 with runner status `PASS`, `scientific_acceptance=NOT_RUN`, and a
structured prediction artifact containing 80 rows. The manifest records input,
code, interpreter, process, and output SHA-256 values. This is an execution and
provenance checkpoint only; independent validation and evidence gates remain
outstanding.

## Q4 history reverified from manifests

Historical `verify_run(current_sources=False)` verification corrects the prior
interruption diagnosis. The original run
`run-bbd8302dde454614a0116f1f3c71d19d` completed with `PASS` in 252 seconds.
Run `run-0faae49c2b0c48aab05d1b4ea5e8f1ad` returned code 0 but was rejected
with `VALIDATION_FAILURE`: the canonical input manifest/spec changed during
execution. An observation ending without a manifest did not establish that
either process had been interrupted.

Run `run-5ddffaac4b484e32905b68b637a41f5e` completed with `PASS` in 231 seconds
under a different method ID. Its `retry_of` is null, so it is not evidence of a
bounded retry. It also uses 120 trees instead of the original 250: previous
model-quality metrics and attachment predictions do not validate this variant.
All these records remain preserved. Scientific acceptance is `NOT_RUN`.

The original Q1/Q4 prediction-only manifests contain no pinned validation
criteria. They remain execution checkpoints, separate from the labeled Q1
comparison below. Unlabeled official test predictions cannot establish accuracy.

## Q1 grouped development validation

The private child workspace `evaluations/q1-grouped-v1` now contains a real
main/baseline/independent-validator/evidence chain. A parent decoding run
`run-2a5dab5981944671bf728c94b16679e1` preserved all 12,400 labeled training
rows and their 1,024 waveform samples as JSON. It retained source input ID,
worksheet and Excel row identity; its manifest pins the original Excel bytes,
decoder source and derived output. The child input manifest pins that JSON,
the decoder manifest/code and original problem/training sheets. Parent run
verification succeeded before and after evaluation.

Before predictions, the comparison fixed seed 20240921 and a 20% group holdout
by material/temperature/waveform: 9,764 training rows and 2,636 holdout rows.
Duplicates within these groups cannot cross the split. Both candidates use
19 shape features after per-row peak-absolute flux normalization, with fitting
restricted to training IDs. Main uses RF250; the usable baseline is a depth-six
decision tree with minimum leaf size three. This is a new development comparison,
not retrospective validation of the original full-data prediction-only models.

The same criteria hash was pinned into both real runs before execution:
main error and macro-F1 loss <= 0.05; baseline error and macro-F1 loss <= 0.15;
main macro-F1 improvement >= 0; complete coverage and zero split leakage.
These are engineering thresholds, not official competition scoring rules.

- Main: `run-814b8141a23041919e895c23d10d1df0`, runner PASS.
- Baseline: `run-b572ca4c6e41452cb95d8a90faae567c`, runner PASS.
- Independent recomputation: both error rates 0 and macro-F1 1.0; improvement 0.
- Reverified numerical evidence gate: PASS.
- Negative controls rejected missing predictions, duplicate IDs, unknown labels,
  fitting leakage and intentionally wrong predictions. No accepted artifact was
  mutated for these checks.

The parent receipt is `preflight/q1_holdout_checkpoint.json`. The simple baseline
matched RF250 on this partition, so there is no measured advantage for the more
complex classifier. This single partition does not establish seed sensitivity,
out-of-distribution accuracy, independent semantic/assumption review or full
G5 acceptance. No question is frozen and no whole-case baseline is sealed;
same-problem reference PDFs remain unread.

## Reopened downstream rebuild

After the corrected Q4 rerun, grouped holdout validation was regenerated with
the same material encoding used by the production feature function. The rebuilt
attachment was then checked against the current Q1/Q4 prediction hashes and
the evidence index was refreshed. These artifacts remain draft evidence:
scientific acceptance is still `NOT_RUN`, and no baseline freeze or reference
paper admission is implied.


