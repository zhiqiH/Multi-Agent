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
from collections import defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.failure_taxonomy import (  # noqa: E402
    FAILURE_TYPES,
    NO_FAILURE_DISPLAY,
    display_failure_type,
)

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
FAILURE_DISPLAY_ORDER = (NO_FAILURE_DISPLAY, *FAILURE_TYPES[1:])
LEGACY_FIGURE_FILENAMES = (
    "protocol_score_distribution.png",
    "communication_vs_quality.png",
    "quality_vs_cost.png",
    "evidence_pass_rate.png",
)


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
    parser.add_argument(
        "--failure-threshold",
        type=float,
        default=0.5,
        help=(
            "Quality scores below this value are displayed as outcome failures "
            "in failure_distribution.png (default: 0.5)."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.dpi <= 0:
        raise SystemExit("--dpi must be positive")
    if not 0.0 <= args.failure_threshold <= 1.0:
        raise SystemExit("--failure-threshold must be between 0 and 1")

    results_dir = _project_path(args.results_dir)
    scores_path = results_dir / "scores.csv"
    rows = _read_scores(scores_path)
    figure_dir = results_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    removed = _remove_legacy_figures(figure_dir)

    plt = _load_matplotlib()
    _configure_style(plt)
    protocols = _ordered_values((row["protocol"] for row in rows), PROTOCOL_ORDER)
    colors = {
        protocol: plt.get_cmap("tab10")(index % 10)
        for index, protocol in enumerate(protocols)
    }

    plotters = (
        (_plot_protocol_quality, {}),
        (_plot_category_protocol_heatmap, {}),
        (_plot_quality_vs_tokens, {}),
        (
            _plot_failure_distribution,
            {"failure_threshold": args.failure_threshold},
        ),
    )
    generated: list[Path] = []
    skipped: list[str] = []
    for plotter, plotter_options in plotters:
        output = plotter(
            plt,
            rows,
            protocols,
            colors,
            figure_dir,
            args.dpi,
            **plotter_options,
        )
        if output is None:
            skipped.append(plotter.__name__.removeprefix("_plot_"))
        else:
            generated.append(output)

    print(f"Loaded {len(rows)} scored runs from {scores_path}")
    for output in removed:
        print(f"REMOVED legacy figure {output}")
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
        required = {
            "protocol",
            "overall_quality_score",
            "total_tokens",
            "failure_type",
            "score_eligible",
        }
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
            row["total_tokens"] = _as_float(raw.get("total_tokens"))
            row["score_eligible"] = _as_bool(raw.get("score_eligible"))
            try:
                row["failure_type"] = display_failure_type(raw.get("failure_type"))
            except ValueError as exc:
                raise SystemExit(
                    f"{path} contains a failure type outside the current seven-category taxonomy. "
                    "Rescore the logs with 'python3 scripts/score.py --overwrite'."
                ) from exc
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


def _plot_failure_distribution(
    plt: Any,
    rows: list[dict[str, Any]],
    protocols: list[str],
    colors: dict[str, Any],
    figure_dir: Path,
    dpi: int,
    *,
    failure_threshold: float,
) -> Path | None:
    del protocols, colors
    ordered = list(FAILURE_DISPLAY_ORDER)
    passed_counts = {label: 0 for label in ordered}
    failed_counts = {label: 0 for label in ordered}
    for row in rows:
        label = str(row["failure_type"])
        outcome_failed = (
            label != NO_FAILURE_DISPLAY
            or row["score_eligible"] is not True
            or row["overall_quality_score"] < failure_threshold
        )
        target = failed_counts if outcome_failed else passed_counts
        target[label] += 1

    fig, ax = plt.subplots(figsize=(9, max(4.5, 0.5 * len(ordered))))
    positions = list(range(len(ordered)))
    passed_values = [passed_counts[label] for label in ordered]
    failed_values = [failed_counts[label] for label in ordered]
    totals = [passed + failed for passed, failed in zip(passed_values, failed_values)]
    ax.barh(
        positions,
        passed_values,
        color=plt.get_cmap("tab10")(2),
        alpha=0.78,
        label="No failure signal",
    )
    ax.barh(
        positions,
        failed_values,
        left=passed_values,
        color=plt.get_cmap("tab10")(3),
        alpha=0.82,
        label="Failure: classified, low score, or invalid",
    )
    ax.set_yticks(positions, labels=ordered)
    ax.invert_yaxis()
    ax.set_xlabel("Scored run count")
    ax.set_title(
        "Failure Distribution "
        f"(all scored runs; low score < {failure_threshold:.2f})"
    )
    ax.legend(loc="lower right")
    maximum = max(totals, default=0)
    ax.set_xlim(0, max(1, maximum * 1.12))
    for position, value in zip(positions, totals):
        offset = max(0.06, maximum * 0.015)
        ax.text(value + offset, position, str(value), va="center")
    return _save(fig, figure_dir / "failure_distribution.png", dpi)


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
) -> Path | None:
    available_rows = [
        row
        for row in rows
        if row.get(field) is not None
        and row[field] > 0
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


def _remove_legacy_figures(figure_dir: Path) -> list[Path]:
    removed: list[Path] = []
    for filename in LEGACY_FIGURE_FILENAMES:
        path = figure_dir / filename
        if path.is_file():
            path.unlink()
            removed.append(path)
    return removed


def _project_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_ROOT / path


if __name__ == "__main__":
    sys.exit(main())
