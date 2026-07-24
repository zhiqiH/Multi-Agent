# Benchmark Summary

- Total scored runs: 192
- Best average group: gpt-5-nano; deepseek-v4-pro; Single Agent (0.7722)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-5-nano | deepseek-v4-pro | Debate | 24 | 0.7602 | 79.2% | 1.04 | 63069.5 | 15.8% | 6.00 | 72.79 | 0.007357 |
| gpt-5-nano | deepseek-v4-pro | Dynamic Task Allocation | 24 | 0.7191 | 70.8% | 1.00 | 110800.2 | 27.7% | 10.00 | 103.06 | 0.011147 |
| gpt-5-nano | deepseek-v4-pro | Manager-Worker | 24 | 0.6993 | 70.8% | 0.96 | 56010.7 | 14.0% | 7.00 | 73.93 | 0.007154 |
| gpt-5-nano | deepseek-v4-pro | Sequential Handoff | 24 | 0.7420 | 75.0% | 0.67 | 26107.2 | 6.5% | 3.00 | 42.06 | 0.003422 |
| gpt-5-nano | deepseek-v4-pro | Shared Blackboard | 24 | 0.7642 | 79.2% | 1.08 | 87672.9 | 21.9% | 8.00 | 80.92 | 0.008776 |
| gpt-5-nano | deepseek-v4-pro | Single Agent | 24 | 0.7722 | 83.3% | 0.29 | 5044.9 | 1.3% | 0.00 | 11.86 | 0.000922 |
| gpt-5-nano | deepseek-v4-pro | Unstructured Group Chat | 24 | 0.7618 | 75.0% | 1.25 | 156301.8 | 39.1% | 12.00 | 117.83 | 0.014048 |
| gpt-5-nano | deepseek-v4-pro | Voting | 24 | 0.7399 | 75.0% | 0.96 | 55761.2 | 13.9% | 8.00 | 51.45 | 0.005528 |

## Lowest-Scoring Runs

- lr-02__debate__gpt-5-nano__run01: score=0.0, failure_types=['Other Failure'], notes=The submission provides a well-structured review with all required sections and a claim-evidence ledger, but it fails to supply any authentic, identifiable scholarly sources. All citations are placeholders, making the evidence untraceable and the review essentially fabricated. This triggers caps for fabricated citations and unmet evidence policy.
- lr-02__dynamic_task_allocation__gpt-5-nano__run01: score=0.0, failure_types=['Coordination Failure'], notes=
- lr-02__manager_worker__gpt-5-nano__run01: score=0.0, failure_types=['Coordination Failure', 'Role Confusion', 'Hallucination Propagation', 'Manager Bottleneck'], notes=
- lr-02__sequential_handoff__gpt-5-nano__run01: score=0.0, failure_types=['Role Confusion'], notes=
- lr-02__shared_blackboard__gpt-5-nano__run01: score=0.0, failure_types=['Coordination Failure', 'Role Confusion', 'Hallucination Propagation', 'Over-Collaboration', 'Noise Accumulation'], notes=The submission is a template with placeholder sources and no verifiable evidence. It fails to meet the core requirement of using six authentic scholarly sources, resulting in a severe fabrication penalty and a low overall score cap.
