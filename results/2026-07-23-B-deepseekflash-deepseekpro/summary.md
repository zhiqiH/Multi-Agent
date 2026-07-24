# Benchmark Summary

- Total scored runs: 9
- Best average group: deepseek-v4-flash; deepseek-v4-pro; Unstructured Group Chat (1.0000)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| deepseek-v4-flash | deepseek-v4-pro | Debate | 3 | 0.7167 | 66.7% | 2.00 | 46281.3 | 15.4% | 6.00 | 99.02 | 0.007648 |
| deepseek-v4-flash | deepseek-v4-pro | Unstructured Group Chat | 3 | 1.0000 | 100.0% | 2.33 | 101172.7 | 33.7% | 12.00 | 163.81 | 0.016179 |
| deepseek-v4-flash | deepseek-v4-pro | Voting | 3 | 0.7167 | 66.7% | 1.00 | 46112.3 | 15.4% | 8.00 | 85.08 | 0.007392 |

## Lowest-Scoring Runs

- lr-02__debate__deepseek-v4-flash__run01: score=0.15, failure_types=['Role Confusion'], notes=
- lr-02__voting__deepseek-v4-flash__run01: score=0.15, failure_types=['Role Confusion', 'Premature Consensus'], notes=The submission is a single tool call with no actual review content. It fails to meet any of the task requirements.
- ec-02__debate__deepseek-v4-flash__run01: score=1.0, failure_types=['None'], notes=The submission fully satisfies all criteria with correct recurrence, worked table, greedy comparison, timeline, activity, quiz, and consistency audit. No caps or failure risks are triggered.
- ec-02__unstructured_group_chat__deepseek-v4-flash__run01: score=1.0, failure_types=['None'], notes=The submission fully satisfies all criteria with correct recurrence, table, greedy comparison, timeline, and consistency audit. No errors or omissions detected.
- ec-02__voting__deepseek-v4-flash__run01: score=1.0, failure_types=['None'], notes=The submission fully satisfies all criteria with correct recurrence, worked table, greedy comparison, exact 50-minute timeline, consistent artifacts, and no external sources. No failure risks or caps are triggered.
