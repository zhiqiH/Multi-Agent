from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.llm_client import LLMResponse  # noqa: E402
from src.scorer import build_score_id, score_run_log  # noqa: E402


def _judge_task() -> dict[str, Any]:
    return {
        "task_id": "TA-01",
        "category": "Technical Analysis",
        "difficulty": "Easy",
        "tool_requirement": "Prohibited",
        "prompt": "Explain a deterministic algorithm.",
        "required_output_format": "Short report.",
        "evaluation_criteria": [
            {"id": "correct", "criterion": "The algorithm is correct.", "weight": 2},
            {"id": "clear", "criterion": "The explanation is clear.", "weight": 1},
        ],
        "ground_truth": {"required": ["correct algorithm"]},
        "expected_failure_risks": ["unsupported claim"],
        "scoring_rubric": {"correct": "Required"},
        "required_evidence": "Self-contained reasoning.",
    }


def _run_log() -> dict[str, Any]:
    return {
        "run_id": "experiment__ta-01__single_agent__profile-model__c-abc__run01",
        "experiment_id": "experiment",
        "condition_id": "condition",
        "task_id": "TA-01",
        "category": "Technical Analysis",
        "protocol": "Single Agent",
        "protocol_id": "single_agent",
        "protocol_version": "3.1",
        "role_mode": "specialized",
        "evaluation_mode": "blind",
        "agent_provider": "deepseek",
        "agent_profile": "deepseek_v4_flash",
        "agent_model": "deepseek-v4-flash",
        "final_output": "A self-contained answer.",
        "total_tokens": 100,
        "estimated_cost": 0.01,
    }


class _JudgeClient:
    provider = "openai"
    profile = "judge_profile"
    model = "judge-model"

    def __init__(self, content: str, *, finish_reason: str = "stop") -> None:
        self.content = content
        self.finish_reason = finish_reason
        self.max_tokens_seen: int | None = None
        self.effective_config = {
            "judge_max_tokens": 4321,
            "pricing_per_1m_tokens": {"input": 1.0, "output": 2.0},
        }

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        response_format: dict[str, Any] | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        self.max_tokens_seen = max_tokens
        return LLMResponse(
            content=self.content,
            input_tokens=20,
            output_tokens=10,
            total_tokens=30,
            raw={},
            finish_reason=self.finish_reason,
        )


class ScorerTests(unittest.TestCase):
    def test_score_uses_judge_budget_and_canonical_agent_identity(self) -> None:
        payload = {
            "criterion_scores": [
                {"id": "correct", "score": 1, "reason": "covered"},
                {"id": "clear", "score": 0.5, "reason": "partly covered"},
            ],
            "accuracy_raw": 5,
            "completeness_norm": 0,
            "helpfulness_raw": 4,
            "hallucination_rate": 0,
            "overall_score_cap": 1,
            "failure_type": "None",
        }
        client = _JudgeClient(json.dumps(payload))

        score = score_run_log(_run_log(), _judge_task(), client, judge_condition_id="judge-condition")

        self.assertEqual(client.max_tokens_seen, 4321)
        self.assertEqual(score["agent_profile"], "deepseek_v4_flash")
        self.assertEqual(score["judge_condition_id"], "judge-condition")
        self.assertAlmostEqual(score["completeness_norm"], 5 / 6, places=4)
        self.assertIn("__jc-judge-condition", score["score_id"])
        self.assertGreater(score["judge_estimated_cost"], 0)

    def test_score_id_changes_with_judge_condition(self) -> None:
        client = _JudgeClient("{}")
        first = build_score_id("run", client, "condition-a")
        second = build_score_id("run", client, "condition-b")
        self.assertNotEqual(first, second)

    def test_empty_or_truncated_judge_output_fails_clearly(self) -> None:
        empty = _JudgeClient("", finish_reason="length")
        with self.assertRaisesRegex(RuntimeError, "Increase judge_max_tokens"):
            score_run_log(_run_log(), _judge_task(), empty, judge_condition_id="judge-condition")

        truncated = _JudgeClient("{}", finish_reason="length")
        with self.assertRaisesRegex(RuntimeError, "token limit"):
            score_run_log(_run_log(), _judge_task(), truncated, judge_condition_id="judge-condition")


if __name__ == "__main__":
    unittest.main()
