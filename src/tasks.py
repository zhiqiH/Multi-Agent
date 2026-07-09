from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import read_json


REQUIRED_TASK_FIELDS = {
    "task_id",
    "category",
    "difficulty",
    "author",
    "tool_requirement",
    "prompt",
    "required_output_format",
    "evaluation_criteria",
    "required_evidence",
    "scoring_rubric",
    "expected_failure_risks",
}


def load_benchmark(path: Path) -> dict[str, Any]:
    benchmark = read_json(path)
    tasks = benchmark.get("tasks", [])
    if not tasks:
        raise ValueError(f"No tasks found in benchmark file: {path}")
    for task in tasks:
        missing = sorted(REQUIRED_TASK_FIELDS - set(task))
        if missing:
            raise ValueError(f"Task {task.get('task_id', '<unknown>')} missing fields: {missing}")
    return benchmark


def select_tasks(benchmark: dict[str, Any], task_ids: list[str]) -> list[dict[str, Any]]:
    tasks = benchmark["tasks"]
    if not task_ids:
        return tasks
    wanted = set(task_ids)
    selected = [task for task in tasks if task["task_id"] in wanted]
    missing = sorted(wanted - {task["task_id"] for task in selected})
    if missing:
        raise ValueError(f"Unknown task IDs: {missing}")
    return selected


def criteria_text(task: dict[str, Any]) -> str:
    lines = []
    for item in task.get("evaluation_criteria", []):
        weight = item.get("weight", 1)
        lines.append(f"- {item.get('id')}: {item.get('criterion')} (weight={weight})")
    return "\n".join(lines)


def task_brief(task: dict[str, Any]) -> str:
    return f"""Task ID: {task["task_id"]}
Category: {task["category"]}
Difficulty: {task["difficulty"]}
Tool Requirement: {task["tool_requirement"]}

Prompt:
{task["prompt"]}

Required Output Format:
{task["required_output_format"]}

Evaluation Criteria:
{criteria_text(task)}

Required Evidence:
{task["required_evidence"]}
"""

