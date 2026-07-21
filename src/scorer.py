from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from statistics import mean
from typing import Any

from .evidence import build_evidence_audit, compact_evidence_audit
from .failure_taxonomy import FAILURE_TYPES, NO_FAILURE
from .llm_client import LLMClient
from .prompts import scoring_prompt
from .response_audit import apply_criterion_caps, build_response_audit


def build_result_run_id(run_log: dict[str, Any]) -> str:
    components = [
        _slug_component(run_log["task_id"]),
        _slug_component(run_log.get("protocol_id") or run_log["protocol"]),
        _slug_component(run_log["agent_model"]),
        _run_label(run_log),
    ]
    return "__".join(components)


def build_score_id(run_log: dict[str, Any], client: LLMClient) -> str:
    return f"{build_result_run_id(run_log)}__judge-{_slug_component(client.model)}"


def score_run_log(
    run_log: dict[str, Any],
    task: dict[str, Any],
    client: LLMClient,
) -> dict[str, Any]:
    evidence_audit = build_evidence_audit(run_log, task, run_log["final_output"])
    response_audit = build_response_audit(task, run_log["final_output"], evidence_audit)
    failure_trace = _build_failure_trace(run_log)
    messages = scoring_prompt(
        task,
        run_log["final_output"],
        evidence_audit,
        response_audit,
        failure_trace,
    )
    effective_config = dict(getattr(client, "effective_config", {}) or {})
    judge_max_tokens = int(effective_config["judge_max_tokens"])
    response = client.chat(messages, response_format={"type": "json_object"}, max_tokens=judge_max_tokens)
    if not response.content.strip():
        detail = f"finish_reason={response.finish_reason or 'unknown'}, output_tokens={response.output_tokens}"
        raise RuntimeError(
            "Judge returned no visible JSON content "
            f"({detail}). Increase judge_max_tokens or reduce reasoning effort."
        )
    if response.finish_reason == "length":
        raise RuntimeError(
            "Judge response reached its token limit before a complete score was guaranteed. "
            "Increase judge_max_tokens or reduce reasoning effort."
        )
    parsed = _parse_json_object(response.content)
    evidence_assessment = _validated_evidence_assessment(parsed.get("evidence_assessment"))
    judge_failure_type, failure_evidence = _validated_failure_assessment(parsed, run_log)
    judge_failure_evidence = list(failure_evidence)
    failure_type, failure_evidence, failure_classification_source = (
        _apply_log_failure_rules(
            judge_failure_type,
            failure_evidence,
            run_log,
            task,
            evidence_audit,
            response_audit,
        )
    )
    judge_criterion_scores = _validated_criterion_scores(
        task.get("evaluation_criteria", []), parsed.get("criterion_scores")
    )
    criterion_scores = apply_criterion_caps(judge_criterion_scores, response_audit)

    accuracy_raw = _clamp_int(parsed.get("accuracy_raw", 3), 1, 5)
    helpfulness_raw = _clamp_int(parsed.get("helpfulness_raw", 3), 1, 5)
    completeness_norm = _criterion_completeness(
        task.get("evaluation_criteria", []),
        criterion_scores,
        fallback=parsed.get("completeness_norm", 0.5),
    )
    hallucination_rate = _clamp_float(parsed.get("hallucination_rate", 0.2), 0.0, 1.0)
    accuracy_norm = (accuracy_raw - 1) / 4
    helpfulness_norm = (helpfulness_raw - 1) / 4
    uncapped_quality_score = (
        0.35 * accuracy_norm
        + 0.30 * completeness_norm
        + 0.20 * helpfulness_norm
        + 0.15 * (1 - hallucination_rate)
    )
    judge_reported_score_cap = _clamp_float(parsed.get("overall_score_cap", 1.0), 0.0, 1.0)
    judge_evidence_score_cap = evidence_assessment["evidence_score_cap"]
    deterministic_hard_fail_cap = _clamp_float(
        response_audit.get("deterministic_hard_fail_score_cap", 1.0), 0.0, 1.0
    )
    # Judge evidence caps are advisory. Tool execution, source traceability,
    # evidence policy, and objective hard fails are enforced by deterministic
    # audits. An uncorroborated LLM cap must not override those audits.
    judge_score_cap = (
        min(judge_reported_score_cap, deterministic_hard_fail_cap)
        if deterministic_hard_fail_cap < 1.0
        else 1.0
    )
    evidence_score_cap = _clamp_float(
        evidence_audit.get("deterministic_score_cap", 1.0), 0.0, 1.0
    )
    overall_score_cap = min(judge_score_cap, evidence_score_cap)
    judge_capped_quality_score = round(min(uncapped_quality_score, judge_score_cap), 4)
    overall_quality_score = round(min(uncapped_quality_score, overall_score_cap), 4)
    cap_reasons = _deduplicate_strings(
        [
            *((parsed.get("cap_reasons") or []) if judge_score_cap < 1.0 else []),
            *(evidence_audit.get("deterministic_cap_reasons") or []),
            *(response_audit.get("triggered_hard_fail_rules") or []),
        ]
    )
    agent_tokens = max(1, int(run_log.get("total_tokens", 0)))
    quality_token_ratio = round(overall_quality_score / agent_tokens, 8)

    judge_model = client.model
    judge_estimated_cost = _estimate_judge_cost(client, response.input_tokens, response.output_tokens)
    agent_cost = float(run_log.get("estimated_cost", 0.0) or 0.0)
    total_estimated_cost = round(agent_cost + judge_estimated_cost, 8)

    return {
        "record_type": "score",
        "score_id": build_score_id(run_log, client),
        "run_id": build_result_run_id(run_log),
        "task_id": run_log["task_id"],
        "category": run_log.get("category"),
        "protocol": run_log["protocol"],
        "agent_model": run_log["agent_model"],
        "judge_model": judge_model,
        "accuracy_raw": accuracy_raw,
        "accuracy_norm": round(accuracy_norm, 4),
        "completeness_norm": round(completeness_norm, 4),
        "helpfulness_raw": helpfulness_raw,
        "helpfulness_norm": round(helpfulness_norm, 4),
        "hallucination_rate": round(hallucination_rate, 4),
        "overall_quality_score": overall_quality_score,
        "uncapped_quality_score": round(uncapped_quality_score, 4),
        "judge_capped_quality_score": judge_capped_quality_score,
        "judge_reported_score_cap": judge_reported_score_cap,
        "judge_evidence_score_cap": judge_evidence_score_cap,
        "judge_score_cap": judge_score_cap,
        "evidence_score_cap": evidence_score_cap,
        "overall_score_cap": overall_score_cap,
        "cap_reasons": cap_reasons,
        "criterion_scores": criterion_scores,
        "response_audit": response_audit,
        "runtime_seconds": run_log.get("runtime_seconds", 0),
        "input_tokens": run_log.get("input_tokens", 0),
        "output_tokens": run_log.get("output_tokens", 0),
        "total_tokens": run_log.get("total_tokens", 0),
        "max_total_tokens": run_log.get("max_total_tokens"),
        "final_writer_reserve_tokens": run_log.get("final_writer_reserve_tokens"),
        "budget_remaining_tokens": run_log.get("budget_remaining_tokens"),
        "budget_overrun_tokens": run_log.get("budget_overrun_tokens"),
        "budget_utilization": run_log.get("budget_utilization"),
        "budget_limited_call_count": run_log.get("budget_limited_call_count"),
        "budget_skipped_call_count": run_log.get("budget_skipped_call_count"),
        "role_max_output_tokens": run_log.get("role_max_output_tokens", {}),
        "role_usage": run_log.get("role_usage", {}),
        "estimated_cost": agent_cost,
        "active_agent_count": run_log.get("active_agent_count", 1),
        "interaction_count": run_log.get("interaction_count", 1),
        "model_call_count": run_log.get("model_call_count", run_log.get("interaction_count", 1)),
        "rounds_completed": run_log.get("rounds_completed", 1),
        "message_count": run_log.get("message_count", 0),
        "communication_density": run_log.get("communication_density", 0.0),
        "agreement_rate": run_log.get("agreement_rate"),
        "critique_acceptance_rate": run_log.get("critique_acceptance_rate"),
        "tool_requirement": evidence_audit["tool_requirement"],
        "task_available_tools": evidence_audit["allowed_tools"],
        "run_exposed_tools": evidence_audit["exposed_tools"],
        "tool_surface_matches_benchmark": evidence_audit[
            "tool_surface_matches_benchmark"
        ],
        "tool_expectations_satisfied": evidence_audit["tool_expectations_satisfied"],
        "tool_expectation_violations": evidence_audit["tool_expectation_violations"],
        "unauthorized_tool_names": evidence_audit["unauthorized_tool_names"],
        "unauthorized_tool_call_count": evidence_audit["unauthorized_tool_call_count"],
        "tool_access_used": bool(run_log.get("tool_access_used")),
        "tool_requirement_satisfied": bool(evidence_audit["execution_requirement_satisfied"]),
        "score_eligible": bool(evidence_audit["score_eligible"]),
        "evidence_execution_status": evidence_audit["execution_status"],
        "citation_alignment_status": evidence_audit["citation_alignment_status"],
        "evidence_policy_satisfied": evidence_audit["evidence_policy_satisfied"],
        "evidence_policy_violations": evidence_audit["evidence_policy_violations"],
        "tool_call_count": evidence_audit["tool_call_count"],
        "successful_tool_call_count": evidence_audit["successful_tool_call_count"],
        "successful_authorized_tool_call_count": evidence_audit[
            "successful_authorized_tool_call_count"
        ],
        "successful_substantive_tool_call_count": evidence_audit[
            "successful_substantive_tool_call_count"
        ],
        "successful_discovery_tool_call_count": evidence_audit[
            "successful_discovery_tool_call_count"
        ],
        "substantive_source_count": evidence_audit["substantive_source_count"],
        "discovery_source_count": evidence_audit["discovery_source_count"],
        "academic_record_count": evidence_audit["academic_record_count"],
        "identifier_record_count": evidence_audit["identifier_record_count"],
        "local_document_count": evidence_audit["local_document_count"],
        "citation_traceability_rate": evidence_audit["citation_audit"]["traceability_rate"],
        "unaccessed_citation_count": len(evidence_audit["citation_audit"]["unaccessed_urls"])
        + len(evidence_audit["citation_audit"]["unaccessed_identifiers"]),
        "quality_token_ratio": quality_token_ratio,
        "quality_api_cost_ratio": (
            round(overall_quality_score / total_estimated_cost, 8) if total_estimated_cost > 0 else None
        ),
        "failure_type": failure_type,
        "failure_evidence": failure_evidence,
        "failure_classification_source": failure_classification_source,
        "judge_failure_type": judge_failure_type,
        "judge_failure_evidence": judge_failure_evidence,
        "detected_failure_risks": parsed.get("detected_failure_risks") or [],
        "judge_evidence_assessment": evidence_assessment,
        "evidence_audit": compact_evidence_audit(evidence_audit),
        "notes": parsed.get("notes", ""),
        "scorer_input_tokens": response.input_tokens,
        "scorer_output_tokens": response.output_tokens,
        "scorer_total_tokens": response.total_tokens,
        "judge_finish_reason": response.finish_reason,
        "judge_estimated_cost": judge_estimated_cost,
        "total_estimated_cost": total_estimated_cost,
        "raw_evaluation": parsed,
    }


def _build_failure_trace(run_log: dict[str, Any]) -> dict[str, Any]:
    messages: list[dict[str, Any]] = []
    for index, raw_message in enumerate(run_log.get("intermediate_messages") or [], start=1):
        if not isinstance(raw_message, dict):
            continue
        messages.append(
            {
                "message_id": str(raw_message.get("message_id") or f"m{index:03d}"),
                "sender": raw_message.get("sender"),
                "recipients": raw_message.get("recipients") or [],
                "round": raw_message.get("round"),
                "channel": raw_message.get("channel"),
                "content": str(raw_message.get("content") or ""),
                "finish_reason": raw_message.get("finish_reason"),
                "input_tokens": raw_message.get("input_tokens", 0),
                "output_tokens": raw_message.get("output_tokens", 0),
                "total_tokens": raw_message.get("total_tokens", 0),
            }
        )
    return {
        "execution_summary": {
            "protocol": run_log.get("protocol"),
            "protocol_id": run_log.get("protocol_id"),
            "is_multi_agent": run_log.get("protocol_id") != "single_agent",
            "termination_reason": run_log.get("termination_reason"),
            "run_errors": run_log.get("errors") or [],
            "run_metrics": {
                "active_agent_count": run_log.get("active_agent_count"),
                "interaction_count": run_log.get("interaction_count"),
                "rounds_completed": run_log.get("rounds_completed"),
                "message_count": run_log.get("message_count"),
                "communication_density": run_log.get("communication_density"),
                "agreement_rate": run_log.get("agreement_rate"),
                "critique_count": run_log.get("critique_count"),
                "critique_acceptance_rate": run_log.get("critique_acceptance_rate"),
                "total_tokens": run_log.get("total_tokens"),
                "max_total_tokens": run_log.get("max_total_tokens"),
                "budget_utilization": run_log.get("budget_utilization"),
                "budget_limited_call_count": run_log.get("budget_limited_call_count"),
                "budget_skipped_call_count": run_log.get("budget_skipped_call_count"),
            },
            "role_usage": run_log.get("role_usage") or {},
            "final_output_present": bool(str(run_log.get("final_output") or "").strip()),
            "tool_execution": _tool_execution_summary(run_log),
        },
        "intermediate_messages": messages,
        "valid_trace_refs": [
            *(message["message_id"] for message in messages),
            "final_output",
            "run_metrics",
            "termination_reason",
            "run_errors",
            "role_usage",
            "tool_execution",
        ],
    }


def _tool_execution_summary(run_log: dict[str, Any]) -> dict[str, Any]:
    calls = [call for call in run_log.get("tool_calls") or [] if isinstance(call, dict)]
    failed_errors = _deduplicate_strings(
        call.get("error") for call in calls if not call.get("success") and call.get("error")
    )
    return {
        "tool_requirement": run_log.get("tool_requirement"),
        "tool_requirement_satisfied": bool(run_log.get("tool_requirement_satisfied")),
        "tool_call_count": len(calls),
        "successful_tool_call_count": sum(bool(call.get("success")) for call in calls),
        "failed_tool_call_count": sum(not bool(call.get("success")) for call in calls),
        "failed_tool_errors": failed_errors[:5],
        "validity_warnings": run_log.get("validity_warnings") or [],
    }


def _validated_failure_assessment(
    parsed: dict[str, Any], run_log: dict[str, Any]
) -> tuple[str, list[dict[str, Any]]]:
    raw_failure_type = str(parsed.get("failure_type") or NO_FAILURE).strip()
    if raw_failure_type not in FAILURE_TYPES:
        raise ValueError(
            f"Judge failure_type must be one of {FAILURE_TYPES}; got {raw_failure_type!r}"
        )
    raw_evidence = parsed.get("failure_evidence")
    if not isinstance(raw_evidence, list):
        raise ValueError("Judge output must include failure_evidence as a list")
    if len(raw_evidence) > 3:
        raise ValueError("Judge failure_evidence may contain at most three observable signals")

    message_records = {
        str(message.get("message_id") or f"m{index:03d}"): message
        for index, message in enumerate(run_log.get("intermediate_messages") or [], start=1)
        if isinstance(message, dict)
    }
    message_refs = set(message_records)
    valid_refs = {
        "final_output",
        "run_metrics",
        "termination_reason",
        "run_errors",
        "role_usage",
        "tool_execution",
    }
    valid_refs.update(message_refs)
    evidence: list[dict[str, Any]] = []
    referenced: set[str] = set()
    for item in raw_evidence:
        if not isinstance(item, dict):
            raise ValueError("Each failure_evidence item must be an object")
        signal = item.get("signal")
        refs = item.get("trace_refs")
        if not isinstance(signal, str) or not signal.strip():
            raise ValueError("Each failure_evidence item must include a non-empty signal")
        if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) for ref in refs):
            raise ValueError("Each failure_evidence item must include non-empty trace_refs")
        normalized_refs = list(dict.fromkeys(ref.strip() for ref in refs if ref.strip()))
        unknown_refs = sorted(set(normalized_refs) - valid_refs)
        if unknown_refs:
            raise ValueError(f"Judge failure_evidence contains unknown trace_refs: {unknown_refs}")
        referenced.update(normalized_refs)
        evidence.append({"signal": signal.strip(), "trace_refs": normalized_refs})

    if raw_failure_type == NO_FAILURE:
        if evidence:
            raise ValueError("failure_evidence must be empty when failure_type is None")
        return raw_failure_type, []
    if run_log.get("protocol_id") == "single_agent" and raw_failure_type != "Tool Failure":
        raise ValueError("Single-agent runs may only be assigned Tool Failure or None")
    if not evidence:
        raise ValueError("A non-None failure_type requires observable failure_evidence")
    if "final_output" not in referenced:
        raise ValueError("A collaboration failure must cite final_output to show material downstream impact")
    referenced_messages = referenced.intersection(message_refs)
    if raw_failure_type == "Coordination Failure" and len(referenced_messages) < 2:
        raise ValueError("Coordination Failure must cite at least two recorded Agent messages")
    if raw_failure_type in {
        "Communication Failure",
        "Role Confusion",
        "Hallucination Propagation",
    } and not referenced_messages:
        raise ValueError(f"{raw_failure_type} must cite at least one recorded intermediate message")
    if raw_failure_type == "Premature Consensus" and len(referenced_messages) < 2:
        raise ValueError("Premature Consensus must cite at least two recorded Agent messages")
    if raw_failure_type == "Tool Failure" and "tool_execution" not in referenced:
        raise ValueError("Tool Failure must cite tool_execution from the raw execution log")
    if raw_failure_type == "Over-Collaboration":
        if "run_metrics" not in referenced:
            raise ValueError(
                "Over-Collaboration must cite run_metrics in addition to repeated work and final impact"
            )
        if len(referenced_messages) < 2:
            raise ValueError("Over-Collaboration must cite at least two repeated intermediate messages")
    if raw_failure_type == "Manager Bottleneck":
        if run_log.get("protocol_id") != "manager_worker":
            raise ValueError("Manager Bottleneck is only valid for the manager_worker protocol")
        manager_refs = {
            ref
            for ref, message in message_records.items()
            if "manager" in str(message.get("sender") or "").lower()
        }
        if not referenced_messages.intersection(manager_refs):
            raise ValueError("Manager Bottleneck must cite a recorded Manager message")
        if not (referenced_messages - manager_refs):
            raise ValueError("Manager Bottleneck must cite an affected downstream Agent message")
    if raw_failure_type == "Noise Accumulation":
        workspace_refs = {
            ref
            for ref, message in message_records.items()
            if "blackboard" in str(message.get("channel") or "").lower()
        }
        if run_log.get("protocol_id") != "shared_blackboard":
            raise ValueError("Noise Accumulation is only valid for the shared_blackboard protocol")
        if len(referenced_messages.intersection(workspace_refs)) < 2:
            raise ValueError("Noise Accumulation must cite at least two recorded blackboard messages")
    return raw_failure_type, evidence


def _apply_log_failure_rules(
    failure_type: str,
    failure_evidence: list[dict[str, Any]],
    run_log: dict[str, Any],
    task: dict[str, Any],
    evidence_audit: dict[str, Any],
    response_audit: dict[str, Any],
) -> tuple[str, list[dict[str, Any]], str]:
    """Prefer objective raw-log failures over an LLM's semantic trace classification."""

    del task, response_audit
    tool_failure = _tool_failure_from_log(run_log, evidence_audit)
    if tool_failure is not None:
        return "Tool Failure", tool_failure, "deterministic_log_audit"

    over_collaboration = _budget_over_collaboration_from_log(run_log)
    if over_collaboration is not None:
        return "Over-Collaboration", over_collaboration, "deterministic_log_audit"

    if run_log.get("protocol_id") == "single_agent" and failure_type != "Tool Failure":
        return NO_FAILURE, [], "deterministic_log_audit"
    return failure_type, failure_evidence, "judge"


def apply_log_failure_analysis(
    scores: list[dict[str, Any]],
    run_logs_by_id: dict[str, dict[str, Any]],
    *,
    relative_drop_threshold: float = 0.15,
) -> int:
    """Re-audit every score from its raw log and a matching Single Agent baseline."""

    baseline_groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for score in scores:
        if score.get("protocol") != "Single Agent":
            continue
        baseline_log = run_logs_by_id.get(str(score.get("run_id") or ""))
        if baseline_log is None or _tool_failure_from_log(baseline_log, score) is not None:
            continue
        baseline_groups.setdefault(_baseline_key(score), []).append(score)

    analyzed = 0
    for score in scores:
        run_log = run_logs_by_id.get(str(score.get("run_id") or ""))
        if run_log is None:
            continue
        baselines = baseline_groups.get(_baseline_key(score), [])
        baseline_score = (
            mean(float(item.get("overall_quality_score") or 0.0) for item in baselines)
            if baselines
            else None
        )
        baseline_tokens = (
            mean(float(item.get("total_tokens") or 0.0) for item in baselines)
            if baselines
            else None
        )
        quality = float(score.get("overall_quality_score") or 0.0)
        relative_drop = (
            max(0.0, (baseline_score - quality) / baseline_score)
            if baseline_score is not None and baseline_score > 0
            else None
        )
        suspected = bool(
            run_log.get("protocol_id") != "single_agent"
            and relative_drop is not None
            and relative_drop > relative_drop_threshold
        )

        judge_type = str(score.get("judge_failure_type") or NO_FAILURE)
        if judge_type not in FAILURE_TYPES:
            judge_type = NO_FAILURE
        judge_evidence = (
            score.get("judge_failure_evidence", score.get("failure_evidence"))
            if judge_type != NO_FAILURE
            else []
        )
        if not isinstance(judge_evidence, list):
            judge_evidence = []
        failure_type, failure_evidence, source = _apply_log_failure_rules(
            judge_type,
            judge_evidence,
            run_log,
            {},
            score,
            {},
        )

        if failure_type == NO_FAILURE and suspected:
            relative_over_collaboration = _relative_over_collaboration_from_log(
                run_log,
                baseline_tokens=baseline_tokens,
                relative_drop=relative_drop,
            )
            if relative_over_collaboration is not None:
                failure_type = "Over-Collaboration"
                failure_evidence = relative_over_collaboration
                source = "relative_log_audit"

        score.update(
            {
                "failure_type": failure_type,
                "failure_evidence": failure_evidence,
                "failure_classification_source": source,
                "single_agent_baseline_score": (
                    round(baseline_score, 4) if baseline_score is not None else None
                ),
                "relative_score_drop": (
                    round(relative_drop, 4) if relative_drop is not None else None
                ),
                "relative_failure_suspected": suspected,
                "failure_analysis_condition": {
                    "source": "raw_log",
                    "relative_single_agent_drop_threshold": relative_drop_threshold,
                },
            }
        )
        analyzed += 1
    return analyzed


def _baseline_key(score: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(score.get("benchmark_id") or ""),
        str(score.get("task_id") or ""),
        str(score.get("agent_model") or ""),
        str(score.get("judge_model") or ""),
    )


def _tool_failure_from_log(
    run_log: dict[str, Any], evidence_audit: dict[str, Any]
) -> list[dict[str, Any]] | None:
    requirement = str(
        evidence_audit.get("tool_requirement") or run_log.get("tool_requirement") or ""
    ).strip().lower()
    satisfied_value = evidence_audit.get("execution_requirement_satisfied")
    if satisfied_value is None:
        satisfied_value = evidence_audit.get("tool_requirement_satisfied")
    if satisfied_value is None:
        satisfied_value = run_log.get("tool_requirement_satisfied")
    satisfied = bool(satisfied_value)
    call_count = int(
        evidence_audit.get("tool_call_count")
        if evidence_audit.get("tool_call_count") is not None
        else len(run_log.get("tool_calls") or [])
    )
    unauthorized = int(evidence_audit.get("unauthorized_tool_call_count") or 0)
    surface_matches = evidence_audit.get("tool_surface_matches_benchmark", True)

    failed = (
        (requirement == "required" and not satisfied)
        or (requirement == "prohibited" and call_count > 0)
        or unauthorized > 0
        or surface_matches is False
    )
    if not failed:
        return None
    failed_calls = [
        call
        for call in run_log.get("tool_calls") or []
        if isinstance(call, dict) and not call.get("success")
    ]
    failed_errors = _deduplicate_strings(call.get("error") for call in failed_calls)
    error_text = "; ".join(error.rstrip(". ") for error in failed_errors[:2])
    detail = f"; recorded errors include: {error_text}" if error_text else ""
    signal = (
        f"The raw log records tool_requirement={requirement or 'unknown'}, "
        f"tool_requirement_satisfied={satisfied}, tool_call_count={call_count}, and "
        f"unauthorized_tool_call_count={unauthorized}{detail}. The task's tool execution condition therefore failed."
    )
    return [{"signal": signal, "trace_refs": ["tool_execution", "final_output"]}]


def _budget_over_collaboration_from_log(
    run_log: dict[str, Any]
) -> list[dict[str, Any]] | None:
    if run_log.get("protocol_id") == "single_agent":
        return None
    termination = str(run_log.get("termination_reason") or "").strip().lower()
    final_output = str(run_log.get("final_output") or "").strip().lower()
    budget_terminated = termination == "max_total_tokens" or (
        "token budget" in final_output and "exhaust" in final_output
    )
    budget_pressure = (
        int(run_log.get("budget_skipped_call_count") or 0) > 0
        or int(run_log.get("budget_limited_call_count") or 0) > 0
    )
    repeated_pair = _most_repeated_message_pair(run_log)
    if not (budget_terminated and budget_pressure and repeated_pair):
        return None
    first_ref, second_ref, similarity = repeated_pair
    signal = (
        f"The multi-agent run repeated highly similar work in {first_ref} and {second_ref} "
        f"(similarity={similarity:.2f}), exhausted its token budget, skipped or limited later calls, "
        "and returned no usable final deliverable."
    )
    return [
        {
            "signal": signal,
            "trace_refs": [
                first_ref,
                second_ref,
                "run_metrics",
                "termination_reason",
                "final_output",
            ],
        }
    ]


def _relative_over_collaboration_from_log(
    run_log: dict[str, Any], *, baseline_tokens: float | None, relative_drop: float
) -> list[dict[str, Any]] | None:
    repeated_pair = _most_repeated_message_pair(run_log)
    total_tokens = float(run_log.get("total_tokens") or 0.0)
    if (
        baseline_tokens is None
        or baseline_tokens <= 0
        or total_tokens < 1.5 * baseline_tokens
        or repeated_pair is None
    ):
        return None
    first_ref, second_ref, similarity = repeated_pair
    signal = (
        f"Quality was {relative_drop:.1%} below the matching Single Agent baseline while the run used "
        f"{total_tokens / baseline_tokens:.1f}x its tokens and repeated highly similar work in "
        f"{first_ref} and {second_ref} (similarity={similarity:.2f})."
    )
    return [
        {
            "signal": signal,
            "trace_refs": [first_ref, second_ref, "run_metrics", "final_output"],
        }
    ]


def _most_repeated_message_pair(
    run_log: dict[str, Any], *, minimum_similarity: float = 0.72
) -> tuple[str, str, float] | None:
    messages: list[tuple[str, str]] = []
    for index, message in enumerate(run_log.get("intermediate_messages") or [], start=1):
        if not isinstance(message, dict):
            continue
        content = " ".join(str(message.get("content") or "").lower().split())
        if len(content) < 200:
            continue
        message_id = str(message.get("message_id") or f"m{index:03d}")
        messages.append((message_id, content))
    best: tuple[str, str, float] | None = None
    for index, (first_id, first_content) in enumerate(messages):
        for second_id, second_content in messages[index + 1 :]:
            similarity = SequenceMatcher(None, first_content, second_content).ratio()
            if similarity < minimum_similarity:
                continue
            if best is None or similarity > best[2]:
                best = (first_id, second_id, similarity)
    return best


def _deduplicate_strings(values: list[Any]) -> list[str]:
    unique: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in unique:
            unique.append(text)
    return unique


def _validated_evidence_assessment(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Judge output must include an evidence_assessment object")
    required = {
        "used_retrieved_sources",
        "required_evidence_satisfied",
        "citation_traceability",
        "evidence_score_cap",
        "evidence_cap_reasons",
        "unsupported_or_unverified_citations",
        "source_requirement_findings",
    }
    missing = sorted(required - set(value))
    if missing:
        raise ValueError(f"Judge evidence_assessment is missing keys: {missing}")
    if not isinstance(value["used_retrieved_sources"], bool):
        raise ValueError("Judge evidence_assessment.used_retrieved_sources must be boolean")
    if not isinstance(value["required_evidence_satisfied"], bool):
        raise ValueError("Judge evidence_assessment.required_evidence_satisfied must be boolean")
    citation_traceability = _clamp_float(value["citation_traceability"], 0.0, 1.0)
    evidence_score_cap = _clamp_float(value["evidence_score_cap"], 0.0, 1.0)
    evidence_cap_reasons = value["evidence_cap_reasons"]
    unsupported = value["unsupported_or_unverified_citations"]
    findings = value["source_requirement_findings"]
    if (
        not isinstance(evidence_cap_reasons, list)
        or not isinstance(unsupported, list)
        or not isinstance(findings, list)
    ):
        raise ValueError("Judge evidence assessment citation and finding fields must be lists")
    return {
        "used_retrieved_sources": value["used_retrieved_sources"],
        "required_evidence_satisfied": value["required_evidence_satisfied"],
        "citation_traceability": citation_traceability,
        "evidence_score_cap": evidence_score_cap,
        "evidence_cap_reasons": evidence_cap_reasons,
        "unsupported_or_unverified_citations": unsupported,
        "source_requirement_findings": findings,
    }


def _validated_criterion_scores(criteria: Any, value: Any) -> list[dict[str, Any]]:
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("Task evaluation_criteria must be a non-empty list")
    if not isinstance(value, list):
        raise ValueError("Judge output criterion_scores must be a list")
    expected_ids = [str(item.get("id")) for item in criteria if isinstance(item, dict)]
    rendered: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict) or item.get("id") is None:
            raise ValueError("Each Judge criterion score must be an object with an id")
        criterion_id = str(item["id"])
        if criterion_id in seen:
            raise ValueError(f"Judge returned duplicate criterion id: {criterion_id}")
        seen.add(criterion_id)
        try:
            score = float(item.get("score"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Judge criterion {criterion_id} has a non-numeric score") from exc
        if score not in {0.0, 0.5, 1.0}:
            raise ValueError(f"Judge criterion {criterion_id} score must be 0, 0.5, or 1")
        reason = item.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"Judge criterion {criterion_id} must include a non-empty reason")
        rendered.append({"id": criterion_id, "score": score, "reason": reason.strip()})
    missing = [criterion_id for criterion_id in expected_ids if criterion_id not in seen]
    extra = [criterion_id for criterion_id in seen if criterion_id not in expected_ids]
    if missing or extra or len(rendered) != len(expected_ids):
        raise ValueError(
            f"Judge criterion ids do not match task criteria (missing={missing}, extra={sorted(extra)})"
        )
    by_id = {item["id"]: item for item in rendered}
    return [by_id[criterion_id] for criterion_id in expected_ids]


def _criterion_completeness(criteria: Any, raw_scores: Any, *, fallback: Any) -> float:
    if not isinstance(criteria, list) or not criteria or not raw_scores:
        return _clamp_float(fallback, 0.0, 1.0)
    score_by_id: dict[str, float] = {}
    if isinstance(raw_scores, dict):
        for criterion_id, score in raw_scores.items():
            score_by_id[str(criterion_id)] = _clamp_float(score, 0.0, 1.0)
    elif isinstance(raw_scores, list):
        for item in raw_scores:
            if not isinstance(item, dict) or item.get("id") is None:
                continue
            score_by_id[str(item["id"])] = _clamp_float(item.get("score", 0.0), 0.0, 1.0)
    if not score_by_id:
        return _clamp_float(fallback, 0.0, 1.0)

    earned = 0.0
    possible = 0.0
    for criterion in criteria:
        if not isinstance(criterion, dict):
            continue
        weight = max(0.0, _clamp_float(criterion.get("weight", 1.0), 0.0, float("inf")))
        possible += weight
        earned += weight * score_by_id.get(str(criterion.get("id")), 0.0)
    if possible <= 0:
        return _clamp_float(fallback, 0.0, 1.0)
    return round(earned / possible, 4)


def _estimate_judge_cost(
    client: LLMClient,
    input_tokens: int,
    output_tokens: int,
) -> float:
    config = getattr(client, "effective_config", {}) or {}
    pricing = config.get("pricing_per_1m_tokens", {}) if isinstance(config, dict) else {}
    rates = pricing if isinstance(pricing, dict) else {}
    try:
        return round(
            (input_tokens / 1_000_000) * float(rates.get("input", 0.0))
            + (output_tokens / 1_000_000) * float(rates.get("output", 0.0)),
            8,
        )
    except (AttributeError, TypeError, ValueError):
        return 0.0


def _parse_json_object(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Judge output must be a JSON object")
    return parsed


def _run_label(run_log: dict[str, Any]) -> str:
    run_number = run_log.get("run_number")
    if isinstance(run_number, int) and run_number > 0:
        return f"run{run_number:02d}"
    match = re.search(r"(?:^|__)run(\d+)$", str(run_log.get("run_id") or ""))
    if match:
        return f"run{int(match.group(1)):02d}"
    return "run-unknown"


def _slug_component(value: Any) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value)).strip("-._").lower()
    return slug or "unknown"


def _clamp_float(value: Any, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = low
    return max(low, min(high, number))


def _clamp_int(value: Any, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = low
    return max(low, min(high, number))
