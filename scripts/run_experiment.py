#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.io_utils import read_json, slug_list, write_json  # noqa: E402
from src.llm_client import build_client  # noqa: E402
from src.protocols import (  # noqa: E402
    DEFAULT_PROTOCOLS,
    PROTOCOLS,
    PROTOCOL_SCHEMA_VERSION,
    build_condition_id,
    build_run_id,
    resolve_protocols,
    run_protocol,
)
from src.tasks import (  # noqa: E402
    DEFAULT_AGENT_FIELDS,
    KNOWN_TASK_FIELDS,
    PROTECTED_FIELDS,
    benchmark_sha256,
    load_benchmark,
    project_task,
    select_tasks,
)

TOOL_EXECUTION_LAYER_AVAILABLE = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run controlled single-agent and multi-agent protocol experiments.")
    parser.add_argument("--benchmark", default="benchmark/benchmark-full.json")
    parser.add_argument("--model-config", default="configs/model_config.json")
    parser.add_argument("--experiment-config", default="configs/experiment_config.json")
    parser.add_argument("--out-dir", default="logs/raw")
    parser.add_argument("--experiment-id", default="", help="Human-readable experiment label included in run IDs.")
    parser.add_argument("--protocols", default=",".join(DEFAULT_PROTOCOLS))
    parser.add_argument("--tasks", default="", help="Comma-separated task IDs. Empty means all tasks.")
    parser.add_argument(
        "--agent-profiles",
        "--agent-profile",
        dest="agent_profiles",
        default="",
        help="Comma-separated agent model profiles. Empty uses defaults.agent; 'all' uses every profile.",
    )
    parser.add_argument("--model", default="", help="Temporarily override one selected agent profile's model ID.")
    parser.add_argument(
        "--agent-visible-fields",
        dest="agent_visible_fields",
        default="",
        help="Comma-separated benchmark fields visible to agents.",
    )
    parser.add_argument(
        "--allow-protected-agent-fields",
        action="store_true",
        help="Allow private grading fields in an intentional open-book ablation.",
    )
    parser.add_argument("--role-mode", choices=("specialized", "generalist"), default="")
    parser.add_argument("--run-number", type=int, default=1, help="First replicate number.")
    parser.add_argument("--runs", type=int, default=0, help="Number of replicates; 0 uses experiment config.")
    parser.add_argument("--max-rounds", type=int, default=0, help="Override max rounds for all selected protocols.")
    parser.add_argument(
        "--max-interactions", type=int, default=0, help="Override max model interactions for all selected protocols."
    )
    parser.add_argument("--dry-run", action="store_true", help="Use deterministic local model output.")
    parser.add_argument("--overwrite", action="store_true", help="Replace exact matching run IDs only.")
    parser.add_argument("--strict-tool-requirements", action="store_true")
    parser.add_argument("--print-agent-view", action="store_true", help="Print exactly what agents see, then exit.")
    parser.add_argument("--list-protocols", action="store_true")
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--list-task-fields", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_protocols:
        for protocol_id, meta in PROTOCOLS.items():
            print(
                f"{protocol_id}: {meta['condition']} / {meta['name']} | "
                f"rounds={meta['default_max_rounds']} interactions={meta['default_max_interactions']}"
            )
        return 0

    model_config_path = _project_path(args.model_config)
    model_config = read_json(model_config_path)
    if args.list_models:
        _print_model_profiles(model_config)
        return 0

    experiment_config_path = _project_path(args.experiment_config)
    experiment_config = read_json(experiment_config_path)
    benchmark_path = _project_path(args.benchmark)
    benchmark = load_benchmark(benchmark_path)
    benchmark_hash = benchmark_sha256(benchmark_path)

    if args.list_task_fields:
        present = set().union(*(set(task) for task in benchmark["tasks"]))
        for field in sorted(KNOWN_TASK_FIELDS):
            suffix = " [protected grading data]" if field in PROTECTED_FIELDS else ""
            availability = "" if field in present else " [not present]"
            print(f"{field}{suffix}{availability}")
        return 0

    raw_tasks = select_tasks(benchmark, slug_list(args.tasks))
    visibility = experiment_config.get("task_visibility", {})
    agent_fields = tuple(
        slug_list(args.agent_visible_fields)
        or visibility.get("agent_fields")
        or DEFAULT_AGENT_FIELDS
    )
    protected_requested = sorted(set(agent_fields) & PROTECTED_FIELDS)
    protected_allowed = bool(
        args.allow_protected_agent_fields
        or visibility.get("allow_protected_fields_for_agents", False)
    )
    if protected_requested and not protected_allowed:
        raise SystemExit(
            "Refusing to expose protected grading fields to agents: "
            f"{', '.join(protected_requested)}. Remove them or add --allow-protected-agent-fields."
        )
    evaluation_mode = "open_book" if protected_requested else "blind"
    if protected_requested:
        print(
            "NOTICE: intentional open-book ablation; agents can see protected fields: "
            + ", ".join(protected_requested),
            file=sys.stderr,
        )

    agent_tasks = [(raw, project_task(raw, agent_fields)) for raw in raw_tasks]
    if args.print_agent_view:
        print(
            json.dumps(
                {
                    "evaluation_mode": evaluation_mode,
                    "agent_visible_fields": list(agent_fields),
                    "tasks": [agent_task for _, agent_task in agent_tasks],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    protocols = resolve_protocols(slug_list(args.protocols))
    profile_names = _selected_profiles(model_config, args.agent_profiles, role="agent")
    if args.model and len(profile_names) > 1:
        raise SystemExit("--model can only be used with one agent profile.")

    run_policy = experiment_config.get("run_policy", {})
    role_mode = args.role_mode or str(run_policy.get("role_mode") or "specialized")
    runs = args.runs or int(run_policy.get("runs_per_condition") or 1)
    if args.run_number <= 0 or runs <= 0:
        raise SystemExit("--run-number and --runs must be positive")
    experiment_id = args.experiment_id or str(run_policy.get("experiment_id") or "main")

    out_dir = _project_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    store_prompts = bool(visibility.get("store_agent_prompts", True))
    protocol_overrides = experiment_config.get("protocols", {})

    print(f"Benchmark: {benchmark_path}")
    print(f"Benchmark ID: {benchmark.get('benchmark_id', benchmark_path.stem)}")
    print(f"Tasks: {', '.join(task['task_id'] for task in raw_tasks)}")
    print(f"Protocols: {', '.join(protocols)}")
    print(f"Evaluation mode: {evaluation_mode}")
    print(f"Agent-visible fields: {', '.join(agent_fields)}")

    completed = 0
    skipped = 0
    warnings_seen = 0
    manifest_conditions: list[dict[str, Any]] = []
    for requested_profile in profile_names:
        client = build_client(
            model_config,
            dry_run=args.dry_run,
            role="agent",
            profile=requested_profile,
            model=args.model or None,
            secrets_path=PROJECT_ROOT / ".secrets" / "model_keys.json",
        )
        effective_config = dict(getattr(client, "effective_config", {}) or {})
        print(
            f"Agent model: provider={client.provider} profile={client.profile} "
            f"model={client.model} dry_run={args.dry_run}"
        )

        for protocol_id in protocols:
            protocol_config = _protocol_config(
                protocol_id,
                protocol_overrides,
                max_rounds=args.max_rounds,
                max_interactions=args.max_interactions,
            )
            condition = {
                "schema_version": "3.0",
                "benchmark_sha256": benchmark_hash,
                "protocol_id": protocol_id,
                "protocol_version": PROTOCOL_SCHEMA_VERSION,
                "protocol_config": protocol_config,
                "agent_provider": client.provider,
                "agent_profile": client.profile,
                "agent_model": client.model,
                "agent_effective_config": effective_config,
                "evaluation_mode": evaluation_mode,
                "agent_visible_fields": list(agent_fields),
                "role_mode": role_mode,
                "tool_policy": experiment_config.get("tool_policy", {}),
            }
            condition_id = build_condition_id(condition)
            manifest_conditions.append({"condition_id": condition_id, **condition})

            for raw_task, agent_task in agent_tasks:
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
                for run_number in range(args.run_number, args.run_number + runs):
                    run_id = build_run_id(
                        raw_task["task_id"],
                        protocol_id,
                        client.profile,
                        client.model,
                        run_number,
                        condition_id=condition_id,
                        experiment_id=experiment_id,
                    )
                    out_path = out_dir / f"{run_id}.json"
                    if out_path.exists() and not args.overwrite:
                        print(f"SKIP existing exact condition {run_id}")
                        skipped += 1
                        continue

                    log = run_protocol(
                        protocol_id,
                        agent_task,
                        client,
                        effective_config,
                        task_metadata=metadata,
                        run_id=run_id,
                        run_number=run_number,
                        agent_visible_fields=list(agent_fields),
                        validity_warnings=task_warnings,
                        protocol_config=protocol_config,
                        role_mode=role_mode,
                    )
                    log.update(
                        {
                            "experiment_id": experiment_id,
                            "condition_id": condition_id,
                            "condition": condition,
                            "evaluation_mode": evaluation_mode,
                            "protected_agent_fields": protected_requested,
                            "benchmark_id": benchmark.get("benchmark_id", benchmark_path.stem),
                            "benchmark_version": benchmark.get("benchmark_version", "unspecified"),
                            "benchmark_file": _display_path(benchmark_path),
                            "benchmark_sha256": benchmark_hash,
                            "experiment_config_file": _display_path(experiment_config_path),
                            "model_config_file": _display_path(model_config_path),
                        }
                    )
                    if not store_prompts:
                        log.pop("prompts", None)
                    write_json(out_path, log)
                    status = "ERROR" if log["errors"] else "OK"
                    print(
                        f"{status} {run_id}: tokens={log['total_tokens']} messages={log['message_count']} "
                        f"rounds={log['rounds_completed']} runtime={log['runtime_seconds']}s"
                    )
                    completed += 1

    manifest_conditions = _deduplicate_conditions(manifest_conditions)
    manifest_basis = {
        "experiment_id": experiment_id,
        "benchmark_sha256": benchmark_hash,
        "task_ids": [task["task_id"] for task in raw_tasks],
        "condition_ids": [condition["condition_id"] for condition in manifest_conditions],
        "first_run_number": args.run_number,
        "runs": runs,
    }
    manifest_id = build_condition_id(manifest_basis)
    manifest = {
        "record_type": "experiment_manifest",
        "schema_version": "3.0",
        "manifest_id": manifest_id,
        "experiment_id": experiment_id,
        "benchmark_file": _display_path(benchmark_path),
        "benchmark_sha256": benchmark_hash,
        "task_ids": manifest_basis["task_ids"],
        "first_run_number": args.run_number,
        "runs": runs,
        "evaluation_mode": evaluation_mode,
        "role_mode": role_mode,
        "conditions": manifest_conditions,
        "completed_runs": completed,
        "skipped_runs": skipped,
        "validity_warning_count": warnings_seen,
    }
    manifest_path = out_dir / f"{_safe_name(experiment_id)}__manifest__{manifest_id}.json"
    write_json(manifest_path, manifest)
    print(
        f"Done. completed={completed}, skipped={skipped}, validity_warnings={warnings_seen}, "
        f"manifest={manifest_path}, raw_logs={out_dir}"
    )
    return 0


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
        default_label = f" defaults={','.join(roles)}" if roles else ""
        print(
            f"{name}: provider={profile.get('provider', 'unknown')} model={profile.get('model', 'unknown')} "
            f"roles={','.join(profile.get('supported_roles') or []) or 'unspecified'} "
            f"key_env={profile.get('api_key_env', '-')}{default_label}"
        )


def _protocol_config(
    protocol_id: str,
    configured: Any,
    *,
    max_rounds: int,
    max_interactions: int,
) -> dict[str, Any]:
    definition = PROTOCOLS[protocol_id]
    result = {
        "max_rounds": definition["default_max_rounds"],
        "max_interactions": definition["default_max_interactions"],
        "max_total_tokens": 0,
    }
    if isinstance(configured, dict) and isinstance(configured.get(protocol_id), dict):
        result.update(configured[protocol_id])
    if max_rounds:
        result["max_rounds"] = max_rounds
    if max_interactions:
        result["max_interactions"] = max_interactions
    return result


def _task_validity_warnings(task: dict[str, Any], experiment_config: dict[str, Any]) -> list[str]:
    requirement = str(task.get("tool_requirement", "")).strip().lower()
    tool_policy = experiment_config.get("tool_policy", {})
    should_warn = tool_policy.get("warn_when_required_tools_are_unavailable", True)
    if requirement == "required" and not TOOL_EXECUTION_LAYER_AVAILABLE and should_warn:
        return [
            "This task requires external tools, but this runner has no tool execution layer. "
            "The run is retained for transparency and is not a controlled tool-satisfied result."
        ]
    return []


def _deduplicate_conditions(conditions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for condition in conditions:
        unique[str(condition["condition_id"])] = condition
    return [unique[key] for key in sorted(unique)]


def _safe_name(value: str) -> str:
    return "".join(character if character.isalnum() or character in "-_." else "-" for character in value).strip("-.") or "experiment"


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
