# Benchmark Summary

- Total scored runs: 48
- Best average group: gpt-4o-mini; gpt-5.4-mini; Debate (0.7221)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Avg Tokens | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|
| gpt-4o-mini | gpt-5.4-mini | Debate | 6 | 0.7221 | 24706.3 | 6.00 | 82.62 | 0.006539 |
| gpt-4o-mini | gpt-5.4-mini | Dynamic Task Allocation | 6 | 0.6695 | 44839.8 | 10.00 | 119.10 | 0.010435 |
| gpt-4o-mini | gpt-5.4-mini | Manager-Worker | 6 | 0.6852 | 22658.7 | 7.00 | 83.90 | 0.006303 |
| gpt-4o-mini | gpt-5.4-mini | Sequential Handoff | 6 | 0.6954 | 10978.0 | 3.00 | 49.52 | 0.003308 |
| gpt-4o-mini | gpt-5.4-mini | Shared Blackboard | 6 | 0.6340 | 43351.0 | 8.00 | 103.96 | 0.009899 |
| gpt-4o-mini | gpt-5.4-mini | Single Agent | 6 | 0.6669 | 1603.5 | 0.00 | 15.34 | 0.000744 |
| gpt-4o-mini | gpt-5.4-mini | Unstructured Group Chat | 6 | 0.7085 | 67579.2 | 12.00 | 113.82 | 0.013599 |
| gpt-4o-mini | gpt-5.4-mini | Voting | 6 | 0.6994 | 25462.7 | 8.00 | 65.05 | 0.005731 |

## Low-Scoring / Failure Runs

- lr-04__voting__gpt-4o-mini__run01: score=0.3362, failure_type=Hallucination Propagation, notes=
- lr-04__debate__gpt-4o-mini__run01: score=0.37, failure_type=Hallucination Propagation, notes=
- lr-04__sequential_handoff__gpt-4o-mini__run01: score=0.37, failure_type=Hallucination Propagation, notes=
- lr-04__manager_worker__gpt-4o-mini__run01: score=0.3737, failure_type=Hallucination Propagation, notes=
- lr-04__shared_blackboard__gpt-4o-mini__run01: score=0.3737, failure_type=Hallucination Propagation, notes=
