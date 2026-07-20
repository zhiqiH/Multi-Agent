# Benchmark Summary

- Total scored runs: 9
- Best average group: gpt-4o-mini; gpt-5.4-mini; Single Agent (0.5483)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-4o-mini | gpt-5.4-mini | Shared Blackboard | 3 | 0.5340 | 66.7% | 2.67 | 65280.7 | 65.3% | 8.00 | 81.19 | 0.011919 |
| gpt-4o-mini | gpt-5.4-mini | Single Agent | 3 | 0.5483 | 66.7% | 0.33 | 5026.0 | 5.0% | 0.00 | 11.46 | 0.001084 |
| gpt-4o-mini | gpt-5.4-mini | Voting | 3 | 0.5452 | 66.7% | 2.00 | 52105.3 | 52.1% | 8.00 | 54.92 | 0.009130 |

## Low-Scoring / Failure Runs

- mr-03__single_agent__gpt-4o-mini__run01: score=0.0, failure_type=Tool Failure, notes=The submission follows the requested section structure and includes a matrix, but several factual values do not match the benchmark expectations and the source list is not traceable to substantive evidence. The run is also invalid for required evidence acquisition per the audit.
- mr-03__voting__gpt-4o-mini__run01: score=0.0, failure_type=Tool Failure, notes=
- mr-03__shared_blackboard__gpt-4o-mini__run01: score=0.15, failure_type=Over-Collaboration, notes=
- lr-03__shared_blackboard__gpt-4o-mini__run01: score=0.625, failure_type=None, notes=The submission is structurally compliant and evidence-backed, but it violates the exact-three-paper requirement and uses several generic or weakly grounded limitation statements. The references are traceable, and the required sections are present.
- lr-03__voting__gpt-4o-mini__run01: score=0.6355, failure_type=None, notes=
