from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.analysis import aggregate_by_protocol, aggregate_scores, write_scores_csv, write_summary_markdown


def _score(
    *,
    run_id: str,
    candidate_profile: str,
    candidate_model: str,
    judge_profile: str = "judge",
    evaluator: str = "judge-model",
    protocol: str = "Single Agent",
    protocol_id: str = "single_agent",
    quality: float = 0.8,
) -> dict[str, object]:
    return {
        "score_id": f"score::{run_id}::{judge_profile}",
        "run_id": run_id,
        "task_id": "TA-01",
        "protocol": protocol,
        "protocol_id": protocol_id,
        "candidate_provider": "test-provider",
        "candidate_profile": candidate_profile,
        "candidate_model": candidate_model,
        "judge_provider": "judge-provider",
        "judge_profile": judge_profile,
        "evaluator": evaluator,
        "overall_quality_score": quality,
        "accuracy_norm": quality,
        "completeness_norm": quality,
        "helpfulness_norm": quality,
        "hallucination_rate": 0.0,
        "runtime_seconds": 1.0,
        "total_tokens": 100,
        "estimated_cost": 0.01,
        "message_count": 1,
        "communication_density": 1.0,
        "quality_cost_ratio": quality / 100,
    }


class AggregateAnalysisTests(unittest.TestCase):
    def test_default_condition_grouping_keeps_models_and_judges_separate(self) -> None:
        scores = [
            _score(run_id="r1", candidate_profile="candidate-a", candidate_model="model-a", quality=0.4),
            _score(run_id="r2", candidate_profile="candidate-b", candidate_model="model-b", quality=0.8),
            _score(
                run_id="r3",
                candidate_profile="candidate-a",
                candidate_model="model-a",
                judge_profile="judge-2",
                evaluator="judge-model-2",
                quality=1.0,
            ),
        ]

        rows = aggregate_scores(scores)

        self.assertEqual(len(rows), 3)
        self.assertEqual({row["candidate_model"] for row in rows}, {"model-a", "model-b"})
        self.assertEqual({row["evaluator"] for row in rows}, {"judge-model", "judge-model-2"})

    def test_same_condition_is_averaged(self) -> None:
        scores = [
            _score(run_id="r1", candidate_profile="candidate-a", candidate_model="model-a", quality=0.4),
            _score(run_id="r2", candidate_profile="candidate-a", candidate_model="model-a", quality=0.8),
        ]

        rows = aggregate_scores(scores)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["runs"], 2)
        self.assertEqual(rows[0]["avg_overall_quality_score"], 0.6)

    def test_protocol_grouping_preserves_legacy_behavior(self) -> None:
        scores = [
            _score(run_id="r1", candidate_profile="candidate-a", candidate_model="model-a", quality=0.4),
            _score(run_id="r2", candidate_profile="candidate-b", candidate_model="model-b", quality=0.8),
        ]

        rows = aggregate_by_protocol(scores)

        self.assertEqual(rows, aggregate_scores(scores, group_by="protocol"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["protocol"], "Single Agent")
        self.assertEqual(rows[0]["avg_overall_quality_score"], 0.6)

    def test_legacy_scores_receive_explicit_identity_fallbacks(self) -> None:
        rows = aggregate_scores(
            [{"run_id": "legacy-run", "protocol": "Single Agent", "overall_quality_score": 0.75}]
        )

        self.assertEqual(rows[0]["candidate_provider"], "unknown")
        self.assertEqual(rows[0]["candidate_profile"], "legacy")
        self.assertEqual(rows[0]["candidate_model"], "unknown")
        self.assertEqual(rows[0]["judge_provider"], "unknown")
        self.assertEqual(rows[0]["judge_profile"], "legacy")
        self.assertEqual(rows[0]["evaluator"], "unknown")
        self.assertEqual(rows[0]["protocol_id"], "legacy")

    def test_score_csv_contains_all_identity_fields_and_serializes_raw_evaluation(self) -> None:
        score = _score(run_id="r1", candidate_profile="candidate-a", candidate_model="model-a")
        score["raw_evaluation"] = {"criterion": "通过"}
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "scores.csv"
            write_scores_csv(path, [score])
            with path.open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))

        for field in (
            "score_id",
            "run_id",
            "task_id",
            "protocol",
            "protocol_id",
            "candidate_provider",
            "candidate_profile",
            "candidate_model",
            "judge_provider",
            "judge_profile",
            "evaluator",
        ):
            self.assertIn(field, row)
        self.assertEqual(json.loads(row["raw_evaluation"]), {"criterion": "通过"})

    def test_condition_summary_includes_candidate_and_judge(self) -> None:
        scores = [_score(run_id="r1", candidate_profile="candidate-a", candidate_model="model-a")]
        rows = aggregate_scores(scores)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "summary.md"
            write_summary_markdown(path, rows, scores, group_by="condition")
            summary = path.read_text(encoding="utf-8")

        self.assertIn("Condition Averages", summary)
        self.assertIn("test-provider/candidate-a/model-a", summary)
        self.assertIn("judge-provider/judge/judge-model", summary)


if __name__ == "__main__":
    unittest.main()
