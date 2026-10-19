"""Tests for the eval-viewer's generate_review.py report builder.

generate_review.py turns a skill's ``workspace/iteration-*`` tree into a
single self-contained HTML report. These tests cover its pure and disk-backed
helpers:

- ``find_runs`` discovers eval runs (dirs with an ``outputs/`` child) while
  skipping each run's private ``sandbox/`` — a sandbox may itself hold a nested
  eval workspace whose outputs are fixtures, not runs of the skill under test.
- ``_load_json`` / ``embed_file`` — tolerant JSON loading and text/image/binary
  file embedding.
- ``build_run`` — assembling a run dict (variant, metadata, outputs, grading,
  comparison) from a variant directory.
- ``discover_iterations`` / ``_latest_iteration`` — iteration enumeration.
- ``build_progression_data`` — per-eval pass-rate rollup across configurations.
- ``_resolve_embed_iterations`` — which iterations to inline for baseline vs
  regression mode.
- ``generate_html`` — escaping the embedded data payload so it can't break out
  of its ``<script>`` block.

Stdlib unittest only, matching the sibling runner tests.
"""

from __future__ import annotations

import base64
import json
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_VIEWER_DIR = _REPO_ROOT / "skills" / "skill-eval-runner" / "eval-viewer"
_CLI_USAGE_FIXTURE = (
    _REPO_ROOT / "tests" / "fixtures" / "copilot_usage" / "cli-final-usage.json"
)
_CLI_EVENTS_FIXTURE = (
    _REPO_ROOT / "tests" / "fixtures" / "copilot_usage" / "cli-session-events.jsonl"
)
sys.path.insert(0, str(_VIEWER_DIR))

import generate_review as gr  # noqa: E402


def _mk_run(variant_dir: Path, response: str, metadata: dict | None = None) -> None:
    """Create a <variant>/outputs/response.md (+ optional eval_metadata.json)."""
    outputs = variant_dir / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    (outputs / "response.md").write_text(response, encoding="utf-8")
    if metadata is not None:
        (variant_dir.parent / "eval_metadata.json").write_text(
            json.dumps(metadata), encoding="utf-8"
        )


class FindRunsSandboxTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.iter_dir = Path(self._tmp.name) / "iteration-1"
        self.iter_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_ignores_nested_fixture_runs_inside_sandbox(self) -> None:
        """A nested eval workspace staged inside a run's sandbox is not a run."""
        # Real eval-1: two variants, each with an outputs/ dir.
        eval1 = self.iter_dir / "eval-1-stop-when-no-evals-json"
        _mk_run(eval1 / "current_skill", "No evals found.", {"id": 1})
        _mk_run(eval1 / "without_skill", "No evals found either.", {"id": 1})

        # Real eval-8 is a meta-eval: its sandbox holds a whole fixture workspace
        # with its own eval-1/eval-2 runs that must NOT be discovered.
        eval8 = self.iter_dir / "eval-8-diagnose-misplaced-grading"
        _mk_run(eval8 / "current_skill", "Diagnosis output.", {"id": 8})
        _mk_run(eval8 / "without_skill", "Diagnosis baseline.", {"id": 8})
        fixture = (
            eval8
            / "current_skill"
            / "sandbox"
            / "files"
            / "fixture-workspace-misplaced-grading"
            / "iteration-1"
            / "eval-1-single-feature-release"
        )
        _mk_run(fixture / "current_skill", "## v1.4.0\n\nFeatures", {"id": 1})
        _mk_run(fixture / "without_skill", "Release v1.4.0 dark-mode.", {"id": 1})

        runs = gr.find_runs(self.iter_dir)

        # Only the four real variant dirs — no sandbox descendants.
        self.assertEqual(len(runs), 4)
        for r in runs:
            self.assertNotIn(
                "sandbox",
                r.parts,
                f"run {r} was discovered inside a sandbox/",
            )

    def test_discovers_ordinary_runs(self) -> None:
        """A plain eval with no sandbox is still discovered normally."""
        eval1 = self.iter_dir / "eval-1-plain"
        _mk_run(eval1 / "current_skill", "out", {"id": 1})
        _mk_run(eval1 / "without_skill", "out", {"id": 1})

        runs = gr.find_runs(self.iter_dir)

        self.assertEqual(len(runs), 2)

    def test_missing_workspace_returns_empty(self) -> None:
        runs = gr.find_runs(self.iter_dir / "does-not-exist")
        self.assertEqual(runs, [])


class LoadJsonTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_missing_file_returns_none(self) -> None:
        self.assertIsNone(gr._load_json(self.dir / "nope.json"))

    def test_malformed_json_returns_none(self) -> None:
        p = self.dir / "bad.json"
        p.write_text("{not valid", encoding="utf-8")
        self.assertIsNone(gr._load_json(p))

    def test_valid_json_round_trips(self) -> None:
        p = self.dir / "ok.json"
        p.write_text('{"a": 1, "b": [2, 3]}', encoding="utf-8")
        self.assertEqual(gr._load_json(p), {"a": 1, "b": [2, 3]})


class EmbedFileTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_text_file_embedded_as_text(self) -> None:
        p = self.dir / "response.md"
        p.write_text("# Title\n\nbody", encoding="utf-8")
        embedded = gr.embed_file(p)
        self.assertEqual(embedded["type"], "text")
        self.assertEqual(embedded["name"], "response.md")
        self.assertEqual(embedded["content"], "# Title\n\nbody")

    def test_image_file_embedded_as_data_uri(self) -> None:
        # 1x1 transparent PNG.
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
        )
        p = self.dir / "shot.png"
        p.write_bytes(png)
        embedded = gr.embed_file(p)
        self.assertEqual(embedded["type"], "image")
        self.assertTrue(embedded["data_uri"].startswith("data:image/png;base64,"))

    def test_unknown_binary_embedded_as_binary_with_size(self) -> None:
        p = self.dir / "blob.bin"
        p.write_bytes(b"\x00\x01\x02\x03")
        embedded = gr.embed_file(p)
        self.assertEqual(embedded["type"], "binary")
        self.assertEqual(embedded["size"], 4)


class BuildRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.iter_dir = Path(self._tmp.name) / "iteration-1"
        self.iter_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_variant_and_metadata_and_comparison(self) -> None:
        eval_dir = self.iter_dir / "eval-3-compose"
        cur = eval_dir / "current_skill"
        _mk_run(
            cur,
            "the answer",
            {
                "id": 3,
                "name": "compose",
                "prompt": "do the thing",
                "expectations": ["e1", "e2"],
            },
        )
        # Sibling files the report should surface / hide.
        (cur / "outputs" / "metrics.json").write_text("{}", encoding="utf-8")
        (cur / "grading.json").write_text('{"expectations": []}', encoding="utf-8")
        (eval_dir / "comparison.json").write_text('{"winner": "A"}', encoding="utf-8")

        run = gr.build_run(self.iter_dir, cur)

        self.assertEqual(run["variant"], "current_skill")
        self.assertEqual(run["eval_id"], 3)
        self.assertEqual(run["eval_name"], "compose")
        self.assertEqual(run["prompt"], "do the thing")
        self.assertEqual(run["expectations"], ["e1", "e2"])
        self.assertEqual(run["comparison"], {"winner": "A"})
        self.assertIsNotNone(run["grading"])
        # metrics.json is metadata, not a displayed output file.
        names = [o["name"] for o in run["outputs"]]
        self.assertIn("response.md", names)
        self.assertNotIn("metrics.json", names)

    def test_eval_name_falls_back_to_parent_dir(self) -> None:
        eval_dir = self.iter_dir / "eval-4-fallback-name"
        cur = eval_dir / "current_skill"
        # eval_metadata.json without a name.
        _mk_run(cur, "x", {"id": 4})
        run = gr.build_run(self.iter_dir, cur)
        self.assertEqual(run["eval_name"], "eval-4-fallback-name")

    def test_host_telemetry_details_remain_in_report_run_payload(self) -> None:
        eval_dir = self.iter_dir / "eval-5-telemetry"
        cur = eval_dir / "current_skill"
        _mk_run(cur, "telemetry response", {"id": 5, "name": "telemetry"})
        telemetry = {
            "source": "notification",
            "model": "gpt-5.5",
            "input_tokens": 100,
            "input_cached_tokens": 70,
            "output_tokens": 25,
            "output_reasoning_tokens": 8,
            "total_tokens": 125,
        }
        (cur / "outputs" / "metrics.json").write_text(
            json.dumps({"host_telemetry": telemetry}), encoding="utf-8"
        )

        run = gr.build_run(self.iter_dir, cur)

        self.assertEqual(run["metrics"]["host_telemetry"], telemetry)


class DiscoverIterationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_numeric_sort_and_ignores_non_iteration_dirs(self) -> None:
        for name in ["iteration-2", "iteration-10", "iteration-1", "scratch"]:
            (self.ws / name).mkdir()
        nums = [n for n, _ in gr.discover_iterations(self.ws)]
        self.assertEqual(nums, [1, 2, 10])

    def test_latest_iteration(self) -> None:
        for name in ["iteration-1", "iteration-3", "iteration-2"]:
            (self.ws / name).mkdir()
        self.assertEqual(gr._latest_iteration(self.ws), 3)

    def test_latest_iteration_none_when_empty(self) -> None:
        self.assertIsNone(gr._latest_iteration(self.ws))


class ProgressionDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _benchmark(
        self, iter_num: int, runs: list[dict], run_summary: dict | None = None
    ) -> None:
        d = self.ws / f"iteration-{iter_num}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "benchmark.json").write_text(
            json.dumps(
                {
                    "metadata": {"comparison_mode": "baseline"},
                    "runs": runs,
                    "run_summary": run_summary or {},
                }
            ),
            encoding="utf-8",
        )

    def test_pairs_current_and_without_skill_per_eval(self) -> None:
        self._benchmark(
            1,
            [
                {
                    "eval_id": 1,
                    "eval_name": "a",
                    "configuration": "current_skill",
                    "result": {"pass_rate": 1.0, "time_seconds": 5, "tokens": 100},
                },
                {
                    "eval_id": 1,
                    "eval_name": "a",
                    "configuration": "without_skill",
                    "result": {"pass_rate": 0.5, "time_seconds": 4, "tokens": 90},
                },
            ],
        )
        data = gr.build_progression_data(self.ws, "some-skill")
        self.assertEqual(data["skill_name"], "some-skill")
        per_eval = data["iterations"][0]["per_eval"]
        self.assertEqual(len(per_eval), 1)
        self.assertEqual(per_eval[0]["current_skill_pass_rate"], 1.0)
        self.assertEqual(per_eval[0]["without_skill_pass_rate"], 0.5)

    def test_progression_data_preserves_previous_iteration(self) -> None:
        self._benchmark(6, [], {})
        benchmark_path = self.ws / "iteration-6" / "benchmark.json"
        benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
        benchmark["metadata"].update(
            {"comparison_mode": "regression", "previous_iteration": 5}
        )
        benchmark_path.write_text(json.dumps(benchmark), encoding="utf-8")

        data = gr.build_progression_data(self.ws, "some-skill")

        self.assertEqual(data["iterations"][0]["previous_iteration"], 5)

    def test_session_usage_survives_progression_data_build(self) -> None:
        session_usage = {
            "input_tokens": 100,
            "output_tokens": 25,
            "total_tokens": 125,
            "models": ["gpt-session"],
            "source": "copilot-cli",
        }
        self._benchmark(1, [], {"session_usage": session_usage})

        data = gr.build_progression_data(self.ws, "some-skill")

        self.assertEqual(
            data["iterations"][0]["run_summary"]["session_usage"], session_usage
        )

    def test_iteration_without_benchmark_is_skipped(self) -> None:
        (self.ws / "iteration-1").mkdir()  # no benchmark.json
        self._benchmark(2, [])
        nums = [
            it["iteration"]
            for it in gr.build_progression_data(self.ws, "s")["iterations"]
        ]
        self.assertEqual(nums, [2])


class ResolveEmbedIterationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _iteration(self, num: int, config: dict | None = None) -> None:
        d = self.ws / f"iteration-{num}"
        d.mkdir(parents=True, exist_ok=True)
        if config is not None:
            (d / "iteration_config.json").write_text(
                json.dumps(config), encoding="utf-8"
            )

    def test_baseline_mode_embeds_only_served(self) -> None:
        self._iteration(1, {"mode": "baseline"})
        self._iteration(2, {"mode": "baseline"})
        self.assertEqual(gr._resolve_embed_iterations(self.ws, 2), [2])

    def test_regression_mode_embeds_served_baseline_and_previous(self) -> None:
        self._iteration(1)
        self._iteration(2)
        self._iteration(3, {"mode": "regression", "baseline_iteration": 1})
        # served=3 → {3, baseline 1, previous 2}
        self.assertEqual(gr._resolve_embed_iterations(self.ws, 3), [1, 2, 3])

    def test_regression_wanted_set_intersected_with_existing(self) -> None:
        # previous iteration (1) is missing on disk → not embedded.
        self._iteration(2, {"mode": "regression", "baseline_iteration": 2})
        self.assertEqual(gr._resolve_embed_iterations(self.ws, 2), [2])


class GenerateHtmlEscapingTests(unittest.TestCase):
    # Line/paragraph separators are valid in JSON strings but are line
    # terminators in JS source; build them by codepoint to keep this file ASCII.
    LS = chr(0x2028)
    PS = chr(0x2029)

    def test_less_than_is_escaped_to_unicode(self) -> None:
        # A </script> in the payload must not close the injection block early.
        payload = {"prompt": "if a < b then </script><script>alert(1)"}
        html = gr.generate_html(_report_data_stub(payload))
        self.assertNotIn("</script><script>alert(1)", html)
        self.assertIn("\\u003c/script>", html)

    def test_line_and_paragraph_separators_escaped(self) -> None:
        payload = {"prompt": f"a{self.LS}b{self.PS}c"}
        html = gr.generate_html(_report_data_stub(payload))
        self.assertNotIn(self.LS, html)
        self.assertNotIn(self.PS, html)
        self.assertIn("\\u2028", html)
        self.assertIn("\\u2029", html)


class UsageSummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name) / "workspace"
        self.ws.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _iteration(self, number: int = 1) -> Path:
        iteration = self.ws / f"iteration-{number}"
        iteration.mkdir(parents=True)
        (iteration / "iteration_config.json").write_text(
            json.dumps({"mode": "regression", "baseline_iteration": 1}),
            encoding="utf-8",
        )
        eval_dir = iteration / "eval-1"
        _mk_run(eval_dir / "current_skill", "current output", {"id": 1})
        _mk_run(eval_dir / "without_skill", "baseline output", {"id": 1})
        (iteration / "benchmark.json").write_text(
            json.dumps({"runs": [], "run_summary": {}}), encoding="utf-8"
        )
        return iteration

    def _generate_static(
        self,
        iteration: Path,
        output: Path,
        usage_file: Path | None = None,
        events_file: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(_VIEWER_DIR / "generate_review.py"),
            str(self.ws),
            "--skill-name",
            "usage-test",
            "--iteration",
            iteration.name.removeprefix("iteration-"),
            "--static",
            str(output),
        ]
        if usage_file is not None:
            command.extend(["--usage-output-file", str(usage_file)])
        if events_file is not None:
            command.extend(["--copilot-events-file", str(events_file)])
        return subprocess.run(command, capture_output=True, text=True, check=False)

    def test_report_data_loads_usage_summaries_for_available_iterations(self) -> None:
        first = self._iteration(1)
        second = self._iteration(2)
        first_summary = {
            "schema_version": 1,
            "source": "copilot-cli",
            "eval_count": 1,
            "session": {"models": ["gpt-first"], "total_tokens": 10},
            "eval_agents": [],
            "other_agents": [],
        }
        second_summary = {
            "schema_version": 1,
            "source": "copilot-cli",
            "eval_count": 1,
            "session": {"models": ["gpt-second"], "total_tokens": 20},
            "eval_agents": [],
            "other_agents": [],
        }
        (first / "usage_summary.json").write_text(
            json.dumps(first_summary), encoding="utf-8"
        )
        (second / "usage_summary.json").write_text(
            json.dumps(second_summary), encoding="utf-8"
        )

        report_data = gr.build_report_data(self.ws, 2, "usage-test", embed_all=True)

        self.assertEqual(
            report_data.get("iteration_usage_summaries"),
            {"1": first_summary, "2": second_summary},
        )

    def test_saved_usage_summary_sanitizes_untrusted_agent_fields(self) -> None:
        iteration = self._iteration(1)
        summary = {
            "schema_version": 1,
            "source": "copilot-cli",
            "eval_count": 1,
            "session": {"models": ["gpt-safe"], "total_tokens": 10},
            "eval_agents": [
                {
                    "eval_id": "eval-1",
                    "role": "executor",
                    "variant": [],
                    "models": [],
                    "agent_id": "private-agent-id",
                },
                {
                    "eval_id": "eval-1",
                    "role": [],
                    "models": [],
                    "private_label": "must not leak",
                },
            ],
            "other_agents": [
                {"label": [], "models": [], "private_label": "must not leak"}
            ],
            "diagnostic_prompt": "must not leak",
        }
        (iteration / "usage_summary.json").write_text(
            json.dumps(summary), encoding="utf-8"
        )

        try:
            report_data = gr.build_report_data(
                self.ws, 1, "usage-test", embed_all=True
            )
        except TypeError as exc:
            self.fail(f"malformed sidecar fields should be sanitized: {exc}")

        normalized = report_data["iteration_usage_summaries"]["1"]
        self.assertEqual(len(normalized["eval_agents"]), 1)
        self.assertNotIn("variant", normalized["eval_agents"][0])
        self.assertEqual(normalized["other_agents"][0]["label"], "Other agent")
        serialized = json.dumps(normalized)
        self.assertNotIn("private-agent-id", serialized)
        self.assertNotIn("private_label", serialized)
        self.assertNotIn("must not leak", serialized)
        self.assertNotIn("diagnostic_prompt", serialized)

    def test_usage_output_file_writes_summary_and_static_report(self) -> None:
        iteration = self._iteration(4)
        output = self.ws / "report.html"
        usage_file = _REPO_ROOT / "tests" / "fixtures" / "copilot_usage" / "final-usage.json"
        metrics_path = iteration / "eval-1" / "current_skill" / "outputs" / "metrics.json"
        metrics_path.write_text('{"keep": "metrics"}', encoding="utf-8")
        benchmark_path = iteration / "benchmark.json"
        original_metrics = metrics_path.read_bytes()
        original_benchmark = benchmark_path.read_bytes()

        result = self._generate_static(iteration, output, usage_file)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(output.is_file())
        summary_path = iteration / "usage_summary.json"
        self.assertTrue(summary_path.is_file())
        summary_text = summary_path.read_text(encoding="utf-8")
        report_text = output.read_text(encoding="utf-8")
        self.assertIn('"schema_version": 1', summary_text)
        self.assertNotIn("raw-agent-id", summary_text)
        self.assertNotIn("diagnosticPrompt", summary_text)
        self.assertNotIn("private-fixture.py", summary_text)
        self.assertNotIn(str(usage_file), report_text)
        self.assertIn("iteration_usage_summaries", report_text)
        self.assertEqual(metrics_path.read_bytes(), original_metrics)
        self.assertEqual(benchmark_path.read_bytes(), original_benchmark)

    def test_missing_usage_option_preserves_legacy_static_generation(self) -> None:
        iteration = self._iteration(1)
        output = self.ws / "report.html"

        result = self._generate_static(iteration, output)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(output.is_file())
        self.assertFalse((iteration / "usage_summary.json").exists())

    def test_invalid_usage_file_preserves_existing_outputs(self) -> None:
        iteration = self._iteration(1)
        output = self.ws / "report.html"
        output.write_text("existing report", encoding="utf-8")
        summary_path = iteration / "usage_summary.json"
        summary_path.write_text("existing summary", encoding="utf-8")
        usage_file = self.ws / "malformed-usage.json"
        usage_file.write_text("{not valid json", encoding="utf-8")

        result = self._generate_static(iteration, output, usage_file)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Copilot usage", result.stderr)
        self.assertNotIn("unrecognized arguments", result.stderr)
        self.assertEqual(output.read_text(encoding="utf-8"), "existing report")
        self.assertEqual(summary_path.read_text(encoding="utf-8"), "existing summary")

    def test_usage_output_file_requires_static_before_writing(self) -> None:
        iteration = self._iteration(1)
        output = self.ws / "report.html"
        output.write_text("existing report", encoding="utf-8")
        summary_path = iteration / "usage_summary.json"
        summary_path.write_text("existing summary", encoding="utf-8")
        usage_file = (
            _REPO_ROOT / "tests" / "fixtures" / "copilot_usage" / "final-usage.json"
        )

        with socket.socket() as occupied_port:
            occupied_port.bind(("127.0.0.1", 0))
            occupied_port.listen()
            port = occupied_port.getsockname()[1]
            result = subprocess.run(
                [
                    sys.executable,
                    str(_VIEWER_DIR / "generate_review.py"),
                    str(self.ws),
                    "--skill-name",
                    "usage-test",
                    "--iteration",
                    "1",
                    "--usage-output-file",
                    str(usage_file),
                    "--port",
                    str(port),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(output.read_text(encoding="utf-8"), "existing report")
        self.assertEqual(summary_path.read_text(encoding="utf-8"), "existing summary")
        self.assertIn("--static", result.stderr)

    def test_static_usage_report_is_deterministic(self) -> None:
        iteration = self._iteration(1)
        output = self.ws / "report.html"
        usage_file = _REPO_ROOT / "tests" / "fixtures" / "copilot_usage" / "final-usage.json"

        first = self._generate_static(iteration, output, usage_file)
        self.assertEqual(first.returncode, 0, first.stderr)
        first_html = output.read_bytes()
        first_summary = (iteration / "usage_summary.json").read_bytes()

        second = self._generate_static(iteration, output, usage_file)

        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(output.read_bytes(), first_html)
        self.assertEqual((iteration / "usage_summary.json").read_bytes(), first_summary)

    def test_copilot_events_file_attributes_eval_usage_by_variant(self) -> None:
        iteration = self._iteration(1)
        output = self.ws / "report.html"

        result = self._generate_static(
            iteration, output, _CLI_USAGE_FIXTURE, _CLI_EVENTS_FIXTURE
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(
            (iteration / "usage_summary.json").read_text(encoding="utf-8")
        )
        executors = {
            agent["variant"]: agent["total_tokens"]
            for agent in summary["eval_agents"]
            if agent["role"] == "executor"
        }
        self.assertEqual(executors, {"current_skill": 330, "without_skill": 220})
        report_text = output.read_text(encoding="utf-8")
        for private in (
            "helper-with-private-task-text",
            "synthetic prompt text",
            "call_synthetic",
            str(_CLI_EVENTS_FIXTURE),
        ):
            self.assertNotIn(private, report_text)

    def test_delegated_runner_events_render_per_variant_usage(self) -> None:
        iteration = self._iteration(1)
        output = self.ws / "report.html"
        events = [
            json.loads(line) for line in _CLI_EVENTS_FIXTURE.read_text().splitlines()
        ]
        for event in events:
            if event.get("type") == "tool.execution_start":
                event["agentId"] = "delegated-runner"
        events.extend([
            {
                "type": "tool.execution_start",
                "data": {
                    "toolCallId": "runner-call",
                    "toolName": "task",
                    "arguments": {
                        "name": "private-delegated-task",
                        "agent_type": "Skill Eval Runner",
                    },
                },
            },
            {
                "type": "subagent.started",
                "agentId": "delegated-runner",
                "data": {"toolCallId": "runner-call", "agentName": "Skill Eval Runner"},
            },
        ])
        events_file = self.ws / "nested-events.jsonl"
        events_file.write_text("".join(json.dumps(e) + "\n" for e in events))

        result = self._generate_static(
            iteration, output, _CLI_USAGE_FIXTURE, events_file
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Warning", result.stderr)
        summary = json.loads((iteration / "usage_summary.json").read_text())
        self.assertEqual(len(summary["eval_agents"]), 5)
        self.assertEqual(
            {a["variant"] for a in summary["eval_agents"] if a["role"] == "executor"},
            {"current_skill", "without_skill"},
        )
        report = output.read_text()
        for private in ("private-delegated-task", "delegated-runner", "runner-call"):
            self.assertNotIn(private, report)

    def test_copilot_events_file_requires_usage_output_file(self) -> None:
        iteration = self._iteration(1)
        output = self.ws / "report.html"

        result = subprocess.run(
            [
                sys.executable,
                str(_VIEWER_DIR / "generate_review.py"),
                str(self.ws),
                "--skill-name",
                "usage-test",
                "--iteration",
                "1",
                "--static",
                str(output),
                "--copilot-events-file",
                str(_CLI_EVENTS_FIXTURE),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--copilot-events-file requires --usage-output-file", result.stderr)
        self.assertFalse(output.exists())
        self.assertFalse((iteration / "usage_summary.json").exists())

    def test_unreadable_copilot_events_file_keeps_unattributed_usage(self) -> None:
        iteration = self._iteration(1)
        output = self.ws / "report.html"
        missing_events = self.ws / "private-session" / "events.jsonl"

        result = self._generate_static(
            iteration, output, _CLI_USAGE_FIXTURE, missing_events
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Warning", result.stderr)
        self.assertNotIn("private-session", result.stderr)
        self.assertTrue(output.is_file())
        summary = json.loads(
            (iteration / "usage_summary.json").read_text(encoding="utf-8")
        )
        self.assertEqual(summary["eval_agents"], [])
        self.assertEqual(summary["session"]["total_tokens"], 1903)
        self.assertIn("Executor", [agent["label"] for agent in summary["other_agents"]])

    def test_events_file_without_conforming_names_warns_and_continues(self) -> None:
        iteration = self._iteration(1)
        output = self.ws / "report.html"
        events = self.ws / "events.jsonl"
        events.write_text(
            json.dumps({"type": "tool.execution_start", "data": {"toolCallId": "c1", "toolName": "task", "arguments": {"name": "private-unconventional-name"}}})
            + "\n"
            + json.dumps({"type": "subagent.started", "agentId": "00000000-0000-4000-8000-000000000001", "data": {"toolCallId": "c1"}})
            + "\n",
            encoding="utf-8",
        )

        result = self._generate_static(iteration, output, _CLI_USAGE_FIXTURE, events)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Warning", result.stderr)
        self.assertIn("naming convention", result.stderr)
        self.assertNotIn("private-unconventional-name", result.stderr)
        self.assertNotIn(str(events), result.stderr)

    def test_saved_usage_summary_keeps_executor_label_and_sorts_variants(
        self,
    ) -> None:
        iteration = self._iteration(1)
        summary = {
            "schema_version": 1,
            "source": "copilot-cli",
            "eval_count": 1,
            "session": {"models": ["gpt-safe"], "total_tokens": 10},
            "eval_agents": [
                {
                    "eval_id": "eval-1",
                    "role": "executor",
                    "variant": "without_skill",
                    "models": [],
                },
                {
                    "eval_id": "eval-1",
                    "role": "executor",
                    "variant": "current_skill",
                    "models": [],
                },
                {"eval_id": "eval-1", "role": "executor", "models": []},
            ],
            "other_agents": [{"label": "Executor", "models": ["gpt-safe"]}],
        }
        (iteration / "usage_summary.json").write_text(
            json.dumps(summary), encoding="utf-8"
        )

        report_data = gr.build_report_data(self.ws, 1, "usage-test", embed_all=True)

        normalized = report_data["iteration_usage_summaries"]["1"]
        self.assertEqual(
            [agent.get("variant") for agent in normalized["eval_agents"]],
            [None, "current_skill", "without_skill"],
        )
        self.assertEqual(normalized["other_agents"][0]["label"], "Executor")


def _report_data_stub(extra: dict) -> dict:
    """Minimal report_data payload merged with extra keys for HTML tests."""
    base = {
        "skill_name": "s",
        "served_iteration": 1,
        "iterations": [],
        "iteration_benchmarks": {},
        "iteration_runs": {},
    }
    base.update(extra)
    return base


if __name__ == "__main__":
    unittest.main()
