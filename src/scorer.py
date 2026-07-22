from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from typing import Any

from .evidence import build_evidence_audit, compact_evidence_audit
from .failure_taxonomy import (
    COLLABORATION_FAILURE_TYPES,
    NO_FAILURE,
    OTHER_FAILURE,
    OTHER_FAILURE_SUBTYPES,
    allowed_collaboration_failure_types,
    allowed_failure_types,
    normalize_failure_type,
    normalize_failure_types,
)
from .llm_client import LLMClient
from .prompts import failure_analysis_prompt, scoring_prompt
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


def _request_json_response(
    client: LLMClient,
    messages: list[dict[str, Any]],
    *,
    max_tokens: int,
    label: str,
) -> tuple[Any, dict[str, Any]]:
    response = client.chat(
        messages,
        response_format={"type": "json_object"},
        max_tokens=max_tokens,
    )
    if not response.content.strip():
        detail = (
            f"finish_reason={response.finish_reason or 'unknown'}, "
            f"output_tokens={response.output_tokens}"
        )
        raise RuntimeError(f"{label} returned no visible JSON content ({detail}).")
    if response.finish_reason == "length":
        raise RuntimeError(f"{label} reached its token limit before returning complete JSON.")
    return response, _parse_json_object(response.content)


def _reject_cross_scope_fields(
    payload: dict[str, Any], *, forbidden: set[str], label: str
) -> None:
    unexpected = sorted(forbidden.intersection(payload))
    if unexpected:
        raise ValueError(f"{label} returned fields outside its isolated scope: {unexpected}")


def score_run_log(
    run_log: dict[str, Any],
    task: dict[str, Any],
    client: LLMClient,
) -> dict[str, Any]:
    effective_config = dict(getattr(client, "effective_config", {}) or {})
    judge_max_tokens = int(effective_config["judge_max_tokens"])
    failure_analysis_max_tokens = int(effective_config["failure_analysis_max_tokens"])

    # This request is constructed and completed before any protocol trace is built.
    quality_response, parsed = _request_json_response(
        client,
        scoring_prompt(task, run_log["final_output"]),
        max_tokens=judge_max_tokens,
        label="Quality Judge",
    )
    _reject_cross_scope_fields(
        parsed,
        forbidden={
            "failure_type",
            "failure_types",
            "failure_evidence",
            "failure_checks",
            "other_failure",
        },
        label="Quality Judge",
    )
    evidence_assessment = _validated_evidence_assessment(parsed.get("evidence_assessment"))
    judge_criterion_scores = _validated_criterion_scores(
        task.get("evaluation_criteria", []), parsed.get("criterion_scores")
    )

    evidence_audit = build_evidence_audit(run_log, task, run_log["final_output"])
    response_audit = build_response_audit(task, run_log["final_output"], evidence_audit)
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

    # Failure analysis starts only after every quality component and cap is fixed.
    failure_trace = _build_failure_trace(run_log)
    failure_response = None
    failure_parsed: dict[str, Any] = {}
    failure_analysis_error: str | None = None
    failure_analyzer_assessments: list[dict[str, Any]] = []
    failure_analysis_warnings: list[str] = []
    try:
        failure_response, failure_parsed = _request_json_response(
            client,
            failure_analysis_prompt(task, run_log["final_output"], failure_trace),
            max_tokens=failure_analysis_max_tokens,
            label="Failure analyzer",
        )
        _reject_cross_scope_fields(
            failure_parsed,
            forbidden={
                "criterion_scores",
                "evidence_assessment",
                "overall_score_cap",
                "cap_reasons",
                "accuracy_raw",
                "completeness_norm",
                "helpfulness_raw",
                "hallucination_rate",
            },
            label="Failure analyzer",
        )
        failure_analyzer_assessments, failure_analysis_warnings = _validated_failure_assessment(
            failure_parsed, run_log
        )
    except Exception as exc:  # Keep an already-computed blind quality score.
        failure_analysis_error = str(exc)
    failure_analyzer_types = (
        _assessment_types(failure_analyzer_assessments)
        if failure_analysis_error is None
        else []
    )
    failure_types, failure_assessments, failure_classification_source = (
        _apply_log_failure_rules(
            failure_analyzer_assessments,
            run_log,
            task,
            evidence_audit,
            response_audit,
        )
    )
    if failure_analysis_error and failure_classification_source == "failure_analyzer":
        failure_classification_source = "failure_analyzer_error_fallback"

    judge_model = client.model
    quality_judge_estimated_cost = _estimate_judge_cost(
        client, quality_response.input_tokens, quality_response.output_tokens
    )
    failure_analyzer_estimated_cost = (
        _estimate_judge_cost(
            client, failure_response.input_tokens, failure_response.output_tokens
        )
        if failure_response is not None
        else 0.0
    )
    judge_estimated_cost = round(
        quality_judge_estimated_cost + failure_analyzer_estimated_cost, 8
    )
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
        "failure_types": failure_types,
        "failure_count": sum(
            failure_type != NO_FAILURE for failure_type in failure_types
        ),
        "failure_assessments": failure_assessments,
        "failure_classification_source": failure_classification_source,
        "failure_analyzer_types": failure_analyzer_types,
        "failure_analyzer_assessments": failure_analyzer_assessments,
        "failure_analysis_warnings": failure_analysis_warnings,
        "failure_analysis_status": "error" if failure_analysis_error else "success",
        "failure_analysis_error": failure_analysis_error,
        "detected_failure_risks": parsed.get("detected_failure_risks") or [],
        "judge_evidence_assessment": evidence_assessment,
        "evidence_audit": compact_evidence_audit(evidence_audit),
        "notes": parsed.get("notes", ""),
        "quality_judge_input_tokens": quality_response.input_tokens,
        "quality_judge_output_tokens": quality_response.output_tokens,
        "quality_judge_total_tokens": quality_response.total_tokens,
        "quality_judge_finish_reason": quality_response.finish_reason,
        "quality_judge_estimated_cost": quality_judge_estimated_cost,
        "failure_analyzer_input_tokens": (
            failure_response.input_tokens if failure_response is not None else 0
        ),
        "failure_analyzer_output_tokens": (
            failure_response.output_tokens if failure_response is not None else 0
        ),
        "failure_analyzer_total_tokens": (
            failure_response.total_tokens if failure_response is not None else 0
        ),
        "failure_analyzer_finish_reason": (
            failure_response.finish_reason if failure_response is not None else "error"
        ),
        "failure_analyzer_estimated_cost": failure_analyzer_estimated_cost,
        "scorer_input_tokens": quality_response.input_tokens
        + (failure_response.input_tokens if failure_response is not None else 0),
        "scorer_output_tokens": quality_response.output_tokens
        + (failure_response.output_tokens if failure_response is not None else 0),
        "scorer_total_tokens": quality_response.total_tokens
        + (failure_response.total_tokens if failure_response is not None else 0),
        "judge_estimated_cost": judge_estimated_cost,
        "total_estimated_cost": total_estimated_cost,
        "raw_quality_evaluation": parsed,
        "raw_failure_evaluation": failure_parsed,
    }


def _build_failure_trace(run_log: dict[str, Any]) -> dict[str, Any]:
    expected_actions = _expected_actions_from_run_prompts(run_log)
    messages: list[dict[str, Any]] = []
    for index, raw_message in enumerate(run_log.get("intermediate_messages") or [], start=1):
        if not isinstance(raw_message, dict):
            continue
        action_key = (
            str(raw_message.get("sender") or ""),
            raw_message.get("round"),
            str(raw_message.get("channel") or ""),
        )
        expected_action = raw_message.get("expected_action")
        if not expected_action:
            candidates = expected_actions.get(action_key) or []
            expected_action = candidates.pop(0) if candidates else None
        messages.append(
            {
                "message_id": str(raw_message.get("message_id") or f"m{index:03d}"),
                "sender": raw_message.get("sender"),
                "recipients": raw_message.get("recipients") or [],
                "round": raw_message.get("round"),
                "channel": raw_message.get("channel"),
                "phase": raw_message.get("phase") or raw_message.get("channel"),
                "message_kind": raw_message.get("message_kind") or raw_message.get("channel"),
                "expected_action": expected_action,
                "content": str(raw_message.get("content") or ""),
                "finish_reason": raw_message.get("finish_reason"),
                "input_tokens": raw_message.get("input_tokens", 0),
                "output_tokens": raw_message.get("output_tokens", 0),
                "total_tokens": raw_message.get("total_tokens", 0),
                **(
                    {"proposal_index": raw_message.get("proposal_index")}
                    if raw_message.get("proposal_index") is not None
                    else {}
                ),
                **(
                    {
                        "parsed_proposal_index": raw_message.get("parsed_proposal_index"),
                        "ballot_valid": raw_message.get("ballot_valid"),
                    }
                    if raw_message.get("ballot_valid") is not None
                    else {}
                ),
            }
        )
    protocol_id = run_log.get("protocol_id")
    protocol_artifacts = dict(run_log.get("protocol_artifacts") or {})
    if protocol_id == "voting":
        protocol_artifacts.setdefault("voting", _annotate_voting_trace(messages))
    return {
        "execution_summary": {
            "protocol": run_log.get("protocol"),
            "protocol_id": protocol_id,
            "is_multi_agent": protocol_id != "single_agent",
            "allowed_failure_types": list(allowed_failure_types(protocol_id)),
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
            "protocol_artifacts": protocol_artifacts,
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
            "protocol_artifacts",
            "tool_execution",
        ],
    }


def _expected_actions_from_run_prompts(
    run_log: dict[str, Any],
) -> dict[tuple[str, Any, str], list[str]]:
    """Recover expected actions from old logs that predate explicit message metadata."""

    actions: dict[tuple[str, Any, str], list[str]] = {}
    pattern = re.compile(
        r"\nInstruction:\n(.*?)\n\nReturn only the content for your role\.",
        flags=re.DOTALL,
    )
    for prompt_record in run_log.get("prompts") or []:
        if not isinstance(prompt_record, dict):
            continue
        user_content = ""
        for message in prompt_record.get("messages") or []:
            if isinstance(message, dict) and message.get("role") == "user":
                user_content = str(message.get("content") or "")
        match = pattern.search(user_content)
        if not match:
            continue
        key = (
            str(prompt_record.get("agent_role") or ""),
            prompt_record.get("round"),
            str(prompt_record.get("channel") or ""),
        )
        actions.setdefault(key, []).append(match.group(1).strip())
    return actions


def _annotate_voting_trace(messages: list[dict[str, Any]]) -> dict[str, Any]:
    proposals = [message for message in messages if message.get("channel") == "private_answer"]
    ballots = [message for message in messages if message.get("channel") == "private_ballot"]
    for proposal_index, message in enumerate(proposals, start=1):
        message["message_kind"] = "proposal"
        message.setdefault("proposal_index", proposal_index)
    valid_ballots: list[int] = []
    for message in ballots:
        match = re.search(r"\b(\d+)\b", str(message.get("content") or ""))
        selected = int(match.group(1)) if match else None
        if selected is not None and not 1 <= selected <= len(proposals):
            selected = None
        message["message_kind"] = "ballot"
        message.setdefault("parsed_proposal_index", selected)
        message.setdefault("ballot_valid", selected is not None)
        if selected is not None:
            valid_ballots.append(selected)
    counts = {index: valid_ballots.count(index) for index in range(1, len(proposals) + 1)}
    winner = (
        min(counts, key=lambda index: (-counts[index], index))
        if counts
        else None
    )
    return {
        "proposal_count": len(proposals),
        "ballots_are_proposal_indices": True,
        "valid_ballots": valid_ballots,
        "invalid_ballot_count": len(ballots) - len(valid_ballots),
        "vote_counts_by_proposal_index": {
            str(index): count for index, count in counts.items()
        },
        "winning_proposal_index": winner,
        "tie_break": "lowest_proposal_index",
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
) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate exhaustive per-category checks and derive positive assessments.

    The analyzer never chooses No Failure. It must check every collaboration
    category permitted for this protocol, after which this function derives all
    positive labels and applies the residual-only rule for Other Failure.
    """

    protocol_id = run_log.get("protocol_id")
    required_types = allowed_collaboration_failure_types(protocol_id)
    raw_checks = parsed.get("failure_checks")
    if not isinstance(raw_checks, list):
        raise ValueError("Failure analyzer output must include failure_checks as a list")
    returned_types: list[str] = []
    for check in raw_checks:
        if not isinstance(check, dict):
            raise ValueError("Each failure_checks item must be an object")
        try:
            returned_types.append(normalize_failure_type(check.get("failure_type")))
        except ValueError as exc:
            raise ValueError(
                f"Failure analyzer returned an unknown failure check: {check.get('failure_type')!r}"
            ) from exc
    if (
        len(returned_types) != len(required_types)
        or len(set(returned_types)) != len(returned_types)
        or set(returned_types) != set(required_types)
    ):
        raise ValueError(
            "Failure analyzer must check every protocol-allowed collaboration type exactly once "
            f"Expected {list(required_types)}, got {returned_types}."
        )
    checks_by_type = dict(zip(returned_types, raw_checks))

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
        "protocol_artifacts",
        "tool_execution",
    }
    valid_refs.update(message_refs)
    assessments: list[dict[str, Any]] = []
    warnings: list[str] = []
    for failure_type in required_types:
        check = checks_by_type[failure_type]
        detected = _strict_bool(check.get("detected"), f"{failure_type}.detected")
        reason = str(check.get("reason") or "").strip()
        if not reason:
            raise ValueError(f"{failure_type} requires a concise reason for its yes/no decision")
        signal = str(check.get("signal") or "").strip()
        raw_refs = check.get("trace_refs")
        recovered = _strict_bool(check.get("recovered"), f"{failure_type}.recovered")
        final_output_impacted = _strict_bool(
            check.get("final_output_impacted"),
            f"{failure_type}.final_output_impacted",
        )
        if not detected:
            if signal or raw_refs or recovered or final_output_impacted:
                warnings.append(
                    f"Ignored evidence/impact fields from detected=false check: {failure_type}"
                )
            continue
        refs = _validated_trace_refs(
            raw_refs,
            valid_refs,
            label=failure_type,
            maximum=5,
        )
        if not signal:
            raise ValueError(f"{failure_type} detected=true requires a non-empty signal")
        _reject_self_negating_positive_signal(signal, failure_type)
        if final_output_impacted and "final_output" not in refs:
            raise ValueError(
                f"{failure_type} claims final_output_impacted=true but does not cite final_output"
            )
        _validate_failure_evidence_gate(
            failure_type,
            refs,
            message_records,
            run_log,
        )
        assessments.append(
            {
                "failure_type": failure_type,
                "reason": reason,
                "failure_evidence": [{"signal": signal, "trace_refs": refs}],
                "recovered": recovered,
                "final_output_impacted": final_output_impacted,
                "source": "failure_analyzer",
            }
        )

    raw_other = parsed.get("other_failure")
    if not isinstance(raw_other, dict):
        raise ValueError("Failure analyzer output must include other_failure as an object")
    other_detected = _strict_bool(raw_other.get("detected"), "other_failure.detected")
    other_reason = str(raw_other.get("reason") or "").strip()
    if not other_reason:
        raise ValueError("other_failure requires a concise reason for its yes/no decision")
    if assessments:
        if other_detected:
            warnings.append(
                "Suppressed Other Failure because at least one collaboration failure was detected"
            )
        return assessments, warnings
    if not other_detected:
        if raw_other.get("subtype") or raw_other.get("signal") or raw_other.get("trace_refs"):
            warnings.append("Ignored residual fields from other_failure.detected=false")
        return [], warnings

    subtype = str(raw_other.get("subtype") or "").strip()
    if subtype not in OTHER_FAILURE_SUBTYPES:
        raise ValueError(
            f"Other Failure subtype must be one of {OTHER_FAILURE_SUBTYPES}; got {subtype!r}"
        )
    signal = str(raw_other.get("signal") or "").strip()
    if not signal:
        raise ValueError("Other Failure detected=true requires a non-empty signal")
    _reject_self_negating_positive_signal(signal, OTHER_FAILURE)
    refs = _validated_trace_refs(
        raw_other.get("trace_refs"),
        valid_refs,
        label=OTHER_FAILURE,
        maximum=5,
    )
    _validate_other_failure_gate(subtype, refs, run_log)
    return [
        {
            "failure_type": OTHER_FAILURE,
            "other_subtype": subtype,
            "reason": other_reason,
            "failure_evidence": [{"signal": signal, "trace_refs": refs}],
            "recovered": False,
            "final_output_impacted": "final_output" in refs,
            "source": "failure_analyzer",
        }
    ], warnings


def _strict_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"Failure analyzer {label} must be a boolean")
    return value


def _reject_self_negating_positive_signal(signal: str, failure_type: str) -> None:
    normalized = " ".join(signal.lower().split())
    self_negating_patterns = (
        r"\bno (?:observable |dominant |collaboration |protocol-level )?failures?\b",
        r"\bnone (?:was |were )?(?:observed|detected|found)\b",
        r"\bfailures? (?:was |were )?not (?:observed|detected|found)\b",
        r"\bdoes not (?:show|exhibit|constitute) (?:a )?failures?\b",
    )
    if any(re.search(pattern, normalized) for pattern in self_negating_patterns):
        raise ValueError(
            f"{failure_type} detected=true has a self-negating signal: {signal!r}"
        )


def _validated_trace_refs(
    raw_refs: Any,
    valid_refs: set[str],
    *,
    label: str,
    maximum: int,
) -> list[str]:
    if not isinstance(raw_refs, list) or not raw_refs or not all(
        isinstance(ref, str) for ref in raw_refs
    ):
        raise ValueError(f"{label} requires a non-empty trace_refs list")
    refs = list(dict.fromkeys(ref.strip() for ref in raw_refs if ref.strip()))
    if len(refs) > maximum:
        raise ValueError(f"{label} may cite at most {maximum} trace references")
    unknown_refs = sorted(set(refs) - valid_refs)
    if unknown_refs:
        raise ValueError(f"Failure analyzer contains unknown trace_refs: {unknown_refs}")
    return refs


def _validate_failure_evidence_gate(
    failure_type: str,
    refs: list[str],
    message_records: dict[str, dict[str, Any]],
    run_log: dict[str, Any],
) -> None:
    message_refs = set(message_records)
    referenced_messages = set(refs).intersection(message_refs)
    if failure_type == "Coordination Failure":
        if not referenced_messages or len(refs) < 2:
            raise ValueError(
                "Coordination Failure must cite a recorded assignment/dependency and its consequence"
            )
    elif failure_type == "Communication Failure":
        if not referenced_messages or len(refs) < 2:
            raise ValueError(
                "Communication Failure must cite upstream information and a downstream loss or distortion"
            )
    elif failure_type == "Role Confusion":
        final_role_mismatch = {
            "protocol_artifacts",
            "final_output",
        }.issubset(refs)
        if not referenced_messages and not final_role_mismatch:
            raise ValueError(
                "Role Confusion must cite an Agent message or the recorded final-call expectation and final output"
            )
    elif failure_type in {"Hallucination Propagation", "Premature Consensus"}:
        if len(referenced_messages) < 2:
            raise ValueError(f"{failure_type} must cite at least two recorded Agent messages")
    elif failure_type == "Over-Collaboration":
        if "run_metrics" not in refs or len(referenced_messages) < 2:
            raise ValueError(
                "Over-Collaboration must cite run_metrics and at least two redundant messages"
            )
    elif failure_type == "Manager Bottleneck":
        if run_log.get("protocol_id") != "manager_worker":
            raise ValueError("Manager Bottleneck is only valid for manager_worker")
        manager_refs = {
            ref
            for ref, message in message_records.items()
            if "manager" in str(message.get("sender") or "").lower()
        }
        if not referenced_messages.intersection(manager_refs):
            raise ValueError("Manager Bottleneck must cite a recorded Manager message")
        if not (referenced_messages - manager_refs):
            raise ValueError("Manager Bottleneck must cite an affected downstream Agent message")
    elif failure_type == "Noise Accumulation" and len(referenced_messages) < 2:
        raise ValueError(
            "Noise Accumulation must cite at least two context-visible Agent messages"
        )


def _validate_other_failure_gate(
    subtype: str, refs: list[str], run_log: dict[str, Any]
) -> None:
    required_refs = {
        "tool_failure": {"tool_execution"},
        "runtime_error": {"run_errors", "termination_reason"},
        "malformed_output": {"final_output"},
        "single_agent_answer_error": {"final_output"},
        "unmapped_non_collaboration_failure": {
            "final_output",
            "run_errors",
            "termination_reason",
        },
    }
    if subtype == "single_agent_answer_error" and run_log.get("protocol_id") != "single_agent":
        raise ValueError("single_agent_answer_error is only valid for single_agent")
    expected = required_refs.get(subtype)
    if expected and not set(refs).intersection(expected):
        raise ValueError(
            f"Other Failure subtype {subtype} must cite one of {sorted(expected)}"
        )


def _assessment_types(assessments: list[dict[str, Any]]) -> list[str]:
    return normalize_failure_types(
        [assessment.get("failure_type") for assessment in assessments]
    )


def _apply_log_failure_rules(
    analyzer_assessments: list[dict[str, Any]],
    run_log: dict[str, Any],
    task: dict[str, Any],
    evidence_audit: dict[str, Any],
    response_audit: dict[str, Any],
) -> tuple[list[str], list[dict[str, Any]], str]:
    """Merge semantic and deterministic findings without collapsing labels."""

    del task, response_audit
    allowed_collaboration = set(
        allowed_collaboration_failure_types(run_log.get("protocol_id"))
    )
    by_type: dict[str, dict[str, Any]] = {}
    for assessment in analyzer_assessments:
        try:
            failure_type = normalize_failure_type(assessment.get("failure_type"))
        except ValueError:
            continue
        if failure_type in allowed_collaboration or failure_type == OTHER_FAILURE:
            by_type.setdefault(failure_type, dict(assessment))

    over_collaboration = _budget_over_collaboration_from_log(run_log)
    if over_collaboration is not None and "Over-Collaboration" in allowed_collaboration:
        _merge_assessment(
            by_type,
            {
                "failure_type": "Over-Collaboration",
                "failure_evidence": over_collaboration,
                "recovered": False,
                "final_output_impacted": True,
                "source": "deterministic_log_audit",
            },
        )

    tool_failure = _tool_failure_from_log(run_log, evidence_audit)
    collaboration_types = [
        failure_type
        for failure_type in COLLABORATION_FAILURE_TYPES
        if failure_type in by_type and failure_type in allowed_collaboration
    ]
    if collaboration_types:
        # Other is residual and never coexists with a collaboration label.
        by_type.pop(OTHER_FAILURE, None)
        assessments = [by_type[failure_type] for failure_type in collaboration_types]
    elif tool_failure is not None:
        assessments = [
            {
                "failure_type": OTHER_FAILURE,
                "other_subtype": "tool_failure",
                "failure_evidence": tool_failure,
                "recovered": False,
                "final_output_impacted": True,
                "source": "deterministic_log_audit",
            }
        ]
    elif OTHER_FAILURE in by_type:
        assessments = [by_type[OTHER_FAILURE]]
    else:
        assessments = []

    failure_types = _assessment_types(assessments)
    sources = {
        str(assessment.get("source") or "failure_analyzer")
        for assessment in assessments
    }
    if not sources:
        source = "failure_analyzer"
    elif sources == {"failure_analyzer"}:
        source = "failure_analyzer"
    elif sources == {"deterministic_log_audit"}:
        source = "deterministic_log_audit"
    else:
        source = "hybrid_log_audit"
    return failure_types, assessments, source


def _merge_assessment(
    by_type: dict[str, dict[str, Any]], incoming: dict[str, Any]
) -> None:
    failure_type = str(incoming["failure_type"])
    existing = by_type.get(failure_type)
    if existing is None:
        by_type[failure_type] = incoming
        return
    evidence = list(existing.get("failure_evidence") or [])
    evidence.extend(incoming.get("failure_evidence") or [])
    existing["failure_evidence"] = evidence
    existing["source"] = "failure_analyzer+deterministic_log_audit"
    existing["recovered"] = bool(existing.get("recovered"))
    existing["final_output_impacted"] = bool(
        existing.get("final_output_impacted") or incoming.get("final_output_impacted")
    )


def apply_log_failure_analysis(
    scores: list[dict[str, Any]],
    run_logs_by_id: dict[str, dict[str, Any]],
) -> int:
    """Re-audit every classification from its raw log, independently of quality scores."""

    analyzed = 0
    for score in scores:
        run_log = run_logs_by_id.get(str(score.get("run_id") or ""))
        if run_log is None:
            continue
        analyzer_assessments = score.get("failure_analyzer_assessments")
        if not isinstance(analyzer_assessments, list):
            analyzer_assessments = _legacy_analyzer_assessments(score)
        failure_types, failure_assessments, source = _apply_log_failure_rules(
            analyzer_assessments,
            run_log,
            {},
            score,
            {},
        )
        if (
            score.get("failure_analysis_status") == "error"
            and source == "failure_analyzer"
        ):
            source = "failure_analyzer_error_fallback"

        score.update(
            {
                "failure_types": failure_types,
                "failure_count": sum(
                    failure_type != NO_FAILURE for failure_type in failure_types
                ),
                "failure_assessments": failure_assessments,
                "failure_classification_source": source,
            }
        )
        for legacy_field in (
            "failure_type",
            "failure_evidence",
            "failure_analyzer_type",
            "failure_analyzer_evidence",
            "judge_failure_type",
            "judge_failure_evidence",
        ):
            score.pop(legacy_field, None)
        analyzed += 1
    return analyzed


def _legacy_analyzer_assessments(score: dict[str, Any]) -> list[dict[str, Any]]:
    """Read old score records only long enough to migrate them in memory."""

    raw_type = score.get("failure_analyzer_type", score.get("judge_failure_type"))
    try:
        failure_type = normalize_failure_type(raw_type)
    except ValueError:
        return []
    if failure_type == NO_FAILURE:
        return []
    evidence = score.get(
        "failure_analyzer_evidence",
        score.get("judge_failure_evidence", score.get("failure_evidence")),
    )
    if not isinstance(evidence, list):
        evidence = []
    return [
        {
            "failure_type": failure_type,
            "failure_evidence": evidence,
            "recovered": False,
            "final_output_impacted": True,
            "source": "failure_analyzer",
        }
    ]

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
