# Shared Scoring Rubric

All protocol outputs are scored with the same rubric. Evaluate the final answer only, except for explicit communication metrics such as message count and communication density.

## Quality Formula

Normalize all components to `[0, 1]`.

`overall_quality_score = 0.35 * accuracy_norm + 0.30 * completeness_norm + 0.20 * helpfulness_norm + 0.15 * (1 - hallucination_rate)`

## Components

- Accuracy: raw score from 1 to 5, normalized as `(raw - 1) / 4`.
- Completeness: covered required criteria divided by total required criteria.
- Helpfulness: raw score from 1 to 5, normalized as `(raw - 1) / 4`.
- Hallucination Rate: unsupported factual claims divided by total factual claims.

## Evaluator Rules

1. Use the same rubric for all protocols.
2. Do not reward a protocol just because the transcript looks impressive.
3. Penalize missing required output format.
4. Penalize unsupported facts, fabricated citations, or claims that violate the task tool requirement.
5. Record notes for low-scoring or unusual cases.

