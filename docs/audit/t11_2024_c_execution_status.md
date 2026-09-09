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

Q4 runner integration has been prepared, but its first long execution ended
without a manifest after the controlling session stopped. It is therefore not
accepted as a run result; the workspace retains the snapshots for diagnosis
and a fresh bounded retry is required.

## Reopened downstream rebuild

After the corrected Q4 rerun, grouped holdout validation was regenerated with
the same material encoding used by the production feature function. The rebuilt
attachment was then checked against the current Q1/Q4 prediction hashes and
the evidence index was refreshed. These artifacts remain draft evidence:
scientific acceptance is still `NOT_RUN`, and no baseline freeze or reference
paper admission is implied.


