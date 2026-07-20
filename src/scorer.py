from __future__ import annotations

import json
import re
from collections import Counter
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
    failure_type, failure_evidence, failure_classification_source = (
        _apply_deterministic_failure_rules(
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
            "protocol_signals": _protocol_signals(run_log),
        },
        "intermediate_messages": messages,
    }


def _protocol_signals(run_log: dict[str, Any]) -> dict[str, Any]:
    if run_log.get("protocol_id") != "voting":
        return {}
    messages = [
        message
        for message in run_log.get("intermediate_messages") or []
        if isinstance(message, dict)
    ]
    proposals = [message for message in messages if message.get("channel") == "private_answer"]
    ballots = [message for message in messages if message.get("channel") == "private_ballot"]
    ballot_values: list[int] = []
    ballot_records: list[dict[str, Any]] = []
    for message in ballots:
        match = re.search(r"\b(\d+)\b", str(message.get("content") or ""))
        value = int(match.group(1)) if match else None
        if value is not None and 1 <= value <= len(proposals):
            ballot_values.append(value)
        ballot_records.append(
            {
                "message_id": message.get("message_id"),
                "sender": message.get("sender"),
                "selected_proposal": value,
            }
        )
    counts = Counter(ballot_values)
    winner = (
        min(range(1, len(proposals) + 1), key=lambda index: (-counts[index], index))
        if proposals and ballot_values
        else None
    )
    final_output = str(run_log.get("final_output") or "").strip()
    final_matches = next(
        (
            index
            for index, proposal in enumerate(proposals, start=1)
            if str(proposal.get("content") or "").strip() == final_output
        ),
        None,
    )
    return {
        "proposal_message_ids": [proposal.get("message_id") for proposal in proposals],
        "ballots": ballot_records,
        "ballot_counts": {str(index): counts[index] for index in range(1, len(proposals) + 1)},
        "computed_winner_proposal": winner,
        "final_matches_proposal": final_matches,
        "unanimous_valid_ballots": bool(ballot_values)
        and len(set(ballot_values)) == 1,
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

    message_refs = {
        str(message.get("message_id") or f"m{index:03d}")
        for index, message in enumerate(run_log.get("intermediate_messages") or [], start=1)
        if isinstance(message, dict)
    }
    valid_refs = {
        "final_output",
        "run_metrics",
        "termination_reason",
        "run_errors",
        "role_usage",
        "protocol_signals",
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
    if run_log.get("protocol_id") == "single_agent":
        raise ValueError("Single-agent runs cannot be assigned a multi-agent collaboration failure")
    if not evidence:
        raise ValueError("A non-None failure_type requires observable failure_evidence")
    if "final_output" not in referenced:
        raise ValueError("A collaboration failure must cite final_output to show material downstream impact")
    if raw_failure_type in {
        "Communication Failure",
        "Hallucination Propagation",
        "Premature Consensus",
    } and not referenced.intersection(message_refs):
        raise ValueError(f"{raw_failure_type} must cite at least one recorded intermediate message")
    if raw_failure_type == "Over-Collaboration":
        if "run_metrics" not in referenced:
            raise ValueError(
                "Over-Collaboration must cite run_metrics in addition to repeated work and final impact"
            )
        if len(referenced.intersection(message_refs)) < 2:
            raise ValueError("Over-Collaboration must cite at least two repeated intermediate messages")
    return raw_failure_type, evidence


def _apply_deterministic_failure_rules(
    failure_type: str,
    failure_evidence: list[dict[str, Any]],
    run_log: dict[str, Any],
    task: dict[str, Any],
    evidence_audit: dict[str, Any],
    response_audit: dict[str, Any],
) -> tuple[str, list[dict[str, Any]], str]:
    """Correct only collaboration failures that are directly proven by the run trace."""

    if failure_type != NO_FAILURE or run_log.get("protocol_id") != "voting":
        return failure_type, failure_evidence, "judge"
    triggered_rules = set(response_audit.get("triggered_hard_fail_rules") or [])
    if not triggered_rules:
        return failure_type, failure_evidence, "judge"

    messages = [
        message
        for message in run_log.get("intermediate_messages") or []
        if isinstance(message, dict)
    ]
    proposals = [message for message in messages if message.get("channel") == "private_answer"]
    ballots = [message for message in messages if message.get("channel") == "private_ballot"]
    final_output = str(run_log.get("final_output") or "").strip()
    selected_index = next(
        (
            index
            for index, proposal in enumerate(proposals, start=1)
            if str(proposal.get("content") or "").strip() == final_output
        ),
        None,
    )
    if selected_index is None or not ballots:
        return failure_type, failure_evidence, "judge"

    alternatives: list[tuple[int, dict[str, Any]]] = []
    for index, proposal in enumerate(proposals, start=1):
        if index == selected_index:
            continue
        audit = build_response_audit(task, str(proposal.get("content") or ""), evidence_audit)
        alternative_rules = set(audit.get("triggered_hard_fail_rules") or [])
        if not triggered_rules.intersection(alternative_rules):
            alternatives.append((index, proposal))
    if not alternatives:
        return failure_type, failure_evidence, "judge"

    selected = proposals[selected_index - 1]
    alternative_index, alternative = alternatives[0]
    ballot_refs = [
        str(ballot.get("message_id"))
        for ballot in ballots
        if ballot.get("message_id")
    ]
    selected_ref = str(selected.get("message_id") or f"proposal-{selected_index}")
    alternative_ref = str(alternative.get("message_id") or f"proposal-{alternative_index}")
    signal = (
        f"Voting selected proposal {selected_index} ({selected_ref}), whose final output triggered "
        f"the benchmark hard-fail rule, even though proposal {alternative_index} "
        f"({alternative_ref}) avoided that rule; the recorded ballots converged on the failing proposal."
    )
    return (
        "Premature Consensus",
        [
            {
                "signal": signal,
                "trace_refs": list(
                    dict.fromkeys(
                        [
                            alternative_ref,
                            selected_ref,
                            *ballot_refs,
                            "protocol_signals",
                            "final_output",
                        ]
                    )
                ),
            }
        ],
        "deterministic_voting_audit",
    )


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
