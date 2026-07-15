#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.tasks import BENCHMARK_CATEGORIES, benchmark_sha256, load_benchmark  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate benchmark schema, IDs, categories, and manifest counts.")
    parser.add_argument("--benchmark", default="benchmark/benchmark-full.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = Path(args.benchmark)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    benchmark = load_benchmark(path)
    tasks = benchmark["tasks"]
    categories = Counter(str(task["category"]) for task in tasks)
    difficulties = Counter(str(task["difficulty"]) for task in tasks)
    tools = Counter(str(task["tool_requirement"]) for task in tasks)

    expected_count = benchmark.get("expected_task_count")
    if expected_count is None:
        raise SystemExit("Benchmark manifest must define expected_task_count")
    if len(tasks) != int(expected_count):
        raise SystemExit(f"Expected {expected_count} tasks, found {len(tasks)}")
    expected_per_category = benchmark.get("expected_tasks_per_category")
    expected_categories = tuple(benchmark.get("expected_categories") or ())
    if expected_categories != BENCHMARK_CATEGORIES:
        raise SystemExit(
            "Benchmark manifest expected_categories must exactly match the six project categories"
        )
    if not expected_per_category:
        raise SystemExit("Benchmark manifest must define expected_tasks_per_category")
    wrong = {
        category: categories.get(category, 0)
        for category in expected_categories
        if categories.get(category, 0) != int(expected_per_category)
    }
    if wrong:
        raise SystemExit(f"Unexpected tasks per category: {wrong}")
    difficulty_sets = {
        category: {
            str(task["difficulty"])
            for task in tasks
            if task["category"] == category
        }
        for category in expected_categories
    }
    incomplete_mix = {
        category: sorted({"Easy", "Medium", "Hard"} - observed)
        for category, observed in difficulty_sets.items()
        if observed != {"Easy", "Medium", "Hard"}
    }
    if incomplete_mix:
        raise SystemExit(
            "Every category must contain Easy, Medium, and Hard tasks; "
            f"missing difficulties: {incomplete_mix}"
        )

    print(f"VALID benchmark={path}")
    print(f"benchmark_sha256={benchmark_sha256(path)}")
    print(f"tasks={len(tasks)}")
    print("categories=" + ", ".join(f"{key}:{categories[key]}" for key in sorted(categories)))
    print("difficulties=" + ", ".join(f"{key}:{difficulties[key]}" for key in sorted(difficulties)))
    print("tool_requirements=" + ", ".join(f"{key}:{tools[key]}" for key in sorted(tools)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
