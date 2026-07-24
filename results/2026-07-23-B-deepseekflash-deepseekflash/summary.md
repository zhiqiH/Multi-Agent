# Benchmark Summary

- Total scored runs: 9
- Best average group: deepseek-v4-flash; deepseek-v4-flash; Unstructured Group Chat (1.0000)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| deepseek-v4-flash | deepseek-v4-flash | Debate | 3 | 0.7167 | 66.7% | 2.00 | 46281.3 | 15.4% | 6.00 | 99.02 | 0.007648 |
| deepseek-v4-flash | deepseek-v4-flash | Unstructured Group Chat | 3 | 1.0000 | 100.0% | 2.33 | 101172.7 | 33.7% | 12.00 | 163.81 | 0.016179 |
| deepseek-v4-flash | deepseek-v4-flash | Voting | 3 | 0.7167 | 66.7% | 1.00 | 46112.3 | 15.4% | 8.00 | 85.08 | 0.007392 |

## Lowest-Scoring Runs

- lr-02__debate__deepseek-v4-flash__run01: score=0.15, failure_types=['Other Failure'], notes=The submission contains only a tool call message and no final answer content. All criteria are scored 0 because no substantive response is provided. The evidence policy is violated, triggering a 50% cap. The detected failure risks are listed as potential issues, but the primary failure is the absence of any answer.
- lr-02__voting__deepseek-v4-flash__run01: score=0.15, failure_types=['Other Failure'], notes=The submission contains only a tool call and no final answer content. All criteria are scored 0 due to absence of required content. Caps applied per hard fail rules.
- ec-02__debate__deepseek-v4-flash__run01: score=1.0, failure_types=['None'], notes=The submission fully satisfies all criteria with no errors or inconsistencies.
- ec-02__unstructured_group_chat__deepseek-v4-flash__run01: score=1.0, failure_types=['None'], notes=All criteria fully satisfied; no hard fail conditions triggered; submission is complete, consistent, and correct.
- ec-02__voting__deepseek-v4-flash__run01: score=1.0, failure_types=['None'], notes=The submission fully satisfies all criteria and contains no errors or inconsistencies.
