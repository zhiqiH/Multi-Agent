from __future__ import annotations

import json
import unittest

from src.llm_client import LLMResponse
from src.protocols import PROTOCOLS, build_condition_id, build_run_id, run_protocol
from src.tasks import DEFAULT_AGENT_FIELDS, project_task


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
    profile = "spy-agent"
    model = "spy-model"
    effective_config = {
        "provider": provider,
        "profile": profile,
        "model": model,
        "agent_max_tokens": 100,
        "final_max_tokens": 120,
        "temperature": 0.0,
        "pricing_per_1m_tokens": {"input": 0.0, "output": 0.0},
    }

    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    def chat(self, messages, *, response_format=None, max_tokens=None) -> LLMResponse:
        self.calls.append(messages)
        content = "1" if "Vote for the strongest proposal" in messages[-1]["content"] else "Public spy response."
        return LLMResponse(
            content=content,
            input_tokens=5,
            output_tokens=3,
            total_tokens=8,
            raw={"spy": True},
            response_model=self.model,
            finish_reason="stop",
        )


class ProtocolIsolationTests(unittest.TestCase):
    def test_pdf_eight_conditions_are_implemented(self) -> None:
        self.assertEqual(
            set(PROTOCOLS),
            {
                "single_agent",
                "unstructured_group_chat",
                "sequential_handoff",
                "shared_blackboard",
                "manager_worker",
                "debate",
                "voting",
                "dynamic_task_allocation",
            },
        )
        self.assertEqual(len(PROTOCOLS), 8)

    def test_every_protocol_payload_and_log_exclude_private_canaries(self) -> None:
        raw_task = _raw_task()
        agent_task = project_task(raw_task, DEFAULT_AGENT_FIELDS)
        metadata = {
            field: raw_task[field]
            for field in ("task_id", "category", "difficulty", "tool_requirement")
        }
        for protocol_id in PROTOCOLS:
            with self.subTest(protocol=protocol_id):
                client = SpyClient()
                log = run_protocol(
                    protocol_id,
                    agent_task,
                    client,
                    client.effective_config,
                    task_metadata=metadata,
                    agent_visible_fields=list(DEFAULT_AGENT_FIELDS),
                )
                serialized = json.dumps({"api_calls": client.calls, "run_log": log}, ensure_ascii=False)
                self.assertTrue(client.calls)
                self.assertFalse(log["errors"])
                self.assertEqual(log["agent_visible_fields"], list(DEFAULT_AGENT_FIELDS))
                self.assertEqual(log["record_type"], "agent_run")
                self.assertIn("termination_reason", log)
                self.assertIn("rounds_completed", log)
                for sentinel in PRIVATE_SENTINELS:
                    self.assertNotIn(sentinel, serialized)

    def test_voting_records_agreement(self) -> None:
        raw = _raw_task()
        log = run_protocol(
            "voting",
            project_task(raw, DEFAULT_AGENT_FIELDS),
            SpyClient(),
            SpyClient.effective_config,
            task_metadata={"task_id": raw["task_id"]},
            agent_visible_fields=list(DEFAULT_AGENT_FIELDS),
        )
        self.assertEqual(log["agreement_rate"], 1.0)
        self.assertEqual(log["termination_reason"], "vote_complete")

    def test_round_budget_changes_protocol_execution(self) -> None:
        raw = _raw_task()
        agent_task = project_task(raw, DEFAULT_AGENT_FIELDS)
        metadata = {"task_id": raw["task_id"]}

        manager = run_protocol(
            "manager_worker",
            agent_task,
            SpyClient(),
            SpyClient.effective_config,
            task_metadata=metadata,
            agent_visible_fields=list(DEFAULT_AGENT_FIELDS),
            protocol_config={"max_rounds": 1, "max_interactions": 2},
        )
        self.assertEqual(manager["rounds_completed"], 1)
        self.assertEqual(manager["interaction_count"], 2)

        debate = run_protocol(
            "debate",
            agent_task,
            SpyClient(),
            SpyClient.effective_config,
            task_metadata=metadata,
            agent_visible_fields=list(DEFAULT_AGENT_FIELDS),
            protocol_config={"max_rounds": 3, "max_interactions": 10},
        )
        self.assertEqual(debate["rounds_completed"], 3)
        self.assertEqual(debate["critique_count"], 6)

        voting = run_protocol(
            "voting",
            agent_task,
            SpyClient(),
            SpyClient.effective_config,
            task_metadata=metadata,
            agent_visible_fields=list(DEFAULT_AGENT_FIELDS),
            protocol_config={"max_rounds": 1, "max_interactions": 4},
        )
        self.assertEqual(voting["interaction_count"], 4)
        self.assertEqual(voting["termination_reason"], "max_rounds")

    def test_protocol_rejects_task_keys_outside_declared_view(self) -> None:
        raw_task = _raw_task()
        with self.assertRaisesRegex(ValueError, "Agent task keys"):
            run_protocol(
                "single_agent",
                raw_task,
                SpyClient(),
                SpyClient.effective_config,
                task_metadata={"task_id": raw_task["task_id"]},
                agent_visible_fields=list(DEFAULT_AGENT_FIELDS),
            )

    def test_run_ids_separate_conditions_models_and_replicates(self) -> None:
        condition_a = build_condition_id({"visibility": "blind"})
        condition_b = build_condition_id({"visibility": "open_book"})
        ids = {
            build_run_id("TA-01", "single_agent", "agent-a", "model-a", 1, condition_id=condition_a),
            build_run_id("TA-01", "single_agent", "agent-a", "model-a", 1, condition_id=condition_b),
            build_run_id("TA-01", "single_agent", "agent-b", "model-a", 1, condition_id=condition_a),
            build_run_id("TA-01", "single_agent", "agent-a", "model-b", 1, condition_id=condition_a),
            build_run_id("TA-01", "single_agent", "agent-a", "model-a", 2, condition_id=condition_a),
        }
        self.assertEqual(len(ids), 5)


if __name__ == "__main__":
    unittest.main()
