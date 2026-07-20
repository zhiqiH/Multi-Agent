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
    "available_tools",
    "tool_expectations",
    "prompt",
    "required_output_format",
)

GRADING_FIELDS: tuple[str, ...] = (
    "evaluation_criteria",
    "ground_truth",
    "expected_failure_risks",
    "scoring_rubric",
    "required_evidence",
    "evidence_policy",
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

TOOL_CONTROL_FIELDS: frozenset[str] = frozenset({"available_tools", "tool_expectations"})
KNOWN_TASK_FIELDS: frozenset[str] = REQUIRED_TASK_FIELDS | TOOL_CONTROL_FIELDS | {
    "evidence_policy",
    "notes",
    "title",
    "input_files",
}
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

_LEGACY_GOOGLE_SEARCH_EXPECTATION: dict[str, Any] = {
    "description": (
        "Searches the web for task-relevant sources and returns auditable title, URL or DOI, "
        "and snippet records."
    ),
    "required_output": {
        "results": [
            {
                "title": "string",
                "url_or_doi": "string",
                "snippet": "string",
            }
        ]
    },
}

_TASK_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9_-]*-\d{2}$")
_TASK_FIELD_LABELS = {
    "task_id": "Task ID",
    "category": "Category",
    "difficulty": "Difficulty",
    "author": "Author",
    "tool_requirement": "Tool Requirement",
    "available_tools": "Available Tools",
    "tool_expectations": "Tool Expectations",
    "prompt": "Prompt",
    "required_output_format": "Required Output Format",
    "evaluation_criteria": "Evaluation Criteria",
    "required_evidence": "Required Evidence",
    "evidence_policy": "Evidence Policy",
    "scoring_rubric": "Scoring Rubric",
    "expected_failure_risks": "Expected Failure Risks",
    "ground_truth": "Ground Truth",
    "notes": "Notes",
    "title": "Title",
    "input_files": "Input Files",
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
    for index, raw_task in enumerate(tasks):
        task = _normalize_task(raw_task, source=path)
        tasks[index] = task
        _validate_task(task, source=path)
        task_id = str(task["task_id"])
        if task_id in task_ids:
            raise ValueError(f"Duplicate task_id {task_id!r} in benchmark: {path}")
        task_ids.add(task_id)

    result = {key: deepcopy(value) for key, value in payload.items() if key != "tasks"}
    result["tasks"] = tasks
    return result


def _normalize_task(task: Any, *, source: Path) -> Any:
    """Return the canonical Benchmark-C task shape.

    Benchmark D predates the current Agent/Judge field boundary and stores one
    weighted ``evaluation_rubric`` instead of the canonical private grading
    fields.  The conversion below preserves that source rubric rather than
    inventing new task-specific answers.  New benchmark files should be authored
    directly in the canonical Benchmark-C shape.
    """

    if not isinstance(task, dict):
        return task
    normalized = deepcopy(task)

    legacy_rubric = normalized.pop("evaluation_rubric", None)
    is_legacy_task = isinstance(legacy_rubric, list)
    if "evaluation_criteria" not in normalized and isinstance(legacy_rubric, list):
        criteria: list[dict[str, Any]] = []
        for index, item in enumerate(legacy_rubric, start=1):
            if not isinstance(item, dict):
                continue
            name = str(item.get("criterion") or f"criterion_{index}").strip()
            description = str(item.get("description") or name).strip()
            criteria.append(
                {
                    "id": f"C{index}",
                    "criterion": f"{name}: {description}",
                    "weight": item.get("weight", 1),
                }
            )
        normalized["evaluation_criteria"] = criteria
        normalized.setdefault(
            "scoring_rubric",
            {
                "scoring_method": (
                    "Score each converted legacy evaluation criterion independently using its "
                    "recorded weight, then apply the standard benchmark caps."
                ),
                "legacy_evaluation_rubric": deepcopy(legacy_rubric),
            },
        )
        normalized.setdefault(
            "ground_truth",
            {
                "evaluation_requirements": [
                    criterion["criterion"] for criterion in criteria
                ]
            },
        )
        normalized.setdefault(
            "expected_failure_risks",
            [
                "Failure to satisfy one or more recorded evaluation-rubric requirements.",
                "Failure to follow the required output structure or quantitative constraints.",
                "Use of a prohibited tool or failure to use a task-required tool.",
            ],
        )

    normalized.setdefault("author", f"Legacy task from {source.stem}")
    requirement = str(normalized.get("tool_requirement") or "").strip().lower()
    normalized.setdefault(
        "required_evidence",
        (
            "External evidence is required as specified by the task prompt and task tool expectations."
            if requirement == "required"
            else "No external evidence is required; external tool use is prohibited."
        ),
    )

    output_format = normalized.get("required_output_format")
    if output_format is not None and not isinstance(output_format, str):
        normalized["required_output_format"] = json.dumps(
            output_format, ensure_ascii=False, indent=2
        )

    evidence_policy = normalized.get("evidence_policy")
    if isinstance(evidence_policy, dict):
        evidence_policy = deepcopy(evidence_policy)
        legacy_traceability = evidence_policy.pop(
            "minimum_citation_traceability_rate", None
        )
        if legacy_traceability is not None:
            evidence_policy.setdefault("minimum_traceability_rate", legacy_traceability)
        normalized["evidence_policy"] = evidence_policy
    elif is_legacy_task and requirement == "required":
        # Benchmark D predates structured evidence policies.  Keep it runnable
        # without editing the benchmark while applying a conservative minimum;
        # the legacy rubric and prompt remain the semantic source of truth.
        normalized["evidence_policy"] = {
            "minimum_substantive_sources": 1,
            "minimum_traceability_rate": 0.0,
            "violation_score_cap": 0.5,
        }

    uses_compatibility_tools = "available_tools" not in normalized
    if uses_compatibility_tools:
        normalized["available_tools"] = _compatibility_available_tools(
            requirement, normalized.get("evidence_policy")
        )
    if "tool_expectations" not in normalized:
        normalized["tool_expectations"] = (
            {"google_search_tool": deepcopy(_LEGACY_GOOGLE_SEARCH_EXPECTATION)}
            if uses_compatibility_tools
            and normalized["available_tools"] == ["google_search_tool"]
            else {}
        )
    return normalized


def _compatibility_available_tools(requirement: str, evidence_policy: Any) -> list[str]:
    """Derive a narrow tool surface for tasks authored before task-level tool fields."""

    if requirement != "required":
        return []
    policy = evidence_policy if isinstance(evidence_policy, dict) else {}
    tools: list[str] = []
    if int(policy.get("minimum_local_documents", 0)) > 0:
        tools.extend(
            ["list_local_documents", "read_local_document", "read_local_documents"]
        )
    if any(
        int(policy.get(field, 0)) > 0
        for field in (
            "minimum_academic_records",
            "minimum_recent_academic_records",
            "minimum_identifier_records",
        )
    ) or policy.get("academic_provider_consistency"):
        tools.extend(["academic_search", "academic_lookup"])
    if policy.get("required_domain_groups"):
        tools.extend(["web_search", "fetch_url", "fetch_urls"])
    return list(dict.fromkeys(tools)) or ["google_search_tool"]


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
    if task["tool_requirement"] == "Required":
        _validate_evidence_policy(task_id, task.get("evidence_policy"))

    for field in ("category", "author", "prompt", "required_output_format"):
        if not isinstance(task[field], str) or not task[field].strip():
            raise ValueError(f"Task {task_id} field {field!r} must be a non-empty string")

    available_tools = task.get("available_tools")
    if not isinstance(available_tools, list) or not all(
        isinstance(name, str) and name.strip() for name in available_tools
    ):
        raise ValueError(f"Task {task_id} available_tools must be a list of non-empty names")
    if len(set(available_tools)) != len(available_tools):
        raise ValueError(f"Task {task_id} available_tools contains duplicate names")
    if task["tool_requirement"] == "Required" and not available_tools:
        raise ValueError(
            f"Task {task_id} requires tools but available_tools is empty; "
            "the benchmark task must declare its exact tool surface"
        )
    if task["tool_requirement"] == "Prohibited" and available_tools:
        raise ValueError(f"Task {task_id} prohibits tools but available_tools is not empty")

    tool_expectations = task.get("tool_expectations")
    if not isinstance(tool_expectations, dict):
        raise ValueError(f"Task {task_id} tool_expectations must be an object")
    unknown_expectations = sorted(set(tool_expectations) - set(available_tools))
    if unknown_expectations:
        raise ValueError(
            f"Task {task_id} has tool_expectations for unavailable tools: {unknown_expectations}"
        )
    for name, expectation in tool_expectations.items():
        if not isinstance(expectation, dict) or not expectation:
            raise ValueError(
                f"Task {task_id} tool_expectations.{name} must be a non-empty object"
            )

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


def _validate_evidence_policy(task_id: str, policy: Any) -> None:
    if not isinstance(policy, dict) or not policy:
        raise ValueError(f"Task {task_id} requires a non-empty evidence_policy")
    integer_fields = (
        "minimum_substantive_sources",
        "minimum_academic_records",
        "minimum_recent_academic_records",
        "minimum_publication_year",
        "minimum_identifier_records",
        "minimum_local_documents",
    )
    for field in integer_fields:
        value = policy.get(field, 0)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"Task {task_id} evidence_policy.{field} must be a non-negative integer")
    domain_groups = policy.get("required_domain_groups") or []
    if not isinstance(domain_groups, list) or not all(
        isinstance(group, list)
        and group
        and all(isinstance(domain, str) and domain.strip() for domain in group)
        for group in domain_groups
    ):
        raise ValueError(f"Task {task_id} evidence_policy.required_domain_groups is invalid")
    for field in ("academic_provider_consistency", "common_retrieval_date"):
        if not isinstance(policy.get(field, False), bool):
            raise ValueError(f"Task {task_id} evidence_policy.{field} must be boolean")
    traceability = policy.get("minimum_traceability_rate", 0.0)
    if not isinstance(traceability, (int, float)) or isinstance(traceability, bool):
        raise ValueError(f"Task {task_id} evidence_policy.minimum_traceability_rate must be numeric")
    if not 0 <= float(traceability) <= 1:
        raise ValueError(f"Task {task_id} evidence_policy.minimum_traceability_rate must be from 0 to 1")
    cap = policy.get("violation_score_cap", 0.5)
    if not isinstance(cap, (int, float)) or isinstance(cap, bool) or not 0 <= float(cap) <= 1:
        raise ValueError(f"Task {task_id} evidence_policy.violation_score_cap must be from 0 to 1")


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
