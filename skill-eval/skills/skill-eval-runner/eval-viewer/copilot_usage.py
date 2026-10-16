"""Normalize Copilot CLI final usage JSON for the static Skill Eval report.

Copilot CLI keys ``agentMetrics`` by agent id and names each record after its
agent definition, so per-eval attribution relies on the task names the runner
chose at launch. Those names only appear in the CLI session events, which
``load_task_names`` reduces to an agent-id to task-name map. Task names,
agent ids, prompts and paths are never persisted.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = 1
SOURCE = "copilot-cli"

_MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}\Z")
_EVAL_DIR_RE = re.compile(r"eval-(\d+)(?:[-_].*)?\Z")
# Optional eval slug, then role, then optional variant ("with" = current).
_AGENT_NAME_RE = re.compile(
    r"eval-(\d+)-(?:[a-z0-9-]{0,120}?-)?(?<!-comparator-)"
    r"(executor|grader|comparator-recovery|comparator|recovery)"
    r"(?:-(current|with|without|previous)-skill)?\Z"
)
_EVAL_ROLES = frozenset(
    {"executor", "grader", "comparator", "comparator-recovery", "recovery"}
)
_VARIANT_ROLES = frozenset({"executor", "grader"})
_VARIANTS = ("current_skill", "without_skill", "previous_skill")
_KNOWN_AGENT_LABELS = {
    "skill-eval-runner": "Runner",
    "skill-eval-executor": "Executor",
    "skill-eval-analyzer": "Analyzer",
    "skill-eval-comparator": "Comparator",
    "skill-eval-grader": "Grader",
    "skill-eval-recovery": "Recovery",
}
_EVENT_MARKERS = ("tool.execution_start", "subagent.started")
_USAGE_FIELDS = (
    ("input_tokens", "inputTokens"),
    ("input_cached_tokens", "cacheReadTokens"),
    ("input_cache_creation_tokens", "cacheCreationTokens"),
    ("input_cache_write_tokens", "cacheWriteTokens"),
    ("output_tokens", "outputTokens"),
    ("output_reasoning_tokens", "reasoningTokens"),
)


class CopilotUsageError(ValueError):
    """A safe, user-facing error while reading final usage data."""


def _nonnegative_int(value: Any) -> int | None:
    if type(value) is int and value >= 0:
        return value
    return None


def _safe_model(value: Any) -> str | None:
    if isinstance(value, str) and _MODEL_RE.fullmatch(value):
        return value
    return None


def _model_usage(model_metrics: Any) -> tuple[list[str], dict[str, int]]:
    if model_metrics is None:
        return [], {}
    if not isinstance(model_metrics, dict):
        return [], {}

    entries: list[tuple[str, dict[str, Any]]] = []
    for raw_model in sorted(model_metrics):
        model = _safe_model(raw_model)
        record = model_metrics[raw_model]
        if model is None or not isinstance(record, dict):
            continue
        usage = record.get("usage")
        if isinstance(usage, dict):
            entries.append((model, usage))
        else:
            entries.append((model, {}))

    models = sorted({model for model, _ in entries})
    values: dict[str, int] = {}
    for output_name, source_name in _USAGE_FIELDS:
        field_values = [_nonnegative_int(usage.get(source_name)) for _, usage in entries]
        if field_values and all(value is not None for value in field_values):
            values[output_name] = sum(value for value in field_values if value is not None)

    total_values = [
        _nonnegative_int(usage.get("totalTokens")) for _, usage in entries
    ]
    if total_values and all(value is not None for value in total_values):
        values["total_tokens"] = sum(
            value for value in total_values if value is not None
        )
    elif "input_tokens" in values and "output_tokens" in values:
        values["total_tokens"] = values["input_tokens"] + values["output_tokens"]

    return models, values


def _iteration_layout(iteration_dir: Path) -> tuple[dict[str, set[str]], str | None]:
    if not iteration_dir.is_dir():
        raise CopilotUsageError("Target iteration directory is unavailable")

    variants_by_eval: dict[str, set[str]] = {}
    for eval_dir in sorted(iteration_dir.iterdir()):
        if not eval_dir.is_dir():
            continue
        match = _EVAL_DIR_RE.fullmatch(eval_dir.name)
        if not match:
            continue
        eval_id = f"eval-{int(match.group(1))}"
        variants = {
            variant
            for variant in _VARIANTS
            if (eval_dir / variant / "outputs" / "response.md").is_file()
        }
        variants_by_eval[eval_id] = variants

    config_path = iteration_dir / "iteration_config.json"
    mode: str | None = None
    if config_path.is_file():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            config = None
        if isinstance(config, dict) and config.get("mode") in ("baseline", "regression"):
            mode = config["mode"]

    return variants_by_eval, mode


def _record_usage(record: dict[str, Any]) -> dict[str, Any]:
    models, values = _model_usage(record.get("modelMetrics"))
    summary: dict[str, Any] = {"models": models}
    summary.update(values)
    api_duration = _nonnegative_int(record.get("totalApiDurationMs"))
    if api_duration is not None:
        summary["total_api_duration_ms"] = api_duration
    return summary


def _sum_record_values(records: list[dict[str, Any]]) -> dict[str, Any]:
    models = sorted(
        {
            model
            for record in records
            for model in record.get("models", [])
            if isinstance(model, str)
        }
    )
    summary: dict[str, Any] = {"models": models}
    fields = (
        "input_tokens",
        "input_cached_tokens",
        "input_cache_creation_tokens",
        "input_cache_write_tokens",
        "output_tokens",
        "output_reasoning_tokens",
        "total_tokens",
        "total_api_duration_ms",
    )
    for field in fields:
        values = [record.get(field) for record in records]
        if values and all(_nonnegative_int(value) is not None for value in values):
            summary[field] = sum(value for value in values if value is not None)
    return summary


def _normalize_name(name: str) -> str:
    return re.sub(r"[\s_]+", "-", name.strip().lower())


def _safe_other_label(
    record_key: str, record: dict[str, Any], task_name: Any = None
) -> str:
    if isinstance(task_name, str) and _normalize_name(task_name) == "analyzer":
        return "Analyzer"
    for name in (record.get("agentDisplayName"), record.get("agentName")):
        if isinstance(name, str):
            normalized = _normalize_name(name)
            label = _KNOWN_AGENT_LABELS.get(normalized)
            if label is not None:
                return label
    if record_key == "main":
        return "Runner"
    return "Other agent"


def _variant_for_agent(
    eval_id: str,
    role: str,
    variants_by_eval: dict[str, set[str]],
    mode: str | None,
) -> str | None:
    if role not in _VARIANT_ROLES or mode not in ("baseline", "regression"):
        return None
    variants = variants_by_eval.get(eval_id, set())
    if len(variants) == 1:
        return next(iter(variants))
    return None


def _eval_agent_for_name(
    name: Any,
    variants_by_eval: dict[str, set[str]],
    mode: str | None,
) -> tuple[str, str, str] | None:
    """Return ``(eval_id, role, variant or "")`` for a recognized agent name."""
    if not isinstance(name, str):
        return None
    match = _AGENT_NAME_RE.fullmatch(_normalize_name(name))
    if not match:
        return None
    eval_id = f"eval-{int(match.group(1))}"
    role = match.group(2)
    if role not in _EVAL_ROLES or eval_id not in variants_by_eval:
        return None
    if role in _VARIANT_ROLES and match.group(3):
        prefix = "current" if match.group(3) == "with" else match.group(3)
        variant: str | None = f"{prefix}_skill"
    else:
        variant = _variant_for_agent(eval_id, role, variants_by_eval, mode)
    return eval_id, role, variant or ""


def _normalize_usage(
    raw: dict[str, Any],
    iteration_dir: Path,
    task_names: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if "modelMetrics" in raw and not isinstance(raw["modelMetrics"], dict):
        raise CopilotUsageError("Copilot usage model metrics have an unsupported structure")
    if "agentMetrics" in raw and not isinstance(raw["agentMetrics"], dict):
        raise CopilotUsageError("Copilot usage agent metrics have an unsupported structure")

    task_names = task_names or {}
    variants_by_eval, mode = _iteration_layout(iteration_dir)
    session_models, session_values = _model_usage(raw.get("modelMetrics"))
    session: dict[str, Any] = {"models": session_models}
    session.update(session_values)
    session_api_duration = _nonnegative_int(raw.get("totalApiDurationMs"))
    if session_api_duration is not None:
        session["total_api_duration_ms"] = session_api_duration

    grouped_eval: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    grouped_other: dict[tuple[str, tuple[str, ...]], list[dict[str, Any]]] = defaultdict(list)
    all_models = set(session_models)
    agent_metrics = raw.get("agentMetrics")
    if isinstance(agent_metrics, dict):
        for record_key in sorted(agent_metrics):
            record = agent_metrics[record_key]
            if not isinstance(record, dict):
                continue
            record_summary = _record_usage(record)
            all_models.update(record_summary.get("models", []))
            # Launch-time task name first, then a name-like record key (future
            # CLI layouts), then the legacy display name.
            attribution = None
            for candidate in (
                task_names.get(record_key),
                record_key,
                record.get("agentDisplayName"),
            ):
                attribution = _eval_agent_for_name(candidate, variants_by_eval, mode)
                if attribution is not None:
                    break
            if attribution is not None:
                grouped_eval[attribution].append(record_summary)
                continue

            label = _safe_other_label(record_key, record, task_names.get(record_key))
            model_key = tuple(record_summary.get("models", []))
            grouped_other[(label, model_key)].append(record_summary)

    session["models"] = sorted(all_models)
    eval_agents: list[dict[str, Any]] = []
    for (eval_id, role, variant), records in sorted(grouped_eval.items()):
        agent = {"eval_id": eval_id, "role": role, **_sum_record_values(records)}
        if variant:
            agent["variant"] = variant
        eval_agents.append(agent)

    other_agents: list[dict[str, Any]] = []
    for (label, _models), records in sorted(grouped_other.items()):
        other_agents.append({"label": label, **_sum_record_values(records)})

    useful = bool(
        session.get("models")
        or any(key != "models" for key in session)
        or eval_agents
        or other_agents
    )
    if not useful:
        raise CopilotUsageError("Copilot usage file contains no supported usage data")

    return {
        "schema_version": SCHEMA_VERSION,
        "source": SOURCE,
        "eval_count": len(variants_by_eval),
        "session": session,
        "eval_agents": eval_agents,
        "other_agents": other_agents,
    }


def load_task_names(events_path: Path) -> dict[str, str]:
    """Map Copilot CLI sub-agent ids to the task names chosen at launch.

    Joins ``tool.execution_start`` events of the ``task`` tool (which carry
    the requested ``name``) with ``subagent.started`` events (which carry the
    resulting ``agentId``) on their shared ``toolCallId``. Malformed lines and
    unrelated events are skipped. The returned names stay in memory only.
    """
    names_by_call: dict[str, str] = {}
    call_by_agent: dict[str, list[str]] = {}
    try:
        with events_path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not any(marker in line for marker in _EVENT_MARKERS):
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                data = event.get("data")
                if not isinstance(data, dict):
                    continue
                call_id = data.get("toolCallId")
                if not isinstance(call_id, str) or not call_id:
                    continue
                event_type = event.get("type")
                # Task starts made inside a sub-agent carry its agentId; they
                # are nested helpers, not eval agents launched by the runner.
                if event_type == "tool.execution_start" and "agentId" not in event:
                    arguments = data.get("arguments")
                    name = (
                        arguments.get("name") if isinstance(arguments, dict) else None
                    )
                    if data.get("toolName") == "task" and isinstance(name, str) and name:
                        names_by_call[call_id] = name
                elif event_type == "subagent.started":
                    agent_id = event.get("agentId")
                    if isinstance(agent_id, str) and agent_id:
                        call_by_agent.setdefault(agent_id, []).append(call_id)
    except OSError as exc:
        raise CopilotUsageError(
            "Copilot session events file could not be read"
        ) from exc
    task_names: dict[str, str] = {}
    for agent_id, call_ids in call_by_agent.items():
        for call_id in call_ids:
            if call_id in names_by_call:
                task_names[agent_id] = names_by_call[call_id]
                break
    return task_names


def load_copilot_usage(
    usage_path: Path,
    iteration_dir: Path,
    task_names: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Load and sanitize final Copilot usage data for one iteration.

    ``task_names`` (from ``load_task_names``) enables per-eval attribution of
    sub-agent usage recorded by current Copilot CLI versions.
    """
    try:
        raw = json.loads(usage_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CopilotUsageError("Copilot usage file could not be read or parsed") from exc
    if not isinstance(raw, dict):
        raise CopilotUsageError("Copilot usage file has an unsupported structure")
    return _normalize_usage(raw, iteration_dir, task_names)
