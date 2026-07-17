# Benchmark Summary

- Total scored runs: 48
- Best average group: gpt-5-nano; gpt-5.4-mini; Debate (0.8823)

## Group Averages

| Agent Model | Judge Model | Protocol | Runs | Avg Quality | Avg Tokens | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|---:|
| gpt-5-nano | gpt-5.4-mini | Debate | 6 | 0.8823 | 21272.7 | 6.00 | 66.37 | 0.004595 |
| gpt-5-nano | gpt-5.4-mini | Dynamic Task Allocation | 6 | 0.7745 | 44851.3 | 10.00 | 129.57 | 0.007746 |
| gpt-5-nano | gpt-5.4-mini | Manager-Worker | 6 | 0.8595 | 27468.7 | 7.00 | 69.39 | 0.005060 |
| gpt-5-nano | gpt-5.4-mini | Sequential Handoff | 6 | 0.8498 | 10202.5 | 3.00 | 35.73 | 0.002563 |
| gpt-5-nano | gpt-5.4-mini | Shared Blackboard | 6 | 0.8287 | 36150.2 | 8.00 | 74.18 | 0.006159 |
| gpt-5-nano | gpt-5.4-mini | Single Agent | 6 | 0.8556 | 2245.0 | 0.00 | 10.71 | 0.000729 |
| gpt-5-nano | gpt-5.4-mini | Unstructured Group Chat | 6 | 0.5360 | 52891.8 | 10.83 | 97.66 | 0.008046 |
| gpt-5-nano | gpt-5.4-mini | Voting | 6 | 0.8303 | 38493.7 | 8.00 | 54.40 | 0.004345 |

## Low-Scoring / Failure Runs

- lr-04__dynamic_task_allocation__gpt-5-nano__run01: score=0.0, failure_type=Communication Failure, notes=
- ec-04__unstructured_group_chat__gpt-5-nano__run01: score=0.15, failure_type=Communication Failure, notes=
- ta-04__unstructured_group_chat__gpt-5-nano__run01: score=0.15, failure_type=Communication Failure, notes=The submission is off-task and evaluates a draft rather than answering the benchmark prompt. It contains some relevant-sounding architectural advice, but not in the required form or scope.
- lr-04__manager_worker__gpt-5-nano__run01: score=0.3512, failure_type=Hallucination Propagation, notes=
- lr-04__unstructured_group_chat__gpt-5-nano__run01: score=0.4387, failure_type=Hallucination Propagation, notes=
