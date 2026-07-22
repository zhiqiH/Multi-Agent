# Benchmark Summary

- Total scored runs: 48
- Best average group: gpt-3.5-turbo; gpt-4o-mini; Shared Blackboard (0.6976)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-3.5-turbo | gpt-4o-mini | Debate | 6 | 0.5337 | 66.7% | 0.17 | 17440.5 | 17.4% | 6.00 | 29.16 | 0.010764 |
| gpt-3.5-turbo | gpt-4o-mini | Dynamic Task Allocation | 6 | 0.4713 | 66.7% | 0.00 | 31041.2 | 31.0% | 10.00 | 41.30 | 0.018098 |
| gpt-3.5-turbo | gpt-4o-mini | Manager-Worker | 6 | 0.5297 | 66.7% | 0.17 | 18797.8 | 18.8% | 7.00 | 33.20 | 0.011989 |
| gpt-3.5-turbo | gpt-4o-mini | Sequential Handoff | 6 | 0.5271 | 83.3% | 0.67 | 9787.5 | 9.8% | 3.00 | 16.32 | 0.006249 |
| gpt-3.5-turbo | gpt-4o-mini | Shared Blackboard | 6 | 0.6976 | 83.3% | 1.67 | 33720.3 | 33.7% | 8.00 | 44.30 | 0.020202 |
| gpt-3.5-turbo | gpt-4o-mini | Single Agent | 6 | 0.6479 | 83.3% | 0.17 | 2790.8 | 2.8% | 0.00 | 7.69 | 0.002182 |
| gpt-3.5-turbo | gpt-4o-mini | Unstructured Group Chat | 6 | 0.4852 | 83.3% | 0.50 | 37851.2 | 37.9% | 12.00 | 42.78 | 0.021797 |
| gpt-3.5-turbo | gpt-4o-mini | Voting | 6 | 0.5354 | 66.7% | 0.00 | 24374.5 | 24.4% | 8.00 | 35.95 | 0.014775 |

## Lowest-Scoring Runs

- lr-02__debate__gpt-3.5-turbo__run01: score=0.0, failure_types=['Coordination Failure'], notes=
- lr-02__dynamic_task_allocation__gpt-3.5-turbo__run01: score=0.0, failure_types=['Coordination Failure'], notes=
- lr-02__manager_worker__gpt-3.5-turbo__run01: score=0.0, failure_types=['Coordination Failure'], notes=
- lr-02__voting__gpt-3.5-turbo__run01: score=0.0, failure_types=['Other Failure'], notes=
- mr-02__dynamic_task_allocation__gpt-3.5-turbo__run01: score=0.0, failure_types=['Coordination Failure'], notes=
