from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from .io_utils import ensure_dir, write_json


NUMERIC_FIELDS = [
    "overall_quality_score",
    "accuracy_norm",
    "completeness_norm",
    "helpfulness_norm",
    "hallucination_rate",
    "runtime_seconds",
    "total_tokens",
    "estimated_cost",
    "active_agent_count",
    "interaction_count",
    "rounds_completed",
    "message_count",
    "communication_density",
    "agreement_rate",
    "critique_acceptance_rate",
    "tool_call_count",
    "quality_token_ratio",
    "quality_api_cost_ratio",
    "uncapped_quality_score",
    "overall_score_cap",
    "scorer_input_tokens",
    "scorer_output_tokens",
    "scorer_total_tokens",
    "judge_estimated_cost",
    "total_estimated_cost",
]

SCORE_IDENTITY_FIELDS = [
    "score_id",
    "run_id",
    "experiment_id",
    "condition_id",
    "judge_condition_id",
    "task_id",
    "category",
    "protocol_id",
    "protocol",
    "protocol_version",
    "role_mode",
    "evaluation_mode",
    "agent_provider",
    "agent_profile",
    "agent_model",
    "judge_provider",
    "judge_profile",
    "judge_model",
]

SCORE_CSV_FIELDS = SCORE_IDENTITY_FIELDS + [
    "accuracy_raw",
    "accuracy_norm",
    "completeness_norm",
    "helpfulness_raw",
    "helpfulness_norm",
    "hallucination_rate",
    "overall_quality_score",
    "uncapped_quality_score",
    "overall_score_cap",
    "cap_reasons",
    "runtime_seconds",
    "total_tokens",
    "estimated_cost",
    "active_agent_count",
    "interaction_count",
    "rounds_completed",
    "message_count",
    "communication_density",
    "agreement_rate",
    "critique_acceptance_rate",
    "tool_call_count",
    "quality_token_ratio",
    "quality_api_cost_ratio",
    "failure_type",
    "detected_failure_risks",
    "notes",
    "scorer_input_tokens",
    "scorer_output_tokens",
    "scorer_total_tokens",
    "judge_finish_reason",
    "judge_estimated_cost",
    "total_estimated_cost",
    "benchmark_sha256",
    "run_validity_warnings",
    "raw_evaluation",
]

CONDITION_GROUP_FIELDS = [
    "condition_id",
    "judge_condition_id",
    "agent_provider",
    "agent_profile",
    "agent_model",
    "evaluation_mode",
    "role_mode",
    "judge_provider",
    "judge_profile",
    "judge_model",
    "protocol_id",
    "protocol",
]
GROUP_BY_CHOICES = ("condition", "protocol", "experiment")


def write_scores_csv(path: Path, scores: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SCORE_CSV_FIELDS)
        writer.writeheader()
        for score in scores:
            writer.writerow({field: _score_csv_value(score, field) for field in SCORE_CSV_FIELDS})


def aggregate_scores(scores: list[dict[str, Any]], *, group_by: str = "condition") -> list[dict[str, Any]]:
    if group_by not in GROUP_BY_CHOICES:
        raise ValueError(f"Unknown group_by={group_by!r}. Choose from {GROUP_BY_CHOICES}.")
    if group_by == "condition":
        group_fields = CONDITION_GROUP_FIELDS
    elif group_by == "experiment":
        group_fields = ["experiment_id", *CONDITION_GROUP_FIELDS]
    else:
        group_fields = ["protocol_id", "protocol"]

    buckets: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for score in scores:
        key = tuple(_required_identity_value(score, field) for field in group_fields)
        buckets[key].append(score)

    rows: list[dict[str, Any]] = []
    for key, items in sorted(buckets.items()):
        row: dict[str, Any] = dict(zip(group_fields, key))
        row["runs"] = len(items)
        for field in NUMERIC_FIELDS:
            values = [_as_float(item[field]) for item in items if item.get(field) is not None]
            row[f"avg_{field}"] = round(mean(values), 6) if values else None
        rows.append(row)
    return rows


def write_aggregate_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_aggregate_json(path: Path, rows: list[dict[str, Any]]) -> None:
    write_json(path, rows)


def write_summary_markdown(
    path: Path,
    rows: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    *,
    group_by: str | None = None,
) -> None:
    ensure_dir(path.parent)
    group_by = group_by or "condition"
    if group_by not in GROUP_BY_CHOICES:
        raise ValueError(f"Unknown group_by={group_by!r}. Choose from {GROUP_BY_CHOICES}.")

    best = max(rows, key=lambda row: _as_float(row.get("avg_overall_quality_score")), default=None)
    lines = ["# Experiment Summary", "", f"- Total scored runs: {len(scores)}"]
    if best:
        best_label = _protocol_label(best) if group_by == "protocol" else _condition_label(best)
        lines.append(
            f"- Best average group: {best_label} "
            f"({_as_float(best.get('avg_overall_quality_score')):.4f})"
        )

    lines.extend(["", "## Group Averages", ""])
    if group_by == "protocol":
        lines.append(
            "| Protocol | Runs | Avg Quality | Avg Tokens | Avg Messages | Avg Runtime | Avg Cost |"
        )
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for row in rows:
            lines.append(
                "| {protocol} | {runs} | {quality:.4f} | {tokens:.1f} | "
                "{messages:.2f} | {runtime:.2f} | {cost:.6f} |".format(
                    protocol=_markdown_cell(_protocol_label(row)),
                    runs=row["runs"],
                    quality=_as_float(row.get("avg_overall_quality_score")),
                    tokens=_as_float(row.get("avg_total_tokens")),
                    messages=_as_float(row.get("avg_message_count")),
                    runtime=_as_float(row.get("avg_runtime_seconds")),
                    cost=_as_float(row.get("avg_estimated_cost")),
                )
            )
    else:
        lines.append(
            "| Agent | Judge | Protocol | Mode | Runs | Avg Quality | Avg Tokens | Avg Messages | Avg Runtime | Avg Cost |"
        )
        lines.append("|---|---|---|---|---:|---:|---:|---:|---:|---:|")
        for row in rows:
            lines.append(
                "| {agent} | {judge} | {protocol} | {mode} | {runs} | {quality:.4f} | "
                "{tokens:.1f} | {messages:.2f} | {runtime:.2f} | {cost:.6f} |".format(
                    agent=_markdown_cell(_agent_label(row)),
                    judge=_markdown_cell(_judge_label(row)),
                    protocol=_markdown_cell(_protocol_label(row)),
                    mode=_markdown_cell(row["evaluation_mode"]),
                    runs=row["runs"],
                    quality=_as_float(row.get("avg_overall_quality_score")),
                    tokens=_as_float(row.get("avg_total_tokens")),
                    messages=_as_float(row.get("avg_message_count")),
                    runtime=_as_float(row.get("avg_runtime_seconds")),
                    cost=_as_float(row.get("avg_estimated_cost")),
                )
            )

    lines.extend(["", "## Low-Scoring / Failure Runs", ""])
    low = sorted(scores, key=lambda item: _as_float(item.get("overall_quality_score")))[
        : max(1, min(5, len(scores)))
    ]
    for item in low:
        lines.append(
            f"- {_required_identity_value(item, 'run_id')}: score={item.get('overall_quality_score')}, "
            f"failure_type={item.get('failure_type')}, notes={item.get('notes', '')}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _identity_value(score: dict[str, Any], field: str) -> str:
    value = score.get(field)
    if value is not None and str(value).strip():
        return str(value)
    return "mixed"


def _required_identity_value(score: dict[str, Any], field: str) -> str:
    value = score.get(field)
    if value is None or not str(value).strip():
        raise ValueError(f"Score record is missing required identity field: {field}")
    return str(value)


def _score_csv_value(score: dict[str, Any], field: str) -> Any:
    if field in SCORE_IDENTITY_FIELDS:
        return _required_identity_value(score, field)
    value = score.get(field, "")
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def _as_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _agent_label(row: dict[str, Any]) -> str:
    return "/".join(
        _identity_value(row, field) for field in ("agent_provider", "agent_profile", "agent_model")
    )


def _judge_label(row: dict[str, Any]) -> str:
    return "/".join(
        _identity_value(row, field) for field in ("judge_provider", "judge_profile", "judge_model")
    )


def _protocol_label(row: dict[str, Any]) -> str:
    return f"{_identity_value(row, 'protocol_id')} ({_identity_value(row, 'protocol')})"


def _condition_label(row: dict[str, Any]) -> str:
    return f"{_agent_label(row)}; {_judge_label(row)}; {_protocol_label(row)}"


def _markdown_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
