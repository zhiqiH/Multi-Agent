#!/usr/bin/env python3
"""Generate score-based experiment figures from a results directory."""

from __future__ import annotations

import argparse
import csv
import math
import os
import statistics
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_ORDER = (
    "Single Agent",
    "Unstructured Group Chat",
    "Sequential Handoff",
    "Shared Blackboard",
    "Manager-Worker",
    "Debate",
    "Voting",
    "Dynamic Task Allocation",
)
CATEGORY_ORDER = (
    "Literature Review",
    "Technical Analysis",
    "Software Engineering",
    "Market Research",
    "Educational Content",
    "Strategic Planning",
)
CATEGORY_BY_PREFIX = {
    "LR": "Literature Review",
    "TA": "Technical Analysis",
    "SE": "Software Engineering",
    "MR": "Market Research",
    "EC": "Educational Content",
    "SP": "Strategic Planning",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate PNG figures from score.py outputs."
    )
    parser.add_argument(
        "--results-dir",
        default="results/current",
        help="Directory containing scores.csv; figures are written to its figures subdirectory.",
    )
    parser.add_argument("--dpi", type=int, default=200, help="PNG resolution.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.dpi <= 0:
        raise SystemExit("--dpi must be positive")

    results_dir = _project_path(args.results_dir)
    scores_path = results_dir / "scores.csv"
    rows = _read_scores(scores_path)
    figure_dir = results_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    plt = _load_matplotlib()
    _configure_style(plt)
    protocols = _ordered_values((row["protocol"] for row in rows), PROTOCOL_ORDER)
    colors = {
        protocol: plt.get_cmap("tab10")(index % 10)
        for index, protocol in enumerate(protocols)
    }

    plotters: tuple[Callable[..., Path | None], ...] = (
        _plot_protocol_quality,
        _plot_score_distribution,
        _plot_category_protocol_heatmap,
        _plot_quality_vs_tokens,
        _plot_communication_vs_quality,
        _plot_quality_vs_cost,
        _plot_failure_distribution,
        _plot_evidence_pass_rate,
    )
    generated: list[Path] = []
    skipped: list[str] = []
    for plotter in plotters:
        output = plotter(plt, rows, protocols, colors, figure_dir, args.dpi)
        if output is None:
            skipped.append(plotter.__name__.removeprefix("_plot_"))
        else:
            generated.append(output)

    print(f"Loaded {len(rows)} scored runs from {scores_path}")
    for output in generated:
        print(f"CREATED {output}")
    if skipped:
        print(f"SKIPPED unavailable metrics: {', '.join(skipped)}")
    print(f"Done. figures={len(generated)} directory={figure_dir}")
    return 0


def _read_scores(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise SystemExit(
            f"Score file not found: {path}. Run 'python3 scripts/score.py' first."
        )
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"protocol", "overall_quality_score"}
        missing = sorted(required - set(reader.fieldnames or []))
        if missing:
            raise SystemExit(f"{path} is missing required columns: {', '.join(missing)}")
        rows: list[dict[str, Any]] = []
        for raw in reader:
            protocol = str(raw.get("protocol") or "").strip()
            quality = _as_float(raw.get("overall_quality_score"))
            if not protocol or quality is None:
                continue
            row: dict[str, Any] = dict(raw)
            row["protocol"] = protocol
            row["overall_quality_score"] = quality
            row["category"] = _category(raw)
            for field in (
                "total_tokens",
                "message_count",
                "estimated_cost",
                "total_estimated_cost",
            ):
                row[field] = _as_float(raw.get(field))
            row["evidence_policy_satisfied"] = _as_bool(
                raw.get("evidence_policy_satisfied")
            )
            rows.append(row)
    if not rows:
        raise SystemExit(f"No valid scored rows found in: {path}")
    return rows


def _load_matplotlib() -> Any:
    cache_dir = Path(tempfile.gettempdir()) / "multi-agent-matplotlib-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache_dir))
    os.environ.setdefault("XDG_CACHE_HOME", str(cache_dir))
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise SystemExit(
            "matplotlib is required. Run: python3 -m pip install -r requirements.txt"
        ) from exc
    return plt


def _configure_style(plt: Any) -> None:
    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except OSError:
        plt.style.use("default")
    plt.rcParams.update(
        {
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
            "font.size": 10,
            "savefig.facecolor": "white",
        }
    )


def _plot_protocol_quality(
    plt: Any,
    rows: list[dict[str, Any]],
    protocols: list[str],
    colors: dict[str, Any],
    figure_dir: Path,
    dpi: int,
) -> Path:
    grouped = _quality_by_protocol(rows, protocols)
    means = [statistics.fmean(grouped[protocol]) for protocol in protocols]
    errors = [_confidence_interval(grouped[protocol]) for protocol in protocols]
    positions = list(range(len(protocols)))
    fig, ax = plt.subplots(figsize=(9, max(4.8, 0.58 * len(protocols))))
    ax.barh(
        positions,
        means,
        xerr=errors,
        color=[colors[protocol] for protocol in protocols],
        alpha=0.86,
        capsize=3,
    )
    ax.set_yticks(positions, labels=protocols)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Overall quality score (mean with 95% CI)")
    ax.set_title("Protocol Quality Comparison")
    for position, protocol, value, error in zip(positions, protocols, means, errors):
        ax.text(
            min(1.01, value + error + 0.015),
            position,
            f"{value:.3f}  n={len(grouped[protocol])}",
            va="center",
        )
    return _save(fig, figure_dir / "protocol_quality.png", dpi)


def _plot_score_distribution(
    plt: Any,
    rows: list[dict[str, Any]],
    protocols: list[str],
    colors: dict[str, Any],
    figure_dir: Path,
    dpi: int,
) -> Path:
    grouped = _quality_by_protocol(rows, protocols)
    values = [grouped[protocol] for protocol in protocols]
    fig, ax = plt.subplots(figsize=(9, max(4.8, 0.58 * len(protocols))))
    boxes = ax.boxplot(
        values,
        vert=False,
        patch_artist=True,
        showmeans=True,
        meanprops={"marker": "D", "markerfacecolor": "white", "markeredgecolor": "black"},
        medianprops={"color": "black", "linewidth": 1.5},
    )
    for patch, protocol in zip(boxes["boxes"], protocols):
        patch.set_facecolor(colors[protocol])
        patch.set_alpha(0.72)
    ax.set_yticks(range(1, len(protocols) + 1), labels=protocols)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.02)
    ax.set_xlabel("Overall quality score")
    ax.set_title("Score Distribution by Protocol")
    return _save(fig, figure_dir / "protocol_score_distribution.png", dpi)


def _plot_category_protocol_heatmap(
    plt: Any,
    rows: list[dict[str, Any]],
    protocols: list[str],
    colors: dict[str, Any],
    figure_dir: Path,
    dpi: int,
) -> Path | None:
    del colors
    categories = _ordered_values(
        (row["category"] for row in rows if row.get("category")), CATEGORY_ORDER
    )
    if not categories:
        return None
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        category = row.get("category")
        if category:
            grouped[(category, row["protocol"])].append(row["overall_quality_score"])
    matrix = [
        [
            statistics.fmean(grouped[(category, protocol)])
            if grouped[(category, protocol)]
            else math.nan
            for protocol in protocols
        ]
        for category in categories
    ]
    fig, ax = plt.subplots(
        figsize=(max(9, 1.25 * len(protocols)), max(4.5, 0.7 * len(categories)))
    )
    image = ax.imshow(matrix, cmap="viridis", vmin=0, vmax=1, aspect="auto")
    ax.grid(False)
    ax.set_xticks(range(len(protocols)), labels=protocols, rotation=35, ha="right")
    ax.set_yticks(range(len(categories)), labels=categories)
    ax.set_title("Mean Quality by Task Category and Protocol")
    for row_index, values in enumerate(matrix):
        for column_index, value in enumerate(values):
            if math.isnan(value):
                continue
            text_color = "white" if value < 0.45 else "black"
            ax.text(
                column_index,
                row_index,
                f"{value:.2f}",
                ha="center",
                va="center",
                color=text_color,
                fontsize=8,
            )
    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label("Mean overall quality score")
    return _save(fig, figure_dir / "category_protocol_quality.png", dpi)


def _plot_quality_vs_tokens(
    plt: Any,
    rows: list[dict[str, Any]],
    protocols: list[str],
    colors: dict[str, Any],
    figure_dir: Path,
    dpi: int,
) -> Path | None:
    return _scatter_metric(
        plt,
        rows,
        protocols,
        colors,
        figure_dir / "quality_vs_tokens.png",
        dpi,
        field="total_tokens",
        xlabel="Total Agent tokens",
        title="Token Cost vs Quality",
        logarithmic=True,
    )


def _plot_communication_vs_quality(
    plt: Any,
    rows: list[dict[str, Any]],
    protocols: list[str],
    colors: dict[str, Any],
    figure_dir: Path,
    dpi: int,
) -> Path | None:
    return _scatter_metric(
        plt,
        rows,
        protocols,
        colors,
        figure_dir / "communication_vs_quality.png",
        dpi,
        field="message_count",
        xlabel="Inter-agent message count",
        title="Communication Overhead vs Quality",
        logarithmic=False,
        allow_zero=True,
    )


def _plot_quality_vs_cost(
    plt: Any,
    rows: list[dict[str, Any]],
    protocols: list[str],
    colors: dict[str, Any],
    figure_dir: Path,
    dpi: int,
) -> Path | None:
    field = "total_estimated_cost"
    if not any((row.get(field) or 0) > 0 for row in rows):
        field = "estimated_cost"
    return _scatter_metric(
        plt,
        rows,
        protocols,
        colors,
        figure_dir / "quality_vs_cost.png",
        dpi,
        field=field,
        xlabel="Estimated API cost (USD)",
        title="API Cost vs Quality",
        logarithmic=True,
    )


def _plot_failure_distribution(
    plt: Any,
    rows: list[dict[str, Any]],
    protocols: list[str],
    colors: dict[str, Any],
    figure_dir: Path,
    dpi: int,
) -> Path | None:
    del protocols, colors
    if not any("failure_type" in row for row in rows):
        return None
    labels = []
    for row in rows:
        value = str(row.get("failure_type") or "").strip()
        labels.append("No Failure" if not value or value.lower() == "none" else value)
    counts = Counter(labels)
    ordered = sorted(counts, key=lambda label: (label == "No Failure", -counts[label], label))
    fig, ax = plt.subplots(figsize=(9, max(4.5, 0.5 * len(ordered))))
    positions = list(range(len(ordered)))
    values = [counts[label] for label in ordered]
    ax.barh(positions, values, color=plt.get_cmap("tab10")(3), alpha=0.82)
    ax.set_yticks(positions, labels=ordered)
    ax.invert_yaxis()
    ax.set_xlabel("Scored run count")
    ax.set_title("Failure Type Distribution")
    ax.set_xlim(0, max(values) * 1.12 if values else 1)
    for position, value in zip(positions, values):
        ax.text(value + 0.15, position, str(value), va="center")
    return _save(fig, figure_dir / "failure_distribution.png", dpi)


def _plot_evidence_pass_rate(
    plt: Any,
    rows: list[dict[str, Any]],
    protocols: list[str],
    colors: dict[str, Any],
    figure_dir: Path,
    dpi: int,
) -> Path | None:
    grouped: dict[str, list[bool]] = defaultdict(list)
    for row in rows:
        value = row.get("evidence_policy_satisfied")
        if value is not None:
            grouped[row["protocol"]].append(value)
    available = [protocol for protocol in protocols if grouped[protocol]]
    if not available:
        return None
    rates = [sum(grouped[protocol]) / len(grouped[protocol]) for protocol in available]
    positions = list(range(len(available)))
    fig, ax = plt.subplots(figsize=(9, max(4.8, 0.58 * len(available))))
    ax.barh(
        positions,
        rates,
        color=[colors[protocol] for protocol in available],
        alpha=0.86,
    )
    ax.set_yticks(positions, labels=available)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Evidence constraint pass rate")
    ax.set_title("Evidence Constraint Pass Rate by Protocol")
    for position, rate, protocol in zip(positions, rates, available):
        ax.text(
            min(1.01, rate + 0.015),
            position,
            f"{rate:.1%}  n={len(grouped[protocol])}",
            va="center",
        )
    return _save(fig, figure_dir / "evidence_pass_rate.png", dpi)


def _scatter_metric(
    plt: Any,
    rows: list[dict[str, Any]],
    protocols: list[str],
    colors: dict[str, Any],
    output: Path,
    dpi: int,
    *,
    field: str,
    xlabel: str,
    title: str,
    logarithmic: bool,
    allow_zero: bool = False,
) -> Path | None:
    available_rows = [
        row
        for row in rows
        if row.get(field) is not None
        and (row[field] >= 0 if allow_zero else row[field] > 0)
    ]
    if not available_rows:
        return None
    fig, ax = plt.subplots(figsize=(8.5, 6))
    for protocol in protocols:
        selected = [row for row in available_rows if row["protocol"] == protocol]
        if not selected:
            continue
        x_values = [row[field] for row in selected]
        y_values = [row["overall_quality_score"] for row in selected]
        ax.scatter(
            x_values,
            y_values,
            color=colors[protocol],
            alpha=0.62,
            s=42,
            label=protocol,
        )
        ax.scatter(
            [statistics.fmean(x_values)],
            [statistics.fmean(y_values)],
            color=colors[protocol],
            edgecolor="black",
            linewidth=0.7,
            marker="X",
            s=110,
        )
    positive = [row[field] for row in available_rows]
    if logarithmic and min(positive) > 0 and max(positive) / min(positive) >= 20:
        ax.set_xscale("log")
        xlabel += " (log scale)"
    ax.set_ylim(0, 1.02)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Overall quality score")
    ax.set_title(title)
    ax.legend(loc="best", fontsize=8, frameon=True)
    return _save(fig, output, dpi)


def _quality_by_protocol(
    rows: list[dict[str, Any]], protocols: list[str]
) -> dict[str, list[float]]:
    grouped: dict[str, list[float]] = {protocol: [] for protocol in protocols}
    for row in rows:
        grouped[row["protocol"]].append(row["overall_quality_score"])
    return grouped


def _confidence_interval(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return 1.96 * statistics.stdev(values) / math.sqrt(len(values))


def _category(row: dict[str, str]) -> str:
    category = str(row.get("category") or "").strip()
    if category:
        return category
    task_id = str(row.get("task_id") or "")
    return CATEGORY_BY_PREFIX.get(task_id.split("-", 1)[0].upper(), "")


def _ordered_values(values: Any, preferred: tuple[str, ...]) -> list[str]:
    unique = {str(value) for value in values if str(value).strip()}
    ordered = [value for value in preferred if value in unique]
    return ordered + sorted(unique - set(ordered))


def _as_float(value: Any) -> float | None:
    if value is None or not str(value).strip():
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _as_bool(value: Any) -> bool | None:
    normalized = str(value or "").strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    return None


def _save(fig: Any, path: Path, dpi: int) -> Path:
    fig.tight_layout()
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    fig.clear()
    return path


def _project_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_ROOT / path


if __name__ == "__main__":
    sys.exit(main())
