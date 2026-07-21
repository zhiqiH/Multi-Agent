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
    build_run_id,
    resolve_protocols,
    run_protocol,
)
from src.tasks import (  # noqa: E402
    DEFAULT_AGENT_FIELDS,
    KNOWN_TASK_FIELDS,
    PROTECTED_FIELDS,
    load_benchmark,
    project_task,
    select_tasks,
)
from src.tools import EVIDENCE_TOOL_NAMES, ToolRegistry  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run controlled single-agent and multi-agent protocol experiments.")
    parser.add_argument("--benchmark", default="benchmark/benchmark-C.json")
    parser.add_argument("--model-config", default="configs/model_config.json")
    parser.add_argument("--experiment-config", default="configs/experiment_config.json")
    parser.add_argument("--out-dir", default="logs/current")

    parser.add_argument("--protocols", default=",".join(DEFAULT_PROTOCOLS))
    parser.add_argument("--tasks", default="", help="Comma-separated task IDs. Empty means all tasks.")
    parser.add_argument("--model", default="", help="Temporarily override one selected agent profile's model ID.")
    parser.add_argument("--overwrite", action="store_true", help="Replace exact matching run IDs only.")
    parser.add_argument("--strict-tool-requirements", action="store_true")
    parser.add_argument("--print-agent-view", action="store_true", help="Print exactly what agents see, then exit.")
    parser.add_argument("--list-protocols", action="store_true")
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--list-task-fields", action="store_true")
    parser.add_argument(
        "--agent-profiles",
        "--agent-profile",
        dest="agent_profiles",
        default="",
        help="Comma-separated agent model profiles. Empty uses defaults.agent; 'all' uses every profile.",
    )
    parser.add_argument(
        "--agent-visible-fields",
        dest="agent_visible_fields",
        default="",
        help="Comma-separated benchmark fields visible to agents.",
    )
    parser.add_argument(
        "--allow-protected-agent-fields",
        action="store_true",
        help="Allow grading fields to be included in the Agent input.",
    )
    parser.add_argument("--run-number", type=int, default=1, help="First replicate number.")
    parser.add_argument("--runs", type=int, default=0, help="Number of replicates; 0 uses experiment config.")
    parser.add_argument("--max-rounds", type=int, default=0, help="Override max rounds for all selected protocols.")
    parser.add_argument(
        "--max-interactions", type=int, default=0, help="Override max model interactions for all selected protocols."
    )
    parser.add_argument(
        "--max-total-tokens",
        type=int,
        default=0,
        help="Override the total input-plus-output token budget per run; 0 uses the experiment config.",
    )
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
    base_tool_registry = ToolRegistry(
        experiment_config.get("tool_policy", {}), project_root=PROJECT_ROOT
    )
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
    if protected_requested:
        print(
            "NOTICE: Agents receive grading fields: "
            + ", ".join(protected_requested),
            file=sys.stderr,
        )

    agent_tasks = [(raw, project_task(raw, agent_fields)) for raw in raw_tasks]
    task_tool_registries = {
        raw["task_id"]: base_tool_registry.for_task(raw) for raw, _ in agent_tasks
    }
    if args.print_agent_view:
        print(
            json.dumps(
                {
                    "agent_visible_fields": list(agent_fields),
                    "tasks": [agent_task for _, agent_task in agent_tasks],
                    "task_tool_surfaces": {
                        task_id: {
                            "available_tools": list(registry.names),
                            "tool_expectations": registry.tool_expectations,
                        }
                        for task_id, registry in task_tool_registries.items()
                    },
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
    runs = args.runs or int(run_policy.get("runs_per_condition") or 1)
    if args.run_number <= 0 or runs <= 0:
        raise SystemExit("--run-number and --runs must be positive")
    if args.max_total_tokens < 0:
        raise SystemExit("--max-total-tokens cannot be negative")
    out_dir = _project_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    store_prompts = bool(visibility.get("store_agent_prompts", True))
    protocol_overrides = experiment_config.get("protocols", {})

    print(f"Benchmark: {benchmark_path}")
    print(f"Benchmark ID: {benchmark.get('benchmark_id', benchmark_path.stem)}")
    print(f"Tasks: {', '.join(task['task_id'] for task in raw_tasks)}")
    print(f"Protocols: {', '.join(protocols)}")
    print(f"Agent-visible fields: {', '.join(agent_fields)}")

    completed = 0
    skipped = 0
    warnings_seen = 0
    manifest_conditions: list[dict[str, Any]] = []
    for requested_profile in profile_names:
        client = build_client(
            model_config,
            role="agent",
            profile=requested_profile,
            model=args.model or None,
            secrets_path=PROJECT_ROOT / ".secrets" / "model_keys.json",
        )
        effective_config = dict(getattr(client, "effective_config", {}) or {})
        print(f"Agent model: {client.model}")
        capabilities = effective_config.get("capabilities") or {}
        if any(registry.names for registry in task_tool_registries.values()) and not capabilities.get(
            "tool_calling", False
        ):
            raise SystemExit(
                f"Agent model {client.model} is not configured with tool_calling capability."
            )

        for protocol_id in protocols:
            protocol_config = _protocol_config(
                protocol_id,
                protocol_overrides,
                run_policy=run_policy,
                max_rounds=args.max_rounds,
                max_interactions=args.max_interactions,
                max_total_tokens=args.max_total_tokens,
            )
            condition = {
                "benchmark_id": benchmark.get("benchmark_id", benchmark_path.stem),
                "benchmark_file": _display_path(benchmark_path),
                "protocol_id": protocol_id,
                "protocol_config": protocol_config,
                "agent_provider": client.provider,
                "agent_model": client.model,
                "agent_effective_config": effective_config,
                "agent_visible_fields": list(agent_fields),
                "tool_policy": experiment_config.get("tool_policy", {}),
            }
            for raw_task, agent_task in agent_tasks:
                task_tool_registry = task_tool_registries[raw_task["task_id"]]
                task_condition = {
                    **condition,
                    "task_id": raw_task["task_id"],
                    "agent_task": agent_task,
                    "task_tool_policy": {
                        "available_tools": list(task_tool_registry.names),
                        "tool_expectations": task_tool_registry.tool_expectations,
                    },
                }
                manifest_conditions.append(task_condition)
                task_warnings = _task_validity_warnings(raw_task, task_tool_registry)
                if task_warnings and args.strict_tool_requirements:
                    raise SystemExit(f"{raw_task['task_id']}: {task_warnings[0]}")
                for warning in task_warnings:
                    print(f"WARNING {raw_task['task_id']}: {warning}", file=sys.stderr)
                    warnings_seen += 1
                metadata = {
                    field: raw_task.get(field)
                    for field in (
                        "task_id",
                        "category",
                        "difficulty",
                        "tool_requirement",
                        "available_tools",
                        "tool_expectations",
                    )
                }
                for run_number in range(args.run_number, args.run_number + runs):
                    run_id = build_run_id(
                        raw_task["task_id"],
                        protocol_id,
                        client.model,
                        run_number,
                    )
                    out_path = out_dir / f"{run_id}.json"
                    if out_path.exists():
                        existing_log = read_json(out_path)
                        same_condition = _same_recorded_condition(existing_log, task_condition)
                        if not same_condition and not args.overwrite:
                            raise SystemExit(
                                f"Existing run {out_path.name} used a different benchmark or execution "
                                "condition. Rerun with --overwrite to replace the stale log, or use a different "
                                "--out-dir/--run-number to preserve both conditions."
                            )
                        if not args.overwrite:
                            print(f"SKIP existing run {run_id}")
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
                        tool_registry=task_tool_registry,
                    )
                    post_tool_warnings = _post_tool_validity_warnings(raw_task, log)
                    for warning in post_tool_warnings:
                        print(f"WARNING {raw_task['task_id']}: {warning}", file=sys.stderr)
                        warnings_seen += 1
                    log["validity_warnings"].extend(post_tool_warnings)
                    if args.strict_tool_requirements and post_tool_warnings:
                        log["errors"].extend(post_tool_warnings)
                    log.update(
                        {
                            "condition": task_condition,
                            "benchmark_id": benchmark.get("benchmark_id", benchmark_path.stem),
                            "benchmark_file": _display_path(benchmark_path),
                            "experiment_config_file": _display_path(experiment_config_path),
                            "model_config_file": _display_path(model_config_path),
                        }
                    )
                    if not store_prompts:
                        log.pop("prompts", None)
                    write_json(out_path, log)
                    status = "ERROR" if log["errors"] else "OK"
                    print(_format_run_result(status, run_id, log))
                    completed += 1

    manifest_conditions = _deduplicate_conditions(manifest_conditions)
    manifest_model_labels = sorted({str(condition["agent_model"]) for condition in manifest_conditions})
    manifest_id = _safe_name("__".join(
        [
            benchmark_path.stem,
            "-".join(protocols),
            "-".join(manifest_model_labels),
            f"run{args.run_number:02d}",
        ]
    ))
    manifest = {
        "record_type": "experiment_manifest",
        "manifest_id": manifest_id,
        "benchmark_id": benchmark.get("benchmark_id", benchmark_path.stem),
        "benchmark_file": _display_path(benchmark_path),
        "task_ids": [task["task_id"] for task in raw_tasks],
        "first_run_number": args.run_number,
        "runs": runs,
        "conditions": manifest_conditions,
        "completed_runs": completed,
        "skipped_runs": skipped,
        "validity_warning_count": warnings_seen,
    }
    manifest_path = out_dir / f"manifest__{manifest_id}.json"
    if manifest_path.exists():
        existing_manifest = read_json(manifest_path)
        if not _same_manifest_scope(existing_manifest, manifest) and not args.overwrite:
            raise SystemExit(
                f"Existing manifest {manifest_path.name} used a different experiment scope. "
                "Rerun with --overwrite to replace it, or use a different --out-dir/--run-number."
            )
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
        print(f"{name}: model={profile.get('model', 'unknown')} key_env={profile.get('api_key_env', '-')}{default_label}")


def _protocol_config(
    protocol_id: str,
    configured: Any,
    *,
    run_policy: Any,
    max_rounds: int,
    max_interactions: int,
    max_total_tokens: int,
) -> dict[str, Any]:
    definition = PROTOCOLS[protocol_id]
    policy = run_policy if isinstance(run_policy, dict) else {}
    result = {
        "max_rounds": definition["default_max_rounds"],
        "max_interactions": definition["default_max_interactions"],
        "max_total_tokens": int(policy.get("max_total_tokens", 100000)),
        "final_writer_reserve_tokens": int(policy.get("final_writer_reserve_tokens", 0)),
        "minimum_call_output_tokens": int(policy.get("minimum_call_output_tokens", 128)),
        "token_estimation_bytes_per_token": float(
            policy.get("token_estimation_bytes_per_token", 3.0)
        ),
        "token_safety_margin": int(policy.get("token_safety_margin", 1000)),
    }
    if protocol_id in {"single_agent", "voting"}:
        result["final_writer_reserve_tokens"] = 0
    if isinstance(configured, dict) and isinstance(configured.get(protocol_id), dict):
        protocol_values = configured[protocol_id]
        for field in ("max_rounds", "max_interactions"):
            if field in protocol_values:
                result[field] = protocol_values[field]
    if max_rounds:
        result["max_rounds"] = max_rounds
    if max_interactions:
        result["max_interactions"] = max_interactions
    if max_total_tokens:
        result["max_total_tokens"] = max_total_tokens
    return result


def _task_validity_warnings(task: dict[str, Any], tool_registry: ToolRegistry) -> list[str]:
    requirement = str(task.get("tool_requirement", "")).strip().lower()
    if requirement != "required":
        return []
    warnings: list[str] = []
    if not set(tool_registry.names).intersection(EVIDENCE_TOOL_NAMES):
        warnings.append(
            "This task requires external evidence, but its benchmark available_tools field "
            "does not enable an evidence-producing tool."
        )
    prompt = str(task.get("prompt") or "").lower()
    if "local pdf" in prompt and not tool_registry.has_local_documents:
        warnings.append(
            "This task requires provided local PDFs, but no files were found under tool_policy.local_document_roots."
        )
    return warnings


def _post_tool_validity_warnings(task: dict[str, Any], log: dict[str, Any]) -> list[str]:
    requirement = str(task.get("tool_requirement", "")).strip().lower()
    warnings: list[str] = []
    allowed_tools = set(task.get("available_tools") or [])
    unexpected_tools = sorted(
        {
            str(call.get("tool_name") or "")
            for call in log.get("tool_calls") or []
            if isinstance(call, dict) and str(call.get("tool_name") or "") not in allowed_tools
        }
    )
    if unexpected_tools:
        warnings.append(
            "The run recorded tools outside this task's benchmark available_tools field: "
            + ", ".join(unexpected_tools)
            + "."
        )
    if requirement == "required" and not log.get("tool_requirement_satisfied"):
        warnings.append(
            "The task requires external evidence, but the model completed the run without a successful "
            "authorized evidence call satisfying the benchmark tool expectation."
        )
    if requirement == "prohibited" and log.get("tool_call_count"):
        warnings.append("The task prohibits tools, but a tool call was recorded.")
    return warnings


def _deduplicate_conditions(conditions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    for condition in conditions:
        if condition not in unique:
            unique.append(condition)
    return unique


def _same_recorded_condition(existing_log: dict[str, Any], expected: dict[str, Any]) -> bool:
    recorded = dict(existing_log.get("condition") or {})
    for field in ("benchmark_id", "benchmark_file"):
        if field not in recorded and field in existing_log:
            recorded[field] = existing_log[field]
    return all(recorded.get(field) == value for field, value in expected.items())


def _same_manifest_scope(existing: dict[str, Any], expected: dict[str, Any]) -> bool:
    scope_fields = (
        "benchmark_id",
        "benchmark_file",
        "task_ids",
        "first_run_number",
        "runs",
        "conditions",
    )
    return all(existing.get(field) == expected.get(field) for field in scope_fields)


def _tool_call_signal(record: dict[str, Any]) -> str:
    requirement = str(record.get("tool_requirement") or "").strip().lower()
    call_count = int(record.get("tool_call_count") or 0)
    if requirement == "prohibited":
        return "not_required" if call_count == 0 else "failed"
    return "success" if record.get("tool_requirement_satisfied") else "failed"


def _format_run_result(status: str, run_id: str, record: dict[str, Any]) -> str:
    return (
        f"{status} {run_id}: tokens={int(record.get('total_tokens') or 0)} "
        f"runtime={float(record.get('runtime_seconds') or 0):.1f}s "
        f"tool={_tool_call_signal(record)}"
    )


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
