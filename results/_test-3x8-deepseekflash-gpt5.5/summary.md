# Benchmark Summary

- Total scored runs: 24
- Best average group: deepseek-v4-flash; gpt-5.5; Debate (1.0000)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| deepseek-v4-flash | gpt-5.5 | Debate | 3 | 1.0000 | 100.0% | 0.00 | 2177.7 | 2.2% | 6.00 | 9.55 | 0.000348 |
| deepseek-v4-flash | gpt-5.5 | Dynamic Task Allocation | 3 | 1.0000 | 100.0% | 0.00 | 4941.7 | 4.9% | 10.00 | 15.15 | 0.000766 |
| deepseek-v4-flash | gpt-5.5 | Manager-Worker | 3 | 1.0000 | 100.0% | 0.00 | 3827.0 | 3.8% | 7.00 | 12.49 | 0.000608 |
| deepseek-v4-flash | gpt-5.5 | Sequential Handoff | 3 | 0.7167 | 100.0% | 0.00 | 1411.0 | 1.4% | 3.00 | 5.45 | 0.000224 |
| deepseek-v4-flash | gpt-5.5 | Shared Blackboard | 3 | 1.0000 | 100.0% | 0.00 | 3941.0 | 3.9% | 8.00 | 10.75 | 0.000600 |
| deepseek-v4-flash | gpt-5.5 | Single Agent | 3 | 0.7167 | 100.0% | 0.00 | 165.3 | 0.2% | 0.00 | 1.15 | 0.000025 |
| deepseek-v4-flash | gpt-5.5 | Unstructured Group Chat | 3 | 0.7167 | 100.0% | 0.00 | 5030.0 | 5.0% | 12.00 | 14.49 | 0.000744 |
| deepseek-v4-flash | gpt-5.5 | Voting | 3 | 0.7167 | 100.0% | 0.00 | 2023.3 | 2.0% | 8.00 | 8.63 | 0.000294 |

## Lowest-Scoring Runs

- lr-00__sequential_handoff__deepseek-v4-flash__run01: score=0.15, failure_types=['Communication Failure', 'Role Confusion', 'Hallucination Propagation'], notes=The answer is minimally formatted but the numeric result is incorrect.
- lr-00__single_agent__deepseek-v4-flash__run01: score=0.15, failure_types=['Other Failure'], notes=
- lr-00__unstructured_group_chat__deepseek-v4-flash__run01: score=0.15, failure_types=['Role Confusion', 'Hallucination Propagation', 'Premature Consensus', 'Over-Collaboration', 'Noise Accumulation'], notes=
- lr-00__voting__deepseek-v4-flash__run01: score=0.15, failure_types=['Hallucination Propagation', 'Premature Consensus'], notes=
- ec-00__debate__deepseek-v4-flash__run01: score=1.0, failure_types=['Hallucination Propagation', 'Over-Collaboration', 'Noise Accumulation'], notes=The answer fully satisfies the requested educational content and formatting constraints.
