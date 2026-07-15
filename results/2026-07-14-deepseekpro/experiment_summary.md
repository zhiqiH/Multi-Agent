# Experiment Summary

- Total scored runs: 24
- Best average condition: deepseek/deepseek_flash/deepseek-v4-flash [field-isolated]; deepseek/deepseek_pro/deepseek-v4-pro; shared_blackboard (Shared Blackboard) (0.6896)

## Condition Averages

| Candidate | Judge | Protocol | Runs | Avg Quality | Avg Tokens | Avg Messages | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|
| deepseek/deepseek_flash/deepseek-v4-flash [field-isolated] | deepseek/deepseek_pro/deepseek-v4-pro | manager_worker (Manager-Worker) | 6 | 0.6532 | 14069.2 | 6.00 | 0.002583 |
| deepseek/deepseek_flash/deepseek-v4-flash [field-isolated] | deepseek/deepseek_pro/deepseek-v4-pro | sequential_handoff (Sequential Handoff) | 6 | 0.6150 | 8250.5 | 3.00 | 0.001584 |
| deepseek/deepseek_flash/deepseek-v4-flash [field-isolated] | deepseek/deepseek_pro/deepseek-v4-pro | shared_blackboard (Shared Blackboard) | 6 | 0.6896 | 11624.8 | 4.00 | 0.002138 |
| deepseek/deepseek_flash/deepseek-v4-flash [field-isolated] | deepseek/deepseek_pro/deepseek-v4-pro | single_agent (Single Agent) | 6 | 0.6664 | 1414.8 | 0.00 | 0.000354 |

## Low-Scoring / Failure Candidates

- mr-02__shared_blackboard__deepseek_flash-deepseek-v4-flash__run01: score=0.4, failure_type=Communication Failure, notes=The submission cuts off abruptly, missing the source list and leaving the risks section incomplete. All factual claims are provided without any supporting citations, violating the core evidence requirement of the task.
- mr-02__single_agent__deepseek_flash-deepseek-v4-flash__run01: score=0.4, failure_type=Communication Failure, notes=The submission is cut off after the start of section 5, resulting in missing required sections and zero source citations. The overall score is capped at 40% due to unsupported pricing/privacy claims.
- se-02__sequential_handoff__deepseek_flash-deepseek-v4-flash__run01: score=0.4075, failure_type=None, notes=Candidate submission truncated; missing sections 5-10 entirely. Includes unsupported third-party API latency claim.
- se-02__manager_worker__deepseek_flash-deepseek-v4-flash__run01: score=0.4525, failure_type=None, notes=
- mr-02__manager_worker__deepseek_flash-deepseek-v4-flash__run01: score=0.5, failure_type=None, notes=The submission is incomplete and lacks required sections (5 and 6). No sources are cited anywhere, triggering a cap. The recommendation is truncated.
