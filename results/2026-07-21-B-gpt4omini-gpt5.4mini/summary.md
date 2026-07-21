# Benchmark Summary

- Total scored runs: 46
- Best average group: gpt-4o-mini; gpt-5.4-mini; Dynamic Task Allocation (0.6867)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-4o-mini | gpt-5.4-mini | Debate | 6 | 0.6093 | 66.7% | 1.50 | 39219.3 | 39.2% | 6.00 | 86.62 | 0.008319 |
| gpt-4o-mini | gpt-5.4-mini | Dynamic Task Allocation | 4 | 0.6867 | 75.0% | 1.75 | 51346.8 | 51.3% | 10.00 | 100.94 | 0.011051 |
| gpt-4o-mini | gpt-5.4-mini | Manager-Worker | 6 | 0.5861 | 100.0% | 2.50 | 34494.7 | 34.5% | 7.00 | 92.86 | 0.007808 |
| gpt-4o-mini | gpt-5.4-mini | Sequential Handoff | 6 | 0.4471 | 66.7% | 0.50 | 17268.8 | 17.3% | 3.00 | 44.76 | 0.003941 |
| gpt-4o-mini | gpt-5.4-mini | Shared Blackboard | 6 | 0.5023 | 66.7% | 1.67 | 52245.7 | 52.2% | 8.00 | 94.39 | 0.010508 |
| gpt-4o-mini | gpt-5.4-mini | Single Agent | 6 | 0.4647 | 66.7% | 0.17 | 2958.0 | 3.0% | 0.00 | 14.52 | 0.000841 |
| gpt-4o-mini | gpt-5.4-mini | Unstructured Group Chat | 6 | 0.4521 | 83.3% | 1.83 | 69135.3 | 69.1% | 12.00 | 103.58 | 0.013182 |
| gpt-4o-mini | gpt-5.4-mini | Voting | 6 | 0.5253 | 66.7% | 1.17 | 33220.0 | 33.2% | 8.00 | 57.14 | 0.006578 |

## Low-Scoring / Failure Runs

- mr-02__sequential_handoff__gpt-4o-mini__run01: score=0.0, failure_type=Tool Failure, notes=
- mr-02__single_agent__gpt-4o-mini__run01: score=0.0, failure_type=Tool Failure, notes=
- mr-02__voting__gpt-4o-mini__run01: score=0.1325, failure_type=None, notes=
- lr-02__unstructured_group_chat__gpt-4o-mini__run01: score=0.15, failure_type=Over-Collaboration, notes=The run executed valid authorized academic search calls, but the final output did not contain the requested review content. The answer is therefore non-responsive to the benchmark task despite valid tool execution.
- mr-02__debate__gpt-4o-mini__run01: score=0.15, failure_type=Over-Collaboration, notes=The trusted audits indicate some source retrieval occurred during execution, but the final submitted answer is only a token-budget failure statement and does not contain the requested market comparison. Scores reflect the final submission only, not the intermediate draft content.
