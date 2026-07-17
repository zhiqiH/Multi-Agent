#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import (  # noqa: E402
    GROUP_BY_CHOICES,
    aggregate_scores,
    write_aggregate_csv,
    write_aggregate_json,
    write_scores_csv,
    write_summary_markdown,
)
from src.io_utils import read_json, read_jsonl, slug_list, write_jsonl  # noqa: E402
from src.llm_client import build_client  # noqa: E402
from src.scorer import build_result_run_id, build_score_id, score_run_log  # noqa: E402
from src.tasks import load_benchmark, project_task  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score agent-system logs and immediately aggregate all score results."
    )
    parser.add_argument("--benchmark", default="benchmark/benchmark-D.json")
    parser.add_argument("--model-config", default="configs/model_config.json")
    parser.add_argument("--logs-dir", default="logs/raw/current")
    parser.add_argument("--scores-jsonl", default="results/scores.jsonl")
    parser.add_argument("--scores-csv", default="results/scores.csv")
    parser.add_argument("--errors-jsonl", default="results/scoring_errors.jsonl")
    parser.add_argument("--aggregate-csv", default="results/aggregate_results.csv")
    parser.add_argument("--aggregate-json", default="results/aggregate_results.json")
    parser.add_argument("--summary-md", default="results/summary.md")
    parser.add_argument(
        "--group-by",
        choices=GROUP_BY_CHOICES,
        default="condition",
        help="Aggregate by Agent/Judge/protocol condition or by protocol only.",
    )
    parser.add_argument(
        "--judge-profiles",
        "--judge-profile",
        dest="judge_profiles",
        default="",
        help="Comma-separated Judge profiles. Empty uses defaults.judge; 'all' uses every profile.",
    )
    parser.add_argument("--model", default="", help="Temporarily override one Judge profile's model ID.")
    parser.add_argument(
        "--agent-models",
        dest="agent_models",
        default="",
        help="Only score logs produced by these Agent model IDs.",
    )
    parser.add_argument("--tasks", default="", help="Only score these task IDs.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true", help="Rescore exact Judge/run conditions.")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--list-models", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    model_config = read_json(_project_path(args.model_config))
    if args.list_models:
        _print_model_profiles(model_config)
        return 0

    benchmark_path = _project_path(args.benchmark)
    benchmark = load_benchmark(benchmark_path)
    task_by_id = {task["task_id"]: task for task in benchmark["tasks"]}
    judge_fields = tuple(dict.fromkeys(field for task in task_by_id.values() for field in task))
    judge_tasks = {task_id: project_task(task, tuple(task)) for task_id, task in task_by_id.items()}

    profile_names = _selected_profiles(model_config, args.judge_profiles, role="judge")
    if args.model and len(profile_names) > 1:
        raise SystemExit("--model can only be used with one Judge profile.")

    logs_dir = _project_path(args.logs_dir)
    log_paths = sorted(logs_dir.glob("*.json"))
    if not log_paths:
        raise SystemExit(f"No run logs found directly in: {logs_dir}")

    wanted_agents = set(slug_list(args.agent_models))
    wanted_tasks = set(slug_list(args.tasks))
    scores_path = _project_path(args.scores_jsonl)
    scores = read_jsonl(scores_path)
    scores_by_id = {score["score_id"]: score for score in scores if score.get("score_id")}
    scoring_errors: list[dict[str, Any]] = []

    print(f"Benchmark: {benchmark_path}")
    print(f"Logs: {logs_dir} (current directory only)")
    print(f"Judge-visible fields: {', '.join(judge_fields)}")

    scored = 0
    skipped = 0
    skipped_unknown_task = 0
    malformed = 0
    for requested_profile in profile_names:
        client = build_client(
            model_config,
            dry_run=args.dry_run,
            role="judge",
            profile=requested_profile,
            model=args.model or None,
            secrets_path=PROJECT_ROOT / ".secrets" / "model_keys.json",
        )
        effective_config = dict(getattr(client, "effective_config", {}) or {})
        judge_condition = {
            "judge_provider": client.provider,
            "judge_profile": client.profile,
            "judge_model": client.model,
            "judge_effective_config": effective_config,
            "judge_visible_fields": list(judge_fields),
        }
        print(f"Judge model: {client.model} dry_run={args.dry_run}")

        for path in log_paths:
            run_log = read_json(path)
            if run_log.get("record_type") != "agent_run":
                continue
            run_id = run_log.get("run_id")
            task_id = run_log.get("task_id")
            if not run_id or not task_id:
                print(f"SKIP malformed log {path}", file=sys.stderr)
                malformed += 1
                continue
            agent_model = run_log.get("agent_model")
            if not agent_model:
                print(f"SKIP malformed log {path}: missing agent_model", file=sys.stderr)
                malformed += 1
                continue
            if wanted_agents and agent_model not in wanted_agents:
                continue
            if wanted_tasks and task_id not in wanted_tasks:
                continue
            if task_id not in judge_tasks:
                print(f"SKIP {run_id}: task is not in {benchmark_path.name}", file=sys.stderr)
                skipped_unknown_task += 1
                continue

            score_id = build_score_id(run_log, client)
            existing_score = scores_by_id.get(score_id)
            if existing_score is not None:
                if existing_score.get("judge_condition") != judge_condition and not args.overwrite:
                    raise SystemExit(
                        f"Existing score {score_id} used a different Judge field/configuration set. "
                        "Run again with --overwrite to replace it using all current benchmark fields."
                    )
                if not args.overwrite:
                    print(
                        f"SKIP existing task={task_id} protocol={run_log['protocol_id']} "
                        f"agent={agent_model} judge={client.model}"
                    )
                    skipped += 1
                    continue

            try:
                score = score_run_log(run_log, judge_tasks[task_id], client)
            except Exception as exc:  # noqa: BLE001 - keep other completed scores.
                error = {
                    "record_type": "scoring_error",
                    "run_id": build_result_run_id(run_log),
                    "judge_model": client.model,
                    "judge_condition": judge_condition,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
                scoring_errors.append(error)
                print(
                    f"ERROR task={task_id} protocol={run_log['protocol_id']} "
                    f"agent={agent_model} judge={client.model}: {exc}",
                    file=sys.stderr,
                )
                if args.fail_fast:
                    raise
                continue

            if existing_score is not None:
                scores = [existing for existing in scores if existing.get("score_id") != score_id]
            score.update(
                {
                    "benchmark_id": benchmark.get("benchmark_id", benchmark_path.stem),
                    "benchmark_file": _display_path(benchmark_path),
                    "judge_condition": judge_condition,
                    "run_validity_warnings": run_log.get("validity_warnings") or [],
                }
            )
            scores.append(score)
            scores_by_id[score_id] = score
            print(
                f"SCORED task={task_id} protocol={run_log['protocol_id']} "
                f"agent={agent_model} judge={client.model} quality={score['overall_quality_score']}"
            )
            scored += 1

    write_jsonl(scores_path, scores)
    scores_csv_path = _project_path(args.scores_csv)
    errors_path = _project_path(args.errors_jsonl)
    write_scores_csv(scores_csv_path, scores)
    write_jsonl(errors_path, scoring_errors)

    aggregate_csv_path = _project_path(args.aggregate_csv)
    aggregate_json_path = _project_path(args.aggregate_json)
    summary_path = _project_path(args.summary_md)
    aggregate_rows = aggregate_scores(scores, group_by=args.group_by)
    write_aggregate_csv(aggregate_csv_path, aggregate_rows)
    write_aggregate_json(aggregate_json_path, aggregate_rows)
    write_summary_markdown(summary_path, aggregate_rows, scores, group_by=args.group_by)

    print(
        "Done. "
        f"scored={scored}, skipped={skipped}, "
        f"unknown_task_skipped={skipped_unknown_task}, "
        f"malformed={malformed}, errors={len(scoring_errors)}"
    )
    print(f"Scores: {scores_csv_path}")
    print(f"Aggregate: {aggregate_csv_path}")
    print(f"Summary: {summary_path}")
    return 0 if not scoring_errors else 2


def _selected_profiles(config: dict[str, Any], raw: str, *, role: str) -> list[str | None]:
    selected = slug_list(raw)
    if not selected:
        return [None]
    if selected == ["all"]:
        profiles = [
            name
            for name, profile in config.get("profiles", {}).items()
            if not profile.get("supported_roles") or role in profile["supported_roles"]
        ]
        if not profiles:
            raise SystemExit(f"No model profiles support the {role} role.")
        return profiles
    return selected


def _print_model_profiles(config: dict[str, Any]) -> None:
    defaults = config.get("defaults", {})
    for name, profile in config.get("profiles", {}).items():
        roles = [role for role in ("agent", "judge") if defaults.get(role) == name]
        label = f" defaults={','.join(roles)}" if roles else ""
        print(f"{name}: model={profile.get('model', 'unknown')}{label}")


def _project_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
