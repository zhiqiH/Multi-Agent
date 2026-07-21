# Benchmark Summary

- Total scored runs: 4
- Best average group: gpt-4o-mini; gpt-5.4-mini; Single Agent (0.2612)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-4o-mini | gpt-5.4-mini | Single Agent | 2 | 0.2612 | 50.0% | 1.00 | 6206.0 | 6.2% | 0.00 | 9.26 | 0.001092 |
| gpt-4o-mini | gpt-5.4-mini | Voting | 2 | 0.1737 | 100.0% | 5.00 | 46389.0 | 46.4% | 8.00 | 40.24 | 0.007686 |

## Low-Scoring / Failure Runs

- lr-04__single_agent__gpt-4o-mini__run01: score=0.0, failure_type=Tool Failure, notes=
- lr-04__voting__gpt-4o-mini__run01: score=0.15, failure_type=Role Confusion, notes=
- mr-04__voting__gpt-4o-mini__run01: score=0.1975, failure_type=None, notes=
- mr-04__single_agent__gpt-4o-mini__run01: score=0.5225, failure_type=None, notes=
