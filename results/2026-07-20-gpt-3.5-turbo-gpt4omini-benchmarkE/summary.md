# Benchmark Summary

- Total scored runs: 39
- Best average group: gpt-3.5-turbo; gpt-4o-mini; Unstructured Group Chat (0.7392)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-3.5-turbo | gpt-4o-mini | Debate | 3 | 0.7275 | 100.0% | 0.00 | 14520.3 | 14.5% | 6.00 | 24.81 | 0.009988 |
| gpt-3.5-turbo | gpt-4o-mini | Dynamic Task Allocation | 4 | 0.5919 | 75.0% | 0.50 | 32762.0 | 32.8% | 10.00 | 40.17 | 0.019469 |
| gpt-3.5-turbo | gpt-4o-mini | Manager-Worker | 3 | 0.6758 | 100.0% | 0.00 | 15149.0 | 15.2% | 7.00 | 29.35 | 0.010752 |
| gpt-3.5-turbo | gpt-4o-mini | Sequential Handoff | 4 | 0.6106 | 100.0% | 0.00 | 6257.5 | 6.3% | 3.00 | 12.99 | 0.004549 |
| gpt-3.5-turbo | gpt-4o-mini | Shared Blackboard | 4 | 0.4888 | 100.0% | 0.00 | 23710.5 | 23.7% | 8.00 | 30.40 | 0.014778 |
| gpt-3.5-turbo | gpt-4o-mini | Single Agent | 5 | 0.6370 | 80.0% | 0.20 | 2384.0 | 2.4% | 0.00 | 7.12 | 0.001894 |
| gpt-3.5-turbo | gpt-4o-mini | Unstructured Group Chat | 3 | 0.7392 | 100.0% | 0.00 | 23109.7 | 23.1% | 12.00 | 25.06 | 0.013764 |
| gpt-3.5-turbo | gpt-4o-mini | Voting | 4 | 0.6181 | 100.0% | 0.00 | 18733.8 | 18.7% | 8.00 | 23.34 | 0.011955 |


## Low-Scoring / Failure Runs

- lr-05__shared_blackboard__gpt-3.5-turbo__run01: score=0.15, failure_type=Tool Failure, notes=The submission is fundamentally flawed due to the lack of required sections and inaccuracies in the content.
- mr-05__dynamic_task_allocation__gpt-3.5-turbo__run01: score=0.15, failure_type=Tool Failure, notes=The submission did not fulfill any of the required sections or provide accurate information.
