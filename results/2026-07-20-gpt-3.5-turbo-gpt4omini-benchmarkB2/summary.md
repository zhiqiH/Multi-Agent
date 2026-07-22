# Benchmark Summary

- Total scored runs: 48
- Best average group: gpt-3.5-turbo; gpt-4o-mini; Single Agent (0.8040)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-3.5-turbo | gpt-4o-mini | Debate | 6 | 0.6329 | 66.7% | 0.33 | 15737.3 | 15.7% | 6.00 | 27.17 | 0.009819 |
| gpt-3.5-turbo | gpt-4o-mini | Dynamic Task Allocation | 6 | 0.5939 | 66.7% | 0.17 | 27872.0 | 27.9% | 10.00 | 35.56 | 0.016475 |
| gpt-3.5-turbo | gpt-4o-mini | Manager-Worker | 6 | 0.6592 | 66.7% | 0.33 | 16372.8 | 16.4% | 7.00 | 31.44 | 0.010572 |
| gpt-3.5-turbo | gpt-4o-mini | Sequential Handoff | 6 | 0.6383 | 83.3% | 0.33 | 11082.0 | 11.1% | 3.00 | 18.93 | 0.007131 |
| gpt-3.5-turbo | gpt-4o-mini | Shared Blackboard | 6 | 0.5824 | 66.7% | 0.50 | 22844.7 | 22.8% | 8.00 | 35.29 | 0.013932 |
| gpt-3.5-turbo | gpt-4o-mini | Single Agent | 6 | 0.8040 | 83.3% | 0.17 | 2354.2 | 2.4% | 0.00 | 7.49 | 0.001845 |
| gpt-3.5-turbo | gpt-4o-mini | Unstructured Group Chat | 6 | 0.7150 | 83.3% | 0.17 | 36894.7 | 36.9% | 12.00 | 63.87 | 0.021089 |
| gpt-3.5-turbo | gpt-4o-mini | Voting | 6 | 0.6701 | 83.3% | 1.00 | 23609.2 | 23.6% | 8.00 | 31.24 | 0.013974 |

## Lowest-Scoring Runs

- mr-02__debate__gpt-3.5-turbo__run01: score=0.0, failure_type=Other Failure, notes=
- mr-02__dynamic_task_allocation__gpt-3.5-turbo__run01: score=0.0, failure_type=Other Failure, notes=
- mr-02__sequential_handoff__gpt-3.5-turbo__run01: score=0.0, failure_type=Other Failure, notes=
- mr-02__single_agent__gpt-3.5-turbo__run01: score=0.0, failure_type=Other Failure, notes=
- mr-02__unstructured_group_chat__gpt-3.5-turbo__run01: score=0.0, failure_type=Other Failure, notes=
