# Benchmark Summary

- Total scored runs: 192
- Best average group: gpt-4o-mini; deepseek-v4-pro; Debate (0.6476)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-4o-mini | deepseek-v4-pro | Debate | 24 | 0.6476 | 91.7% | 1.38 | 46615.9 | 11.7% | 6.00 | 88.56 | 0.010056 |
| gpt-4o-mini | deepseek-v4-pro | Dynamic Task Allocation | 24 | 0.6468 | 87.5% | 1.75 | 79917.9 | 20.0% | 10.00 | 119.69 | 0.015690 |
| gpt-4o-mini | deepseek-v4-pro | Manager-Worker | 24 | 0.6206 | 83.3% | 1.17 | 39299.0 | 9.8% | 7.00 | 77.59 | 0.008927 |
| gpt-4o-mini | deepseek-v4-pro | Sequential Handoff | 24 | 0.6192 | 87.5% | 0.62 | 18436.5 | 4.6% | 3.00 | 43.60 | 0.004331 |
| gpt-4o-mini | deepseek-v4-pro | Shared Blackboard | 24 | 0.5949 | 87.5% | 1.58 | 75309.6 | 18.8% | 8.00 | 85.61 | 0.014499 |
| gpt-4o-mini | deepseek-v4-pro | Single Agent | 24 | 0.5719 | 79.2% | 0.17 | 3419.6 | 0.9% | 0.00 | 12.36 | 0.000997 |
| gpt-4o-mini | deepseek-v4-pro | Unstructured Group Chat | 24 | 0.6061 | 91.7% | 2.50 | 136382.0 | 34.1% | 12.00 | 117.57 | 0.024792 |
| gpt-4o-mini | deepseek-v4-pro | Voting | 24 | 0.6334 | 83.3% | 0.79 | 41890.0 | 10.5% | 8.00 | 69.75 | 0.008234 |

## Lowest-Scoring Runs

- lr-02__sequential_handoff__gpt-4o-mini__run01: score=0.0, failure_types=['Role Confusion', 'Hallucination Propagation'], notes=The submission includes two fabricated sources, which severely impacts credibility and violates evidence requirements. The analysis is superficial and lacks depth in tradeoffs and cross-paper comparison. The claim-evidence ledger is present but weak. Overall, the review does not meet the standards for a reliable evidence-based literature review.
- lr-02__single_agent__gpt-4o-mini__run01: score=0.0, failure_types=['Other Failure'], notes=The submission includes two sources with placeholder DOIs that appear fabricated, severely undermining authenticity. The analysis is superficial and lacks deep cross-paper comparison. The claim-evidence ledger is present but some claims are weakly supported. The overall score is capped at 40% due to material fabrication.
- lr-02__unstructured_group_chat__gpt-4o-mini__run01: score=0.0, failure_types=['Coordination Failure', 'Role Confusion', 'Hallucination Propagation', 'Premature Consensus', 'Over-Collaboration', 'Noise Accumulation'], notes=The submission attempts to cover all required sections but suffers from likely fabricated sources, shallow analysis, and weak cross-paper comparison. The duplicate DOIs and generic source details strongly suggest fabrication, which severely undermines the review's credibility. The claim-evidence ledger is present but lacks depth and traceability. The overall score is capped at 40% due to material fabrication and evidence policy violation.
- lr-02__voting__gpt-4o-mini__run01: score=0.0, failure_types=['Hallucination Propagation'], notes=The submission covers the required structure and topics but suffers from likely fabricated sources, reducing evidence reliability. The analysis is superficial in several areas, and the claim-evidence ledger lacks depth. The overall score is capped at 50% due to evidence policy violation.
- lr-04__debate__gpt-4o-mini__run01: score=0.0, failure_types=['Hallucination Propagation'], notes=The submission covers all required sections and categories, but the technical depth is shallow, the references are not verifiable, and the research gap is not well-supported. The evidence cap is triggered due to insufficient source traceability.
