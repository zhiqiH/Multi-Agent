from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.io_utils import read_json, slug_list, write_json
from src.llm_client import build_client
from src.protocols import DEFAULT_PROTOCOLS, PROTOCOLS, build_run_id, resolve_protocols, run_protocol
from src.tasks import (
    DEFAULT_CANDIDATE_FIELDS,
    KNOWN_TASK_FIELDS,
    PROTECTED_FIELDS,
    load_benchmark,
    project_task,
    select_tasks,
)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run multi-agent communication protocol experiments.")
    parser.add_argument("--benchmark", default="benchmark/mini_benchmark.json")
    parser.add_argument("--model-config", default="configs/model_config.json")
    parser.add_argument("--experiment-config", default="configs/experiment_config.json")
    parser.add_argument("--out-dir", default="logs/raw")
    parser.add_argument("--protocols", default=",".join(DEFAULT_PROTOCOLS))
    parser.add_argument("--tasks", default="", help="Comma-separated task IDs. Empty means all tasks.")
    parser.add_argument("--candidate-profiles","--candidate-profile",dest="candidate_profiles",default="",help="Comma-separated model profile names. Empty uses defaults.candidate; 'all' uses every profile.",)
    parser.add_argument("--model", default="", help="Temporarily override the selected profile's model ID.")
    parser.add_argument("--agent-visible-fields",default="",help="Comma-separated candidate-visible benchmark fields; overrides experiment_config.json.",)
    parser.add_argument("--allow-protected-agent-fields",action="store_true",help="Explicitly allow grading fields in the candidate view. This invalidates blind evaluation.",)
    parser.add_argument("--run-number", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true", help="Use deterministic mock model, no API calls.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing run logs.")
    parser.add_argument("--strict-tool-requirements", action="store_true")
    parser.add_argument("--print-agent-view", action="store_true", help="Print exactly what candidates see, then exit.")
    parser.add_argument("--list-protocols", action="store_true")
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--list-task-fields", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_protocols:
        for protocol_id, meta in PROTOCOLS.items():
            print(f"{protocol_id}: {meta['name']} - {meta['description']}")
        return 0

    model_config = read_json(_project_path(args.model_config))
    if args.list_models:
        _print_model_profiles(model_config)
        return 0

    experiment_config = read_json(_project_path(args.experiment_config))
    benchmark_path = _project_path(args.benchmark)
    benchmark = load_benchmark(benchmark_path)

    if args.list_task_fields:
        present = set().union(*(set(task) for task in benchmark["tasks"]))
        for field in sorted(KNOWN_TASK_FIELDS):
            suffix = " [protected grading data]" if field in PROTECTED_FIELDS else ""
            availability = "" if field in present else " [not present]"
            print(f"{field}{suffix}{availability}")
        return 0

    raw_tasks = select_tasks(benchmark, slug_list(args.tasks))
    visibility = experiment_config.get("task_visibility", {})
    candidate_fields = tuple(
        slug_list(args.agent_visible_fields)
        or visibility.get("candidate_fields")
        or DEFAULT_CANDIDATE_FIELDS
    )
    protected_requested = sorted(set(candidate_fields) & PROTECTED_FIELDS)
    protected_allowed = bool(
        args.allow_protected_agent_fields
        or visibility.get("allow_protected_fields_for_candidates", False)
    )
    if protected_requested and not protected_allowed:
        raise SystemExit(
            "Refusing to expose protected grading fields to candidates: "
            f"{', '.join(protected_requested)}. Remove them or add --allow-protected-agent-fields."
        )
    if protected_requested:
        print(
            "WARNING: blind evaluation is disabled because candidates can see protected fields: "
            + ", ".join(protected_requested),
            file=sys.stderr,
        )

    candidate_tasks = [(raw, project_task(raw, candidate_fields)) for raw in raw_tasks]
    if args.print_agent_view:
        payload = {
            "candidate_visible_fields": list(candidate_fields),
            "tasks": [candidate for _, candidate in candidate_tasks],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    protocols = resolve_protocols(slug_list(args.protocols))
    profile_names = _selected_profiles(model_config, args.candidate_profiles)
    if args.model and len(profile_names) > 1:
        raise SystemExit("--model can only be used with one candidate profile.")

    benchmark_sha256 = _sha256_file(benchmark_path)
    out_dir = _project_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    store_prompts = bool(visibility.get("store_candidate_prompts", True))

    print(f"Benchmark: {benchmark_path}")
    print(f"Tasks: {', '.join(task['task_id'] for task in raw_tasks)}")
    print(f"Protocols: {', '.join(protocols)}")
    print(f"Candidate-visible fields: {', '.join(candidate_fields)}")

    completed = 0
    skipped = 0
    warnings_seen = 0
    for requested_profile in profile_names:
        client = build_client(
            model_config,
            dry_run=args.dry_run,
            role="candidate",
            profile=requested_profile,
            model=args.model or None,
            secrets_path=PROJECT_ROOT / ".secrets" / "model_keys.json",
        )
        effective_config = dict(getattr(client, "effective_config", {}) or {})
        print(
            f"Candidate model: provider={client.provider} profile={client.profile} "
            f"model={client.model} dry_run={args.dry_run}"
        )

        for raw_task, candidate_task in candidate_tasks:
            task_warnings = _task_validity_warnings(raw_task, experiment_config)
            if task_warnings and args.strict_tool_requirements:
                raise SystemExit(f"{raw_task['task_id']}: {task_warnings[0]}")
            for warning in task_warnings:
                print(f"WARNING {raw_task['task_id']}: {warning}", file=sys.stderr)
                warnings_seen += 1

            metadata = {
                field: raw_task.get(field)
                for field in ("task_id", "category", "difficulty", "tool_requirement")
            }
            for protocol_id in protocols:
                run_id = build_run_id(
                    raw_task["task_id"],
                    protocol_id,
                    client.profile,
                    client.model,
                    args.run_number,
                )
                out_path = out_dir / f"{run_id}.json"
                if out_path.exists() and not args.overwrite:
                    print(f"SKIP existing {run_id}")
                    skipped += 1
                    continue

                log = run_protocol(
                    protocol_id,
                    candidate_task,
                    client,
                    effective_config,
                    task_metadata=metadata,
                    run_id=run_id,
                    run_number=args.run_number,
                    candidate_visible_fields=list(candidate_fields),
                    validity_warnings=task_warnings,
                )
                log["benchmark_file"] = _display_path(benchmark_path)
                log["benchmark_sha256"] = benchmark_sha256
                log["experiment_config_file"] = _display_path(_project_path(args.experiment_config))
                log["protected_fields_exposed"] = protected_requested
                if not store_prompts:
                    log.pop("prompts", None)
                write_json(out_path, log)
                status = "ERROR" if log["errors"] else "OK"
                print(
                    f"{status} {run_id}: tokens={log['total_tokens']} "
                    f"messages={log['message_count']} runtime={log['runtime_seconds']}s"
                )
                completed += 1

    print(
        f"Done. completed={completed}, skipped={skipped}, "
        f"validity_warnings={warnings_seen}, raw_logs={out_dir}"
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
    profiles = config.get("profiles", {})
    if not profiles:
        print("No model profiles configured.")
        return
    for name, profile in profiles.items():
        roles = [role for role, default_name in defaults.items() if default_name == name]
        default_label = f" defaults={','.join(roles)}" if roles else ""
        print(
            f"{name}: provider={profile.get('provider', 'unknown')} "
            f"model={profile.get('model', 'unknown')} key_env={profile.get('api_key_env', '-')}{default_label}"
        )


def _task_validity_warnings(task: dict[str, Any], experiment_config: dict[str, Any]) -> list[str]:
    requirement = str(task.get("tool_requirement", "")).strip().lower()
    tool_policy = experiment_config.get("tool_policy", {})
    implemented_tools = tool_policy.get("implemented_tools") or []
    should_warn = tool_policy.get("warn_when_required_tools_are_unavailable", True)
    if requirement == "required" and not implemented_tools and should_warn:
        return [
            "This task requires external tools, but the current runner has no tool execution layer. "
            "The run is recorded with tool_access_used=false and is not a controlled valid result for this task."
        ]
    return []


def _project_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())