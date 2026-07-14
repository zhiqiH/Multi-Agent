from __future__ import annotations

import json
import unittest

from src.llm_client import LLMResponse
from src.protocols import PROTOCOLS, build_run_id, run_protocol
from src.tasks import DEFAULT_CANDIDATE_FIELDS, project_task


PRIVATE_SENTINELS = (
    "CANARY_EVALUATION_CRITERIA_7D21",
    "CANARY_GROUND_TRUTH_91AF",
    "CANARY_FAILURE_RISK_30C4",
    "CANARY_SCORING_RUBRIC_4BE8",
    "CANARY_REQUIRED_EVIDENCE_E662",
)


def _raw_task() -> dict:
    return {
        "task_id": "ISO-01",
        "category": "Isolation",
        "difficulty": "Hard",
        "author": "Test",
        "tool_requirement": "Prohibited",
        "prompt": "Return a concise public answer.",
        "required_output_format": "One paragraph.",
        "evaluation_criteria": [{"id": "C1", "criterion": PRIVATE_SENTINELS[0], "weight": 1}],
        "ground_truth": {"must_have": [PRIVATE_SENTINELS[1]]},
        "expected_failure_risks": [PRIVATE_SENTINELS[2]],
        "scoring_rubric": {"rule": PRIVATE_SENTINELS[3]},
        "required_evidence": PRIVATE_SENTINELS[4],
    }


class SpyClient:
    provider = "spy-provider"
    profile = "spy-candidate"
    model = "spy-model"
    effective_config = {
        "provider": provider,
        "profile": profile,
        "model": model,
        "agent_max_tokens": 100,
        "final_max_tokens": 120,
        "temperature": 0.0,
        "pricing_per_1m_tokens": {"default": {"input": 0.0, "output": 0.0}},
    }

    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    def chat(self, messages, *, response_format=None, max_tokens=None) -> LLMResponse:
        self.calls.append(messages)
        return LLMResponse(
            content="Public spy response.",
            input_tokens=5,
            output_tokens=3,
            total_tokens=8,
            raw={"spy": True},
            response_model=self.model,
        )


class ProtocolIsolationTests(unittest.TestCase):
    def test_every_protocol_payload_and_log_exclude_private_canaries(self) -> None:
        raw_task = _raw_task()
        candidate_task = project_task(raw_task, DEFAULT_CANDIDATE_FIELDS)
        metadata = {
            field: raw_task[field]
            for field in ("task_id", "category", "difficulty", "tool_requirement")
        }

        for protocol_id in PROTOCOLS:
            with self.subTest(protocol=protocol_id):
                client = SpyClient()
                log = run_protocol(
                    protocol_id,
                    candidate_task,
                    client,
                    client.effective_config,
                    task_metadata=metadata,
                    candidate_visible_fields=list(DEFAULT_CANDIDATE_FIELDS),
                )
                serialized = json.dumps(
                    {"api_calls": client.calls, "run_log": log},
                    ensure_ascii=False,
                    sort_keys=True,
                )
                self.assertTrue(client.calls)
                self.assertEqual(log["candidate_visible_fields"], list(DEFAULT_CANDIDATE_FIELDS))
                for sentinel in PRIVATE_SENTINELS:
                    self.assertNotIn(sentinel, serialized)

    def test_protocol_rejects_task_keys_outside_declared_view(self) -> None:
        raw_task = _raw_task()
        with self.assertRaisesRegex(ValueError, "Candidate task keys"):
            run_protocol(
                "single_agent",
                raw_task,
                SpyClient(),
                SpyClient.effective_config,
                task_metadata={"task_id": raw_task["task_id"]},
                candidate_visible_fields=list(DEFAULT_CANDIDATE_FIELDS),
            )

    def test_run_ids_separate_profiles_models_and_run_numbers(self) -> None:
        ids = {
            build_run_id("TA-01", "single_agent", "deepseek", "model-a", 1),
            build_run_id("TA-01", "single_agent", "openai", "model-a", 1),
            build_run_id("TA-01", "single_agent", "deepseek", "model-b", 1),
            build_run_id("TA-01", "single_agent", "deepseek", "model-a", 2),
        }
        self.assertEqual(len(ids), 4)


if __name__ == "__main__":
    unittest.main()
