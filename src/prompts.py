from __future__ import annotations

import json
from typing import Any

from .tasks import criteria_text, task_brief


ROLE_SYSTEM_PROMPTS = {
    "Planner": "You are Planner. Decompose the task, identify deliverables, constraints, and a concise execution plan. Do not fabricate external evidence.",
    "Researcher": "You are Researcher. Gather and organize evidence available in the prompt and common conceptual knowledge. Respect the task tool requirement.",
    "Analyst": "You are Analyst. Compare options, reason through tradeoffs, and produce grounded conclusions tied to the rubric.",
    "Critic": "You are Critic. Find omissions, unsupported claims, format violations, and coordination risks. Be specific and constructive.",
    "Writer": "You are Writer. Produce the final deliverable in the required format. Use only supported claims and keep the answer clear.",
    "Manager": "You are Manager. Assign work, synthesize worker outputs, resolve conflicts, and approve a final direction.",
    "Judge": "You are Judge. Evaluate competing answers against the task rubric and select or synthesize the strongest final answer.",
    "Single Agent": "You are a careful single-agent baseline. Complete the task directly using the required format and rubric.",
}


def agent_prompt(role: str, task: dict[str, Any], instruction: str, visible_context: str = "") -> str:
    context_block = visible_context.strip() or "No prior agent output is visible."
    return f"""You are acting as role: {role}.

{task_brief(task)}

Visible prior context:
{context_block}

Instruction:
{instruction}

Return only the content for your role. Do not include hidden chain-of-thought. Use concise reasoning summaries where useful.
"""


def single_agent_prompt(task: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": ROLE_SYSTEM_PROMPTS["Single Agent"]},
        {
            "role": "user",
            "content": f"""Complete this benchmark task as a single-agent baseline.

{task_brief(task)}

Follow the required output format exactly. Do not use external tools if the task prohibits them.
""",
        },
    ]


def scoring_prompt(task: dict[str, Any], final_output: str) -> list[dict[str, str]]:
    rubric = json.dumps(task["scoring_rubric"], ensure_ascii=False, indent=2)
    return [
        {
            "role": "system",
            "content": (
                "You are an impartial evaluator. Score only the final answer, not the transcript. "
                "Return strict json with keys: accuracy_raw, completeness_norm, helpfulness_raw, "
                "hallucination_rate, notes, failure_type."
            ),
        },
        {
            "role": "user",
            "content": f"""Evaluate the final output for this benchmark task.

Task:
{task_brief(task)}

Scoring Rubric:
{rubric}

Ground-truth / Evaluation Criteria:
{criteria_text(task)}

Final Output:
{final_output}

Return json only. Use these scales:
- accuracy_raw: integer 1-5.
- completeness_norm: number from 0 to 1 based on covered criteria / total criteria.
- helpfulness_raw: integer 1-5.
- hallucination_rate: number from 0 to 1.
- failure_type: one of None, Coordination Failure, Communication Failure, Role Confusion, Hallucination Propagation, Premature Consensus, Over-Collaboration, Manager Bottleneck, Noise Accumulation.
""",
        },
    ]

