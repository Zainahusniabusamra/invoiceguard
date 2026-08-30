# Baseline vs Agent Comparison

## Headline Metric: Actionability Rate

| Metric | Baseline (no AI) | Agent (with AI) |
|---|---|---|
| Cases with a clear, human-actionable next step | 0/10 (0%) | 6/6 review cases (100%) |
| Cases explaining WHY the discrepancy matters | 0/10 (0%) | 6/6 (100%) |
| Average explanation length | 0 words (just an error code) | ~147 words (with evidence + action) |

## Per-Case Breakdown

| Case ID | Baseline Output | Agent Output | Clear Action? |
|---------|-----------------|--------------|---------------|
| case_01 | MATCHED | No | No |
| case_02 | MATCHED | No | No |
| case_03 | MATCHED | No | No |
| case_04 | MATCHED | No | No |
| case_05 | REVIEW_REQUIRED: QTY_MISMATCH | Yes (143 words) | Yes |
| case_06 | REVIEW_REQUIRED: QTY_MISMATCH, QTY_MISMATCH | Yes (155 words) | Yes |
| case_07 | REVIEW_REQUIRED: PRICE_MISMATCH | Yes (139 words) | Yes |
| case_08 | REVIEW_REQUIRED: PRICE_MISMATCH | Yes (125 words) | Yes |
| case_09 | REVIEW_REQUIRED: UNKNOWN_ITEM | Yes (163 words) | Yes |
| case_10 | REVIEW_REQUIRED: MISSING_FIELD | Yes (161 words) | Yes |

## Summary Statistics

- **Total Cases**: 10
- **Matched** (no issues): 4
- **Review Required** (issues found): 6
- **Cases with Clear Next Actions**: 6/6

## Notes

- **Baseline Output**: Status and issue codes from the audit logic (PO vs GR vs Invoice comparison)
- **Agent Output**: Whether the AI generated an explanation (yes/no) and the word count
- **Clear Action**: Whether the explanation includes actionable next steps (contact vendor, verify records, etc.)
