# Benchmark Summary

- Total scored runs: 8
- Best average group: gpt-4o-mini; gpt-5.4-mini; Shared Blackboard (0.4808)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-4o-mini | gpt-5.4-mini | Shared Blackboard | 3 | 0.4808 | 100.0% | 4.67 | 78437.0 | 78.4% | 8.00 | 102.53 | 0.014371 |
| gpt-4o-mini | gpt-5.4-mini | Single Agent | 3 | 0.3683 | 66.7% | 0.67 | 4778.7 | 4.8% | 0.00 | 13.29 | 0.001091 |
| gpt-4o-mini | gpt-5.4-mini | Voting | 2 | 0.4500 | 100.0% | 3.50 | 33065.0 | 33.1% | 8.00 | 59.44 | 0.006548 |

## Low-Scoring / Failure Runs

- lr-04__single_agent__gpt-4o-mini__run01: score=0.0, failure_type=Tool Failure, notes=
- mr-04__shared_blackboard__gpt-4o-mini__run01: score=0.1175, failure_type=Over-Collaboration, notes=
- mr-04__single_agent__gpt-4o-mini__run01: score=0.3325, failure_type=None, notes=
- mr-04__voting__gpt-4o-mini__run01: score=0.3625, failure_type=None, notes=The submission is structurally close to the requested format but falls short on word count and source quality. The comparison is usable at a high level, yet several claims are not well grounded in the retrieved evidence.
- ec-04__voting__gpt-4o-mini__run01: score=0.5375, failure_type=Over-Collaboration, notes=The submission is substantially aligned with the lesson topic and includes correct metric calculations and scenario mapping, but it is visibly truncated before completing the required final quiz and later sections. No tool use occurred, which is valid for this prohibited-tool task.
