# Experiment Summary

- Total scored runs: 48
- Best average group: deepseek/deepseek_v4_flash/deepseek-v4-flash; openai/openai_gpt_5_4_mini/gpt-5.4-mini; dynamic_task_allocation (Dynamic Task Allocation) (0.8040)

## Group Averages

| Agent | Judge | Protocol | Mode | Runs | Avg Quality | Avg Tokens | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| deepseek/deepseek_v4_flash/deepseek-v4-flash | openai/openai_gpt_5_4_mini/gpt-5.4-mini | manager_worker (Manager-Worker) | blind | 6 | 0.7975 | 22914.7 | 7.00 | 68.71 | 0.004110 |
| deepseek/deepseek_v4_flash/deepseek-v4-flash | openai/openai_gpt_5_4_mini/gpt-5.4-mini | dynamic_task_allocation (Dynamic Task Allocation) | blind | 6 | 0.8040 | 36859.7 | 10.00 | 82.10 | 0.006236 |
| deepseek/deepseek_v4_flash/deepseek-v4-flash | openai/openai_gpt_5_4_mini/gpt-5.4-mini | debate (Debate) | blind | 6 | 0.7258 | 22486.3 | 6.00 | 72.82 | 0.004017 |
| deepseek/deepseek_v4_flash/deepseek-v4-flash | openai/openai_gpt_5_4_mini/gpt-5.4-mini | single_agent (Single Agent) | blind | 6 | 0.8029 | 1792.2 | 0.00 | 14.01 | 0.000435 |
| deepseek/deepseek_v4_flash/deepseek-v4-flash | openai/openai_gpt_5_4_mini/gpt-5.4-mini | voting (Voting) | blind | 6 | 0.6900 | 29557.5 | 8.00 | 64.46 | 0.004848 |
| deepseek/deepseek_v4_flash/deepseek-v4-flash | openai/openai_gpt_5_4_mini/gpt-5.4-mini | unstructured_group_chat (Unstructured Group Chat) | blind | 6 | 0.2731 | 53239.3 | 11.17 | 90.41 | 0.008515 |
| deepseek/deepseek_v4_flash/deepseek-v4-flash | openai/openai_gpt_5_4_mini/gpt-5.4-mini | sequential_handoff (Sequential Handoff) | blind | 6 | 0.7386 | 10319.8 | 3.00 | 30.48 | 0.001940 |
| deepseek/deepseek_v4_flash/deepseek-v4-flash | openai/openai_gpt_5_4_mini/gpt-5.4-mini | shared_blackboard (Shared Blackboard) | blind | 6 | 0.7377 | 36866.0 | 8.00 | 64.63 | 0.006112 |

## Low-Scoring / Failure Runs

- main__ec-04__unstructured_group_chat__deepseek_v4_flash-deepseek-v4-flash__c-b142a93f358e__run01: score=0.0, failure_type=Communication Failure, notes=
- main__sp-04__unstructured_group_chat__deepseek_v4_flash-deepseek-v4-flash__c-b142a93f358e__run01: score=0.135, failure_type=Communication Failure, notes=
- main__sp-04__voting__deepseek_v4_flash-deepseek-v4-flash__c-695daf11757f__run01: score=0.15, failure_type=Communication Failure, notes=
- main__ta-04__unstructured_group_chat__deepseek_v4_flash-deepseek-v4-flash__c-b142a93f358e__run01: score=0.15, failure_type=Communication Failure, notes=
- main__se-04__unstructured_group_chat__deepseek_v4_flash-deepseek-v4-flash__c-b142a93f358e__run01: score=0.4125, failure_type=Coordination Failure, notes=
