"""Tests for deterministic normalization of Copilot CLI final usage JSON."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_VIEWER_DIR = _REPO_ROOT / "skills" / "skill-eval-runner" / "eval-viewer"
_FIXTURE = (
    _REPO_ROOT / "tests" / "fixtures" / "copilot_usage" / "final-usage.json"
)
sys.path.insert(0, str(_VIEWER_DIR))

try:
    import copilot_usage as usage_module  # noqa: E402
except ModuleNotFoundError as exc:
    if exc.name != "copilot_usage":
        raise
    usage_module = None


class CopilotUsageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertIsNotNone(
            usage_module,
            "copilot_usage.py is not implemented yet",
        )
        self._tmp = tempfile.TemporaryDirectory()
        self.iteration_dir = Path(self._tmp.name) / "iteration-4"
        variant = self.iteration_dir / "eval-1" / "current_skill"
        outputs = variant / "outputs"
        outputs.mkdir(parents=True)
        (outputs / "response.md").write_text("synthetic response", encoding="utf-8")
        (self.iteration_dir / "iteration_config.json").write_text(
            json.dumps({"mode": "regression", "baseline_iteration": 1}),
            encoding="utf-8",
        )
        self.usage_path = self.iteration_dir / "copilot-usage.json"
        self.raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
        self.usage_path.write_text(json.dumps(self.raw), encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _normalize(self, raw: dict | None = None) -> dict:
        if raw is not None:
            self.usage_path.write_text(json.dumps(raw), encoding="utf-8")
        return usage_module.load_copilot_usage(self.usage_path, self.iteration_dir)

    def test_model_and_agent_views_are_not_double_counted(self) -> None:
        summary = self._normalize()

        self.assertEqual(summary["session"]["input_tokens"], 80)
        self.assertEqual(summary["session"]["output_tokens"], 25)
        self.assertEqual(summary["session"]["total_tokens"], 105)
        self.assertEqual(summary["eval_count"], 1)

    def test_subset_counters_do_not_change_total(self) -> None:
        summary = self._normalize()
        session = summary["session"]

        self.assertEqual(session["total_tokens"], 105)
        self.assertEqual(session["input_cached_tokens"], 34)
        self.assertEqual(session["input_cache_creation_tokens"], 5)
        self.assertEqual(session["input_cache_write_tokens"], 5)
        self.assertEqual(session["output_reasoning_tokens"], 4)

    def test_duplicate_comparator_records_group_by_eval_role(self) -> None:
        summary = self._normalize()
        comparators = [
            agent
            for agent in summary["eval_agents"]
            if agent["eval_id"] == "eval-1" and agent["role"] == "comparator"
        ]

        self.assertEqual(len(comparators), 1)
        self.assertEqual(comparators[0]["input_tokens"], 20)
        self.assertEqual(comparators[0]["output_tokens"], 10)
        self.assertEqual(comparators[0]["total_tokens"], 30)
        self.assertEqual(comparators[0]["total_api_duration_ms"], 300)
        self.assertNotIn("variant", comparators[0])

    def test_ambiguous_variant_is_not_assigned(self) -> None:
        without_skill = self.iteration_dir / "eval-1" / "without_skill" / "outputs"
        without_skill.mkdir(parents=True)
        (without_skill / "response.md").write_text(
            "synthetic baseline response", encoding="utf-8"
        )

        summary = self._normalize()
        executor = next(
            agent for agent in summary["eval_agents"] if agent["role"] == "executor"
        )

        self.assertNotIn("variant", executor)

    def test_unknown_agent_label_is_not_persisted(self) -> None:
        summary = self._normalize()
        serialized = json.dumps(summary, sort_keys=True)

        self.assertNotIn("custom helper with private task text", serialized)
        self.assertNotIn("raw-agent-id", serialized)
        self.assertNotIn("private-fixture.py", serialized)
        self.assertNotIn("synthetic prompt text", serialized)
        self.assertTrue(summary["other_agents"])

    def test_missing_or_invalid_counters_are_not_zero(self) -> None:
        raw = copy.deepcopy(self.raw)
        for metrics in raw["modelMetrics"].values():
            metrics["usage"]["inputTokens"] = True
            metrics["usage"]["outputTokens"] = -1

        summary = self._normalize(raw)
        session = summary["session"]

        self.assertNotIn("input_tokens", session)
        self.assertNotIn("output_tokens", session)
        self.assertNotIn("total_tokens", session)

    def test_unusable_usage_structure_raises_sanitized_error(self) -> None:
        self.usage_path.write_text(
            json.dumps({"diagnosticPrompt": "private fixture phrase"}),
            encoding="utf-8",
        )

        with self.assertRaises(usage_module.CopilotUsageError) as raised:
            usage_module.load_copilot_usage(self.usage_path, self.iteration_dir)

        self.assertNotIn("private fixture phrase", str(raised.exception))

    def test_normalization_is_deterministic(self) -> None:
        first = self._normalize()
        second = self._normalize()

        self.assertEqual(first, second)
        self.assertEqual(first["session"]["models"], ["gpt-5.6-luna", "gpt-6-luna"])


if __name__ == "__main__":
    unittest.main()
