#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.deepseek_client import build_client  # noqa: E402
from src.io_utils import read_json, slug_list, write_json  # noqa: E402
from src.protocols import DEFAULT_PROTOCOLS, PROTOCOLS, resolve_protocols, run_protocol  # noqa: E402
from src.tasks import load_benchmark, select_tasks  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run multi-agent communication protocol experiments.")
    parser.add_argument("--benchmark", default="benchmark/mini_benchmark.json")
    parser.add_argument("--model-config", default="configs/model_config.json")
    parser.add_argument("--out-dir", default="logs/raw")
    parser.add_argument("--protocols", default=",".join(DEFAULT_PROTOCOLS))
    parser.add_argument("--tasks", default="", help="Comma-separated task IDs. Empty means all tasks.")
    parser.add_argument("--run-number", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true", help="Use deterministic mock model, no API calls.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing run logs.")
    parser.add_argument("--list-protocols", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_protocols:
        for protocol_id, meta in PROTOCOLS.items():
            print(f"{protocol_id}: {meta['name']} - {meta['description']}")
        return 0

    benchmark_path = PROJECT_ROOT / args.benchmark
    config = read_json(PROJECT_ROOT / args.model_config)
    benchmark = load_benchmark(benchmark_path)
    tasks = select_tasks(benchmark, slug_list(args.tasks))
    protocols = resolve_protocols(slug_list(args.protocols))
    client = build_client(config, dry_run=args.dry_run)
    out_dir = PROJECT_ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Benchmark: {benchmark_path}")
    print(f"Tasks: {', '.join(task['task_id'] for task in tasks)}")
    print(f"Protocols: {', '.join(protocols)}")
    print(f"Model: {getattr(client, 'model', 'unknown')} | dry_run={args.dry_run}")

    completed = 0
    skipped = 0
    for task in tasks:
        for protocol_id in protocols:
            run_id = f"{task['task_id']}__{protocol_id}__run{args.run_number:02d}"
            out_path = out_dir / f"{run_id}.json"
            if out_path.exists() and not args.overwrite:
                print(f"SKIP existing {run_id}")
                skipped += 1
                continue
            log = run_protocol(protocol_id, task, client, config, run_number=args.run_number)
            write_json(out_path, log)
            status = "ERROR" if log["errors"] else "OK"
            print(
                f"{status} {run_id}: tokens={log['total_tokens']} "
                f"messages={log['message_count']} runtime={log['runtime_seconds']}s"
            )
            completed += 1

    print(f"Done. completed={completed}, skipped={skipped}, raw_logs={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())