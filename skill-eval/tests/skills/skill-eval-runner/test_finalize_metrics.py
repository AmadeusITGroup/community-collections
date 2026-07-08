"""Unit tests for finalize_metrics.py.

Covers the timestamp coercion, debug-log scanning, executor-layer
normalization, host_telemetry source precedence, and the per-variant
finalization round-trip (including sidecar merge + legacy cleanup).

finalize_metrics assembles outputs/metrics.json from up to three sources
(executor self-report, parent notification sidecar, VS Code debug log), so
the precedence logic in _build_host_telemetry is the most fragile part and
gets the most coverage here.

Stdlib unittest only.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_DIR = _REPO_ROOT / "skills" / "skill-eval-runner" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

import finalize_metrics as fm  # noqa: E402


class ToIsoUtcTests(unittest.TestCase):
    def test_none_passthrough(self) -> None:
        self.assertIsNone(fm.to_iso_utc(None))

    def test_string_passthrough(self) -> None:
        self.assertEqual(fm.to_iso_utc("2026-04-16T10:00:00Z"), "2026-04-16T10:00:00Z")

    def test_epoch_seconds(self) -> None:
        # 2021-01-01T00:00:00Z = 1609459200 seconds
        out = fm.to_iso_utc(1609459200)
        self.assertEqual(out, "2021-01-01T00:00:00Z")

    def test_epoch_millis_heuristic(self) -> None:
        # > 1e12 → treated as milliseconds
        out = fm.to_iso_utc(1609459200000)
        self.assertEqual(out, "2021-01-01T00:00:00Z")

    def test_unsupported_type(self) -> None:
        self.assertIsNone(fm.to_iso_utc([1, 2, 3]))


class ParseIsoTests(unittest.TestCase):
    def test_z_suffix_parsed(self) -> None:
        dt = fm._parse_iso("2026-04-16T10:00:00Z")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2026)

    def test_invalid_returns_none(self) -> None:
        self.assertIsNone(fm._parse_iso("not-a-date"))

    def test_none_returns_none(self) -> None:
        self.assertIsNone(fm._parse_iso(None))


class EnsureExecutorLayersTests(unittest.TestCase):
    def test_empty_gets_stubs(self) -> None:
        out = fm._ensure_executor_layers({})
        self.assertIn("self_report", out)
        self.assertIn("user_notes", out)
        self.assertEqual(out["self_report"]["total_tool_calls"], 0)
        # user_notes has the full skill_feedback shape
        self.assertEqual(
            set(out["user_notes"]["skill_feedback"]),
            {"missing_from_skill", "ambiguous_instructions",
             "broken_references", "outdated_or_wrong"},
        )

    def test_legacy_flat_shape_folded_into_self_report(self) -> None:
        legacy = {
            "tool_calls": {"Read": 3},
            "total_tool_calls": 3,
            "total_steps": 2,
            "files_created": ["response.md"],
            "output_chars": 100,
        }
        out = fm._ensure_executor_layers(dict(legacy))
        self.assertEqual(out["self_report"]["tool_calls"], {"Read": 3})
        self.assertEqual(out["self_report"]["total_tool_calls"], 3)
        # Top-level legacy keys removed after folding.
        self.assertNotIn("tool_calls", out)
        self.assertNotIn("output_chars", out)

    def test_existing_self_report_preserved(self) -> None:
        existing = {
            "self_report": {"total_tool_calls": 9, "tool_calls": {"Bash": 9}},
            "user_notes": {"response_risks": [], "missing_inputs": [],
                           "skill_feedback": {}},
        }
        out = fm._ensure_executor_layers(dict(existing))
        self.assertEqual(out["self_report"]["total_tool_calls"], 9)


class BuildHostTelemetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.variant_dir = Path(self._tmp.name) / "current_skill"
        (self.variant_dir / "outputs").mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_response(self) -> None:
        (self.variant_dir / "outputs" / "response.md").write_text("x", encoding="utf-8")

    def test_debug_log_wins_over_notification(self) -> None:
        notification = {
            "spawned_at": "2026-04-16T10:00:00Z",
            "returned_at": "2026-04-16T10:00:30Z",
            "total_tokens": 5000,
            "duration_ms": 30000,
        }
        log_scan = {
            "ts_ms": 1609459200000,
            "dur_ms": 23000,
            "total_tokens": 84852,
            "input_tokens": 62100,
            "output_tokens": 22752,
            "turn_count": 6,
            "model": "claude-opus-4.7",
            "tool_calls": {"Read": 5},
            "total_tool_calls": 5,
            "tool_errors": 0,
        }
        block = fm._build_host_telemetry(self.variant_dir, notification, log_scan, None)
        self.assertEqual(block["source"], "debug_log")
        self.assertEqual(block["total_tokens"], 84852)  # log wins
        self.assertEqual(block["duration_ms"], 23000)
        self.assertEqual(block["model"], "claude-opus-4.7")
        self.assertEqual(block["total_tool_calls"], 5)

    def test_notification_only(self) -> None:
        notification = {
            "spawned_at": "2026-04-16T10:00:00Z",
            "returned_at": "2026-04-16T10:00:30Z",
            "total_tokens": 5000,
            "duration_ms": 30000,
        }
        block = fm._build_host_telemetry(self.variant_dir, notification, None, None)
        self.assertEqual(block["source"], "notification")
        self.assertEqual(block["total_tokens"], 5000)
        self.assertEqual(block["duration_ms"], 30000)

    def test_wall_clock_fallback_from_metadata(self) -> None:
        self._write_response()
        eval_metadata = {"prepared_at": "2026-04-16T10:00:00Z"}
        block = fm._build_host_telemetry(self.variant_dir, None, None, eval_metadata)
        self.assertEqual(block["source"], "wall_clock")
        self.assertEqual(block["started_at"], "2026-04-16T10:00:00Z")
        # completed_at comes from response.md mtime; duration derived.
        self.assertIn("completed_at", block)

    def test_duration_derived_from_timestamps(self) -> None:
        notification = {
            "spawned_at": "2026-04-16T10:00:00Z",
            "returned_at": "2026-04-16T10:00:10Z",
            # no duration_ms provided → must derive 10s
        }
        block = fm._build_host_telemetry(self.variant_dir, notification, None, None)
        self.assertEqual(block["duration_ms"], 10000)
        self.assertEqual(block["total_duration_seconds"], 10.0)


class ScanLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_log(self, events: list[dict]) -> Path:
        path = self.root / "runSubagent-skill-eval-executor-abc.jsonl"
        path.write_text(
            "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8"
        )
        return path

    def test_aggregates_tokens_turns_tools(self) -> None:
        log = self._write_log([
            {"type": "user_message", "data": "see /work/current_skill/outputs/response.md"},
            {"type": "subagent", "ts": 1000, "dur": 23000},
            {"type": "llm_request", "name": "chat:claude-opus-4.7",
             "attrs": {"inputTokens": 100, "outputTokens": 50, "ttft": 1820}},
            {"type": "llm_request", "name": "chat:claude-opus-4.7",
             "attrs": {"inputTokens": 200, "outputTokens": 75}},
            {"type": "tool_call", "name": "read_file"},
            {"type": "tool_call", "name": "read_file"},
            {"type": "tool_call", "name": "create_file", "attrs": {"status": "error"}},
        ])
        scan = fm._scan_log(log)
        self.assertEqual(scan["input_tokens"], 300)
        self.assertEqual(scan["output_tokens"], 125)
        self.assertEqual(scan["total_tokens"], 425)
        self.assertEqual(scan["turn_count"], 2)
        self.assertEqual(scan["ttft_ms_first_turn"], 1820)
        self.assertEqual(scan["model"], "claude-opus-4.7")
        self.assertEqual(scan["tool_calls"], {"read_file": 2, "create_file": 1})
        self.assertEqual(scan["total_tool_calls"], 3)
        self.assertEqual(scan["tool_errors"], 1)
        self.assertTrue(scan["response_path"].endswith("response.md"))

    def test_skips_malformed_lines(self) -> None:
        path = self.root / "runSubagent-skill-eval-executor-x.jsonl"
        path.write_text(
            'not json\n{"type": "llm_request", "attrs": {"inputTokens": 10}}\n',
            encoding="utf-8",
        )
        scan = fm._scan_log(path)
        self.assertEqual(scan["turn_count"], 1)
        self.assertEqual(scan["input_tokens"], 10)

    def test_empty_signal_returns_none(self) -> None:
        log = self._write_log([{"type": "other_event"}])
        self.assertIsNone(fm._scan_log(log))


class FinalizeVariantTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.eval_dir = Path(self._tmp.name) / "eval-1-alpha"
        self.variant_dir = self.eval_dir / "current_skill"
        (self.variant_dir / "outputs").mkdir(parents=True)
        (self.variant_dir / "outputs" / "response.md").write_text("x", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_metrics(self, data: dict) -> None:
        (self.variant_dir / "outputs" / "metrics.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

    def test_round_trip_adds_host_telemetry(self) -> None:
        self._write_metrics({
            "self_report": {"total_tool_calls": 4, "tool_calls": {"Read": 4}},
            "user_notes": fm._empty_user_notes(),
        })
        ht_source, metrics_source = fm.finalize_variant(self.variant_dir, None)
        metrics = json.loads(
            (self.variant_dir / "outputs" / "metrics.json").read_text()
        )
        self.assertIn("host_telemetry", metrics)
        # No log scan → tool_calls absent in host_telemetry → self_report source.
        self.assertEqual(metrics_source, "self_report")
        self.assertEqual(metrics["metrics_source"], "self_report")

    def test_notification_sidecar_merged_and_deleted(self) -> None:
        self._write_metrics({"self_report": {}, "user_notes": fm._empty_user_notes()})
        sidecar = self.variant_dir / "outputs" / "notification.json"
        sidecar.write_text(
            json.dumps({"spawned_at": "2026-04-16T10:00:00Z",
                        "returned_at": "2026-04-16T10:00:05Z",
                        "total_tokens": 1234, "duration_ms": 5000}),
            encoding="utf-8",
        )
        fm.finalize_variant(self.variant_dir, None)
        metrics = json.loads(
            (self.variant_dir / "outputs" / "metrics.json").read_text()
        )
        self.assertIn("notification", metrics)
        self.assertEqual(metrics["notification"]["total_tokens"], 1234)
        self.assertEqual(metrics["host_telemetry"]["source"], "notification")
        # sidecar consumed
        self.assertFalse(sidecar.exists())

    def test_legacy_execution_json_removed(self) -> None:
        self._write_metrics({"self_report": {}, "user_notes": fm._empty_user_notes()})
        legacy = self.variant_dir / "execution.json"
        legacy.write_text("{}", encoding="utf-8")
        fm.finalize_variant(self.variant_dir, None)
        self.assertFalse(legacy.exists())

    def test_debug_log_scan_sets_debug_source(self) -> None:
        self._write_metrics({"self_report": {}, "user_notes": fm._empty_user_notes()})
        log_scan = {
            "ts_ms": 1609459200000, "dur_ms": 5000,
            "total_tokens": 999, "input_tokens": 700, "output_tokens": 299,
            "turn_count": 3, "model": "m", "tool_calls": {"Read": 2},
            "total_tool_calls": 2, "tool_errors": 0,
        }
        _, metrics_source = fm.finalize_variant(self.variant_dir, log_scan)
        self.assertEqual(metrics_source, "debug_log")


class DiscoverVariantDirsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.iter_dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_finds_known_variants(self) -> None:
        (self.iter_dir / "eval-1-a" / "current_skill").mkdir(parents=True)
        (self.iter_dir / "eval-1-a" / "without_skill").mkdir(parents=True)
        (self.iter_dir / "eval-2-b" / "current_skill").mkdir(parents=True)
        out = fm.discover_variant_dirs(self.iter_dir)
        names = sorted(str(p.relative_to(self.iter_dir)) for p in out)
        self.assertEqual(
            names,
            ["eval-1-a/current_skill", "eval-1-a/without_skill",
             "eval-2-b/current_skill"],
        )

    def test_ignores_non_eval_dirs(self) -> None:
        (self.iter_dir / "not-an-eval" / "current_skill").mkdir(parents=True)
        self.assertEqual(fm.discover_variant_dirs(self.iter_dir), [])


if __name__ == "__main__":
    unittest.main()
