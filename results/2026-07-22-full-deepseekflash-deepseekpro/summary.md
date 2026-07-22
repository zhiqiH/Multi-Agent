# Benchmark Summary

- Total scored runs: 188
- Best average group: deepseek-v4-flash; deepseek-v4-pro; Unstructured Group Chat (0.8531)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| deepseek-v4-flash | deepseek-v4-pro | Debate | 24 | 0.7360 | 70.8% | 2.21 | 32854.0 | 32.9% | 6.00 | 63.65 | 0.005473 |
| deepseek-v4-flash | deepseek-v4-pro | Dynamic Task Allocation | 24 | 0.7714 | 70.8% | 2.75 | 54230.6 | 54.2% | 10.00 | 77.02 | 0.008812 |
| deepseek-v4-flash | deepseek-v4-pro | Manager-Worker | 24 | 0.7739 | 70.8% | 2.33 | 35402.0 | 35.4% | 7.00 | 81.47 | 0.005986 |
| deepseek-v4-flash | deepseek-v4-pro | Sequential Handoff | 24 | 0.8097 | 79.2% | 1.00 | 16985.3 | 17.0% | 3.00 | 37.79 | 0.002938 |
| deepseek-v4-flash | deepseek-v4-pro | Shared Blackboard | 22 | 0.8518 | 86.4% | 2.23 | 51849.0 | 51.8% | 8.00 | 73.48 | 0.008355 |
| deepseek-v4-flash | deepseek-v4-pro | Single Agent | 23 | 0.7325 | 69.6% | 0.61 | 4647.1 | 4.6% | 0.00 | 14.84 | 0.000836 |
| deepseek-v4-flash | deepseek-v4-pro | Unstructured Group Chat | 23 | 0.8531 | 78.3% | 4.22 | 74792.8 | 74.8% | 12.00 | 98.80 | 0.011785 |
| deepseek-v4-flash | deepseek-v4-pro | Voting | 24 | 0.6197 | 70.8% | 1.67 | 27752.0 | 27.8% | 8.00 | 43.74 | 0.004388 |

## Lowest-Scoring Runs

- lr-02__voting__deepseek-v4-flash__run01: score=0.0, failure_types=['Other Failure'], notes=The submission contains only a tool call and no literature review content. All sections and required elements are missing, therefore no criteria are satisfied. The overall score is capped at 50% due to insufficient sources and evidence policy violation.
- mr-03__debate__deepseek-v4-flash__run01: score=0.0, failure_types=['None'], notes=The submission incorrectly reports Dropbox Advanced's maximum file upload limit as 100 GB, whereas the evaluation criteria expect up to 2 TB. This is the only factual error; otherwise the analysis is sound and well-structured.
- lr-02__debate__deepseek-v4-flash__run01: score=0.15, failure_types=['None'], notes=The final submission consists only of a tool-call text with no actual literature review content. No sources, analysis, claim ledger, or any required sections are provided.
- lr-02__dynamic_task_allocation__deepseek-v4-flash__run01: score=0.15, failure_types=['None'], notes=The submission contains only a raw tool call and no part of the required literature review output.
- lr-02__manager_worker__deepseek-v4-flash__run01: score=0.15, failure_types=['None'], notes=The untrusted submission consists solely of a tool-call attempt and does not deliver the required literature review. No substantive content, sources, or analysis are present. Thus, all evaluation criteria receive a score of 0, and evidence requirements are entirely unmet. The overall score cap is set by the strictest applicable hard-fail rule (50%).
