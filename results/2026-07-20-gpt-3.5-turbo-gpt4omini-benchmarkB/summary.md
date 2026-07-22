# Benchmark Summary

- Total scored runs: 26
- Best average group: gpt-3.5-turbo; gpt-4o-mini; Debate (0.9492)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Evidence Constraint Pass | Avg Evidence Calls | Avg Tokens | Budget Used | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-3.5-turbo | gpt-4o-mini | Debate | 3 | 0.9492 | 100.0% | 0.00 | 9233.7 | 9.2% | 6.00 | 20.48 | 0.006709 |
| gpt-3.5-turbo | gpt-4o-mini | Dynamic Task Allocation | 3 | 0.8006 | 100.0% | 0.00 | 12139.3 | 12.1% | 10.00 | 23.14 | 0.008000 |
| gpt-3.5-turbo | gpt-4o-mini | Manager-Worker | 3 | 0.8514 | 100.0% | 0.00 | 9680.3 | 9.7% | 7.00 | 21.88 | 0.007145 |
| gpt-3.5-turbo | gpt-4o-mini | Sequential Handoff | 2 | 0.7729 | 100.0% | 0.00 | 4811.0 | 4.8% | 3.00 | 12.99 | 0.003909 |
| gpt-3.5-turbo | gpt-4o-mini | Shared Blackboard | 3 | 0.9056 | 100.0% | 0.00 | 17067.7 | 17.1% | 8.00 | 27.12 | 0.011282 |
| gpt-3.5-turbo | gpt-4o-mini | Single Agent | 5 | 0.6418 | 80.0% | 0.20 | 2543.8 | 2.5% | 0.00 | 7.00 | 0.001888 |
| gpt-3.5-turbo | gpt-4o-mini | Unstructured Group Chat | 3 | 0.9089 | 100.0% | 0.00 | 28462.3 | 28.5% | 12.00 | 33.12 | 0.017398 |
| gpt-3.5-turbo | gpt-4o-mini | Voting | 4 | 0.8959 | 100.0% | 2.00 | 32635.0 | 32.6% | 8.00 | 35.38 | 0.019227 |

## Low-Scoring / Failure Runs

- mr-02__single_agent__gpt-3.5-turbo__run01: score=0.0, failure_type=Tool Failure, notes=The submission indicates a failure to retrieve necessary information due to budget exhaustion, leading to a complete lack of required content.
- ec-02__sequential_handoff__gpt-3.5-turbo__run01: score=0.5458, failure_type=None, notes=
- ec-02__dynamic_task_allocation__gpt-3.5-turbo__run01: score=0.5542, failure_type=None, notes=
- ec-02__manager_worker__gpt-3.5-turbo__run01: score=0.5542, failure_type=None, notes=
- ec-02__single_agent__gpt-3.5-turbo__run01: score=0.5542, failure_type=None, notes=
