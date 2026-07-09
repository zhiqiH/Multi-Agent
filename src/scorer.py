from __future__ import annotations

import json
from typing import Any, Union

from .deepseek_client import DeepSeekClient, MockLLMClient
from .prompts import scoring_prompt


Client = Union[DeepSeekClient, MockLLMClient]


def score_run_log(run_log: dict[str, Any], task: dict[str, Any], client: Client) -> dict[str, Any]:
    messages = scoring_prompt(task, run_log.get("final_output", ""))
    response = client.chat(messages, response_format={"type": "json_object"}, max_tokens=700)
    parsed = _parse_json_object(response.content)

    accuracy_raw = _clamp_int(parsed.get("accuracy_raw", 3), 1, 5)
    helpfulness_raw = _clamp_int(parsed.get("helpfulness_raw", 3), 1, 5)
    completeness_norm = _clamp_float(parsed.get("completeness_norm", 0.5), 0.0, 1.0)
    hallucination_rate = _clamp_float(parsed.get("hallucination_rate", 0.2), 0.0, 1.0)
    accuracy_norm = (accuracy_raw - 1) / 4
    helpfulness_norm = (helpfulness_raw - 1) / 4
    overall_quality_score = round(
        0.35 * accuracy_norm
        + 0.30 * completeness_norm
        + 0.20 * helpfulness_norm
        + 0.15 * (1 - hallucination_rate),
        4,
    )
    total_tokens = max(1, int(run_log.get("total_tokens", 0)))
    quality_cost_ratio = round(overall_quality_score / total_tokens, 8)

    return {
        "run_id": run_log["run_id"],
        "task_id": run_log["task_id"],
        "protocol": run_log["protocol"],
        "protocol_id": run_log.get("protocol_id"),
        "evaluator": getattr(client, "model", "unknown-evaluator"),
        "accuracy_raw": accuracy_raw,
        "accuracy_norm": round(accuracy_norm, 4),
        "completeness_norm": round(completeness_norm, 4),
        "helpfulness_raw": helpfulness_raw,
        "helpfulness_norm": round(helpfulness_norm, 4),
        "hallucination_rate": round(hallucination_rate, 4),
        "overall_quality_score": overall_quality_score,
        "runtime_seconds": run_log.get("runtime_seconds", 0),
        "total_tokens": run_log.get("total_tokens", 0),
        "estimated_cost": run_log.get("estimated_cost", 0.0),
        "message_count": run_log.get("message_count", 0),
        "communication_density": run_log.get("communication_density", 0.0),
        "quality_cost_ratio": quality_cost_ratio,
        "failure_type": parsed.get("failure_type", "None"),
        "notes": parsed.get("notes", ""),
        "scorer_input_tokens": response.input_tokens,
        "scorer_output_tokens": response.output_tokens,
        "raw_evaluation": parsed,
    }


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
