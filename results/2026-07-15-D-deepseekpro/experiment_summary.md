# Experiment Summary

- Total scored runs: 48
- Best average group: deepseek/deepseek_v4_flash/deepseek-v4-flash; deepseek/deepseek_v4_pro/deepseek-v4-pro; shared_blackboard (Shared Blackboard) (1.0000)

## Group Averages

| Agent | Judge | Protocol | Mode | Runs | Avg Quality | Avg Tokens | Avg Messages | Avg Runtime | Avg Cost |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| deepseek/deepseek_v4_flash/deepseek-v4-flash | deepseek/deepseek_v4_pro/deepseek-v4-pro | manager_worker (Manager-Worker) | blind | 6 | 0.9600 | 22914.7 | 7.00 | 68.71 | 0.004110 |
| deepseek/deepseek_v4_flash/deepseek-v4-flash | deepseek/deepseek_v4_pro/deepseek-v4-pro | dynamic_task_allocation (Dynamic Task Allocation) | blind | 6 | 0.9479 | 36859.7 | 10.00 | 82.10 | 0.006236 |
| deepseek/deepseek_v4_flash/deepseek-v4-flash | deepseek/deepseek_v4_pro/deepseek-v4-pro | debate (Debate) | blind | 6 | 0.9967 | 22486.3 | 6.00 | 72.82 | 0.004017 |
| deepseek/deepseek_v4_flash/deepseek-v4-flash | deepseek/deepseek_v4_pro/deepseek-v4-pro | single_agent (Single Agent) | blind | 6 | 0.9967 | 1792.2 | 0.00 | 14.01 | 0.000435 |
| deepseek/deepseek_v4_flash/deepseek-v4-flash | deepseek/deepseek_v4_pro/deepseek-v4-pro | voting (Voting) | blind | 6 | 0.8321 | 29557.5 | 8.00 | 64.46 | 0.004848 |
| deepseek/deepseek_v4_flash/deepseek-v4-flash | deepseek/deepseek_v4_pro/deepseek-v4-pro | unstructured_group_chat (Unstructured Group Chat) | blind | 6 | 0.4604 | 53239.3 | 11.17 | 90.41 | 0.008515 |
| deepseek/deepseek_v4_flash/deepseek-v4-flash | deepseek/deepseek_v4_pro/deepseek-v4-pro | sequential_handoff (Sequential Handoff) | blind | 6 | 0.9962 | 10319.8 | 3.00 | 30.48 | 0.001940 |
| deepseek/deepseek_v4_flash/deepseek-v4-flash | deepseek/deepseek_v4_pro/deepseek-v4-pro | shared_blackboard (Shared Blackboard) | blind | 6 | 1.0000 | 36866.0 | 8.00 | 64.63 | 0.006112 |

## Low-Scoring / Failure Runs

- main__ec-04__unstructured_group_chat__deepseek_v4_flash-deepseek-v4-flash__c-b142a93f358e__run01: score=0.0, failure_type=Communication Failure, notes=
- main__sp-04__unstructured_group_chat__deepseek_v4_flash-deepseek-v4-flash__c-b142a93f358e__run01: score=0.0, failure_type=Communication Failure, notes=The submission is a fragment of a collaborative process, not a standalone answer. It lacks all required sections, tables, and content. It does not meet any of the evaluation criteria.
- main__sp-04__voting__deepseek_v4_flash-deepseek-v4-flash__c-695daf11757f__run01: score=0.0, failure_type=Role Confusion, notes=The submission is entirely a critique of a missing plan. It does not fulfill the task requirements and contains no strategic content, roadmap, budget, metrics, risks, or decision framework.
- main__ta-04__unstructured_group_chat__deepseek_v4_flash-deepseek-v4-flash__c-b142a93f358e__run01: score=0.15, failure_type=Role Confusion, notes=The submission completely fails to address the task. It does not explain or compare the three approaches, provide a comparison table, or give a recommendation. Instead, it discusses multi-modal content, which is not part of the required analysis. All criteria are unmet.
- main__se-04__unstructured_group_chat__deepseek_v4_flash-deepseek-v4-flash__c-b142a93f358e__run01: score=0.6125, failure_type=None, notes=The submission is a consolidation of design decisions rather than a full architecture document. It lacks component separation details, a complete workflow description, explicit processing state tracking, a data model, project structure, and testing plan. The API table is present but the Component Table is missing. The design is partially actionable but has significant gaps.
