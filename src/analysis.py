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
    "message_count",
    "communication_density",
    "quality_cost_ratio",
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
    "task_id",
    "protocol_id",
    "protocol",
    "candidate_provider",
    "candidate_profile",
    "candidate_model",
    "candidate_visibility_status",
    "judge_provider",
    "judge_profile",
    "evaluator",
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
    "message_count",
    "communication_density",
    "quality_cost_ratio",
    "failure_type",
    "notes",
    "scorer_input_tokens",
    "scorer_output_tokens",
    "scorer_total_tokens",
    "judge_estimated_cost",
    "total_estimated_cost",
    "benchmark_sha256",
    "run_validity_warnings",
    "raw_evaluation",
]


CONDITION_GROUP_FIELDS = [
    "candidate_provider",
    "candidate_profile",
    "candidate_model",
    "candidate_visibility_status",
    "judge_provider",
    "judge_profile",
    "evaluator",
    "protocol_id",
    "protocol",
]


GROUP_BY_CHOICES = ("condition", "protocol")


_LEGACY_IDENTITY_DEFAULTS = {
    "run_id": "legacy",
    "task_id": "unknown",
    "protocol_id": "legacy",
    "protocol": "Unknown Protocol",
    "candidate_provider": "unknown",
    "candidate_profile": "legacy",
    "candidate_model": "unknown",
    "candidate_visibility_status": "legacy-unverified",
    "judge_provider": "unknown",
    "judge_profile": "legacy",
    "evaluator": "unknown",
}


def write_scores_csv(path: Path, scores: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SCORE_CSV_FIELDS)
        writer.writeheader()
        for score in scores:
            row = {field: _score_csv_value(score, field) for field in SCORE_CSV_FIELDS}
            writer.writerow(row)


def aggregate_scores(scores: list[dict[str, Any]], *, group_by: str = "condition") -> list[dict[str, Any]]:
    """Aggregate scores without mixing model/judge conditions by default.

    ``condition`` groups by candidate identity, judge identity, and protocol.
    ``protocol`` preserves the legacy behavior of grouping only by the protocol
    display name. Missing identity fields in historical scores receive explicit
    ``unknown``/``legacy`` values in the aggregate output.
    """
    if group_by not in GROUP_BY_CHOICES:
        raise ValueError(f"Unknown group_by={group_by!r}. Choose from {GROUP_BY_CHOICES}.")

    group_fields = CONDITION_GROUP_FIELDS if group_by == "condition" else ["protocol"]
    buckets: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for score in scores:
        key = tuple(_identity_value(score, field) for field in group_fields)
        buckets[key].append(score)

    rows: list[dict[str, Any]] = []
    for key, items in sorted(buckets.items()):
        row: dict[str, Any] = dict(zip(group_fields, key))
        row["runs"] = len(items)
        for field in NUMERIC_FIELDS:
            values = [_as_float(item.get(field, 0)) for item in items]
            row[f"avg_{field}"] = round(mean(values), 6) if values else 0
        rows.append(row)
    return rows


def aggregate_by_protocol(scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Backward-compatible wrapper for the original protocol-only aggregate."""
    return aggregate_scores(scores, group_by="protocol")


def write_aggregate_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    if not rows:
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_summary_markdown(
    path: Path,
    rows: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    *,
    group_by: str | None = None,
) -> None:
    ensure_dir(path.parent)
    if group_by is None:
        group_by = "condition" if rows and "candidate_profile" in rows[0] else "protocol"
    if group_by not in GROUP_BY_CHOICES:
        raise ValueError(f"Unknown group_by={group_by!r}. Choose from {GROUP_BY_CHOICES}.")

    best = max(rows, key=lambda row: _as_float(row.get("avg_overall_quality_score", 0)), default=None)
    lines = ["# Experiment Summary", ""]
    lines.append(f"- Total scored runs: {len(scores)}")
    if best:
        if group_by == "condition":
            lines.append(
                f"- Best average condition: {_condition_label(best)} "
                f"({_as_float(best.get('avg_overall_quality_score')):.4f})"
            )
        else:
            lines.append(
                f"- Best average quality protocol: {best['protocol']} "
                f"({_as_float(best.get('avg_overall_quality_score')):.4f})"
            )

    if group_by == "condition":
        lines.extend(["", "## Condition Averages", ""])
        lines.append(
            "| Candidate | Judge | Protocol | Runs | Avg Quality | Avg Tokens | Avg Messages | Avg Cost |"
        )
        lines.append("|---|---|---|---:|---:|---:|---:|---:|")
        for row in rows:
            lines.append(
                "| {candidate} | {judge} | {protocol} | {runs} | {quality:.4f} | "
                "{tokens:.1f} | {messages:.2f} | {cost:.6f} |".format(
                    candidate=_markdown_cell(_candidate_label(row)),
                    judge=_markdown_cell(_judge_label(row)),
                    protocol=_markdown_cell(_protocol_label(row)),
                    runs=row["runs"],
                    quality=_as_float(row.get("avg_overall_quality_score")),
                    tokens=_as_float(row.get("avg_total_tokens")),
                    messages=_as_float(row.get("avg_message_count")),
                    cost=_as_float(row.get("avg_estimated_cost")),
                )
            )
    else:
        lines.extend(["", "## Protocol Averages", ""])
        lines.append("| Protocol | Runs | Avg Quality | Avg Tokens | Avg Messages | Avg Cost |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for row in rows:
            lines.append(
                "| {protocol} | {runs} | {quality:.4f} | {tokens:.1f} | {messages:.2f} | {cost:.6f} |".format(
                    protocol=_markdown_cell(row["protocol"]),
                    runs=row["runs"],
                    quality=_as_float(row.get("avg_overall_quality_score")),
                    tokens=_as_float(row.get("avg_total_tokens")),
                    messages=_as_float(row.get("avg_message_count")),
                    cost=_as_float(row.get("avg_estimated_cost")),
                )
            )

    lines.extend(["", "## Low-Scoring / Failure Candidates", ""])
    low = sorted(scores, key=lambda item: _as_float(item.get("overall_quality_score", 0)))[
        : max(1, min(5, len(scores)))
    ]
    for item in low:
        lines.append(
            f"- {_identity_value(item, 'run_id')}: score={item.get('overall_quality_score')}, "
            f"failure_type={item.get('failure_type')}, notes={item.get('notes', '')}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_aggregate_json(path: Path, rows: list[dict[str, Any]]) -> None:
    write_json(path, rows)


def _identity_value(score: dict[str, Any], field: str) -> str:
    value = score.get(field)
    if value is not None and str(value).strip():
        return str(value)

    if field == "score_id":
        run_id = _identity_value(score, "run_id")
        evaluator = _identity_value(score, "evaluator")
        return f"legacy::{run_id}::{evaluator}"
    if field == "candidate_model" and score.get("model"):
        return str(score["model"])
    if field == "protocol" and score.get("protocol_id"):
        return str(score["protocol_id"])
    return _LEGACY_IDENTITY_DEFAULTS.get(field, "unknown")


def _score_csv_value(score: dict[str, Any], field: str) -> Any:
    if field in SCORE_IDENTITY_FIELDS:
        return _identity_value(score, field)
    value = score.get(field, "")
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def _as_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _candidate_label(row: dict[str, Any]) -> str:
    identity = "/".join(
        str(row.get(field) or _LEGACY_IDENTITY_DEFAULTS[field])
        for field in ("candidate_provider", "candidate_profile", "candidate_model")
    )
    status = str(
        row.get("candidate_visibility_status")
        or _LEGACY_IDENTITY_DEFAULTS["candidate_visibility_status"]
    )
    return f"{identity} [{status}]"


def _judge_label(row: dict[str, Any]) -> str:
    return "/".join(
        str(row.get(field) or _LEGACY_IDENTITY_DEFAULTS[field])
        for field in ("judge_provider", "judge_profile", "evaluator")
    )


def _protocol_label(row: dict[str, Any]) -> str:
    protocol_id = str(row.get("protocol_id") or _LEGACY_IDENTITY_DEFAULTS["protocol_id"])
    protocol = str(row.get("protocol") or _LEGACY_IDENTITY_DEFAULTS["protocol"])
    return f"{protocol_id} ({protocol})"


def _condition_label(row: dict[str, Any]) -> str:
    return f"{_candidate_label(row)}; {_judge_label(row)}; {_protocol_label(row)}"


def _markdown_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
