# Benchmark Summary

- Total scored runs: 48
- Best average group: gpt-3.5-turbo; gpt-4o-mini; Single Agent (0.3021)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-3.5-turbo | gpt-4o-mini | Debate | 6 | 0.2300 | 83.3% | 0.50 | 16592.2 | 16.6% | 6.00 | 25.94 | 0.010388 |
| gpt-3.5-turbo | gpt-4o-mini | Dynamic Task Allocation | 6 | 0.1375 | 83.3% | 0.83 | 23568.0 | 23.6% | 10.00 | 31.13 | 0.013847 |
| gpt-3.5-turbo | gpt-4o-mini | Manager-Worker | 6 | 0.2300 | 83.3% | 0.67 | 14544.3 | 14.5% | 7.00 | 23.75 | 0.009006 |
| gpt-3.5-turbo | gpt-4o-mini | Sequential Handoff | 6 | 0.2629 | 83.3% | 0.17 | 7914.3 | 7.9% | 3.00 | 12.20 | 0.004989 |
| gpt-3.5-turbo | gpt-4o-mini | Shared Blackboard | 6 | 0.1475 | 83.3% | 0.17 | 21758.5 | 21.8% | 8.00 | 27.57 | 0.012918 |
| gpt-3.5-turbo | gpt-4o-mini | Single Agent | 6 | 0.3021 | 83.3% | 0.17 | 1561.2 | 1.6% | 0.00 | 4.49 | 0.001220 |
| gpt-3.5-turbo | gpt-4o-mini | Unstructured Group Chat | 6 | 0.1375 | 83.3% | 0.17 | 41995.7 | 42.0% | 12.00 | 41.76 | 0.024053 |
| gpt-3.5-turbo | gpt-4o-mini | Voting | 6 | 0.2954 | 83.3% | 1.00 | 15931.0 | 15.9% | 8.00 | 21.01 | 0.009156 |

## Low-Scoring / Failure Runs

- lr-04__debate__gpt-3.5-turbo__run01: score=0.0, failure_type=Coordination Failure, notes=
- lr-04__dynamic_task_allocation__gpt-3.5-turbo__run01: score=0.0, failure_type=Coordination Failure, notes=
- lr-04__manager_worker__gpt-3.5-turbo__run01: score=0.0, failure_type=Communication Failure, notes=
- lr-04__sequential_handoff__gpt-3.5-turbo__run01: score=0.0, failure_type=Communication Failure, notes=
- lr-04__shared_blackboard__gpt-3.5-turbo__run01: score=0.0, failure_type=Coordination Failure, notes=
