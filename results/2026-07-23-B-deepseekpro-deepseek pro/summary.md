# Benchmark Summary

- Total scored runs: 9
- Best average group: deepseek-v4-pro; deepseek-v4-pro; Debate (0.8333)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| deepseek-v4-pro | deepseek-v4-pro | Debate | 3 | 0.8333 | 66.7% | 1.33 | 74075.3 | 24.7% | 6.00 | 310.23 | 0.040255 |
| deepseek-v4-pro | deepseek-v4-pro | Unstructured Group Chat | 3 | 0.8333 | 66.7% | 0.67 | 138071.3 | 46.0% | 12.00 | 256.52 | 0.067914 |
| deepseek-v4-pro | deepseek-v4-pro | Voting | 3 | 0.8000 | 66.7% | 1.67 | 125577.3 | 41.9% | 8.00 | 252.14 | 0.060012 |

## Lowest-Scoring Runs

- lr-02__voting__deepseek-v4-pro__run01: score=0.4, failure_types=['Role Confusion', 'Hallucination Propagation', 'Premature Consensus'], notes=The submission fully satisfies all evaluation criteria. It uses exactly six authentic post-2020 sources, covers the required method families, provides a thorough tradeoff analysis, includes a claim-evidence ledger with 12 claims, resolves an apparent disagreement, and identifies three research gaps tied to source limitations. No fabricated content or unsupported claims are detected. The review is well-structured, evidence-calibrated, and helpful for decision-making.
- lr-02__debate__deepseek-v4-pro__run01: score=0.5, failure_types=['Hallucination Propagation'], notes=The submission fully satisfies all evaluation criteria. It uses exactly six authentic post-2020 sources, covers the required method families, provides a thorough tradeoff analysis, includes a well-structured claim-evidence ledger, resolves a genuine tension, and identifies three research gaps tied to source limitations. No fabrication or hallucination is detected.
- lr-02__unstructured_group_chat__deepseek-v4-pro__run01: score=0.5, failure_types=['Hallucination Propagation'], notes=The submission fully satisfies all evaluation criteria. It uses exactly six authentic post-2020 scholarly sources, covers the required method families, provides a detailed source table, a claim-evidence ledger with 12 properly labeled claims, resolves a genuine tension, and identifies three research gaps tied to source limitations. No fabricated sources, unsupported claims, or missing sections are present. The review is well-structured, evidence-calibrated, and helpful for decision-making.
- ec-02__debate__deepseek-v4-pro__run01: score=1.0, failure_types=['None'], notes=The submission fully satisfies all criteria with correct recurrence, worked table, greedy comparison, 50-minute timeline, active learning, quiz, homework, and consistency audit. No external sources or tool use are present. No failure risks are observed.
- ec-02__unstructured_group_chat__deepseek-v4-pro__run01: score=1.0, failure_types=['Hallucination Propagation'], notes=The submission fully satisfies all criteria with correct recurrence, worked table, greedy comparison, timeline, activity, quiz, and consistency audit. No errors, omissions, or inconsistencies detected.
