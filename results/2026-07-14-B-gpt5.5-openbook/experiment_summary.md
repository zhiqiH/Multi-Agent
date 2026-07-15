# Experiment Summary

- Total scored runs: 24
- Best average condition: deepseek/deepseek_flash/deepseek-v4-flash [field-isolated]; openai/openai_judge/gpt-5.5; single_agent (Single Agent) (0.6238)

## Condition Averages

| Candidate | Judge | Protocol | Runs | Avg Quality | Avg Tokens | Avg Messages | Avg Cost |
|---|---|---|---:|---:|---:|---:|---:|
| deepseek/deepseek_flash/deepseek-v4-flash [field-isolated] | openai/openai_judge/gpt-5.5 | manager_worker (Manager-Worker) | 6 | 0.5441 | 14069.2 | 6.00 | 0.002583 |
| deepseek/deepseek_flash/deepseek-v4-flash [field-isolated] | openai/openai_judge/gpt-5.5 | sequential_handoff (Sequential Handoff) | 6 | 0.5687 | 8250.5 | 3.00 | 0.001584 |
| deepseek/deepseek_flash/deepseek-v4-flash [field-isolated] | openai/openai_judge/gpt-5.5 | shared_blackboard (Shared Blackboard) | 6 | 0.6187 | 11624.8 | 4.00 | 0.002138 |
| deepseek/deepseek_flash/deepseek-v4-flash [field-isolated] | openai/openai_judge/gpt-5.5 | single_agent (Single Agent) | 6 | 0.6238 | 1414.8 | 0.00 | 0.000354 |

## Low-Scoring / Failure Candidates

- mr-02__sequential_handoff__deepseek_flash-deepseek-v4-flash__run01: score=0.2375, failure_type=Hallucination Propagation, notes=The submission has a useful basic structure and compares four relevant tools, but it fails the evidence requirement: there are no citations or source list, and many current pricing, feature, platform-support, privacy, consent, and retention claims are unsupported. It also omits required final sections and ends abruptly.
- mr-02__manager_worker__deepseek_flash-deepseek-v4-flash__run01: score=0.245, failure_type=Hallucination Propagation, notes=The submission has a useful high-level structure and compares four relevant tools, but it fails the evidence requirement: no citations, no source list, and many factual claims are unsupported. It also omits the required risks/assumptions/verification section and the answer is truncated during the recommendation.
- mr-02__shared_blackboard__deepseek_flash-deepseek-v4-flash__run01: score=0.355, failure_type=Hallucination Propagation, notes=The submission is structured and includes a plausible set of tools and a lab-specific recommendation, but it fails the evidence requirement. It provides no source list or citations despite making many current product, pricing, platform-support, privacy, consent, and retention claims. Several details are labeled unknown, but many other unsupported claims are presented as factual, making the answer unreliable for procurement or compliance use.
- mr-02__single_agent__deepseek_flash-deepseek-v4-flash__run01: score=0.3625, failure_type=Hallucination Propagation, notes=The submission has a useful high-level structure and compares four relevant tools, but it lacks all required citations and ends before completing the risks/verification notes and source list. Many factual claims about pricing, platform support, privacy, retention, and security are unsupported, making the recommendation difficult to rely on for a university lab procurement decision.
- lr-02__manager_worker__deepseek_flash-deepseek-v4-flash__run01: score=0.4, failure_type=Hallucination Propagation, notes=The submission has a reasonable high-level structure and covers several RAG method families, but it is incomplete, lacks the final required sections, and relies on questionable numerical claims without sufficient citation detail. The source table is present, but the evidence grounding is not strong enough for a scholarly literature review.
