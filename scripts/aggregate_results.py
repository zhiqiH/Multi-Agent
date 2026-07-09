#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import (  # noqa: E402
    aggregate_by_protocol,
    write_aggregate_csv,
    write_aggregate_json,
    write_summary_markdown,
)
from src.io_utils import read_jsonl  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate scored benchmark results by protocol.")
    parser.add_argument("--scores-jsonl", default="results/scores.jsonl")
    parser.add_argument("--aggregate-csv", default="results/aggregate_results.csv")
    parser.add_argument("--aggregate-json", default="results/aggregate_results.json")
    parser.add_argument("--summary-md", default="results/experiment_summary.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scores = read_jsonl(PROJECT_ROOT / args.scores_jsonl)
    if not scores:
        raise SystemExit(f"No scores found: {PROJECT_ROOT / args.scores_jsonl}")
    rows = aggregate_by_protocol(scores)
    write_aggregate_csv(PROJECT_ROOT / args.aggregate_csv, rows)
    write_aggregate_json(PROJECT_ROOT / args.aggregate_json, rows)
    write_summary_markdown(PROJECT_ROOT / args.summary_md, rows, scores)
    print(f"Wrote aggregate results: {PROJECT_ROOT / args.aggregate_csv}")
    print(f"Wrote summary: {PROJECT_ROOT / args.summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

