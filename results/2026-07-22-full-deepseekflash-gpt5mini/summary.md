# Benchmark Summary

- Total scored runs: 192
- Best average group: deepseek-v4-flash; gpt-5-mini; Shared Blackboard (0.8408)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| deepseek-v4-flash | gpt-5-mini | Debate | 24 | 0.7433 | 70.8% | 2.21 | 32854.0 | 32.9% | 6.00 | 63.65 | 0.005473 |
| deepseek-v4-flash | gpt-5-mini | Dynamic Task Allocation | 24 | 0.7674 | 70.8% | 2.75 | 54230.6 | 54.2% | 10.00 | 77.02 | 0.008812 |
| deepseek-v4-flash | gpt-5-mini | Manager-Worker | 24 | 0.7683 | 70.8% | 2.33 | 35402.0 | 35.4% | 7.00 | 81.47 | 0.005986 |
| deepseek-v4-flash | gpt-5-mini | Sequential Handoff | 24 | 0.8172 | 79.2% | 1.00 | 16985.3 | 17.0% | 3.00 | 37.79 | 0.002938 |
| deepseek-v4-flash | gpt-5-mini | Shared Blackboard | 24 | 0.8408 | 83.3% | 2.92 | 50854.5 | 50.9% | 8.00 | 73.31 | 0.008211 |
| deepseek-v4-flash | gpt-5-mini | Single Agent | 24 | 0.7151 | 70.8% | 0.58 | 4596.8 | 4.6% | 0.00 | 15.51 | 0.000839 |
| deepseek-v4-flash | gpt-5-mini | Unstructured Group Chat | 24 | 0.8373 | 79.2% | 4.04 | 72924.1 | 72.9% | 12.00 | 96.21 | 0.011488 |
| deepseek-v4-flash | gpt-5-mini | Voting | 24 | 0.6601 | 70.8% | 1.67 | 27752.0 | 27.8% | 8.00 | 43.74 | 0.004388 |

## Lowest-Scoring Runs

- lr-02__voting__deepseek-v4-flash__run01: score=0.0, failure_types=['Communication Failure', 'Role Confusion', 'Premature Consensus'], notes=The untrusted submission contains only a single tool-call XML fragment and no substantive literature review content. All required sections, citations, and analyses are missing; scores reflect complete absence of deliverables.
- mr-03__debate__deepseek-v4-flash__run01: score=0.0, failure_types=['Coordination Failure', 'Communication Failure', 'Role Confusion', 'Hallucination Propagation', 'Premature Consensus', 'Over-Collaboration', 'Noise Accumulation'], notes=The submission largely meets the task structure and required matrix columns, computes costs correctly, recommends Dropbox Advanced, and justifies exclusions. However, there are inconsistencies in reported Dropbox file-size limits (and omission of Dropbox's higher upload capabilities) that reduce accuracy. Evidence citations are present but some numeric claims appear unverified or inconsistent with typical vendor documentation.
- mr-04__manager_worker__deepseek-v4-flash__run01: score=0.0, failure_types=['Coordination Failure', 'Communication Failure', 'Over-Collaboration', 'Noise Accumulation'], notes=The untrusted submission contains only a web_search tool call targeting microsoft.com and no usable final answer content. All required sections, comparisons, citations, and recommendation are absent, so scores reflect complete lack of deliverable.
- mr-05__single_agent__deepseek-v4-flash__run01: score=0.0, failure_types=['Other Failure'], notes=The submitted content consists solely of tool invocation XML and includes no substantive market-research answer, no pricing, no comparisons, no citations, and no calculations. Scores are minimal across all criteria.
- mr-05__voting__deepseek-v4-flash__run01: score=0.0, failure_types=['Communication Failure', 'Premature Consensus'], notes=The submitted content appears to be only the tool-invocation XML and contains no market-research answer, pricing, comparisons, citations, or calculations. All criteria score zero. The evaluator treated only visible final submission content; tool calls were not treated as fulfilled requirements.
