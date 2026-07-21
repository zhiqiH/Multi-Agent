# Benchmark Summary

- Total scored runs: 24
- Best average group: gpt-4o-mini; gpt-5.4-mini; Debate (1.0000)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-4o-mini | gpt-5.4-mini | Debate | 3 | 1.0000 | 100.0% | 0.00 | 3108.7 | 3.1% | 6.00 | 14.44 | 0.000753 |
| gpt-4o-mini | gpt-5.4-mini | Dynamic Task Allocation | 3 | 1.0000 | 100.0% | 0.00 | 5990.3 | 6.0% | 10.00 | 17.80 | 0.001232 |
| gpt-4o-mini | gpt-5.4-mini | Manager-Worker | 3 | 1.0000 | 100.0% | 0.00 | 4812.3 | 4.8% | 7.00 | 19.66 | 0.001141 |
| gpt-4o-mini | gpt-5.4-mini | Sequential Handoff | 3 | 0.7167 | 100.0% | 0.00 | 1406.3 | 1.4% | 3.00 | 4.89 | 0.000287 |
| gpt-4o-mini | gpt-5.4-mini | Shared Blackboard | 3 | 1.0000 | 100.0% | 0.00 | 5797.3 | 5.8% | 8.00 | 17.22 | 0.001176 |
| gpt-4o-mini | gpt-5.4-mini | Single Agent | 3 | 0.6458 | 100.0% | 0.00 | 172.0 | 0.2% | 0.00 | 1.10 | 0.000032 |
| gpt-4o-mini | gpt-5.4-mini | Unstructured Group Chat | 3 | 0.9042 | 100.0% | 0.00 | 7622.7 | 7.6% | 12.00 | 19.75 | 0.001448 |
| gpt-4o-mini | gpt-5.4-mini | Voting | 3 | 0.7167 | 100.0% | 0.00 | 2052.7 | 2.1% | 8.00 | 6.43 | 0.000341 |

## Low-Scoring / Failure Runs

- lr-test-01__sequential_handoff__gpt-4o-mini__run01: score=0.15, failure_type=None, notes=
- lr-test-01__single_agent__gpt-4o-mini__run01: score=0.15, failure_type=None, notes=
- lr-test-01__voting__gpt-4o-mini__run01: score=0.15, failure_type=None, notes=
- ec-test-01__unstructured_group_chat__gpt-4o-mini__run01: score=0.7125, failure_type=None, notes=
- ec-test-01__single_agent__gpt-4o-mini__run01: score=0.7875, failure_type=None, notes=The answer is conceptually correct and beginner-friendly, but it does not satisfy the exact two-sentence format requirement.
