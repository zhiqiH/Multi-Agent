#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import write_scores_csv  # noqa: E402
from src.io_utils import read_json, read_jsonl, slug_list, write_jsonl  # noqa: E402
from src.llm_client import build_client  # noqa: E402
from src.prompts import PROMPT_SCHEMA_VERSION  # noqa: E402
from src.protocols import build_condition_id  # noqa: E402
from src.scorer import build_score_id, score_run_log  # noqa: E402
from src.tasks import DEFAULT_JUDGE_FIELDS, benchmark_sha256, load_benchmark, project_task  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score agent-system run logs with an independent Judge model.")
    parser.add_argument("--benchmark", default="benchmark/benchmark-full.json")
    parser.add_argument("--model-config", default="configs/model_config.json")
    parser.add_argument("--experiment-config", default="configs/experiment_config.json")
    parser.add_argument("--logs-dir", default="logs/raw")
    parser.add_argument("--scores-jsonl", default="results/scores.jsonl")
    parser.add_argument("--scores-csv", default="results/scores.csv")
    parser.add_argument("--errors-jsonl", default="results/scoring_errors.jsonl")
    parser.add_argument(
        "--judge-profiles",
        "--judge-profile",
        dest="judge_profiles",
        default="",
        help="Comma-separated Judge profiles. Empty uses defaults.judge; 'all' uses every profile.",
    )
    parser.add_argument("--model", default="", help="Temporarily override one Judge profile's model ID.")
    parser.add_argument("--judge-visible-fields", default="")
    parser.add_argument(
        "--agent-profiles",
        dest="agent_profiles",
        default="",
        help="Only score these agent profiles.",
    )
    parser.add_argument("--tasks", default="", help="Only score these task IDs.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true", help="Rescore exact Judge/run conditions.")
    parser.add_argument("--allow-benchmark-mismatch", action="store_true")
    parser.add_argument(
        "--include-open-book",
        action="store_true",
        help="Score intentional open-book ablation logs.",
    )
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--list-models", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    model_config = read_json(_project_path(args.model_config))
    if args.list_models:
        _print_model_profiles(model_config)
        return 0

    experiment_config = read_json(_project_path(args.experiment_config))
    benchmark_path = _project_path(args.benchmark)
    benchmark = load_benchmark(benchmark_path)
    benchmark_hash = benchmark_sha256(benchmark_path)
    task_by_id = {task["task_id"]: task for task in benchmark["tasks"]}

    visibility = experiment_config.get("task_visibility", {})
    judge_fields = tuple(
        slug_list(args.judge_visible_fields)
        or visibility.get("judge_fields")
        or DEFAULT_JUDGE_FIELDS
    )
    judge_tasks = {task_id: project_task(task, judge_fields) for task_id, task in task_by_id.items()}
    profile_names = _selected_profiles(model_config, args.judge_profiles, role="judge")
    if args.model and len(profile_names) > 1:
        raise SystemExit("--model can only be used with one Judge profile.")

    log_paths = sorted(_project_path(args.logs_dir).rglob("*.json"))
    if not log_paths:
        raise SystemExit(f"No run logs found: {_project_path(args.logs_dir)}")

    wanted_agents = set(slug_list(args.agent_profiles))
    wanted_tasks = set(slug_list(args.tasks))
    scores_path = _project_path(args.scores_jsonl)
    scores = read_jsonl(scores_path)
    score_ids = {score.get("score_id") for score in scores if score.get("score_id")}
    scoring_errors: list[dict[str, Any]] = []

    print(f"Benchmark: {benchmark_path}")
    print(f"Judge-visible fields: {', '.join(judge_fields)}")

    scored = 0
    skipped = 0
    skipped_open_book = 0
    skipped_mismatch = 0
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
            "schema_version": "3.0",
            "benchmark_sha256": benchmark_hash,
            "judge_provider": client.provider,
            "judge_profile": client.profile,
            "judge_model": client.model,
            "judge_effective_config": effective_config,
            "judge_visible_fields": list(judge_fields),
            "prompt_schema_version": PROMPT_SCHEMA_VERSION,
            "scoring_formula_version": "quality-0.35-0.30-0.20-0.15-v1",
        }
        judge_condition_id = build_condition_id(judge_condition)
        print(
            f"Judge model: provider={client.provider} profile={client.profile} model={client.model} "
            f"judge_condition={judge_condition_id} dry_run={args.dry_run}"
        )

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
            agent_profile = run_log.get("agent_profile")
            if not agent_profile:
                print(f"SKIP malformed log {path}: missing agent_profile", file=sys.stderr)
                malformed += 1
                continue
            if wanted_agents and agent_profile not in wanted_agents:
                continue
            if wanted_tasks and task_id not in wanted_tasks:
                continue
            if task_id not in judge_tasks:
                print(f"SKIP {run_id}: task is not in {benchmark_path.name}", file=sys.stderr)
                skipped_mismatch += 1
                continue

            logged_hash = run_log.get("benchmark_sha256")
            if logged_hash != benchmark_hash and not args.allow_benchmark_mismatch:
                print(f"SKIP {run_id}: benchmark hash mismatch", file=sys.stderr)
                skipped_mismatch += 1
                continue

            evaluation_mode = run_log.get("evaluation_mode")
            if evaluation_mode not in {"blind", "open_book"}:
                print(f"SKIP malformed log {path}: invalid evaluation_mode", file=sys.stderr)
                malformed += 1
                continue
            if evaluation_mode == "open_book" and not args.include_open_book:
                print(f"SKIP {run_id}: open_book (add --include-open-book)", file=sys.stderr)
                skipped_open_book += 1
                continue

            score_id = build_score_id(run_id, client, judge_condition_id)
            if score_id in score_ids and not args.overwrite:
                print(f"SKIP existing exact score {score_id}")
                skipped += 1
                continue
            try:
                score = score_run_log(
                    run_log,
                    judge_tasks[task_id],
                    client,
                    judge_condition_id=judge_condition_id,
                )
            except Exception as exc:  # noqa: BLE001 - retain other completed scores.
                error = {
                    "record_type": "scoring_error",
                    "run_id": run_id,
                    "judge_condition_id": judge_condition_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
                scoring_errors.append(error)
                print(f"ERROR scoring {score_id}: {exc}", file=sys.stderr)
                if args.fail_fast:
                    raise
                continue

            if score_id in score_ids:
                scores = [existing for existing in scores if existing.get("score_id") != score_id]
                score_ids.discard(score_id)
            score.update(
                {
                    "evaluation_mode": evaluation_mode,
                    "benchmark_sha256": benchmark_hash,
                    "judge_condition": judge_condition,
                    "run_validity_warnings": run_log.get("validity_warnings") or [],
                }
            )
            scores.append(score)
            score_ids.add(score_id)
            print(f"SCORED {score_id}: quality={score['overall_quality_score']}")
            scored += 1

    write_jsonl(scores_path, scores)
    write_scores_csv(_project_path(args.scores_csv), scores)
    write_jsonl(_project_path(args.errors_jsonl), scoring_errors)
    print(
        "Done. "
        f"scored={scored}, skipped={skipped}, open_book_skipped={skipped_open_book}, "
        f"benchmark_mismatch_skipped={skipped_mismatch}, "
        f"malformed={malformed}, errors={len(scoring_errors)}, scores={_project_path(args.scores_csv)}"
    )
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
        print(
            f"{name}: provider={profile.get('provider', 'unknown')} model={profile.get('model', 'unknown')} "
            f"roles={','.join(profile.get('supported_roles') or []) or 'unspecified'}{label}"
        )


def _project_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_ROOT / path


if __name__ == "__main__":
    raise SystemExit(main())
