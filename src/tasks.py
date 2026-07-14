from __future__ import annotations
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable
from .io_utils import read_json

DEFAULT_CANDIDATE_FIELDS: tuple[str, ...] = (
    "task_id",
    "category",
    "difficulty",
    "tool_requirement",
    "prompt",
    "required_output_format",
)

DEFAULT_JUDGE_PRIVATE_FIELDS: tuple[str, ...] = (
    "evaluation_criteria",
    "ground_truth",
    "expected_failure_risks",
    "scoring_rubric",
    "required_evidence",
)

DEFAULT_JUDGE_FIELDS: tuple[str, ...] = DEFAULT_CANDIDATE_FIELDS + DEFAULT_JUDGE_PRIVATE_FIELDS

PROTECTED_FIELDS: frozenset[str] = frozenset(DEFAULT_JUDGE_PRIVATE_FIELDS)

REQUIRED_TASK_FIELDS: frozenset[str] = frozenset(
    {
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
        "ground_truth",
    }
)

KNOWN_TASK_FIELDS: frozenset[str] = REQUIRED_TASK_FIELDS | {"notes"}

_TASK_FIELD_LABELS = {
    "task_id": "Task ID",
    "category": "Category",
    "difficulty": "Difficulty",
    "author": "Author",
    "tool_requirement": "Tool Requirement",
    "prompt": "Prompt",
    "required_output_format": "Required Output Format",
    "evaluation_criteria": "Evaluation Criteria",
    "required_evidence": "Required Evidence",
    "scoring_rubric": "Scoring Rubric",
    "expected_failure_risks": "Expected Failure Risks",
    "ground_truth": "Ground Truth",
    "notes": "Notes",
}

_INLINE_TASK_FIELDS = {
    "task_id",
    "category",
    "difficulty",
    "author",
    "tool_requirement",
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


def project_task(task: dict[str, Any], fields: Iterable[str]) -> dict[str, Any]:

    if isinstance(fields, str):
        raise TypeError("Task fields must be an iterable of field names, not a string")

    requested = tuple(fields)
    invalid = [field for field in requested if not isinstance(field, str) or not field]
    if invalid:
        raise ValueError(f"Task fields must be non-empty strings: {invalid}")

    duplicates = sorted({field for field in requested if requested.count(field) > 1})
    if duplicates:
        raise ValueError(f"Duplicate task fields requested: {duplicates}")

    unknown = sorted(set(requested) - KNOWN_TASK_FIELDS)
    if unknown:
        raise ValueError(f"Unknown task fields requested: {unknown}")

    missing = sorted(set(requested) - set(task))
    if missing:
        task_id = task.get("task_id", "<unknown>")
        raise ValueError(f"Task {task_id} missing requested fields: {missing}")

    return {field: deepcopy(task[field]) for field in requested}


def criteria_text(task: dict[str, Any]) -> str:
    lines = []
    for item in task.get("evaluation_criteria", []):
        weight = item.get("weight", 1)
        lines.append(f"- {item.get('id')}: {item.get('criterion')} (weight={weight})")
    return "\n".join(lines)


def candidate_task_text(candidate_task: dict[str, Any]) -> str:

    sections: list[str] = []
    for field, value in candidate_task.items():
        if field not in KNOWN_TASK_FIELDS:
            raise ValueError(f"Unknown field in projected candidate task: {field}")
        label = _TASK_FIELD_LABELS[field]
        rendered = _render_task_value(value)
        if field in _INLINE_TASK_FIELDS and "\n" not in rendered:
            sections.append(f"{label}: {rendered}")
        else:
            sections.append(f"{label}:\n{rendered}")
    return "\n\n".join(sections)


def task_brief(task: dict[str, Any]) -> str:

    return candidate_task_text(project_task(task, DEFAULT_CANDIDATE_FIELDS))


def _render_task_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)