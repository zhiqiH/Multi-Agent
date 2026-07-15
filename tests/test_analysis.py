from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.analysis import aggregate_scores, write_scores_csv, write_summary_markdown


def _score(
    *,
    run_id: str,
    agent_profile: str,
    agent_model: str,
    judge_profile: str = "judge",
    judge_model: str = "judge-model",
    protocol: str = "Single Agent",
    protocol_id: str = "single_agent",
    quality: float = 0.8,
) -> dict[str, object]:
    return {
        "score_id": f"score::{run_id}::{judge_profile}",
        "run_id": run_id,
        "experiment_id": "exp-a",
        "condition_id": f"condition::{agent_profile}::{agent_model}::{protocol_id}",
        "judge_condition_id": f"judge-condition::{judge_profile}::{judge_model}",
        "task_id": "TA-01",
        "category": "Technical Analysis",
        "protocol": protocol,
        "protocol_id": protocol_id,
        "protocol_version": "3.1",
        "agent_provider": "test-provider",
        "agent_profile": agent_profile,
        "agent_model": agent_model,
        "evaluation_mode": "blind",
        "role_mode": "specialized",
        "judge_provider": "judge-provider",
        "judge_profile": judge_profile,
        "judge_model": judge_model,
        "overall_quality_score": quality,
        "accuracy_norm": quality,
        "completeness_norm": quality,
        "helpfulness_norm": quality,
        "hallucination_rate": 0.0,
        "runtime_seconds": 1.0,
        "total_tokens": 100,
        "estimated_cost": 0.01,
        "active_agent_count": 1,
        "interaction_count": 1,
        "rounds_completed": 1,
        "message_count": 1,
        "communication_density": 1.0,
        "tool_call_count": 0,
        "quality_token_ratio": quality / 100,
    }


class AggregateAnalysisTests(unittest.TestCase):
    def test_default_condition_grouping_keeps_models_and_judges_separate(self) -> None:
        scores = [
            _score(run_id="r1", agent_profile="agent-a", agent_model="model-a", quality=0.4),
            _score(run_id="r2", agent_profile="agent-b", agent_model="model-b", quality=0.8),
            _score(
                run_id="r3",
                agent_profile="agent-a",
                agent_model="model-a",
                judge_profile="judge-2",
                judge_model="judge-model-2",
                quality=1.0,
            ),
        ]
        rows = aggregate_scores(scores)
        self.assertEqual(len(rows), 3)
        self.assertEqual({row["agent_model"] for row in rows}, {"model-a", "model-b"})
        self.assertEqual({row["judge_model"] for row in rows}, {"judge-model", "judge-model-2"})

    def test_same_condition_is_averaged(self) -> None:
        scores = [
            _score(run_id="r1", agent_profile="agent-a", agent_model="model-a", quality=0.4),
            _score(run_id="r2", agent_profile="agent-a", agent_model="model-a", quality=0.8),
        ]
        rows = aggregate_scores(scores)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["runs"], 2)
        self.assertEqual(rows[0]["avg_overall_quality_score"], 0.6)

    def test_protocol_grouping_preserves_cross_condition_view(self) -> None:
        scores = [
            _score(run_id="r1", agent_profile="agent-a", agent_model="model-a", quality=0.4),
            _score(run_id="r2", agent_profile="agent-b", agent_model="model-b", quality=0.8),
        ]
        rows = aggregate_scores(scores, group_by="protocol")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["protocol"], "Single Agent")
        self.assertEqual(rows[0]["avg_overall_quality_score"], 0.6)

    def test_score_csv_contains_canonical_identity_and_raw_evaluation(self) -> None:
        score = _score(run_id="r1", agent_profile="agent-a", agent_model="model-a")
        score["raw_evaluation"] = {"criterion": "通过"}
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "scores.csv"
            write_scores_csv(path, [score])
            with path.open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
        for field in (
            "score_id",
            "run_id",
            "experiment_id",
            "condition_id",
            "judge_condition_id",
            "task_id",
            "protocol",
            "protocol_id",
            "agent_provider",
            "agent_profile",
            "agent_model",
            "judge_provider",
            "judge_profile",
            "judge_model",
        ):
            self.assertIn(field, row)
        self.assertEqual(json.loads(row["raw_evaluation"]), {"criterion": "通过"})

    def test_condition_summary_uses_agent_terminology(self) -> None:
        scores = [_score(run_id="r1", agent_profile="agent-a", agent_model="model-a")]
        rows = aggregate_scores(scores)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "summary.md"
            write_summary_markdown(path, rows, scores, group_by="condition")
            summary = path.read_text(encoding="utf-8")
        self.assertIn("Group Averages", summary)
        self.assertIn("test-provider/agent-a/model-a", summary)
        self.assertIn("judge-provider/judge/judge-model", summary)

    def test_protocol_summary_does_not_invent_mixed_model_identity(self) -> None:
        scores = [
            _score(run_id="r1", agent_profile="agent-a", agent_model="model-a"),
            _score(run_id="r2", agent_profile="agent-b", agent_model="model-b"),
        ]
        rows = aggregate_scores(scores, group_by="protocol")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "summary.md"
            write_summary_markdown(path, rows, scores, group_by="protocol")
            summary = path.read_text(encoding="utf-8")
        self.assertIn("| Protocol | Runs |", summary)
        self.assertNotIn("| Agent | Judge |", summary)


if __name__ == "__main__":
    unittest.main()
