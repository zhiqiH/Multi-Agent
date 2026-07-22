# Benchmark Summary

- Total scored runs: 24
- Best average group: deepseek-v4-flash; deepseek-v4-pro; Debate (1.0000)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| deepseek-v4-flash | deepseek-v4-pro | Debate | 3 | 1.0000 | 100.0% | 0.00 | 2164.0 | 2.2% | 6.00 | 10.42 | 0.000346 |
| deepseek-v4-flash | deepseek-v4-pro | Dynamic Task Allocation | 3 | 1.0000 | 100.0% | 0.00 | 5183.0 | 5.2% | 10.00 | 16.42 | 0.000801 |
| deepseek-v4-flash | deepseek-v4-pro | Manager-Worker | 3 | 1.0000 | 100.0% | 0.00 | 3938.0 | 3.9% | 7.00 | 14.15 | 0.000629 |
| deepseek-v4-flash | deepseek-v4-pro | Sequential Handoff | 3 | 0.7167 | 100.0% | 0.00 | 1310.7 | 1.3% | 3.00 | 5.63 | 0.000206 |
| deepseek-v4-flash | deepseek-v4-pro | Shared Blackboard | 3 | 1.0000 | 100.0% | 0.00 | 4146.7 | 4.1% | 8.00 | 13.00 | 0.000635 |
| deepseek-v4-flash | deepseek-v4-pro | Single Agent | 3 | 0.7000 | 100.0% | 0.00 | 162.0 | 0.2% | 0.00 | 1.10 | 0.000024 |
| deepseek-v4-flash | deepseek-v4-pro | Unstructured Group Chat | 3 | 1.0000 | 100.0% | 0.00 | 4672.7 | 4.7% | 12.00 | 14.57 | 0.000687 |
| deepseek-v4-flash | deepseek-v4-pro | Voting | 3 | 0.7167 | 100.0% | 0.00 | 1995.0 | 2.0% | 8.00 | 9.28 | 0.000289 |

## Lowest-Scoring Runs

- lr-00__single_agent__deepseek-v4-flash__run01: score=0.1, failure_type=Other Failure, notes=
- lr-00__sequential_handoff__deepseek-v4-flash__run01: score=0.15, failure_type=Hallucination Propagation, notes=The answer is incorrect; the correct character count is 13. The format is correct, but the content is wrong.
- lr-00__voting__deepseek-v4-flash__run01: score=0.15, failure_type=Other Failure, notes=The submission returned 12, which is incorrect; the correct count is 13. The output format meets the minimal requirement, but the answer is wrong, triggering a hard fail cap.
- ec-00__debate__deepseek-v4-flash__run01: score=1.0, failure_type=None, notes=
- ec-00__dynamic_task_allocation__deepseek-v4-flash__run01: score=1.0, failure_type=None, notes=
