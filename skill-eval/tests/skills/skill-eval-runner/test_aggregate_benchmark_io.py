"""Disk-backed tests for aggregate_benchmark.py functions that walk a workspace.

Separated from test_aggregate_benchmark.py (which tests pure functions) because
these build a temporary iteration directory mirroring the real eval layout:

    iteration-N/
      eval-<id>-<name>/
        current_skill/grading.json
        current_skill/outputs/metrics.json
        without_skill/grading.json
        ...

Covers build_runs (the grading.json → run-dict transform), the load-bearing
misplaced-grading detector/repair (a misplaced grading.json silently yields a
0% pass rate), and the skill-feedback rollup aggregation.

Stdlib unittest only.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_DIR = _REPO_ROOT / "skills" / "skill-eval-runner" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

import aggregate_benchmark as ab  # noqa: E402


class _Builder:
    def __init__(self, iter_dir: Path):
        self.iter_dir = iter_dir

    def eval_dir(self, eval_id: int, name: str) -> Path:
        d = self.iter_dir / f"eval-{eval_id}-{name}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def metadata(self, eval_dir: Path, **meta) -> None:
        (eval_dir / "eval_metadata.json").write_text(
            json.dumps(meta), encoding="utf-8"
        )

    def grading(self, eval_dir: Path, variant: str, passed: int, total: int,
                expectations=None, at_outputs=False) -> None:
        vdir = eval_dir / variant
        target = (vdir / "outputs") if at_outputs else vdir
        target.mkdir(parents=True, exist_ok=True)
        grading = {
            "summary": {
                "passed": passed,
                "failed": total - passed,
                "total": total,
                "pass_rate": round(passed / total, 4) if total else 0.0,
            },
            "expectations": expectations or [],
        }
        (target / "grading.json").write_text(json.dumps(grading), encoding="utf-8")

    def metrics(self, eval_dir: Path, variant: str, **payload) -> None:
        out = eval_dir / variant / "outputs"
        out.mkdir(parents=True, exist_ok=True)
        (out / "metrics.json").write_text(json.dumps(payload), encoding="utf-8")


class BuildRunsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.iter_dir = Path(self._tmp.name) / "iteration-1"
        self.iter_dir.mkdir(parents=True)
        self.b = _Builder(self.iter_dir)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_baseline_run_built_from_grading_and_metrics(self) -> None:
        ed = self.b.eval_dir(1, "alpha")
        self.b.metadata(ed, id=1, name="alpha", eval_mode="baseline")
        self.b.grading(ed, "current_skill", passed=4, total=5)
        self.b.metrics(
            ed, "current_skill",
            self_report={"total_tool_calls": 12, "total_steps": 5, "output_chars": 900},
            host_telemetry={"total_duration_seconds": 42.5, "total_tokens": 3800,
                            "input_tokens": 3000, "input_cached_tokens": 1200,
                            "input_cache_creation_tokens": 100,
                            "input_cache_write_tokens": 80, "output_tokens": 800,
                            "output_reasoning_tokens": 250,
                            "model": "m", "tool_errors": 0, "source": "debug_log"},
            metrics_source="debug_log",
        )
        runs = ab.build_runs(ab.discover_eval_dirs(self.iter_dir))
        cs = [r for r in runs if r["configuration"] == "current_skill"]
        self.assertEqual(len(cs), 1)
        result = cs[0]["result"]
        self.assertEqual(result["pass_rate"], 0.8)
        self.assertEqual(result["passed"], 4)
        self.assertEqual(result["time_seconds"], 42.5)
        self.assertEqual(result["tokens"], 3800)
        self.assertEqual(result["input_tokens"], 3000)
        self.assertEqual(result["input_cached_tokens"], 1200)
        self.assertEqual(result["input_cache_creation_tokens"], 100)
        self.assertEqual(result["input_cache_write_tokens"], 80)
        self.assertEqual(result["output_tokens"], 800)
        self.assertEqual(result["output_reasoning_tokens"], 250)
        self.assertEqual(result["total_tool_calls"], 12)  # from self_report
        self.assertEqual(result["metrics_source"], "debug_log")

    def test_missing_run_tokens_are_null_but_measured_zero_is_preserved(self) -> None:
        ed = self.b.eval_dir(1, "alpha")
        self.b.metadata(ed, id=1, name="alpha", eval_mode="baseline")
        self.b.grading(ed, "current_skill", passed=5, total=5)
        self.b.grading(ed, "without_skill", passed=4, total=5)
        self.b.metrics(
            ed,
            "current_skill",
            host_telemetry={"total_tokens": 0, "source": "wall_clock"},
        )
        self.b.metrics(
            ed,
            "without_skill",
            host_telemetry={"total_tokens": 0, "source": "notification"},
        )

        runs = ab.build_runs(ab.discover_eval_dirs(self.iter_dir))
        results = {run["configuration"]: run["result"] for run in runs}

        self.assertIsNone(results["current_skill"]["tokens"])
        self.assertEqual(results["without_skill"]["tokens"], 0)

    def test_host_telemetry_tool_calls_preferred(self) -> None:
        ed = self.b.eval_dir(1, "alpha")
        self.b.metadata(ed, id=1, name="alpha", eval_mode="baseline")
        self.b.grading(ed, "current_skill", passed=5, total=5)
        self.b.metrics(
            ed, "current_skill",
            self_report={"total_tool_calls": 99},
            host_telemetry={"total_tool_calls": 7, "source": "debug_log"},
        )
        runs = ab.build_runs(ab.discover_eval_dirs(self.iter_dir))
        self.assertEqual(runs[0]["result"]["total_tool_calls"], 7)  # log wins

    def test_missing_grading_skips_variant(self) -> None:
        ed = self.b.eval_dir(1, "alpha")
        self.b.metadata(ed, id=1, name="alpha", eval_mode="baseline")
        self.b.grading(ed, "current_skill", passed=5, total=5)
        # without_skill has no grading.json
        runs = ab.build_runs(ab.discover_eval_dirs(self.iter_dir))
        configs = {r["configuration"] for r in runs}
        self.assertEqual(configs, {"current_skill"})

    def test_expectations_copied(self) -> None:
        ed = self.b.eval_dir(1, "alpha")
        self.b.metadata(ed, id=1, name="alpha", eval_mode="baseline")
        self.b.grading(
            ed, "current_skill", passed=1, total=1,
            expectations=[{"text": "checks X", "passed": True,
                           "evidence": ["quote A", "quote B"]}],
        )
        runs = ab.build_runs(ab.discover_eval_dirs(self.iter_dir))
        exp = runs[0]["expectations"][0]
        self.assertEqual(exp["text"], "checks X")
        self.assertTrue(exp["passed"])
        self.assertEqual(exp["evidence"], ["quote A", "quote B"])


class MisplacedGradingTests(unittest.TestCase):
    """A grading.json under {variant}/outputs/ silently yields 0% — must be caught."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.iter_dir = Path(self._tmp.name) / "iteration-1"
        self.iter_dir.mkdir(parents=True)
        self.b = _Builder(self.iter_dir)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_detects_misplaced(self) -> None:
        ed = self.b.eval_dir(1, "alpha")
        self.b.grading(ed, "current_skill", passed=1, total=1, at_outputs=True)
        misplaced = ab.detect_misplaced_grading(ab.discover_eval_dirs(self.iter_dir))
        self.assertEqual(len(misplaced), 1)
        self.assertTrue(str(misplaced[0]).endswith("outputs/grading.json"))

    def test_correctly_placed_not_flagged(self) -> None:
        ed = self.b.eval_dir(1, "alpha")
        self.b.grading(ed, "current_skill", passed=1, total=1, at_outputs=False)
        misplaced = ab.detect_misplaced_grading(ab.discover_eval_dirs(self.iter_dir))
        self.assertEqual(misplaced, [])

    def test_not_flagged_when_correct_also_exists(self) -> None:
        ed = self.b.eval_dir(1, "alpha")
        self.b.grading(ed, "current_skill", passed=1, total=1, at_outputs=False)
        self.b.grading(ed, "current_skill", passed=1, total=1, at_outputs=True)
        misplaced = ab.detect_misplaced_grading(ab.discover_eval_dirs(self.iter_dir))
        self.assertEqual(misplaced, [])

    def test_fix_moves_to_variant_root(self) -> None:
        ed = self.b.eval_dir(1, "alpha")
        self.b.grading(ed, "current_skill", passed=1, total=1, at_outputs=True)
        misplaced = ab.detect_misplaced_grading(ab.discover_eval_dirs(self.iter_dir))
        moved = ab.fix_misplaced_grading(misplaced)
        self.assertEqual(len(moved), 1)
        self.assertTrue((ed / "current_skill" / "grading.json").exists())
        self.assertFalse((ed / "current_skill" / "outputs" / "grading.json").exists())


class SessionUsageTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.iter_dir = Path(self._tmp.name) / "iteration-1"
        self.iter_dir.mkdir(parents=True)
        self.builder = _Builder(self.iter_dir)
        eval_dir = self.builder.eval_dir(1, "alpha")
        self.builder.metadata(eval_dir, id=1, name="alpha", eval_mode="baseline")
        self.builder.grading(eval_dir, "current_skill", passed=4, total=5)
        self.builder.metrics(
            eval_dir,
            "current_skill",
            host_telemetry={
                "total_tokens": 15,
                "input_tokens": 10,
                "output_tokens": 5,
                "model": "gpt-run",
                "source": "notification",
            },
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _aggregate(self) -> tuple[int, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        argv = [
            "aggregate_benchmark.py",
            str(self.iter_dir),
            "--skill-name",
            "example-skill",
        ]
        with patch.object(ab.sys, "argv", argv), contextlib.redirect_stdout(
            stdout
        ), contextlib.redirect_stderr(stderr):
            result = ab.main()
        self.assertEqual(result, 0, stderr.getvalue())
        return result, stderr.getvalue()

    def _benchmark(self) -> dict:
        return json.loads((self.iter_dir / "benchmark.json").read_text(encoding="utf-8"))

    def test_valid_session_sidecar_is_separate_and_allowlisted(self) -> None:
        sidecar = {
            "input_tokens": 100,
            "input_cached_tokens": 40,
            "output_tokens": 25,
            "output_reasoning_tokens": 10,
            "ai_credits": 1.25,
            "premium_requests": 1,
            "duration_ms": 1200,
            "models": ["gpt-session"],
            "source": "copilot-cli",
            "request_body": "must not be copied into the benchmark",
        }
        (self.iter_dir / "session_usage.json").write_text(
            json.dumps(sidecar), encoding="utf-8"
        )

        _, stderr = self._aggregate()

        benchmark = self._benchmark()
        session_usage = benchmark["run_summary"]["session_usage"]
        self.assertNotIn("request_body", session_usage)
        self.assertEqual(session_usage["total_tokens"], 125)
        self.assertEqual(session_usage["input_tokens"], 100)
        self.assertEqual(session_usage["ai_credits"], 1.25)
        self.assertEqual(benchmark["run_summary"]["models"], ["gpt-run", "gpt-session"])
        self.assertEqual(benchmark["runs"][0]["result"]["tokens"], 15)
        self.assertEqual(benchmark["runs"][0]["result"]["input_tokens"], 10)
        self.assertNotIn("ai_credits", benchmark["runs"][0]["result"])
        self.assertEqual(stderr, "")

    def test_missing_session_sidecar_is_omitted(self) -> None:
        self._aggregate()

        benchmark = self._benchmark()

        self.assertNotIn("session_usage", benchmark["run_summary"])

    def test_invalid_session_sidecar_is_omitted_with_sanitized_warning(self) -> None:
        (self.iter_dir / "session_usage.json").write_text(
            json.dumps(
                {
                    "input_tokens": -1,
                    "models": ["gpt-session"],
                    "source": "copilot-cli",
                }
            ),
            encoding="utf-8",
        )

        _, stderr = self._aggregate()

        benchmark = self._benchmark()
        self.assertNotIn("session_usage", benchmark["run_summary"])
        self.assertIn("session_usage.json", stderr)
        self.assertNotIn("gpt-session", stderr)

    def test_malformed_session_sidecar_is_omitted_with_warning(self) -> None:
        (self.iter_dir / "session_usage.json").write_text(
            "{malformed", encoding="utf-8"
        )

        _, stderr = self._aggregate()

        benchmark = self._benchmark()
        self.assertNotIn("session_usage", benchmark["run_summary"])
        self.assertIn("session_usage.json", stderr)


class SkillFeedbackRollupTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.iter_dir = Path(self._tmp.name) / "iteration-1"
        self.iter_dir.mkdir(parents=True)
        self.b = _Builder(self.iter_dir)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_aggregates_missing_from_skill(self) -> None:
        ed = self.b.eval_dir(1, "alpha")
        self.b.metadata(ed, id=1, name="alpha")
        self.b.metrics(
            ed, "current_skill",
            user_notes={
                "skill_feedback": {
                    "missing_from_skill": [
                        {"topic": "no ratio path", "impact": "major",
                         "reference": "references/failure-modes.md#FM-1"}
                    ],
                    "ambiguous_instructions": [],
                    "broken_references": [],
                    "outdated_or_wrong": [],
                },
                "response_risks": [],
                "missing_inputs": [],
            },
        )
        rollup = ab._build_skill_feedback_rollup(
            ab.discover_eval_dirs(self.iter_dir), None
        )
        self.assertEqual(rollup["totals"]["missing_from_skill"], 1)
        self.assertEqual(rollup["by_impact"]["major"], 1)
        self.assertEqual(rollup["top_references"][0]["count"], 1)
        self.assertEqual(rollup["top_references"][0]["eval_ids"], [1])

    def test_response_risks_collected_from_both_variants(self) -> None:
        ed = self.b.eval_dir(1, "alpha")
        self.b.metadata(ed, id=1, name="alpha")
        for variant in ("current_skill", "without_skill"):
            self.b.metrics(
                ed, variant,
                user_notes={
                    "skill_feedback": {"missing_from_skill": [],
                                       "ambiguous_instructions": [],
                                       "broken_references": [],
                                       "outdated_or_wrong": []},
                    "response_risks": [
                        {"assumption": "a", "if_wrong": "b", "grounded_in": "c"}
                    ],
                    "missing_inputs": [],
                },
            )
        rollup = ab._build_skill_feedback_rollup(
            ab.discover_eval_dirs(self.iter_dir), None
        )
        self.assertEqual(len(rollup["response_risks"]), 2)
        variants = {r["variant"] for r in rollup["response_risks"]}
        self.assertEqual(variants, {"current_skill", "without_skill"})

    def test_empty_when_no_feedback(self) -> None:
        ed = self.b.eval_dir(1, "alpha")
        self.b.metadata(ed, id=1, name="alpha")
        self.b.metrics(ed, "current_skill", user_notes=ab_empty_notes())
        rollup = ab._build_skill_feedback_rollup(
            ab.discover_eval_dirs(self.iter_dir), None
        )
        self.assertEqual(sum(rollup["totals"].values()), 0)


def ab_empty_notes() -> dict:
    return {
        "skill_feedback": {
            "missing_from_skill": [], "ambiguous_instructions": [],
            "broken_references": [], "outdated_or_wrong": [],
        },
        "response_risks": [],
        "missing_inputs": [],
    }


if __name__ == "__main__":
    unittest.main()
