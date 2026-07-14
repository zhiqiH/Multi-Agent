from __future__ import annotations

import json
import re
from typing import Any, Union

from .deepseek_client import DeepSeekClient, MockLLMClient
from .prompts import scoring_prompt


Client = Union[DeepSeekClient, MockLLMClient]


def build_score_id(run_id: str, client: Client) -> str:
    profile = getattr(client, "profile", "legacy")
    model = getattr(client, "model", "unknown-evaluator")
    tag = _slug_component(f"{profile}-{model}")
    return f"{run_id}__judge-{tag}"


def score_run_log(run_log: dict[str, Any], task: dict[str, Any], client: Client) -> dict[str, Any]:
    messages = scoring_prompt(task, run_log.get("final_output", ""))
    response = client.chat(messages, response_format={"type": "json_object"}, max_tokens=700)
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
    total_tokens = max(1, int(run_log.get("total_tokens", 0)))
    quality_cost_ratio = round(overall_quality_score / total_tokens, 8)

    judge_provider = getattr(client, "provider", "unknown-provider")
    judge_profile = getattr(client, "profile", "legacy")
    judge_model = getattr(client, "model", "unknown-evaluator")
    judge_estimated_cost = _estimate_judge_cost(client, response.input_tokens, response.output_tokens)

    return {
        "score_id": build_score_id(run_log["run_id"], client),
        "run_id": run_log["run_id"],
        "task_id": run_log["task_id"],
        "protocol": run_log["protocol"],
        "protocol_id": run_log.get("protocol_id"),
        "candidate_provider": run_log.get("candidate_provider", "unknown-provider"),
        "candidate_profile": run_log.get("candidate_profile", "legacy"),
        "candidate_model": run_log.get("candidate_model") or run_log.get("model", "unknown-model"),
        "judge_provider": judge_provider,
        "judge_profile": judge_profile,
        "evaluator": judge_model,
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
        "estimated_cost": run_log.get("estimated_cost", 0.0),
        "message_count": run_log.get("message_count", 0),
        "communication_density": run_log.get("communication_density", 0.0),
        "quality_cost_ratio": quality_cost_ratio,
        "failure_type": parsed.get("failure_type") or "None",
        "notes": parsed.get("notes", ""),
        "scorer_input_tokens": response.input_tokens,
        "scorer_output_tokens": response.output_tokens,
        "scorer_total_tokens": response.total_tokens,
        "judge_estimated_cost": judge_estimated_cost,
        "total_estimated_cost": round(float(run_log.get("estimated_cost", 0.0) or 0.0) + judge_estimated_cost, 8),
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
    model = getattr(client, "model", "")
    rates = pricing.get(model) or pricing.get("default") or {"input": 0.0, "output": 0.0}
    try:
        return round(
            (input_tokens / 1_000_000) * float(rates.get("input", 0.0))
            + (output_tokens / 1_000_000) * float(rates.get("output", 0.0)),
            8,
        )
    except (AttributeError, TypeError, ValueError):
        return 0.0


def _slug_component(value: Any) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value)).strip("-._").lower()
    return slug or "unknown"


def _parse_json_object(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


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
