# Experiment Summary

- Total scored runs: 24
- Best average condition: deepseek/deepseek_flash/deepseek-v4-flash [field-isolated]; openai/openai_judge/gpt-5.5; shared_blackboard (Shared Blackboard) (0.6181)

## Condition Averages

| Candidate | Judge | Protocol | Runs | Avg Quality | Avg Tokens | Avg Messages | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|
| deepseek/deepseek_flash/deepseek-v4-flash [field-isolated] | openai/openai_judge/gpt-5.5 | manager_worker (Manager-Worker) | 6 | 0.5563 | 14069.2 | 6.00 | 0.002583 |
| deepseek/deepseek_flash/deepseek-v4-flash [field-isolated] | openai/openai_judge/gpt-5.5 | sequential_handoff (Sequential Handoff) | 6 | 0.5736 | 8250.5 | 3.00 | 0.001584 |
| deepseek/deepseek_flash/deepseek-v4-flash [field-isolated] | openai/openai_judge/gpt-5.5 | shared_blackboard (Shared Blackboard) | 6 | 0.6181 | 11624.8 | 4.00 | 0.002138 |
| deepseek/deepseek_flash/deepseek-v4-flash [field-isolated] | openai/openai_judge/gpt-5.5 | single_agent (Single Agent) | 6 | 0.6014 | 1414.8 | 0.00 | 0.000354 |

## Low-Scoring / Failure Candidates

- mr-02__sequential_handoff__deepseek_flash-deepseek-v4-flash__run01: score=0.275, failure_type=Hallucination Propagation, notes=The submission has a useful high-level structure and compares four relevant tools, but it fails the evidence requirement: there are no citations or source list despite many factual claims about pricing, integrations, privacy, consent, and retention. It also omits required final sections and appears truncated.
- mr-02__manager_worker__deepseek_flash-deepseek-v4-flash__run01: score=0.3175, failure_type=Hallucination Propagation, notes=The submission has a useful basic structure and compares four relevant tools, but it lacks any citations or source list despite making numerous factual claims about integrations, features, pricing, compliance, consent, and data retention. The recommendation is incomplete and does not adequately address the lab's cross-platform requirement or institutional privacy risks.
- mr-02__shared_blackboard__deepseek_flash-deepseek-v4-flash__run01: score=0.3475, failure_type=Hallucination Propagation, notes=The submission has a useful high-level structure and compares four relevant tools, but it fails the core evidence requirement. It provides no citations or source list despite making many current factual claims about pricing, platform support, privacy, retention, consent, and compliance. The recommendation is scenario-aware but not reliable without verification.
- mr-02__single_agent__deepseek_flash-deepseek-v4-flash__run01: score=0.3625, failure_type=Hallucination Propagation, notes=The submission has a usable high-level structure and compares four relevant products, but it does not provide citations or a source list, leaves the risks/verification section incomplete, and states many current-market claims without evidence. Because the task required public verification, the answer is not reliable as market research.
- lr-02__manager_worker__deepseek_flash-deepseek-v4-flash__run01: score=0.4, failure_type=Hallucination Propagation, notes=The submission has a solid high-level structure and identifies relevant RAG method families, but it is truncated, omits required final sections, and relies on several unsupported numerical claims. The scholarly source set is plausible, yet source details are thin and evidence support is inconsistent.
