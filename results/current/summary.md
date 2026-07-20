# Benchmark Summary

- Total scored runs: 9
- Best average group: gpt-4o-mini; gpt-5.4-mini; Voting (0.5600)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-4o-mini | gpt-5.4-mini | Shared Blackboard | 3 | 0.5437 | 66.7% | 3.67 | 67388.7 | 67.4% | 8.00 | 68.84 | 0.012131 |
| gpt-4o-mini | gpt-5.4-mini | Single Agent | 3 | 0.4610 | 66.7% | 0.33 | 5041.3 | 5.0% | 0.00 | 12.02 | 0.001082 |
| gpt-4o-mini | gpt-5.4-mini | Voting | 3 | 0.5600 | 66.7% | 1.67 | 49632.0 | 49.6% | 8.00 | 55.16 | 0.008743 |

## Low-Scoring / Failure Runs

- mr-03__single_agent__gpt-4o-mini__run01: score=0.0, failure_type=None, notes=Single-agent run; no collaboration failure is inferable. The response satisfies the requested section structure and matrix headers, but several key pricing and file-limit claims are inconsistent with the benchmark expectations and lack substantive source support.
- mr-03__voting__gpt-4o-mini__run01: score=0.0, failure_type=None, notes=The response matches the required structure and includes the requested matrix headers and recommendation, but several key factual claims and cost/file-limit figures do not align with the benchmark expectations. Evidence support is not verifiable from the audit because no substantive sources were accessed.
- mr-03__shared_blackboard__gpt-4o-mini__run01: score=0.15, failure_type=None, notes=
- lr-03__single_agent__gpt-4o-mini__run01: score=0.5375, failure_type=None, notes=Single-agent run; no collaboration failure is observable. The response is structurally complete and cites identifiers, but it violates the exact-three-paper requirement and uses weak, generic limitation statements. The references section also includes an extra survey entry, which reduces task fidelity.
- lr-03__shared_blackboard__gpt-4o-mini__run01: score=0.645, failure_type=None, notes=The submission satisfies the required structure and citation presence, but several extracted limitations are generic rather than tightly evidenced. The selected set is PEFT-related and traceable, though one entry is a survey, which weakens technical extraction quality.
