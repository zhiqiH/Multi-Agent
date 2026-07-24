# Benchmark Summary

- Total scored runs: 192
- Best average group: deepseek-v4-flash; deepseek-v4-pro; Dynamic Task Allocation (0.8292)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| deepseek-v4-flash | deepseek-v4-pro | Debate | 24 | 0.8019 | 75.0% | 2.46 | 42630.1 | 10.7% | 6.00 | 95.64 | 0.007148 |
| deepseek-v4-flash | deepseek-v4-pro | Dynamic Task Allocation | 24 | 0.8292 | 75.0% | 2.96 | 74475.6 | 18.6% | 10.00 | 105.35 | 0.011940 |
| deepseek-v4-flash | deepseek-v4-pro | Manager-Worker | 24 | 0.8151 | 75.0% | 1.88 | 41542.7 | 10.4% | 7.00 | 102.29 | 0.007108 |
| deepseek-v4-flash | deepseek-v4-pro | Sequential Handoff | 24 | 0.7589 | 70.8% | 1.38 | 18045.6 | 4.5% | 3.00 | 43.87 | 0.003184 |
| deepseek-v4-flash | deepseek-v4-pro | Shared Blackboard | 24 | 0.7681 | 70.8% | 1.67 | 68382.1 | 17.1% | 8.00 | 93.17 | 0.011006 |
| deepseek-v4-flash | deepseek-v4-pro | Single Agent | 24 | 0.7513 | 70.8% | 0.50 | 4015.2 | 1.0% | 0.00 | 16.09 | 0.000747 |
| deepseek-v4-flash | deepseek-v4-pro | Unstructured Group Chat | 24 | 0.8244 | 75.0% | 3.46 | 102249.0 | 25.6% | 12.00 | 125.24 | 0.015893 |
| deepseek-v4-flash | deepseek-v4-pro | Voting | 24 | 0.7326 | 70.8% | 1.71 | 37337.0 | 9.3% | 8.00 | 70.25 | 0.006003 |

## Lowest-Scoring Runs

- lr-02__sequential_handoff__deepseek-v4-flash__run01: score=0.0, failure_types=['Other Failure'], notes=The submission consists solely of a tool call and contains no literature review content. All evaluation criteria are unmet. The evidence policy cap of 50% is applied due to the complete absence of sources.
- lr-02__shared_blackboard__deepseek-v4-flash__run01: score=0.0, failure_types=['Role Confusion'], notes=
- lr-02__voting__deepseek-v4-flash__run01: score=0.0, failure_types=['Role Confusion'], notes=
- lr-04__debate__deepseek-v4-flash__run01: score=0.0, failure_types=['Role Confusion'], notes=The submission is empty of any literature review content; it contains only a tool-call attempt. All criteria are scored 0. The evidence policy is violated, triggering a 50% cap. No fabricated sources are present, so hallucination rate is 0.
- lr-04__sequential_handoff__deepseek-v4-flash__run01: score=0.0, failure_types=['Other Failure'], notes=The submission is entirely non-substantive; it contains only tool-call invocations and no review content. All criteria are scored 0. The evidence policy cap of 50% is applied because no sources are cited in the final answer.
