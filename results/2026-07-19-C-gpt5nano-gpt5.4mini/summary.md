# Benchmark Summary

- Total scored runs: 48
- Best average group: gpt-5-nano; gpt-5.4-mini; Unstructured Group Chat (0.7450)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-5-nano | gpt-5.4-mini | Debate | 6 | 0.6960 | 100.0% | 1.67 | 23029.5 | 23.0% | 6.00 | 37.03 | 0.003215 |
| gpt-5-nano | gpt-5.4-mini | Dynamic Task Allocation | 6 | 0.6991 | 100.0% | 1.33 | 42520.7 | 42.5% | 10.00 | 58.01 | 0.005318 |
| gpt-5-nano | gpt-5.4-mini | Manager-Worker | 6 | 0.5745 | 100.0% | 1.33 | 29144.3 | 29.1% | 7.00 | 46.90 | 0.004030 |
| gpt-5-nano | gpt-5.4-mini | Sequential Handoff | 6 | 0.7383 | 100.0% | 1.17 | 14897.2 | 14.9% | 3.00 | 26.70 | 0.001991 |
| gpt-5-nano | gpt-5.4-mini | Shared Blackboard | 6 | 0.7049 | 100.0% | 1.17 | 36774.3 | 36.8% | 8.00 | 48.72 | 0.004286 |
| gpt-5-nano | gpt-5.4-mini | Single Agent | 6 | 0.6528 | 100.0% | 0.50 | 4350.0 | 4.3% | 0.00 | 6.99 | 0.000573 |
| gpt-5-nano | gpt-5.4-mini | Unstructured Group Chat | 6 | 0.7450 | 83.3% | 1.50 | 57610.8 | 57.6% | 12.00 | 64.59 | 0.006180 |
| gpt-5-nano | gpt-5.4-mini | Voting | 6 | 0.5117 | 83.3% | 1.50 | 20258.2 | 20.3% | 8.00 | 27.04 | 0.002288 |

## Low-Scoring / Failure Runs

- mr-03__manager_worker__gpt-5-nano__run01: score=0.0, failure_type=Hallucination Propagation, notes=
- mr-03__single_agent__gpt-5-nano__run01: score=0.0, failure_type=Hallucination Propagation, notes=
- lr-03__voting__gpt-5-nano__run01: score=0.15, failure_type=Communication Failure, notes=The submission is empty, so all required sections, paper extraction, synthesis, and references are missing. Tool use occurred in execution, but no traceable evidence was surfaced in the answer.
- mr-03__voting__gpt-5-nano__run01: score=0.15, failure_type=Communication Failure, notes=The submission was empty, so no required sections, matrix, recommendation, or sources were present. No tools were used, which is valid for this prohibited-tool task.
- se-03__voting__gpt-5-nano__run01: score=0.15, failure_type=Communication Failure, notes=The submitted answer was empty, so no substantive claims, structure, or recommendations were present to evaluate beyond absence.
