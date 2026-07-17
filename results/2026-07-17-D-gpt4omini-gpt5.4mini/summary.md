# Benchmark Summary

- Total scored runs: 48
- Best average group: gpt-4o-mini; gpt-5.4-mini; Sequential Handoff (0.7496)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-4o-mini | gpt-5.4-mini | Debate | 6 | 0.6923 | 83.3% | 1.17 | 35026.7 | 35.0% | 6.00 | 107.66 | 0.007850 |
| gpt-4o-mini | gpt-5.4-mini | Dynamic Task Allocation | 6 | 0.6279 | 83.3% | 1.83 | 61624.8 | 61.6% | 10.00 | 134.32 | 0.012766 |
| gpt-4o-mini | gpt-5.4-mini | Manager-Worker | 6 | 0.6958 | 83.3% | 1.50 | 42487.5 | 42.5% | 7.00 | 112.01 | 0.009135 |
| gpt-4o-mini | gpt-5.4-mini | Sequential Handoff | 6 | 0.7496 | 100.0% | 0.83 | 17787.2 | 17.8% | 3.00 | 53.47 | 0.004341 |
| gpt-4o-mini | gpt-5.4-mini | Shared Blackboard | 6 | 0.6475 | 83.3% | 2.83 | 58954.8 | 59.0% | 8.00 | 88.15 | 0.011760 |
| gpt-4o-mini | gpt-5.4-mini | Single Agent | 6 | 0.6835 | 83.3% | 0.17 | 3488.3 | 3.5% | 0.00 | 15.81 | 0.001038 |
| gpt-4o-mini | gpt-5.4-mini | Unstructured Group Chat | 6 | 0.6425 | 100.0% | 1.67 | 71760.0 | 71.8% | 12.00 | 91.99 | 0.013799 |
| gpt-4o-mini | gpt-5.4-mini | Voting | 6 | 0.6375 | 100.0% | 0.83 | 34792.2 | 34.8% | 8.00 | 56.20 | 0.006914 |

## Low-Scoring / Failure Runs

- lr-04__dynamic_task_allocation__gpt-4o-mini__run01: score=0.0, failure_type=Hallucination Propagation, notes=
- mr-04__single_agent__gpt-4o-mini__run01: score=0.0, failure_type=Hallucination Propagation, notes=['The submission follows the requested structure but does not satisfy the tool-based evidence requirement.', 'Claims are presented as current despite relying on general knowledge and an explicit inability to access official sites.', 'The recommendation is not grounded in verifiable source evidence.']
- lr-04__shared_blackboard__gpt-4o-mini__run01: score=0.15, failure_type=Communication Failure, notes=The submission is a non-answer stating that generation failed due to token budget exhaustion. It does not attempt the task, so all content criteria are unmet. The audit indicates tools and sources were accessed, but none are reflected in the submitted answer.
- lr-04__debate__gpt-4o-mini__run01: score=0.1812, failure_type=Hallucination Propagation, notes=The submission follows the requested outline superficially but relies on unverified citations and mismatched references. It also misassigns literature examples to the required communication categories, weakening synthesis and support.
- lr-04__manager_worker__gpt-4o-mini__run01: score=0.325, failure_type=Hallucination Propagation, notes=
