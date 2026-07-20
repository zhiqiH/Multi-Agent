# Benchmark Summary

- Total scored runs: 48
- Best average group: gpt-3.5-turbo; gpt-4o-mini; Voting (0.5970)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-3.5-turbo | gpt-4o-mini | Debate | 6 | 0.5524 | 83.3% | 0.00 | 12614.0 | 12.6% | 6.00 | 24.95 | 0.008485 |
| gpt-3.5-turbo | gpt-4o-mini | Dynamic Task Allocation | 6 | 0.4316 | 83.3% | 0.00 | 19130.0 | 19.1% | 10.00 | 31.09 | 0.011770 |
| gpt-3.5-turbo | gpt-4o-mini | Manager-Worker | 6 | 0.4903 | 83.3% | 0.00 | 16279.3 | 16.3% | 7.00 | 32.88 | 0.010895 |
| gpt-3.5-turbo | gpt-4o-mini | Sequential Handoff | 6 | 0.2880 | 83.3% | 0.00 | 6586.7 | 6.6% | 3.00 | 13.05 | 0.004324 |
| gpt-3.5-turbo | gpt-4o-mini | Shared Blackboard | 6 | 0.3534 | 83.3% | 0.00 | 20172.7 | 20.2% | 8.00 | 28.39 | 0.012415 |
| gpt-3.5-turbo | gpt-4o-mini | Single Agent | 6 | 0.5693 | 83.3% | 0.00 | 1424.8 | 1.4% | 0.00 | 5.12 | 0.001191 |
| gpt-3.5-turbo | gpt-4o-mini | Unstructured Group Chat | 6 | 0.4577 | 83.3% | 0.00 | 34359.7 | 34.4% | 12.00 | 41.65 | 0.019925 |
| gpt-3.5-turbo | gpt-4o-mini | Voting | 6 | 0.5970 | 83.3% | 0.00 | 13133.5 | 13.1% | 8.00 | 21.52 | 0.008305 |

## Low-Scoring / Failure Runs

- lr-03__debate__gpt-3.5-turbo__run01: score=0.0, failure_type=Coordination Failure, notes=
- lr-03__dynamic_task_allocation__gpt-3.5-turbo__run01: score=0.0, failure_type=Coordination Failure, notes=
- lr-03__manager_worker__gpt-3.5-turbo__run01: score=0.0, failure_type=Coordination Failure, notes=
- lr-03__sequential_handoff__gpt-3.5-turbo__run01: score=0.0, failure_type=Coordination Failure, notes=
- lr-03__shared_blackboard__gpt-3.5-turbo__run01: score=0.0, failure_type=Coordination Failure, notes=
