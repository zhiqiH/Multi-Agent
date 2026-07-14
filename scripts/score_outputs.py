#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import write_scores_csv
from src.io_utils import read_json, read_jsonl, slug_list, write_jsonl
from src.llm_client import build_client
from src.scorer import build_score_id, score_run_log
from src.tasks import DEFAULT_JUDGE_FIELDS, load_benchmark, project_task

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score benchmark run logs with an independent Judge model.")
    parser.add_argument("--benchmark", default="benchmark/mini_benchmark.json")
    parser.add_argument("--model-config", default="configs/model_config.json")
    parser.add_argument("--experiment-config", default="configs/experiment_config.json")
    parser.add_argument("--logs-dir", default="logs/raw")
    parser.add_argument("--scores-jsonl", default="results/scores.jsonl")
    parser.add_argument("--scores-csv", default="results/scores.csv")
    parser.add_argument("--judge-profiles","--judge-profile",dest="judge_profiles",default="",help="Comma-separated Judge profiles. Empty uses defaults.judge; 'all' uses every profile.",)
    parser.add_argument("--model", default="", help="Temporarily override one Judge profile's model ID.")
    parser.add_argument("--judge-visible-fields",default="",help="Comma-separated Judge fields; overrides experiment_config.json.",)
    parser.add_argument("--candidate-profiles", default="", help="Only score these candidate profiles.")
    parser.add_argument("--tasks", default="", help="Only score these task IDs.")
    parser.add_argument("--dry-run", action="store_true", help="Use mock evaluator, no API calls.")
    parser.add_argument("--overwrite",action="store_true",help="Rescore matching Judge/run pairs while preserving scores from other Judges.",)
    parser.add_argument("--allow-benchmark-mismatch", action="store_true")
    parser.add_argument("--include-compromised-logs",action="store_true",help="Score legacy/protected-field-exposed candidate logs. Not recommended for blind experiments.",)
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
    benchmark_sha256 = _sha256_file(benchmark_path)
    task_by_id = {task["task_id"]: task for task in benchmark["tasks"]}

    visibility = experiment_config.get("task_visibility", {})
    judge_fields = tuple(
        slug_list(args.judge_visible_fields)
        or visibility.get("judge_fields")
        or DEFAULT_JUDGE_FIELDS
    )
    judge_tasks = {task_id: project_task(task, judge_fields) for task_id, task in task_by_id.items()}

    profile_names = _selected_profiles(model_config, args.judge_profiles)
    if args.model and len(profile_names) > 1:
        raise SystemExit("--model can only be used with one Judge profile.")

    log_paths = sorted(_project_path(args.logs_dir).rglob("*.json"))
    if not log_paths:
        raise SystemExit(f"No run logs found: {_project_path(args.logs_dir)}")

    wanted_candidates = set(slug_list(args.candidate_profiles))
    wanted_tasks = set(slug_list(args.tasks))
    scores_path = _project_path(args.scores_jsonl)
    scores = read_jsonl(scores_path)
    score_ids = {score.get("score_id") for score in scores if score.get("score_id")}

    print(f"Benchmark: {benchmark_path}")
    print(f"Judge-visible fields: {', '.join(judge_fields)}")

    scored = 0
    skipped = 0
    skipped_compromised = 0
    skipped_mismatch = 0
    for requested_profile in profile_names:
        client = build_client(
            model_config,
            dry_run=args.dry_run,
            role="judge",
            profile=requested_profile,
            model=args.model or None,
            secrets_path=PROJECT_ROOT / ".secrets" / "model_keys.json",
        )
        print(
            f"Judge model: provider={client.provider} profile={client.profile} "
            f"model={client.model} dry_run={args.dry_run}"
        )

        for path in log_paths:
            run_log = read_json(path)
            run_id = run_log.get("run_id")
            task_id = run_log.get("task_id")
            if not run_id or not task_id:
                print(f"SKIP malformed log {path}", file=sys.stderr)
                skipped += 1
                continue
            if wanted_candidates and run_log.get("candidate_profile", "legacy") not in wanted_candidates:
                continue
            if wanted_tasks and task_id not in wanted_tasks:
                continue
            if task_id not in judge_tasks:
                print(f"SKIP {run_id}: task is not in {benchmark_path.name}", file=sys.stderr)
                skipped_mismatch += 1
                continue

            logged_benchmark_hash = run_log.get("benchmark_sha256")
            if (
                logged_benchmark_hash
                and logged_benchmark_hash != benchmark_sha256
                and not args.allow_benchmark_mismatch
            ):
                print(f"SKIP {run_id}: benchmark hash mismatch", file=sys.stderr)
                skipped_mismatch += 1
                continue

            visibility_status = _candidate_visibility_status(run_log)
            if visibility_status in {"legacy-contaminated", "protected-fields-exposed"}:
                if not args.include_compromised_logs:
                    print(f"SKIP {run_id}: {visibility_status}", file=sys.stderr)
                    skipped_compromised += 1
                    continue

            score_id = build_score_id(run_id, client)
            if score_id in score_ids and not args.overwrite:
                print(f"SKIP existing score {score_id}")
                skipped += 1
                continue
            if score_id in score_ids:
                scores = [score for score in scores if score.get("score_id") != score_id]
                score_ids.discard(score_id)

            score = score_run_log(run_log, judge_tasks[task_id], client)
            score["candidate_visibility_status"] = visibility_status
            score["benchmark_sha256"] = benchmark_sha256
            score["run_validity_warnings"] = run_log.get("validity_warnings") or []
            scores.append(score)
            score_ids.add(score_id)
            print(f"SCORED {score_id}: quality={score['overall_quality_score']}")
            scored += 1

    write_jsonl(scores_path, scores)
    write_scores_csv(_project_path(args.scores_csv), scores)
    print(
        f"Done. scored={scored}, skipped={skipped}, compromised_skipped={skipped_compromised}, "
        f"benchmark_mismatch_skipped={skipped_mismatch}, scores={_project_path(args.scores_csv)}"
    )
    return 0


def _selected_profiles(config: dict[str, Any], raw: str) -> list[str | None]:
    selected = slug_list(raw)
    if not selected:
        return [None]
    if selected == ["all"]:
        profiles = list(config.get("profiles", {}))
        if not profiles:
            raise SystemExit("No model profiles are configured.")
        return profiles
    return selected


def _print_model_profiles(config: dict[str, Any]) -> None:
    defaults = config.get("defaults", {})
    for name, profile in config.get("profiles", {}).items():
        roles = [role for role, default_name in defaults.items() if default_name == name]
        default_label = f" defaults={','.join(roles)}" if roles else ""
        print(
            f"{name}: provider={profile.get('provider', 'unknown')} "
            f"model={profile.get('model', 'unknown')} key_env={profile.get('api_key_env', '-')}{default_label}"
        )


def _candidate_visibility_status(run_log: dict[str, Any]) -> str:
    if run_log.get("protected_fields_exposed"):
        return "protected-fields-exposed"
    visible_fields = set(run_log.get("candidate_visible_fields") or [])
    protected = {
        "evaluation_criteria",
        "ground_truth",
        "expected_failure_risks",
        "scoring_rubric",
        "required_evidence",
    }
    if visible_fields & protected:
        return "protected-fields-exposed"
    if visible_fields:
        return "field-isolated"

    serialized_prompts = json.dumps(run_log.get("prompts") or [], ensure_ascii=False)
    if "Evaluation Criteria:" in serialized_prompts or "Required Evidence:" in serialized_prompts:
        return "legacy-contaminated"
    return "legacy-unverified"


def _project_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())