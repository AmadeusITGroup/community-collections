"""Unit tests for aggregate_benchmark.py pure functions.

Covers the statistics, severity bucketing, summary/delta math, comparator
tallying, contradiction + regression detection, note normalization, and the
skill-feedback rollup — the logic-heavy core of the benchmark aggregator.

These functions take plain dicts/lists (the in-memory shape of the JSON
files), so they test without touching disk. The few that read a directory
tree (build_runs, build_per_eval_comparisons) are exercised in
test_aggregate_benchmark_io.py with a temp workspace.

Stdlib unittest only — no third-party runtime dependency, matching
test_eval_paths.py.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_DIR = _REPO_ROOT / "skills" / "skill-eval-runner" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

import aggregate_benchmark as ab  # noqa: E402


def _run(eval_id, config, pass_rate, time_s=10.0, tokens=1000,
         tool_calls=None, steps=None, name="eval"):
    """Build a minimal run dict in the shape build_runs() emits."""
    result = {
        "pass_rate": pass_rate,
        "passed": int(round(pass_rate * 5)),
        "failed": 5 - int(round(pass_rate * 5)),
        "total": 5,
        "time_seconds": time_s,
        "tokens": tokens,
    }
    if tool_calls is not None:
        result["total_tool_calls"] = tool_calls
    if steps is not None:
        result["total_steps"] = steps
    return {
        "eval_id": eval_id,
        "eval_name": name,
        "configuration": config,
        "result": result,
        "expectations": [],
    }


class CalculateStatsTests(unittest.TestCase):
    def test_empty_returns_zeros(self) -> None:
        self.assertEqual(
            ab.calculate_stats([]),
            {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0},
        )

    def test_single_value_zero_stddev(self) -> None:
        stats = ab.calculate_stats([4.0])
        self.assertEqual(stats["mean"], 4.0)
        self.assertEqual(stats["stddev"], 0.0)
        self.assertEqual(stats["min"], 4.0)
        self.assertEqual(stats["max"], 4.0)

    def test_sample_stddev_uses_n_minus_one(self) -> None:
        # values [2, 4]: mean 3, sample variance = ((1)+(1))/(2-1) = 2 → sqrt(2)
        stats = ab.calculate_stats([2.0, 4.0])
        self.assertEqual(stats["mean"], 3.0)
        self.assertAlmostEqual(stats["stddev"], 2.0 ** 0.5, places=4)
        self.assertEqual(stats["min"], 2.0)
        self.assertEqual(stats["max"], 4.0)

    def test_rounds_to_four_places(self) -> None:
        stats = ab.calculate_stats([1.0, 2.0])
        # 1.5 mean, stddev sqrt(0.5) = 0.70710678... → 0.7071
        self.assertEqual(stats["stddev"], 0.7071)


class SeverityFromGapTests(unittest.TestCase):
    def test_blocking_threshold(self) -> None:
        self.assertEqual(ab._severity_from_gap(0.5), "blocking")
        self.assertEqual(ab._severity_from_gap(0.9), "blocking")

    def test_major_threshold(self) -> None:
        self.assertEqual(ab._severity_from_gap(0.3), "major")
        self.assertEqual(ab._severity_from_gap(0.49), "major")

    def test_minor_threshold(self) -> None:
        self.assertEqual(ab._severity_from_gap(0.0), "minor")
        self.assertEqual(ab._severity_from_gap(0.29), "minor")

    def test_uses_absolute_value(self) -> None:
        self.assertEqual(ab._severity_from_gap(-0.6), "blocking")
        self.assertEqual(ab._severity_from_gap(-0.35), "major")


class BuildRunSummaryTests(unittest.TestCase):
    def test_delta_is_current_minus_without(self) -> None:
        runs = [
            _run(1, "current_skill", 0.8),
            _run(2, "current_skill", 1.0),
            _run(1, "without_skill", 0.4),
            _run(2, "without_skill", 0.2),
        ]
        summary = ab.build_run_summary(runs)
        self.assertEqual(summary["current_skill"]["pass_rate"]["mean"], 0.9)
        self.assertEqual(summary["without_skill"]["pass_rate"]["mean"], 0.3)
        # delta formatted string, sign-prefixed
        self.assertEqual(summary["delta"]["pass_rate"], "+0.6")

    def test_negative_delta_has_no_plus(self) -> None:
        runs = [
            _run(1, "current_skill", 0.2),
            _run(1, "without_skill", 0.8),
        ]
        summary = ab.build_run_summary(runs)
        self.assertEqual(summary["delta"]["pass_rate"], "-0.6")

    def test_empty_previous_skill_bucket_omitted(self) -> None:
        runs = [_run(1, "current_skill", 1.0), _run(1, "without_skill", 0.5)]
        summary = ab.build_run_summary(runs)
        self.assertNotIn("previous_skill", summary)

    def test_optional_tool_calls_only_when_present(self) -> None:
        runs = [_run(1, "current_skill", 1.0, tool_calls=7, steps=3)]
        summary = ab.build_run_summary(runs)
        self.assertIn("tool_calls", summary["current_skill"])
        self.assertEqual(summary["current_skill"]["tool_calls"]["mean"], 7.0)
        self.assertIn("steps", summary["current_skill"])

    def test_tool_calls_absent_when_not_reported(self) -> None:
        runs = [_run(1, "current_skill", 1.0)]  # no tool_calls/steps
        summary = ab.build_run_summary(runs)
        self.assertNotIn("tool_calls", summary["current_skill"])
        self.assertNotIn("steps", summary["current_skill"])


class BuildComparisonsTests(unittest.TestCase):
    """build_comparisons reads comparison.json from each eval dir."""

    def setUp(self) -> None:
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _eval_with_comparison(self, name: str, comp: dict) -> Path:
        import json
        d = self.root / name
        d.mkdir(parents=True)
        (d / "comparison.json").write_text(json.dumps(comp), encoding="utf-8")
        return d

    def test_tallies_baseline_winners(self) -> None:
        dirs = [
            self._eval_with_comparison(
                "eval-1-a",
                {"comparison_mode": "baseline", "winner_variant": "current_skill"},
            ),
            self._eval_with_comparison(
                "eval-2-b",
                {"comparison_mode": "baseline", "winner_variant": "without_skill"},
            ),
            self._eval_with_comparison(
                "eval-3-c",
                {"comparison_mode": "baseline", "winner_variant": "tie"},
            ),
        ]
        out = ab.build_comparisons(dirs)
        self.assertEqual(out["current_skill_wins"], 1)
        self.assertEqual(out["without_skill_wins"], 1)
        self.assertEqual(out["ties"], 1)
        # No regression keys when no regression comparisons present.
        self.assertNotIn("current_wins", out)

    def test_regression_tally_adds_keys(self) -> None:
        dirs = [
            self._eval_with_comparison(
                "eval-1-a",
                {"comparison_mode": "regression", "winner_variant": "current_skill"},
            ),
            self._eval_with_comparison(
                "eval-2-b",
                {"comparison_mode": "regression", "winner_variant": "previous_skill"},
            ),
        ]
        out = ab.build_comparisons(dirs)
        self.assertEqual(out["current_wins"], 1)
        self.assertEqual(out["previous_wins"], 1)
        self.assertEqual(out["regression_ties"], 0)

    def test_missing_comparison_file_ignored(self) -> None:
        empty = self.root / "eval-9-none"
        empty.mkdir(parents=True)
        out = ab.build_comparisons([empty])
        self.assertEqual(out["current_skill_wins"], 0)
        self.assertEqual(out["ties"], 0)


class ContradictionTests(unittest.TestCase):
    def test_grader_favours_current_but_comparator_disagrees(self) -> None:
        runs = [
            _run(1, "current_skill", 0.9),
            _run(1, "without_skill", 0.3),  # gap +0.6 → grader loves current
        ]
        comps = [
            {
                "eval_id": 1,
                "eval_name": "e1",
                "comparison_mode": "baseline",
                "winner_variant": "without_skill",  # comparator disagrees
                "reasoning": "tie-ish",
                "assignment": {"A": "current_skill", "B": "without_skill"},
                "rubric_scores": {"A": 6.0, "B": 7.0},
            }
        ]
        out = ab.build_contradictions(runs, comps)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["grader_preferred"], "current_skill")
        self.assertEqual(out[0]["severity"], "blocking")  # gap 0.6
        # rubric scores resolved back to variant names via assignment
        self.assertEqual(out[0]["rubric_scores"]["current_skill"], 6.0)
        self.assertEqual(out[0]["rubric_scores"]["without_skill"], 7.0)

    def test_tie_winner_counts_as_disagreement(self) -> None:
        runs = [_run(1, "current_skill", 0.9), _run(1, "without_skill", 0.3)]
        comps = [{
            "eval_id": 1, "eval_name": "e1", "comparison_mode": "baseline",
            "winner_variant": "tie", "assignment": {}, "rubric_scores": {},
        }]
        out = ab.build_contradictions(runs, comps)
        self.assertEqual(len(out), 1)

    def test_small_gap_is_not_a_contradiction(self) -> None:
        runs = [_run(1, "current_skill", 0.6), _run(1, "without_skill", 0.5)]
        comps = [{
            "eval_id": 1, "eval_name": "e1", "comparison_mode": "baseline",
            "winner_variant": "without_skill", "assignment": {}, "rubric_scores": {},
        }]
        self.assertEqual(ab.build_contradictions(runs, comps), [])

    def test_agreement_is_not_a_contradiction(self) -> None:
        runs = [_run(1, "current_skill", 0.9), _run(1, "without_skill", 0.3)]
        comps = [{
            "eval_id": 1, "eval_name": "e1", "comparison_mode": "baseline",
            "winner_variant": "current_skill", "assignment": {}, "rubric_scores": {},
        }]
        self.assertEqual(ab.build_contradictions(runs, comps), [])

    def test_sorted_by_severity(self) -> None:
        runs = [
            _run(1, "current_skill", 0.7), _run(1, "without_skill", 0.4),   # gap .3 major
            _run(2, "current_skill", 1.0), _run(2, "without_skill", 0.2),   # gap .8 blocking
        ]
        comps = [
            {"eval_id": 1, "eval_name": "e1", "comparison_mode": "baseline",
             "winner_variant": "without_skill", "assignment": {}, "rubric_scores": {}},
            {"eval_id": 2, "eval_name": "e2", "comparison_mode": "baseline",
             "winner_variant": "without_skill", "assignment": {}, "rubric_scores": {}},
        ]
        out = ab.build_contradictions(runs, comps)
        self.assertEqual([c["eval_id"] for c in out], [2, 1])  # blocking first

    def test_regression_mode_uses_previous_skill_alternate(self) -> None:
        runs = [
            _run(1, "current_skill", 0.9),
            _run(1, "previous_skill", 0.3),
        ]
        comps = [{
            "eval_id": 1, "eval_name": "e1", "comparison_mode": "regression",
            "winner_variant": "previous_skill", "assignment": {}, "rubric_scores": {},
        }]
        out = ab.build_contradictions(runs, comps)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["alternate_variant"], "previous_skill")


class SkillRegressionTests(unittest.TestCase):
    def test_baseline_regression_bucketed(self) -> None:
        runs = [_run(1, "current_skill", 0.4), _run(1, "without_skill", 0.9)]
        comps = [{
            "eval_id": 1, "eval_name": "e1", "comparison_mode": "baseline",
            "winner_variant": "without_skill", "reasoning": "baseline clearer",
        }]
        out = ab.build_skill_regressions(runs, comps)
        self.assertEqual(len(out["vs_baseline"]), 1)
        self.assertEqual(out["vs_baseline"][0]["pass_rate_delta"], -0.5)
        self.assertEqual(out["vs_previous"], [])

    def test_previous_regression_bucketed(self) -> None:
        runs = [_run(1, "current_skill", 0.5), _run(1, "previous_skill", 0.8)]
        comps = [{
            "eval_id": 1, "eval_name": "e1", "comparison_mode": "regression",
            "winner_variant": "previous_skill", "reasoning": "regressed",
        }]
        out = ab.build_skill_regressions(runs, comps)
        self.assertEqual(len(out["vs_previous"]), 1)
        self.assertEqual(out["vs_baseline"], [])

    def test_current_winner_not_a_regression(self) -> None:
        runs = [_run(1, "current_skill", 0.9), _run(1, "without_skill", 0.3)]
        comps = [{
            "eval_id": 1, "eval_name": "e1", "comparison_mode": "baseline",
            "winner_variant": "current_skill",
        }]
        out = ab.build_skill_regressions(runs, comps)
        self.assertEqual(out["vs_baseline"], [])
        self.assertEqual(out["vs_previous"], [])

    def test_sorted_worst_first(self) -> None:
        runs = [
            _run(1, "current_skill", 0.6), _run(1, "without_skill", 0.7),  # -0.1
            _run(2, "current_skill", 0.2), _run(2, "without_skill", 0.9),  # -0.7
        ]
        comps = [
            {"eval_id": 1, "eval_name": "e1", "comparison_mode": "baseline",
             "winner_variant": "without_skill"},
            {"eval_id": 2, "eval_name": "e2", "comparison_mode": "baseline",
             "winner_variant": "without_skill"},
        ]
        out = ab.build_skill_regressions(runs, comps)
        self.assertEqual([e["eval_id"] for e in out["vs_baseline"]], [2, 1])


class NormalizeNoteTests(unittest.TestCase):
    def test_string_becomes_observation(self) -> None:
        note = ab._normalize_note("just a string")
        self.assertEqual(note["category"], "observation")
        self.assertEqual(note["text"], "just a string")
        self.assertIn("intent", note)
        self.assertIn("headline", note)

    def test_action_needed_categories(self) -> None:
        for cat in ("non_discriminating", "skill_hurts", "regression",
                    "contradiction", "broken"):
            note = ab._normalize_note({"category": cat, "text": "x"})
            self.assertEqual(note["intent"], "action_needed", cat)

    def test_positive_signal_categories(self) -> None:
        for cat in ("skill_value", "improvement", "cost_saving"):
            note = ab._normalize_note({"category": cat, "text": "x"})
            self.assertEqual(note["intent"], "positive_signal", cat)

    def test_skill_feedback_intent_depends_on_impact(self) -> None:
        major = ab._normalize_note(
            {"category": "skill_feedback", "text": "x", "metrics": {"impact": "major"}}
        )
        minor = ab._normalize_note(
            {"category": "skill_feedback", "text": "x", "metrics": {"impact": "minor"}}
        )
        self.assertEqual(major["intent"], "action_needed")
        self.assertEqual(minor["intent"], "pattern")

    def test_explicit_fields_preserved(self) -> None:
        note = ab._normalize_note(
            {"category": "observation", "text": "x", "intent": "positive_signal",
             "headline": "Custom"}
        )
        self.assertEqual(note["intent"], "positive_signal")
        self.assertEqual(note["headline"], "Custom")

    def test_does_not_mutate_input(self) -> None:
        original = {"category": "observation", "text": "x"}
        ab._normalize_note(original)
        self.assertNotIn("intent", original)  # shallow copy, caller untouched

    def test_non_discriminating_gets_default_suggestion(self) -> None:
        note = ab._normalize_note({"category": "non_discriminating", "text": "x"})
        self.assertIn("suggestion", note)


class DeriveHeadlineTests(unittest.TestCase):
    def test_empty_text(self) -> None:
        self.assertEqual(ab._derive_headline(""), "Observation")

    def test_first_sentence_extracted(self) -> None:
        text = "Short headline here. Then a long elaboration that follows after."
        self.assertEqual(ab._derive_headline(text), "Short headline here")

    def test_long_single_sentence_truncated(self) -> None:
        text = "x" * 200
        headline = ab._derive_headline(text)
        self.assertTrue(headline.endswith("…"))
        self.assertEqual(len(headline), 88)  # 87 chars + ellipsis


class GenerateMarkdownTests(unittest.TestCase):
    def _minimal_benchmark(self) -> dict:
        return {
            "metadata": {
                "skill_name": "example-skill",
                "timestamp": "2026-04-16T10:45:30Z",
                "evals_run": [1],
            },
            "runs": [_run(1, "current_skill", 1.0, name="e1")],
            "run_summary": ab.build_run_summary(
                [_run(1, "current_skill", 1.0), _run(1, "without_skill", 0.4)]
            ),
            "comparisons": {"current_skill_wins": 1, "without_skill_wins": 0, "ties": 0},
            "notes": [],
        }

    def test_renders_title_and_summary(self) -> None:
        md = ab.generate_markdown(self._minimal_benchmark())
        self.assertIn("# Benchmark: example-skill", md)
        self.assertIn("## Summary", md)
        self.assertIn("## Comparisons", md)
        self.assertIn("pass_rate", md)

    def test_notes_section_rendered_when_present(self) -> None:
        bm = self._minimal_benchmark()
        bm["notes"] = [{"category": "skill_value", "text": "Skill helps a lot."}]
        md = ab.generate_markdown(bm)
        self.assertIn("## Notes", md)
        self.assertIn("Skill helps a lot.", md)
        self.assertIn("[SKILL VALUE]", md)


if __name__ == "__main__":
    unittest.main()
