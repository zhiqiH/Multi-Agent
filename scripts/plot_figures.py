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
    "quality_vs_tokens.png",
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
    return parser.parse_args()

def main() -> int:
    args = parse_args()
    if args.dpi <= 0:
        raise SystemExit("--dpi must be positive")

    results_dir = _resolve_results_dir(args.results_dir)
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
        (_plot_failure_distribution, {}),
        (_plot_protocol_token_quality, {}),
        (_plot_protocol_parallel_coordinates, {}),
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
            row["runtime_seconds"] = _as_float(raw.get("runtime_seconds"))
            try:
                row["failure_type"] = display_failure_type(raw.get("failure_type"))
            except ValueError as exc:
                raise SystemExit(
                    f"{path} contains a failure type outside the current failure taxonomy. "
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


def _plot_protocol_token_quality(
    plt: Any,
    rows: list[dict[str, Any]],
    protocols: list[str],
    colors: dict[str, Any],
    figure_dir: Path,
    dpi: int,
) -> Path | None:
    summaries = _protocol_metric_means(rows, protocols)
    available = [
        summary
        for summary in summaries
        if summary["mean_tokens"] is not None and summary["mean_tokens"] > 0
    ]
    if not available:
        return None

    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    for summary in available:
        protocol = summary["protocol"]
        mean_tokens = summary["mean_tokens"]
        mean_quality = summary["mean_quality"]
        ax.scatter(
            mean_tokens,
            mean_quality,
            color=colors[protocol],
            s=90,
            label=f"{protocol} (n={summary['count']})",
            zorder=3,
        )

    token_values = [summary["mean_tokens"] for summary in available]
    lower = min(token_values)
    upper = max(token_values)
    if math.isclose(lower, upper):
        lower /= 2
        upper *= 2
    else:
        lower = 10 ** (math.log10(lower) - 0.12)
        upper = 10 ** (math.log10(upper) + 0.12)
    ax.set_xscale("log")
    ax.set_xlim(lower, upper)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Mean Agent tokens (log scale)")
    ax.set_ylabel("Mean overall quality score")
    ax.set_title("Protocol Mean Token Cost vs Quality")
    ax.legend(
        title="Protocol",
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        borderaxespad=0,
        fontsize=8.5,
        frameon=True,
    )
    return _save(fig, figure_dir / "protocol_token_quality.png", dpi)


def _plot_protocol_parallel_coordinates(
    plt: Any,
    rows: list[dict[str, Any]],
    protocols: list[str],
    colors: dict[str, Any],
    figure_dir: Path,
    dpi: int,
) -> Path | None:
    summaries = _protocol_metric_means(rows, protocols)
    available = [
        summary
        for summary in summaries
        if summary["mean_tokens"] is not None
        and summary["mean_tokens"] > 0
        and summary["mean_runtime"] is not None
        and summary["mean_runtime"] > 0
    ]
    if not available:
        return None

    token_values = [summary["mean_tokens"] for summary in available]
    runtime_values = [summary["mean_runtime"] for summary in available]
    token_bounds = _log_bounds(token_values, expected=(100.0, 100_000.0))
    runtime_bounds = _log_bounds(runtime_values, expected=(5.0, 100.0))
    protocol_positions = {
        summary["protocol"]: (
            0.5
            if len(available) == 1
            else 1 - index / (len(available) - 1)
        )
        for index, summary in enumerate(available)
    }

    x_positions = (0, 1, 2, 3)
    fig, ax = plt.subplots(figsize=(11.5, max(6.2, 0.68 * len(available))))
    for x_position in x_positions:
        ax.axvline(x_position, color="#c7c7c7", linewidth=1.0, zorder=0)

    for summary in available:
        protocol = summary["protocol"]
        y_values = (
            protocol_positions[protocol],
            _log_normalize(summary["mean_tokens"], token_bounds),
            _log_normalize(summary["mean_runtime"], runtime_bounds),
            min(1.0, max(0.0, summary["mean_quality"])),
        )
        ax.plot(
            x_positions,
            y_values,
            color=colors[protocol],
            marker="o",
            markersize=5,
            linewidth=2.0,
            alpha=0.82,
            zorder=2,
        )
        ax.text(
            -0.04,
            y_values[0],
            protocol,
            ha="right",
            va="center",
            fontsize=8.5,
        )

    for x_position, bounds, formatter in (
        (1, token_bounds, _format_tokens),
        (2, runtime_bounds, _format_seconds),
    ):
        lower, upper = bounds
        middle = math.sqrt(lower * upper)
        for value in (lower, middle, upper):
            ax.text(
                x_position + 0.035,
                _log_normalize(value, bounds),
                formatter(value),
                ha="left",
                va="center",
                fontsize=8,
                color="#555555",
            )
    for value in (0.0, 0.5, 1.0):
        ax.text(
            3.035,
            value,
            f"{value:.1f}",
            ha="left",
            va="center",
            fontsize=8,
            color="#555555",
        )

    ax.set_xlim(-0.65, 3.3)
    ax.set_ylim(-0.04, 1.04)
    ax.set_xticks(
        x_positions,
        labels=("Protocol", "Mean tokens (log)", "Mean time (log)", "Mean quality"),
    )
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", length=0, pad=9)
    ax.set_yticks([])
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("Protocol Resource–Quality Profiles", pad=28)
    return _save(fig, figure_dir / "protocol_parallel_coordinates.png", dpi)


def _plot_failure_distribution(
    plt: Any,
    rows: list[dict[str, Any]],
    protocols: list[str],
    colors: dict[str, Any],
    figure_dir: Path,
    dpi: int,
) -> Path | None:
    del protocols, colors
    ordered = list(FAILURE_DISPLAY_ORDER)
    counts = Counter(str(row["failure_type"]) for row in rows)
    fig, ax = plt.subplots(figsize=(9, max(4.5, 0.5 * len(ordered))))
    positions = list(range(len(ordered)))
    values = [counts[label] for label in ordered]
    ax.barh(
        positions,
        values,
        color=plt.get_cmap("tab10")(3),
        alpha=0.82,
    )
    ax.set_yticks(positions, labels=ordered)
    ax.invert_yaxis()
    ax.set_xlabel("Scored run count")
    ax.set_title(f"Log-Derived Failure Distribution (all scored runs; n={len(rows)})")
    maximum = max(values, default=0)
    ax.set_xlim(0, max(1, maximum * 1.12))
    for position, value in zip(positions, values):
        offset = max(0.06, maximum * 0.015)
        ax.text(value + offset, position, str(value), va="center")
    return _save(fig, figure_dir / "failure_distribution.png", dpi)


def _quality_by_protocol(
    rows: list[dict[str, Any]], protocols: list[str]
) -> dict[str, list[float]]:
    grouped: dict[str, list[float]] = {protocol: [] for protocol in protocols}
    for row in rows:
        grouped[row["protocol"]].append(row["overall_quality_score"])
    return grouped


def _protocol_metric_means(
    rows: list[dict[str, Any]], protocols: list[str]
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for protocol in protocols:
        selected = [row for row in rows if row["protocol"] == protocol]
        token_values = [
            row["total_tokens"]
            for row in selected
            if row.get("total_tokens") is not None and row["total_tokens"] > 0
        ]
        runtime_values = [
            row["runtime_seconds"]
            for row in selected
            if row.get("runtime_seconds") is not None and row["runtime_seconds"] > 0
        ]
        summaries.append(
            {
                "protocol": protocol,
                "count": len(selected),
                "mean_quality": statistics.fmean(
                    row["overall_quality_score"] for row in selected
                ),
                "mean_tokens": statistics.fmean(token_values) if token_values else None,
                "mean_runtime": (
                    statistics.fmean(runtime_values) if runtime_values else None
                ),
            }
        )
    return summaries


def _log_bounds(
    values: list[float], *, expected: tuple[float, float]
) -> tuple[float, float]:
    lower = min(expected[0], min(values))
    upper = max(expected[1], max(values))
    if math.isclose(lower, upper):
        return lower / 10, upper * 10
    return lower, upper


def _log_normalize(value: float, bounds: tuple[float, float]) -> float:
    lower, upper = bounds
    return (math.log10(value) - math.log10(lower)) / (
        math.log10(upper) - math.log10(lower)
    )


def _format_tokens(value: float) -> str:
    return f"{value:,.0f}"


def _format_seconds(value: float) -> str:
    return f"{value:.1f}s"


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


def _resolve_results_dir(raw: str | Path) -> Path:
    path = Path(raw)
    candidates: list[Path] = []
    if path.is_absolute():
        candidates.append(path)
    else:
        candidates.extend(
            [
                PROJECT_ROOT / path,
                PROJECT_ROOT / "results" / path,
            ]
        )

    for candidate in candidates:
        if (candidate / "scores.csv").is_file():
            return candidate

    if path.is_absolute():
        return path
    return PROJECT_ROOT / "results" / path


if __name__ == "__main__":
    sys.exit(main())
