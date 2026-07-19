# Benchmark Summary

- Total scored runs: 48
- Best average group: gpt-4o-mini; gpt-5.4-mini; Sequential Handoff (0.7294)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-4o-mini | gpt-5.4-mini | Debate | 6 | 0.6296 | 83.3% | 1.17 | 27025.7 | 27.0% | 6.00 | 47.17 | 0.005685 |
| gpt-4o-mini | gpt-5.4-mini | Dynamic Task Allocation | 6 | 0.6324 | 100.0% | 1.17 | 36728.5 | 36.7% | 10.00 | 62.27 | 0.007656 |
| gpt-4o-mini | gpt-5.4-mini | Manager-Worker | 6 | 0.6658 | 83.3% | 1.33 | 26574.3 | 26.6% | 7.00 | 49.86 | 0.005747 |
| gpt-4o-mini | gpt-5.4-mini | Sequential Handoff | 6 | 0.7294 | 100.0% | 0.67 | 11086.7 | 11.1% | 3.00 | 24.77 | 0.002524 |
| gpt-4o-mini | gpt-5.4-mini | Shared Blackboard | 6 | 0.6355 | 100.0% | 0.67 | 34708.8 | 34.7% | 8.00 | 51.40 | 0.006950 |
| gpt-4o-mini | gpt-5.4-mini | Single Agent | 6 | 0.6561 | 100.0% | 0.17 | 1438.7 | 1.4% | 0.00 | 6.35 | 0.000461 |
| gpt-4o-mini | gpt-5.4-mini | Unstructured Group Chat | 6 | 0.5783 | 83.3% | 1.33 | 52677.8 | 52.7% | 12.00 | 68.63 | 0.010431 |
| gpt-4o-mini | gpt-5.4-mini | Voting | 6 | 0.6066 | 100.0% | 1.33 | 21477.2 | 21.5% | 8.00 | 30.86 | 0.004206 |

## Low-Scoring / Failure Runs

- mr-03__debate__gpt-4o-mini__run01: score=0.0, failure_type=Hallucination Propagation, notes=['Structural requirements were mostly present, but the recommendation and core comparative facts conflict with the task constraints.', 'The submission contains multiple unsupported pricing and file-limit claims and does not select the required platform.']
- mr-03__dynamic_task_allocation__gpt-4o-mini__run01: score=0.0, failure_type=Hallucination Propagation, notes=['Structural requirements were mostly present, but the core recommendation and several key factual claims conflict with the task constraints.', 'The matrix headers match the required format, but the values are materially incorrect for the benchmark expectations.']
- mr-03__manager_worker__gpt-4o-mini__run01: score=0.0, failure_type=Hallucination Propagation, notes=
- mr-03__sequential_handoff__gpt-4o-mini__run01: score=0.0, failure_type=Hallucination Propagation, notes=
- mr-03__shared_blackboard__gpt-4o-mini__run01: score=0.0, failure_type=Hallucination Propagation, notes=
