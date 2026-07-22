# Benchmark Summary

- Total scored runs: 48
- Best average group: gpt-3.5-turbo; gpt-4o-mini; Voting (0.7686)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-3.5-turbo | gpt-4o-mini | Debate | 6 | 0.5286 | 83.3% | 1.50 | 18515.5 | 18.5% | 6.00 | 29.14 | 0.011450 |
| gpt-3.5-turbo | gpt-4o-mini | Dynamic Task Allocation | 6 | 0.6107 | 83.3% | 2.50 | 31914.5 | 31.9% | 10.00 | 43.00 | 0.018606 |
| gpt-3.5-turbo | gpt-4o-mini | Manager-Worker | 6 | 0.6414 | 83.3% | 2.17 | 21201.8 | 21.2% | 7.00 | 30.77 | 0.012538 |
| gpt-3.5-turbo | gpt-4o-mini | Sequential Handoff | 6 | 0.6365 | 83.3% | 1.00 | 10074.0 | 10.1% | 3.00 | 16.81 | 0.006241 |
| gpt-3.5-turbo | gpt-4o-mini | Shared Blackboard | 6 | 0.6173 | 83.3% | 1.33 | 24818.2 | 24.8% | 8.00 | 30.87 | 0.014745 |
| gpt-3.5-turbo | gpt-4o-mini | Single Agent | 6 | 0.7420 | 83.3% | 0.33 | 2540.3 | 2.5% | 0.00 | 5.89 | 0.001686 |
| gpt-3.5-turbo | gpt-4o-mini | Unstructured Group Chat | 6 | 0.6795 | 83.3% | 2.67 | 42790.5 | 42.8% | 12.00 | 45.31 | 0.024312 |
| gpt-3.5-turbo | gpt-4o-mini | Voting | 6 | 0.7686 | 83.3% | 2.00 | 22249.8 | 22.3% | 8.00 | 29.18 | 0.012988 |

## Lowest-Scoring Runs

- mr-03__debate__gpt-3.5-turbo__run01: score=0.0, failure_types=['None'], notes=
- mr-03__dynamic_task_allocation__gpt-3.5-turbo__run01: score=0.15, failure_types=['None'], notes=
- mr-03__manager_worker__gpt-3.5-turbo__run01: score=0.15, failure_types=['None'], notes=
- mr-03__sequential_handoff__gpt-3.5-turbo__run01: score=0.15, failure_types=['None'], notes=
- mr-03__shared_blackboard__gpt-3.5-turbo__run01: score=0.15, failure_types=['None'], notes=
