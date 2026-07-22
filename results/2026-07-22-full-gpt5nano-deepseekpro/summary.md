# Benchmark Summary

- Total scored runs: 185
- Best average group: gpt-5-nano; deepseek-v4-pro; Debate (0.7399)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-5-nano | deepseek-v4-pro | Debate | 22 | 0.7399 | 77.3% | 1.18 | 24330.4 | 24.3% | 6.00 | 57.29 | 0.003763 |
| gpt-5-nano | deepseek-v4-pro | Dynamic Task Allocation | 24 | 0.7267 | 75.0% | 1.46 | 41397.5 | 41.4% | 10.00 | 92.21 | 0.006117 |
| gpt-5-nano | deepseek-v4-pro | Manager-Worker | 24 | 0.6730 | 75.0% | 0.46 | 34517.2 | 34.5% | 7.00 | 78.53 | 0.005153 |
| gpt-5-nano | deepseek-v4-pro | Sequential Handoff | 23 | 0.6920 | 69.6% | 0.83 | 16739.3 | 16.7% | 3.00 | 38.48 | 0.002569 |
| gpt-5-nano | deepseek-v4-pro | Shared Blackboard | 22 | 0.6991 | 72.7% | 1.27 | 38727.8 | 38.7% | 8.00 | 79.28 | 0.005146 |
| gpt-5-nano | deepseek-v4-pro | Single Agent | 24 | 0.6304 | 75.0% | 0.08 | 3935.1 | 3.9% | 0.00 | 13.96 | 0.000802 |
| gpt-5-nano | deepseek-v4-pro | Unstructured Group Chat | 22 | 0.6852 | 72.7% | 1.09 | 51800.1 | 51.8% | 12.00 | 99.39 | 0.006978 |
| gpt-5-nano | deepseek-v4-pro | Voting | 24 | 0.3240 | 70.8% | 1.00 | 19843.4 | 19.8% | 8.00 | 40.23 | 0.002552 |

## Lowest-Scoring Runs

- lr-02__dynamic_task_allocation__gpt-5-nano__run01: score=0.0, failure_types=['Other Failure'], notes=
- lr-02__manager_worker__gpt-5-nano__run01: score=0.0, failure_types=['Other Failure'], notes=All citations are fabricated, rendering the evidence base unusable. The structural elements of the review are present, but the lack of authentic sources violates core requirements and triggers a 40% score cap.
- lr-02__sequential_handoff__gpt-5-nano__run01: score=0.0, failure_types=['Communication Failure', 'Role Confusion'], notes=The submission fails to meet the core evidence requirement; all six citations are effectively fabricated with placeholder IDs. This undermines the entire literature review, and even structural strengths cannot compensate for the lack of authentic, verifiable sources.
- lr-02__shared_blackboard__gpt-5-nano__run01: score=0.0, failure_types=['Other Failure'], notes=The submission contains a structurally complete literature review covering required families and sections, but all cited sources are fabricated placeholders, making the content unsupported and the review unusable as evidence. The apparent disagreement and research gaps lack authentic grounding.
- lr-02__single_agent__gpt-5-nano__run01: score=0.0, failure_types=['Other Failure'], notes=The submission is a template with no actual scholarly sources, leaving all required evidence missing. Structure is present but content is entirely generic and unsupported, resulting in a Fail grade.
