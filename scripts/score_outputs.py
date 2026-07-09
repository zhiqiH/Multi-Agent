from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import write_scores_csv  # noqa: E402
from src.deepseek_client import build_client  # noqa: E402
from src.io_utils import read_json, read_jsonl, write_jsonl  # noqa: E402
from src.scorer import score_run_log  # noqa: E402
from src.tasks import load_benchmark  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score benchmark run logs with a shared rubric.")
    parser.add_argument("--benchmark", default="benchmark/mini_benchmark.json")
    parser.add_argument("--model-config", default="configs/model_config.json")
    parser.add_argument("--logs-dir", default="logs/raw")
    parser.add_argument("--scores-jsonl", default="results/scores.jsonl")
    parser.add_argument("--scores-csv", default="results/scores.csv")
    parser.add_argument("--dry-run", action="store_true", help="Use mock evaluator, no API calls.")
    parser.add_argument("--overwrite", action="store_true", help="Rescore all logs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = read_json(PROJECT_ROOT / args.model_config)
    benchmark = load_benchmark(PROJECT_ROOT / args.benchmark)
    task_by_id = {task["task_id"]: task for task in benchmark["tasks"]}
    client = build_client(config, dry_run=args.dry_run)

    log_paths = sorted((PROJECT_ROOT / args.logs_dir).glob("*.json"))
    existing = [] if args.overwrite else read_jsonl(PROJECT_ROOT / args.scores_jsonl)
    existing_by_run = {score["run_id"]: score for score in existing}
    scores = [] if args.overwrite else existing[:]

    scored = 0
    skipped = 0
    for path in log_paths:
        run_log = read_json(path)
        run_id = run_log["run_id"]
        if run_id in existing_by_run and not args.overwrite:
            print(f"SKIP existing score {run_id}")
            skipped += 1
            continue
        task = task_by_id[run_log["task_id"]]
        score = score_run_log(run_log, task, client)
        scores.append(score)
        print(f"SCORED {run_id}: quality={score['overall_quality_score']}")
        scored += 1

    write_jsonl(PROJECT_ROOT / args.scores_jsonl, scores)
    write_scores_csv(PROJECT_ROOT / args.scores_csv, scores)
    print(f"Done. scored={scored}, skipped={skipped}, scores={PROJECT_ROOT / args.scores_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())