# Benchmark Summary

- Total scored runs: 48
- Best average group: deepseek-v4-flash; deepseek-v4-pro; Unstructured Group Chat (0.8167)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| deepseek-v4-flash | deepseek-v4-pro | Debate | 6 | 0.7288 | 66.7% | 2.17 | 36888.2 | 36.9% | 6.00 | 84.26 | 0.006096 |
| deepseek-v4-flash | deepseek-v4-pro | Dynamic Task Allocation | 6 | 0.7846 | 66.7% | 2.50 | 59364.5 | 59.4% | 10.00 | 104.08 | 0.009758 |
| deepseek-v4-flash | deepseek-v4-pro | Manager-Worker | 6 | 0.7333 | 66.7% | 3.50 | 35107.3 | 35.1% | 7.00 | 92.61 | 0.005997 |
| deepseek-v4-flash | deepseek-v4-pro | Sequential Handoff | 6 | 0.7167 | 66.7% | 1.83 | 14852.5 | 14.9% | 3.00 | 39.57 | 0.002578 |
| deepseek-v4-flash | deepseek-v4-pro | Shared Blackboard | 6 | 0.7808 | 66.7% | 4.33 | 46090.3 | 46.1% | 8.00 | 82.43 | 0.007490 |
| deepseek-v4-flash | deepseek-v4-pro | Single Agent | 6 | 0.7604 | 66.7% | 0.33 | 3867.5 | 3.9% | 0.00 | 20.28 | 0.000783 |
| deepseek-v4-flash | deepseek-v4-pro | Unstructured Group Chat | 6 | 0.8167 | 66.7% | 4.00 | 70985.8 | 71.0% | 12.00 | 112.79 | 0.011252 |
| deepseek-v4-flash | deepseek-v4-pro | Voting | 6 | 0.6174 | 66.7% | 1.50 | 30896.3 | 30.9% | 8.00 | 53.93 | 0.004865 |

## Low-Scoring / Failure Runs

- lr-02__manager_worker__deepseek-v4-flash__run01: score=0.0, failure_type=Tool Failure, notes=The submission is not a literature review; it is a raw tool-call fragment with no content addressing the task. All criteria are scored 0. The evidence policy is violated, and multiple hard-fail caps apply. The final output is unusable.
- mr-02__voting__deepseek-v4-flash__run01: score=0.0525, failure_type=Tool Failure, notes=The submission is severely incomplete and unsupported. It compares only one product, lacks required sections, and provides no verifiable sources. All claims are unverified and likely fabricated.
- lr-02__debate__deepseek-v4-flash__run01: score=0.15, failure_type=Communication Failure, notes=The final submission is only a tool-call fragment and contains none of the required sections, sources, or analysis. It fails every evaluation criterion and triggers multiple hard-fail caps. The evidence policy is not satisfied, and the deterministic score cap of 0.5 applies.
- lr-02__sequential_handoff__deepseek-v4-flash__run01: score=0.15, failure_type=Tool Failure, notes=The final submission is only a raw tool-call block with no literature review content. It fails to meet any of the task requirements.
- lr-02__single_agent__deepseek-v4-flash__run01: score=0.15, failure_type=None, notes=The submission is a single tool call with no review content. It fails all criteria and hard-fail rules. The hallucination rate is 0 because no factual claims are made, but the submission is entirely non-responsive.
