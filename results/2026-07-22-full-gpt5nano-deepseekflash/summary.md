# Benchmark Summary

- Total scored runs: 192
- Best average group: gpt-5-nano; deepseek-v4-flash; Unstructured Group Chat (0.7492)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-5-nano | deepseek-v4-flash | Debate | 24 | 0.7360 | 75.0% | 1.12 | 24314.1 | 24.3% | 6.00 | 58.12 | 0.003778 |
| gpt-5-nano | deepseek-v4-flash | Dynamic Task Allocation | 24 | 0.7032 | 75.0% | 1.46 | 41397.5 | 41.4% | 10.00 | 92.21 | 0.006117 |
| gpt-5-nano | deepseek-v4-flash | Manager-Worker | 24 | 0.6694 | 75.0% | 0.46 | 34517.2 | 34.5% | 7.00 | 78.53 | 0.005153 |
| gpt-5-nano | deepseek-v4-flash | Sequential Handoff | 24 | 0.6915 | 70.8% | 0.79 | 16383.5 | 16.4% | 3.00 | 38.62 | 0.002571 |
| gpt-5-nano | deepseek-v4-flash | Shared Blackboard | 24 | 0.7341 | 75.0% | 1.17 | 36895.4 | 36.9% | 8.00 | 79.97 | 0.005146 |
| gpt-5-nano | deepseek-v4-flash | Single Agent | 24 | 0.6471 | 75.0% | 0.08 | 3935.1 | 3.9% | 0.00 | 13.96 | 0.000802 |
| gpt-5-nano | deepseek-v4-flash | Unstructured Group Chat | 24 | 0.7492 | 75.0% | 1.00 | 49774.4 | 49.8% | 12.00 | 100.85 | 0.006996 |
| gpt-5-nano | deepseek-v4-flash | Voting | 24 | 0.3146 | 70.8% | 1.00 | 19843.4 | 19.8% | 8.00 | 40.23 | 0.002552 |

## Lowest-Scoring Runs

- lr-02__dynamic_task_allocation__gpt-5-nano__run01: score=0.0, failure_types=['Coordination Failure'], notes=The submission is incomplete: it lacks actual sources, a filled source table, and specific citations. The content is generic and does not meet the evidence requirements. The claim-evidence ledger and other sections are present but unsupported. The overall score cap is applied due to missing sources and fabricated placeholders.
- lr-02__manager_worker__gpt-5-nano__run01: score=0.0, failure_types=['Coordination Failure', 'Communication Failure', 'Role Confusion', 'Hallucination Propagation', 'Manager Bottleneck'], notes=The submission follows the required structure and covers all analytical sections, but the sources are not authentic (placeholder DOIs, missing details). This triggers the hard fail cap of 40% for fabricated citations. Criterion scores reflect partial satisfaction for C3 and C16 due to placeholder DOIs, and zero for C2 and C18 due to lack of authentic sources.
- lr-02__sequential_handoff__gpt-5-nano__run01: score=0.0, failure_types=['Communication Failure'], notes=The submission contains fabricated sources and placeholder stable IDs, making it unusable as a credible literature review. The structure is followed but lacks authentic evidence.
- lr-02__shared_blackboard__gpt-5-nano__run01: score=0.0, failure_types=['Other Failure'], notes=The submission is well-structured and covers all required sections, but the use of placeholder stable IDs constitutes fabrication, leading to a hard cap at 40%. Criterion scores reflect that C2, C16, and C18 are scored 0 due to fabricated identifiers.
- lr-02__single_agent__gpt-5-nano__run01: score=0.0, failure_types=['Other Failure'], notes=The submission is a structured outline with placeholders but lacks actual sources, failing core requirements. Scores reflect absence of authentic sources and traceable evidence.
