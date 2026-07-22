# Benchmark Summary

- Total scored runs: 48
- Best average group: gpt-3.5-turbo; gpt-4o-mini; Single Agent (0.8043)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-3.5-turbo | gpt-4o-mini | Debate | 6 | 0.6104 | 83.3% | 0.17 | 18186.3 | 18.2% | 6.00 | 26.67 | 0.011185 |
| gpt-3.5-turbo | gpt-4o-mini | Dynamic Task Allocation | 6 | 0.6221 | 83.3% | 1.33 | 26991.7 | 27.0% | 10.00 | 35.41 | 0.016107 |
| gpt-3.5-turbo | gpt-4o-mini | Manager-Worker | 6 | 0.5542 | 83.3% | 0.17 | 19961.7 | 20.0% | 7.00 | 33.87 | 0.013031 |
| gpt-3.5-turbo | gpt-4o-mini | Sequential Handoff | 6 | 0.5171 | 83.3% | 0.00 | 10434.5 | 10.4% | 3.00 | 18.17 | 0.006682 |
| gpt-3.5-turbo | gpt-4o-mini | Shared Blackboard | 6 | 0.4160 | 83.3% | 0.00 | 33616.5 | 33.6% | 8.00 | 40.22 | 0.019705 |
| gpt-3.5-turbo | gpt-4o-mini | Single Agent | 6 | 0.8043 | 83.3% | 0.17 | 2405.0 | 2.4% | 0.00 | 7.56 | 0.001950 |
| gpt-3.5-turbo | gpt-4o-mini | Unstructured Group Chat | 6 | 0.4850 | 100.0% | 3.17 | 47381.0 | 47.4% | 12.00 | 49.50 | 0.027387 |
| gpt-3.5-turbo | gpt-4o-mini | Voting | 6 | 0.7598 | 83.3% | 0.00 | 25744.0 | 25.7% | 8.00 | 34.24 | 0.015477 |

## Lowest-Scoring Runs

- lr-05__dynamic_task_allocation__gpt-3.5-turbo__run01: score=0.0, failure_types=['None'], notes=
- mr-05__sequential_handoff__gpt-3.5-turbo__run01: score=0.0, failure_types=['Other Failure'], notes=
- mr-05__shared_blackboard__gpt-3.5-turbo__run01: score=0.0, failure_types=['Other Failure'], notes=
- mr-05__voting__gpt-3.5-turbo__run01: score=0.0, failure_types=['Other Failure'], notes=
- lr-05__manager_worker__gpt-3.5-turbo__run01: score=0.15, failure_types=['None'], notes=
