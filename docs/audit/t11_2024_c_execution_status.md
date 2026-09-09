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


