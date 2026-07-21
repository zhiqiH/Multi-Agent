# Benchmark Summary

- Total scored runs: 24
- Best average group: deepseek-v4-flash; deepseek-v4-pro; Debate (1.0000)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| deepseek-v4-flash | deepseek-v4-pro | Debate | 3 | 1.0000 | 100.0% | 0.00 | 2388.7 | 2.4% | 6.00 | 12.93 | 0.000393 |
| deepseek-v4-flash | deepseek-v4-pro | Dynamic Task Allocation | 3 | 0.7667 | 100.0% | 0.00 | 4637.0 | 4.6% | 10.00 | 15.15 | 0.000712 |
| deepseek-v4-flash | deepseek-v4-pro | Manager-Worker | 3 | 1.0000 | 100.0% | 0.00 | 4142.0 | 4.1% | 7.00 | 16.69 | 0.000674 |
| deepseek-v4-flash | deepseek-v4-pro | Sequential Handoff | 3 | 0.7667 | 100.0% | 0.00 | 1334.7 | 1.3% | 3.00 | 6.92 | 0.000210 |
| deepseek-v4-flash | deepseek-v4-pro | Shared Blackboard | 3 | 0.7667 | 100.0% | 0.00 | 4192.0 | 4.2% | 8.00 | 13.48 | 0.000646 |
| deepseek-v4-flash | deepseek-v4-pro | Single Agent | 3 | 0.7667 | 100.0% | 0.00 | 162.3 | 0.2% | 0.00 | 1.32 | 0.000024 |
| deepseek-v4-flash | deepseek-v4-pro | Unstructured Group Chat | 3 | 1.0000 | 100.0% | 0.00 | 4515.7 | 4.5% | 12.00 | 17.63 | 0.000660 |
| deepseek-v4-flash | deepseek-v4-pro | Voting | 3 | 0.7667 | 100.0% | 0.00 | 2006.7 | 2.0% | 8.00 | 8.87 | 0.000291 |

## Low-Scoring / Failure Runs

- lr-00__dynamic_task_allocation__deepseek-v4-flash__run01: score=0.3, failure_type=None, notes=
- lr-00__sequential_handoff__deepseek-v4-flash__run01: score=0.3, failure_type=None, notes=The agent system returned 12 instead of 13, indicating a counting error. The output format is correct (single integer). No tools were used, satisfying the prohibition.
- lr-00__shared_blackboard__deepseek-v4-flash__run01: score=0.3, failure_type=None, notes=The agent system incorrectly counted the characters as 11 instead of 13, missing the space and the period. The output format is correct, but the answer is factually wrong.
- lr-00__single_agent__deepseek-v4-flash__run01: score=0.3, failure_type=None, notes=The agent returned 12 instead of 13, indicating a counting error (likely missing a space or the period). The format is correct, but the answer is factually wrong, triggering the hard fail rule.
- lr-00__voting__deepseek-v4-flash__run01: score=0.3, failure_type=None, notes=The answer is 11 instead of 13, indicating spaces and/or the period were missed. The format is correct (single integer). No tools were used, satisfying the prohibition.
