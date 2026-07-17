from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from .io_utils import read_json


DEFAULT_AGENT_FIELDS: tuple[str, ...] = (
    "task_id",
    "category",
    "difficulty",
    "tool_requirement",
    "prompt",
    "required_output_format",
)

GRADING_FIELDS: tuple[str, ...] = (
    "evaluation_criteria",
    "ground_truth",
    "expected_failure_risks",
    "scoring_rubric",
    "required_evidence",
)

PROTECTED_FIELDS: frozenset[str] = frozenset(GRADING_FIELDS)

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
BENCHMARK_CATEGORIES: tuple[str, ...] = (
    "Literature Review",
    "Technical Analysis",
    "Software Engineering",
    "Market Research",
    "Educational Content",
    "Strategic Planning",
)
VALID_DIFFICULTIES = frozenset({"Easy", "Medium", "Hard"})
VALID_TOOL_REQUIREMENTS = frozenset({"Required", "Optional", "Prohibited"})

_TASK_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9_-]*-\d{2}$")
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
_INLINE_TASK_FIELDS = {"task_id", "category", "difficulty", "author", "tool_requirement"}


def load_benchmark(path: Path) -> dict[str, Any]:
    """Load and validate a benchmark file or a manifest of benchmark shards."""

    return _load_benchmark(path.resolve(), seen=frozenset())


def _load_benchmark(path: Path, *, seen: frozenset[Path]) -> dict[str, Any]:
    if path in seen:
        raise ValueError(f"Benchmark manifest cycle detected at: {path}")
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Benchmark must be a JSON object: {path}")

    tasks: list[dict[str, Any]] = []
    task_files = payload.get("task_files") or []
    if task_files:
        if not isinstance(task_files, list) or not all(isinstance(item, str) and item for item in task_files):
            raise ValueError(f"benchmark task_files must be a list of paths: {path}")
        next_seen = seen | {path}
        for raw_child in task_files:
            child_path = (path.parent / raw_child).resolve()
            child = _load_benchmark(child_path, seen=next_seen)
            tasks.extend(deepcopy(child["tasks"]))

    inline_tasks = payload.get("tasks") or []
    if inline_tasks:
        if not isinstance(inline_tasks, list):
            raise ValueError(f"Benchmark tasks must be a list: {path}")
        tasks.extend(deepcopy(inline_tasks))
    if not tasks:
        raise ValueError(f"No tasks found in benchmark file: {path}")

    task_ids: set[str] = set()
    for task in tasks:
        _validate_task(task, source=path)
        task_id = str(task["task_id"])
        if task_id in task_ids:
            raise ValueError(f"Duplicate task_id {task_id!r} in benchmark: {path}")
        task_ids.add(task_id)

    result = {key: deepcopy(value) for key, value in payload.items() if key != "tasks"}
    result["tasks"] = tasks
    return result


def _validate_task(task: Any, *, source: Path) -> None:
    if not isinstance(task, dict):
        raise ValueError(f"Every benchmark task must be a JSON object: {source}")
    missing = sorted(REQUIRED_TASK_FIELDS - set(task))
    if missing:
        raise ValueError(f"Task {task.get('task_id', '<unknown>')} missing fields: {missing}")

    task_id = str(task["task_id"])
    if not _TASK_ID_PATTERN.fullmatch(task_id):
        raise ValueError(f"Invalid task_id {task_id!r}; expected an uppercase prefix and two-digit suffix")
    if task["difficulty"] not in VALID_DIFFICULTIES:
        raise ValueError(f"Task {task_id} has invalid difficulty: {task['difficulty']!r}")
    if task["tool_requirement"] not in VALID_TOOL_REQUIREMENTS:
        raise ValueError(f"Task {task_id} has invalid tool_requirement: {task['tool_requirement']!r}")

    for field in ("category", "author", "prompt", "required_output_format"):
        if not isinstance(task[field], str) or not task[field].strip():
            raise ValueError(f"Task {task_id} field {field!r} must be a non-empty string")

    criteria = task["evaluation_criteria"]
    if not isinstance(criteria, list) or not criteria:
        raise ValueError(f"Task {task_id} evaluation_criteria must be a non-empty list")
    criterion_ids: set[str] = set()
    for criterion in criteria:
        if not isinstance(criterion, dict):
            raise ValueError(f"Task {task_id} has a non-object evaluation criterion")
        criterion_id = str(criterion.get("id") or "").strip()
        description = str(criterion.get("criterion") or "").strip()
        if not criterion_id or not description:
            raise ValueError(f"Task {task_id} criteria require non-empty id and criterion fields")
        if criterion_id in criterion_ids:
            raise ValueError(f"Task {task_id} has duplicate criterion id {criterion_id!r}")
        criterion_ids.add(criterion_id)
        try:
            weight = float(criterion.get("weight", 1))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Task {task_id} criterion {criterion_id} has invalid weight") from exc
        if weight <= 0:
            raise ValueError(f"Task {task_id} criterion {criterion_id} weight must be positive")

    for field in ("required_evidence", "scoring_rubric", "expected_failure_risks", "ground_truth"):
        if task[field] in (None, "", [], {}):
            raise ValueError(f"Task {task_id} field {field!r} must not be empty")


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


def agent_task_text(agent_task: dict[str, Any]) -> str:
    sections: list[str] = []
    for field, value in agent_task.items():
        if field not in KNOWN_TASK_FIELDS:
            raise ValueError(f"Unknown field in projected agent task: {field}")
        label = _TASK_FIELD_LABELS[field]
        rendered = _render_task_value(value)
        if field in _INLINE_TASK_FIELDS and "\n" not in rendered:
            sections.append(f"{label}: {rendered}")
        else:
            sections.append(f"{label}:\n{rendered}")
    return "\n\n".join(sections)


def _render_task_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)
