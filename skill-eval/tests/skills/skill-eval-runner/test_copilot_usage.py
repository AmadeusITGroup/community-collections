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
_FIXTURE_DIR = _REPO_ROOT / "tests" / "fixtures" / "copilot_usage"
_FIXTURE = _FIXTURE_DIR / "final-usage.json"
_CLI_USAGE_FIXTURE = _FIXTURE_DIR / "cli-final-usage.json"
_CLI_EVENTS_FIXTURE = _FIXTURE_DIR / "cli-session-events.jsonl"
sys.path.insert(0, str(_VIEWER_DIR))


def _agent_id(number: int) -> str:
    return f"00000000-0000-4000-8000-{number:012d}"

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


class CopilotCliAttributionTests(unittest.TestCase):
    """Real Copilot CLI files key sub-agents by id and name them by definition.

    The task name chosen by the runner only appears in the session events, so
    per-eval attribution joins ``tool.execution_start`` (task name) with
    ``subagent.started`` (agent id) through their shared ``toolCallId``.
    """

    def setUp(self) -> None:
        self.assertIsNotNone(
            usage_module,
            "copilot_usage.py is not implemented yet",
        )
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.iteration_dir = self.root / "iteration-1"
        for variant in ("current_skill", "without_skill"):
            outputs = self.iteration_dir / "eval-1-synthetic" / variant / "outputs"
            outputs.mkdir(parents=True)
            (outputs / "response.md").write_text("synthetic", encoding="utf-8")
        (self.iteration_dir / "iteration_config.json").write_text(
            json.dumps({"mode": "baseline"}), encoding="utf-8"
        )
        self.raw = json.loads(_CLI_USAGE_FIXTURE.read_text(encoding="utf-8"))
        self.usage_path = self.root / "copilot-usage.json"
        self.usage_path.write_text(json.dumps(self.raw), encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _normalize(
        self, task_names: dict | None = None, raw: dict | None = None
    ) -> dict:
        if raw is not None:
            self.usage_path.write_text(json.dumps(raw), encoding="utf-8")
        return usage_module.load_copilot_usage(
            self.usage_path, self.iteration_dir, task_names=task_names
        )

    @staticmethod
    def _eval_rows(summary: dict) -> list[tuple]:
        return [
            (
                agent["eval_id"],
                agent["role"],
                agent.get("variant"),
                agent.get("input_tokens"),
                agent.get("output_tokens"),
                agent.get("total_tokens"),
            )
            for agent in summary["eval_agents"]
        ]

    @staticmethod
    def _other_rows(summary: dict) -> list[tuple]:
        return [
            (
                agent["label"],
                agent["models"],
                agent.get("input_tokens"),
                agent.get("output_tokens"),
            )
            for agent in summary["other_agents"]
        ]

    def test_load_task_names_joins_task_starts_to_subagents(self) -> None:
        names = usage_module.load_task_names(_CLI_EVENTS_FIXTURE)

        self.assertEqual(
            names,
            {
                _agent_id(1): "eval-1-executor-current-skill",
                _agent_id(2): "eval-1-executor-without-skill",
                _agent_id(3): "eval-1-grader-current-skill",
                _agent_id(4): "eval-1-grader-without_skill",
                _agent_id(5): "eval-1-comparator",
                _agent_id(6): "analyzer",
                _agent_id(7): "helper-with-private-task-text",
            },
        )

    def test_load_task_names_ignores_malformed_non_task_and_orphan_events(
        self,
    ) -> None:
        def event(event_type: str, data: dict, agent_id: str | None = None) -> str:
            value: dict = {"type": event_type, "data": data, "id": "evt"}
            if agent_id is not None:
                value["agentId"] = agent_id
            return json.dumps(value)

        def task_start(call_id: str, name: object, tool: str = "task") -> str:
            return event(
                "tool.execution_start",
                {"toolCallId": call_id, "toolName": tool, "arguments": {"name": name}},
            )

        def started(call_id: str, agent_id: str) -> str:
            return event("subagent.started", {"toolCallId": call_id}, agent_id)

        lines = [
            "{not json tool.execution_start",
            '["subagent.started"]',
            json.dumps({"type": "subagent.started", "agentId": "no-data"}),
            task_start("call_other", "eval-1-executor-current-skill", "read_agent"),
            started("call_other", "agent-non-task"),
            task_start("call_unstarted", "eval-2-executor-current-skill"),
            task_start("call_bad_name", 42),
            started("call_bad_name", "agent-bad-name"),
            started("call_orphan", "agent-orphan"),
            task_start("call_ok", "eval-3-grader-without-skill"),
            started("call_ok", "agent-ok"),
        ]
        events_path = self.root / "events.jsonl"
        with events_path.open("wb") as handle:
            handle.write(b"\xff\xfe tool.execution_start not utf-8\n")
            handle.write(("\n".join(lines) + "\n").encode("utf-8"))

        self.assertEqual(
            usage_module.load_task_names(events_path),
            {"agent-ok": "eval-3-grader-without-skill"},
        )

    def test_unreadable_events_file_raises_sanitized_error(self) -> None:
        missing = self.root / "private-session-dir" / "events.jsonl"

        with self.assertRaises(usage_module.CopilotUsageError) as raised:
            usage_module.load_task_names(missing)

        self.assertNotIn("private-session-dir", str(raised.exception))

    def test_task_names_attribute_usage_per_eval_role_and_variant(self) -> None:
        summary = self._normalize(usage_module.load_task_names(_CLI_EVENTS_FIXTURE))

        self.assertEqual(
            self._eval_rows(summary),
            [
                ("eval-1", "comparator", None, 60, 6, 66),
                ("eval-1", "executor", "current_skill", 300, 30, 330),
                ("eval-1", "executor", "without_skill", 200, 20, 220),
                ("eval-1", "grader", "current_skill", 50, 5, 55),
                ("eval-1", "grader", "without_skill", 40, 4, 44),
            ],
        )
        self.assertEqual(summary["session"]["total_tokens"], 1903)

    def test_unattributed_agents_use_safe_labels(self) -> None:
        summary = self._normalize(usage_module.load_task_names(_CLI_EVENTS_FIXTURE))

        self.assertEqual(
            self._other_rows(summary),
            [
                ("Analyzer", ["gpt-6-luna"], 70, 7),
                ("Executor", ["claude-sonnet-5.5"], 10, 1),
                ("Runner", ["gpt-6-luna"], 1000, 100),
            ],
        )

    def test_task_names_ids_and_prompts_are_not_persisted(self) -> None:
        summary = self._normalize(usage_module.load_task_names(_CLI_EVENTS_FIXTURE))
        serialized = json.dumps(summary, sort_keys=True)

        for private in (
            "helper-with-private-task-text",
            "eval-1-executor-current-skill",
            "00000000-0000-4000-8000",
            "call_",
            "synthetic prompt text",
            "Synthetic task description",
            "private-fixture.py",
        ):
            self.assertNotIn(private, serialized)

    def test_without_task_names_usage_is_unattributed_with_safe_labels(
        self,
    ) -> None:
        summary = self._normalize()

        self.assertEqual(summary["eval_agents"], [])
        self.assertEqual(
            self._other_rows(summary),
            [
                ("Analyzer", ["gpt-6-luna"], 70, 7),
                ("Comparator", ["claude-sonnet-5.5"], 60, 6),
                ("Executor", ["claude-sonnet-5.5"], 510, 51),
                ("Grader", ["claude-sonnet-5.5"], 90, 9),
                ("Runner", ["gpt-6-luna"], 1000, 100),
            ],
        )

    def test_record_keys_named_like_tasks_are_attributed(self) -> None:
        raw = copy.deepcopy(self.raw)
        metrics = raw["agentMetrics"]
        metrics["eval-1-executor-current-skill"] = metrics.pop(_agent_id(1))
        metrics["eval-1-executor-without-skill"] = metrics.pop(_agent_id(2))

        summary = self._normalize(raw=raw)

        self.assertEqual(
            self._eval_rows(summary),
            [
                ("eval-1", "executor", "current_skill", 300, 30, 330),
                ("eval-1", "executor", "without_skill", 200, 20, 220),
            ],
        )

    def test_task_names_for_unknown_evals_or_roles_are_not_attributed(
        self,
    ) -> None:
        summary = self._normalize(
            {
                _agent_id(1): "eval-9-executor-current-skill",
                _agent_id(2): "eval-1-reviewer-without-skill",
            }
        )

        self.assertEqual(summary["eval_agents"], [])
        self.assertIn(
            ("Executor", ["claude-sonnet-5.5"], 510, 51), self._other_rows(summary)
        )

    def test_task_name_matching_is_case_insensitive(self) -> None:
        summary = self._normalize({_agent_id(1): "Eval-1-Executor-Current-Skill"})

        self.assertEqual(
            self._eval_rows(summary),
            [("eval-1", "executor", "current_skill", 300, 30, 330)],
        )

    def test_runner_agent_display_name_with_spaces_is_labelled_runner(
        self,
    ) -> None:
        raw = copy.deepcopy(self.raw)
        main = raw["agentMetrics"].pop("main")
        main["agentName"] = "Skill Eval Runner"
        main["agentDisplayName"] = "Skill Eval Runner"
        raw["agentMetrics"][_agent_id(8)] = main

        summary = self._normalize(raw=raw)

        self.assertIn(
            ("Runner", ["gpt-6-luna"], 1000, 100), self._other_rows(summary)
        )

    def _write_events(self, events: list) -> Path:
        path = self.root / "events.jsonl"
        path.write_text(
            "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8"
        )
        return path

    @staticmethod
    def _launch(call_id, agent_id, name, agent_type, parent=None):
        start = {
            "type": "tool.execution_start",
            "data": {
                "toolCallId": call_id,
                "toolName": "task",
                "arguments": {"name": name, "agent_type": agent_type},
            },
        }
        if parent is not None:
            start["agentId"] = parent
        return [
            start,
            {
                "type": "subagent.started",
                "agentId": agent_id,
                "data": {"toolCallId": call_id, "agentName": agent_type},
            },
        ]

    def test_eval_agents_under_delegated_runners_are_attributed(self) -> None:
        for depth in (1, 2):
            for reverse in (False, True):
                with self.subTest(depth=depth, reverse=reverse):
                    events = []
                    parent = None
                    for level in range(depth):
                        runner = f"runner-{level}"
                        events += self._launch(
                            runner, runner, "private-run-evals", "Skill Eval Runner",
                            parent,
                        )
                        parent = runner
                    children = [
                        json.loads(line)
                        for line in _CLI_EVENTS_FIXTURE.read_text().splitlines()
                    ]
                    for event in children:
                        if event.get("type") == "tool.execution_start":
                            event["agentId"] = parent
                    events += children
                    if reverse:
                        events.reverse()
                    names = usage_module.load_task_names(self._write_events(events))
                    summary = self._normalize(names)
                    self.assertEqual(len(summary["eval_agents"]), 5)
                    self.assertEqual(summary["session"]["total_tokens"], 1903)
                    self.assertIn(
                        ("eval-1", "executor", "current_skill", 300, 30, 330),
                        self._eval_rows(summary),
                    )
                    self.assertNotIn("private-run-evals", json.dumps(summary))

    def test_runner_identity_comes_from_definition_not_task_name(self) -> None:
        for definition in ("Skill Eval Runner", "skill-eval-runner"):
            events = self._launch("r", "runner", "arbitrary", definition)
            # The task arguments alone can identify a runner when start
            # metadata does not include the definition.
            events[1]["data"].pop("agentName")
            events += self._launch(
                "e", "executor", "eval-1-executor-current-skill",
                "skill-eval-executor", "runner",
            )
            self.assertIn(
                "executor",
                usage_module.load_task_names(self._write_events(events)),
            )

        events = self._launch("r", "runner", "arbitrary", "Skill Eval Runner")
        events[0]["data"]["arguments"].pop("agent_type")
        events += self._launch(
            "e", "executor", "eval-1-executor-current-skill",
            "skill-eval-executor", "runner",
        )
        self.assertIn(
            "executor", usage_module.load_task_names(self._write_events(events))
        )

        # Actual start metadata takes precedence over the requested definition.
        events[0]["data"]["arguments"]["agent_type"] = "Skill Eval Runner"
        events[1]["data"]["agentName"] = "general-purpose"
        self.assertNotIn(
            "executor", usage_module.load_task_names(self._write_events(events))
        )

        events = self._launch("r", "runner", "Skill Eval Runner", "general-purpose")
        events += self._launch(
            "e", "executor", "eval-1-executor-current-skill",
            "skill-eval-executor", "runner",
        )
        self.assertNotIn(
            "executor", usage_module.load_task_names(self._write_events(events))
        )

    def test_helpers_inside_eval_agents_cannot_spoof_eval_attribution(self) -> None:
        events = self._launch("r", "runner", "run", "Skill Eval Runner")
        events += self._launch(
            "e", "executor", "eval-1-executor-current-skill",
            "skill-eval-executor", "runner",
        )
        events += self._launch(
            "h", "helper", "eval-1-grader-current-skill",
            "skill-eval-grader", "executor",
        )
        events += self._launch(
            "n", "nested-runner", "run", "Skill Eval Runner", "executor"
        )
        events += self._launch(
            "f", "fake-eval", "eval-1-executor-without-skill",
            "skill-eval-executor", "nested-runner",
        )
        names = usage_module.load_task_names(self._write_events(events))
        self.assertEqual(set(names), {"runner", "executor"})

    def test_orphan_and_cyclic_runner_chains_are_not_attributed(self) -> None:
        events = self._launch("r1", "r1", "run", "Skill Eval Runner", "r2")
        events += self._launch("r2", "r2", "run", "Skill Eval Runner", "r1")
        events += self._launch(
            "e", "executor", "eval-1-executor-current-skill",
            "skill-eval-executor", "missing",
        )
        self.assertEqual(
            usage_module.load_task_names(self._write_events(events)), {}
        )

    def test_unnamed_runner_wrappers_preserve_named_eval_children(self) -> None:
        events = self._launch("r1", "outer", None, "Skill Eval Runner")
        events[0]["data"]["arguments"].pop("name")
        events += self._launch("r2", "inner", "", "Skill Eval Runner", "outer")
        events += self._launch(
            "e", "executor", "eval-1-executor-current-skill",
            "skill-eval-executor", "inner",
        )
        self.assertEqual(
            usage_module.load_task_names(self._write_events(events)),
            {"executor": "eval-1-executor-current-skill"},
        )

    def test_common_task_name_variations_are_attributed(self) -> None:
        for name in (
            "eval-1-synthetic-executor-current-skill",
            "eval-1-executor_current_skill",
            "eval-1-executor-with-skill",
            "eval 1 executor current skill",
        ):
            with self.subTest(name=name):
                summary = self._normalize({_agent_id(1): name})
                self.assertEqual(
                    self._eval_rows(summary),
                    [("eval-1", "executor", "current_skill", 300, 30, 330)],
                )

    def test_comparator_recovery_role_still_parses(self) -> None:
        summary = self._normalize({_agent_id(5): "eval-1-comparator-recovery"})

        self.assertEqual(
            [(a["eval_id"], a["role"]) for a in summary["eval_agents"]],
            [("eval-1", "comparator-recovery")],
        )

    def test_analyzer_task_name_is_labelled_analyzer(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["agentMetrics"][_agent_id(7)]["agentName"] = "general-purpose"
        raw["agentMetrics"][_agent_id(7)]["agentDisplayName"] = "general-purpose"

        summary = self._normalize({_agent_id(7): "analyzer"}, raw=raw)

        self.assertIn(
            ("Analyzer", ["claude-sonnet-5.5"], 10, 1), self._other_rows(summary)
        )

    def test_nested_task_starts_are_not_used_for_attribution(self) -> None:
        events = self._write_events([
            {"type": "tool.execution_start", "data": {"toolCallId": "c1", "toolName": "task", "arguments": {"name": "eval-1-executor-current-skill"}}},
            {"type": "subagent.started", "agentId": "a1", "data": {"toolCallId": "c1"}},
            {"type": "tool.execution_start", "agentId": "a1", "data": {"toolCallId": "c2", "toolName": "task", "arguments": {"name": "eval-2-executor-current-skill"}}},
            {"type": "subagent.started", "agentId": "n1", "data": {"toolCallId": "c2"}},
        ])

        self.assertEqual(
            usage_module.load_task_names(events),
            {"a1": "eval-1-executor-current-skill"},
        )

    def test_first_task_call_wins_for_repeated_subagent_starts(self) -> None:
        events = self._write_events([
            {"type": "tool.execution_start", "data": {"toolCallId": "c1", "toolName": "task", "arguments": {"name": "eval-1-grader-current-skill"}}},
            {"type": "subagent.started", "agentId": "a1", "data": {"toolCallId": "c1"}},
            {"type": "tool.execution_start", "data": {"toolCallId": "c9", "toolName": "write_agent", "arguments": {"agent_id": "a1"}}},
            {"type": "subagent.started", "agentId": "a1", "data": {"toolCallId": "c9"}},
        ])

        self.assertEqual(
            usage_module.load_task_names(events),
            {"a1": "eval-1-grader-current-skill"},
        )


if __name__ == "__main__":
    unittest.main()
