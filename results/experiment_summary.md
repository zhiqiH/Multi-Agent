# Experiment Summary

- Total scored runs: 24
- Best average quality protocol: Manager-Worker (0.9708)

## Protocol Averages

| Protocol | Runs | Avg Quality | Avg Tokens | Avg Messages | Avg Cost |
|---|---:|---:|---:|---:|---:|
| Manager-Worker | 6 | 0.9708 | 18636.3 | 6.00 | 0.003242 |
| Sequential Handoff | 6 | 0.9471 | 10744.8 | 3.00 | 0.001929 |
| Shared Blackboard | 6 | 0.9563 | 14025.2 | 4.00 | 0.002439 |
| Single Agent | 6 | 0.9513 | 1956.3 | 0.00 | 0.000425 |

## Low-Scoring / Failure Candidates

- SP-04__sequential_handoff__run01: score=0.81, failure_type=None, notes=The response covers most criteria well but has minor issues: budget table incomplete (missing total $180k), some metrics underspecified, and risk register missing. Otherwise strong.
- SP-04__single_agent__run01: score=0.81, failure_type=None, notes=The response is mostly accurate and complete, but the roadmap table is cut off (missing Phase 5 details) and the budget table is incomplete (missing priority column fully). Also, the pilot design section is truncated. These omissions reduce completeness. No major hallucinations, but minor inconsistencies in budget reduction logic (e.g., reducing Engineering by $6,000 not fully justified).
- SP-04__manager_worker__run01: score=0.84, failure_type=None, notes=The response is well-structured and covers most criteria. Minor issues: budget table total is $180,000 but reduced total is $144,000 (should be $144,000 after 20% cut, which is correct). However, the budget table's 'Priority if Budget Is Reduced' column does not explicitly state which items are reduced/delayed/removed for all categories; some are vague. Also, the pilot design section is cut off, missing full explanation of data collection. Overall, strong but with minor omissions.
- SP-04__shared_blackboard__run01: score=0.84, failure_type=None, notes=
- MR-04__sequential_handoff__run01: score=0.9125, failure_type=None, notes=All criteria satisfied. Minor inaccuracy: Slack free plan file sharing limit is 5GB total, not 10GB free. But overall correct and well-supported.
