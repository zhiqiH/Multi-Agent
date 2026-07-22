# Benchmark Summary

- Total scored runs: 192
- Best average group: deepseek-v4-flash; deepseek-v4-flash; Shared Blackboard (0.8870)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| deepseek-v4-flash | deepseek-v4-flash | Debate | 24 | 0.7531 | 70.8% | 2.21 | 32854.0 | 32.9% | 6.00 | 63.65 | 0.005473 |
| deepseek-v4-flash | deepseek-v4-flash | Dynamic Task Allocation | 24 | 0.7875 | 70.8% | 2.75 | 54230.6 | 54.2% | 10.00 | 77.02 | 0.008812 |
| deepseek-v4-flash | deepseek-v4-flash | Manager-Worker | 24 | 0.7905 | 70.8% | 2.33 | 35402.0 | 35.4% | 7.00 | 81.47 | 0.005986 |
| deepseek-v4-flash | deepseek-v4-flash | Sequential Handoff | 24 | 0.8283 | 79.2% | 1.00 | 16985.3 | 17.0% | 3.00 | 37.79 | 0.002938 |
| deepseek-v4-flash | deepseek-v4-flash | Shared Blackboard | 24 | 0.8870 | 83.3% | 2.92 | 50854.5 | 50.9% | 8.00 | 73.31 | 0.008211 |
| deepseek-v4-flash | deepseek-v4-flash | Single Agent | 24 | 0.7447 | 70.8% | 0.58 | 4596.8 | 4.6% | 0.00 | 15.51 | 0.000839 |
| deepseek-v4-flash | deepseek-v4-flash | Unstructured Group Chat | 24 | 0.8800 | 79.2% | 4.04 | 72924.1 | 72.9% | 12.00 | 96.21 | 0.011488 |
| deepseek-v4-flash | deepseek-v4-flash | Voting | 24 | 0.6306 | 70.8% | 1.67 | 27752.0 | 27.8% | 8.00 | 43.74 | 0.004388 |

## Lowest-Scoring Runs

- lr-02__voting__deepseek-v4-flash__run01: score=0.0, failure_types=['Role Confusion'], notes=The submission is not a literature review; it is only a tool call. All criteria are scored 0 because no substantive content is provided. The overall score cap is 0.5 due to missing sources and evidence policy violation.
- mr-03__debate__deepseek-v4-flash__run01: score=0.0, failure_types=['None'], notes=The submission incorrectly states Dropbox Advanced max file upload limit as 100 GB (web) and 50 GB (desktop), which contradicts the expected ground truth of up to 2TB. This is a factual error but does not trigger a hard fail rule. The recommendation is still Dropbox Advanced, and Box is correctly eliminated. The error reduces accuracy and completeness slightly.
- mr-04__dynamic_task_allocation__deepseek-v4-flash__run01: score=0.0, failure_types=['Coordination Failure', 'Over-Collaboration'], notes=The submission is a single error message indicating token budget exhaustion. It contains no content, no sources, no comparison, and no recommendation. All criteria scores are 0. The overall score cap is set to 0.4 due to multiple hard fail conditions, but the base score is 0, so final score is 0.
- mr-04__manager_worker__deepseek-v4-flash__run01: score=0.0, failure_types=['Coordination Failure', 'Communication Failure', 'Over-Collaboration', 'Manager Bottleneck', 'Noise Accumulation'], notes=The submission is not a valid answer; it is a raw tool call JSON with no content. All criteria are scored 0. Caps are applied due to missing evidence and fabrication (no answer).
- mr-05__single_agent__deepseek-v4-flash__run01: score=0.0, failure_types=['None'], notes=The submission is not a final answer; it is a raw tool call JSON. No content to evaluate. All criteria fail.
