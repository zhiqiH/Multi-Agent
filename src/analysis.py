from __future__ import annotations

import csv
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
]


def write_scores_csv(path: Path, scores: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    fields = [
        "run_id",
        "task_id",
        "protocol",
        "accuracy_raw",
        "accuracy_norm",
        "completeness_norm",
        "helpfulness_raw",
        "helpfulness_norm",
        "hallucination_rate",
        "overall_quality_score",
        "runtime_seconds",
        "total_tokens",
        "estimated_cost",
        "message_count",
        "communication_density",
        "quality_cost_ratio",
        "failure_type",
        "notes",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for score in scores:
            writer.writerow({field: score.get(field, "") for field in fields})


def aggregate_by_protocol(scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for score in scores:
        buckets[score["protocol"]].append(score)

    rows: list[dict[str, Any]] = []
    for protocol, items in sorted(buckets.items()):
        row: dict[str, Any] = {"protocol": protocol, "runs": len(items)}
        for field in NUMERIC_FIELDS:
            values = [float(item.get(field, 0) or 0) for item in items]
            row[f"avg_{field}"] = round(mean(values), 6) if values else 0
        rows.append(row)
    return rows


def write_aggregate_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    if not rows:
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_summary_markdown(path: Path, rows: list[dict[str, Any]], scores: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    best = max(rows, key=lambda row: row.get("avg_overall_quality_score", 0), default=None)
    lines = ["# Experiment Summary", ""]
    lines.append(f"- Total scored runs: {len(scores)}")
    if best:
        lines.append(
            f"- Best average quality protocol: {best['protocol']} "
            f"({best['avg_overall_quality_score']:.4f})"
        )
    lines.extend(["", "## Protocol Averages", ""])
    lines.append("| Protocol | Runs | Avg Quality | Avg Tokens | Avg Messages | Avg Cost |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for row in rows:
        lines.append(
            "| {protocol} | {runs} | {quality:.4f} | {tokens:.1f} | {messages:.2f} | {cost:.6f} |".format(
                protocol=row["protocol"],
                runs=row["runs"],
                quality=row.get("avg_overall_quality_score", 0),
                tokens=row.get("avg_total_tokens", 0),
                messages=row.get("avg_message_count", 0),
                cost=row.get("avg_estimated_cost", 0),
            )
        )
    lines.extend(["", "## Low-Scoring / Failure Candidates", ""])
    low = sorted(scores, key=lambda item: item.get("overall_quality_score", 0))[: max(1, min(5, len(scores)))]
    for item in low:
        lines.append(
            f"- {item['run_id']}: score={item.get('overall_quality_score')}, "
            f"failure_type={item.get('failure_type')}, notes={item.get('notes', '')}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_aggregate_json(path: Path, rows: list[dict[str, Any]]) -> None:
    write_json(path, rows)

