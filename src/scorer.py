from __future__ import annotations

import json
import re
from typing import Any, Union

from .llm_client import MockLLMClient, OpenAICompatibleClient
from .prompts import scoring_prompt


Client = Union[OpenAICompatibleClient, MockLLMClient]


def build_result_run_id(run_log: dict[str, Any]) -> str:
    components = [
        _slug_component(run_log["task_id"]),
        _slug_component(run_log.get("protocol_id") or run_log["protocol"]),
        _slug_component(run_log["agent_model"]),
        _run_label(run_log),
    ]
    return "__".join(components)


def build_score_id(run_log: dict[str, Any], client: Client) -> str:
    return f"{build_result_run_id(run_log)}__judge-{_slug_component(client.model)}"


def score_run_log(
    run_log: dict[str, Any],
    task: dict[str, Any],
    client: Client,
) -> dict[str, Any]:
    messages = scoring_prompt(task, run_log["final_output"])
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

    accuracy_raw = _clamp_int(parsed.get("accuracy_raw", 3), 1, 5)
    helpfulness_raw = _clamp_int(parsed.get("helpfulness_raw", 3), 1, 5)
    completeness_norm = _criterion_completeness(
        task.get("evaluation_criteria", []),
        parsed.get("criterion_scores"),
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
    overall_score_cap = _clamp_float(parsed.get("overall_score_cap", 1.0), 0.0, 1.0)
    overall_quality_score = round(min(uncapped_quality_score, overall_score_cap), 4)
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
        "overall_score_cap": overall_score_cap,
        "cap_reasons": parsed.get("cap_reasons") or [],
        "runtime_seconds": run_log.get("runtime_seconds", 0),
        "total_tokens": run_log.get("total_tokens", 0),
        "estimated_cost": agent_cost,
        "active_agent_count": run_log.get("active_agent_count", 1),
        "interaction_count": run_log.get("interaction_count", 1),
        "rounds_completed": run_log.get("rounds_completed", 1),
        "message_count": run_log.get("message_count", 0),
        "communication_density": run_log.get("communication_density", 0.0),
        "agreement_rate": run_log.get("agreement_rate"),
        "critique_acceptance_rate": run_log.get("critique_acceptance_rate"),
        "tool_call_count": run_log.get("tool_call_count", 0),
        "quality_token_ratio": quality_token_ratio,
        "quality_api_cost_ratio": (
            round(overall_quality_score / total_estimated_cost, 8) if total_estimated_cost > 0 else None
        ),
        "failure_type": parsed.get("failure_type") or "None",
        "detected_failure_risks": parsed.get("detected_failure_risks") or [],
        "notes": parsed.get("notes", ""),
        "scorer_input_tokens": response.input_tokens,
        "scorer_output_tokens": response.output_tokens,
        "scorer_total_tokens": response.total_tokens,
        "judge_finish_reason": response.finish_reason,
        "judge_estimated_cost": judge_estimated_cost,
        "total_estimated_cost": total_estimated_cost,
        "raw_evaluation": parsed,
    }


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


def _estimate_judge_cost(client: Client, input_tokens: int, output_tokens: int) -> float:
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
