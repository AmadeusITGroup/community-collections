#!/usr/bin/env python3
"""Finalize ``outputs/metrics.json`` for every variant in an iteration.

Runs after PHASE 2 (executors). This is the single place where the final
per-variant ``outputs/metrics.json`` is assembled. It:

1. Reads the executor-written ``self_report`` + ``user_notes`` already in
   the file (if absent, stubs them).
2. If the parent orchestrator wrote an ``outputs/notification.json``
   sidecar next to ``metrics.json`` (capturing Task-return telemetry from
   hosts like Claude Code), merges it into ``metrics.notification`` and
   deletes the sidecar.
3. If a VS Code Copilot session debug log is available, scans the matching
   ``runSubagent-skill-eval-executor-*-<sid>.jsonl`` file and emits a
   ``host_telemetry`` block with log-derived tokens, turn count, tool
   calls, tool errors, and model.
4. Stamps a top-level ``metrics_source`` tag indicating which tool-count
   layer consumers should trust — ``"debug_log"`` when host_telemetry
   carries log-derived tool counts, otherwise ``"self_report"``.
5. Deletes any legacy ``execution.json`` / ``.notification.json`` left
   over from previous iteration layouts.

Final shape per ``outputs/metrics.json``::

    {
      "self_report":    { ... },   # executor, always present
      "user_notes":     { ... },   # executor, always present
      "notification":   { ... },   # optional, from parent sidecar
      "host_telemetry": { ... },   # harvester — always present, source tag inside
      "metrics_source": "debug_log" | "self_report"
    }

Usage::

    python finalize_metrics.py evals/<skill>/workspace/iteration-1
    python finalize_metrics.py evals/<skill>/workspace/iteration-2 \\
        --session-log /path/to/vscode/logs
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import _sandbox

if sys.stdout.isatty() and not os.environ.get("CI"):
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    NC = "\033[0m"
else:
    RED = GREEN = YELLOW = NC = ""

VARIANT_DIRS = ("current_skill", "without_skill")


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def to_iso_utc(value: Any) -> str | None:
    """Coerce a value (ISO string or epoch ms/sec) to ISO 8601 UTC."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:  # Heuristic: > 10^12 → ms, otherwise seconds
            ts = ts / 1000.0
        return (
            datetime.fromtimestamp(ts, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
    return None


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Variant discovery
# ---------------------------------------------------------------------------


def discover_variant_dirs(iteration_dir: Path) -> list[Path]:
    """Yield each existing variant directory under the iteration."""
    out: list[Path] = []
    for eval_dir in sorted(iteration_dir.iterdir()):
        if not eval_dir.is_dir() or not eval_dir.name.startswith("eval-"):
            continue
        for variant in VARIANT_DIRS:
            vd = eval_dir / variant
            if vd.is_dir():
                out.append(vd)
    return out


# ---------------------------------------------------------------------------
# Debug log scanning
# ---------------------------------------------------------------------------


_RESPONSE_PATH_RE = re.compile(r"([^\s`'\"]+/outputs/response\.md)")


def _list_executor_logs(session_log: Path) -> list[Path]:
    if not session_log.is_dir():
        return []
    return sorted(session_log.glob("runSubagent-skill-eval-executor-*.jsonl"))


def _scan_log(log_path: Path) -> dict[str, Any] | None:
    """Return aggregated metrics for a single executor debug log.

    The event discriminator is ``event["type"]`` (NOT ``event["name"]``).
    The debug log encodes the LLM model and tool name into ``name`` — e.g.
    ``"chat:claude-opus-4.7"`` for ``llm_request`` events and the tool name
    (``"read_file"``, ``"create_file"``, …) for ``tool_call`` events.
    """
    response_path: str | None = None
    ts_ms: int | None = None
    dur_ms: int | None = None
    input_tokens = 0
    output_tokens = 0
    turn_count = 0
    ttft: float | None = None
    tool_calls: dict[str, int] = {}
    tool_errors = 0
    models: list[str] = []

    try:
        for raw in log_path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue

            etype = event.get("type")
            ename = event.get("name")
            attrs = event.get("attrs") or event.get("attributes") or {}

            if response_path is None and etype == "user_message":
                blob = json.dumps(event)
                m = _RESPONSE_PATH_RE.search(blob)
                if m:
                    response_path = m.group(1)

            if etype == "subagent":
                ts_ms = event.get("ts") or attrs.get("ts") or ts_ms
                dur_ms = event.get("dur") or attrs.get("dur") or dur_ms

            elif etype == "llm_request":
                turn_count += 1
                in_t = attrs.get("inputTokens") or attrs.get("input_tokens") or 0
                out_t = attrs.get("outputTokens") or attrs.get("output_tokens") or 0
                input_tokens += int(in_t or 0)
                output_tokens += int(out_t or 0)
                if ttft is None:
                    ttft_val = attrs.get("ttft")
                    if isinstance(ttft_val, (int, float)):
                        ttft = float(ttft_val)
                model = attrs.get("model")
                if not model and isinstance(ename, str) and ename.startswith("chat:"):
                    model = ename.split(":", 1)[1]
                if model and model not in models:
                    models.append(model)

            elif etype == "tool_call":
                tname = ename or attrs.get("tool") or "unknown"
                tool_calls[tname] = tool_calls.get(tname, 0) + 1
                if attrs.get("status") == "error":
                    tool_errors += 1
    except OSError:
        return None

    if response_path is None and ts_ms is None and turn_count == 0:
        return None

    return {
        "response_path": response_path,
        "ts_ms": ts_ms,
        "dur_ms": dur_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "turn_count": turn_count,
        "ttft_ms_first_turn": ttft,
        "model": ",".join(models) if models else None,
        "tool_calls": tool_calls,
        "tool_errors": tool_errors,
        "total_tool_calls": sum(tool_calls.values()),
    }


def index_logs_by_variant(
    session_log: Path | None, iteration_dir: Path
) -> dict[Path, dict[str, Any]]:
    """Map variant_dir → log scan, picking the most recent log when duplicates exist."""
    by_variant: dict[Path, dict[str, Any]] = {}
    if session_log is None or not session_log.is_dir():
        return by_variant

    for log_path in _list_executor_logs(session_log):
        scan = _scan_log(log_path)
        if not scan or not scan.get("response_path"):
            continue
        rp = scan["response_path"]
        for vd in discover_variant_dirs(iteration_dir):
            target = (vd / "outputs" / "response.md").as_posix()
            if rp.endswith(target) or target.endswith(rp):
                prev = by_variant.get(vd)
                if prev is None or (scan.get("ts_ms") or 0) >= (prev.get("ts_ms") or 0):
                    by_variant[vd] = scan
                break
    return by_variant


# ---------------------------------------------------------------------------
# Per-variant finalization
# ---------------------------------------------------------------------------


def _response_mtime_iso(variant_dir: Path) -> str | None:
    resp = variant_dir / "outputs" / "response.md"
    if not resp.exists():
        return None
    return to_iso_utc(resp.stat().st_mtime)


def _empty_user_notes() -> dict[str, Any]:
    return {
        "skill_feedback": {
            "missing_from_skill": [],
            "ambiguous_instructions": [],
            "broken_references": [],
            "outdated_or_wrong": [],
        },
        "response_risks": [],
        "missing_inputs": [],
    }


def _ensure_executor_layers(metrics: dict[str, Any]) -> dict[str, Any]:
    """Ensure self_report + user_notes exist with the expected shape.

    When executors write a legacy flat shape (``tool_calls`` / ``user_notes`` at
    top level), fold it into ``self_report``. When anything is missing, fill in
    minimal stubs so downstream readers have a stable shape.
    """
    if "self_report" not in metrics or not isinstance(metrics.get("self_report"), dict):
        legacy = {
            k: metrics.pop(k)
            for k in (
                "tool_calls",
                "total_tool_calls",
                "total_steps",
                "files_created",
                "output_chars",
            )
            if k in metrics
        }
        metrics["self_report"] = legacy or {
            "tool_calls": {},
            "total_tool_calls": 0,
            "total_steps": 0,
            "files_created": [],
            "output_chars": 0,
        }
    if "user_notes" not in metrics or not isinstance(metrics.get("user_notes"), dict):
        metrics["user_notes"] = _empty_user_notes()
    # Drop any stray legacy harvester keys — this script is now canonical.
    for stale in ("tool_errors", "metrics_source"):
        if stale in metrics and stale == "metrics_source":
            # metrics_source is re-emitted at the end; keep it transient.
            continue
        metrics.pop(stale, None)
    return metrics


def _build_host_telemetry(
    variant_dir: Path,
    notification: dict | None,
    log_scan: dict | None,
    eval_metadata: dict | None,
) -> dict:
    """Assemble the host_telemetry block, layering sources by precedence.

    Precedence (highest first):

    1. debug_log (VS Code subagent logs) — most granular, wins when present
    2. notification (host-reported via parent sidecar)
    3. eval_metadata.prepared_at + ``response.md`` mtime (last resort)
    """
    block: dict[str, Any] = {}
    source = "wall_clock"

    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int | None = None
    total_tokens: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    turn_count: int | None = None
    model: str | None = None
    tool_calls: dict | None = None
    tool_errors: int | None = None
    total_tool_calls: int | None = None
    ttft: float | None = None

    # 1. Notification layer (base)
    if notification:
        started_at = to_iso_utc(notification.get("spawned_at"))
        completed_at = to_iso_utc(notification.get("returned_at"))
        nt = notification.get("total_tokens")
        if isinstance(nt, (int, float)):
            total_tokens = int(nt)
            source = "notification"
        nd = notification.get("duration_ms")
        if isinstance(nd, (int, float)):
            duration_ms = int(nd)
            source = "notification"

    # 2. Debug log layer (overrides, most granular)
    if log_scan:
        if log_scan.get("ts_ms") and log_scan.get("dur_ms"):
            ts_ms = int(log_scan["ts_ms"])
            d_ms = int(log_scan["dur_ms"])
            started_at = to_iso_utc(ts_ms)
            completed_at = to_iso_utc(ts_ms + d_ms)
            duration_ms = d_ms
            source = "debug_log"
        if log_scan.get("total_tokens"):
            total_tokens = int(log_scan["total_tokens"])
            input_tokens = int(log_scan.get("input_tokens") or 0)
            output_tokens = int(log_scan.get("output_tokens") or 0)
            source = "debug_log"
        if log_scan.get("turn_count"):
            turn_count = int(log_scan["turn_count"])
        if log_scan.get("model"):
            model = log_scan["model"]
        if log_scan.get("tool_calls"):
            tool_calls = dict(log_scan["tool_calls"])
            total_tool_calls = int(log_scan.get("total_tool_calls") or 0)
        if log_scan.get("tool_errors") is not None:
            tool_errors = int(log_scan.get("tool_errors") or 0)
        if log_scan.get("ttft_ms_first_turn") is not None:
            ttft = log_scan["ttft_ms_first_turn"]

    # 3. Last-resort fallbacks
    if started_at is None and eval_metadata:
        prepared_at = eval_metadata.get("prepared_at")
        if isinstance(prepared_at, str):
            started_at = prepared_at
    if completed_at is None:
        completed_at = _response_mtime_iso(variant_dir)

    # Derive duration when no numeric value has been provided.
    if duration_ms is None:
        s_dt = _parse_iso(started_at)
        c_dt = _parse_iso(completed_at)
        if s_dt and c_dt:
            delta_ms = int((c_dt - s_dt).total_seconds() * 1000)
            if delta_ms >= 0:
                duration_ms = delta_ms

    if started_at:
        block["started_at"] = started_at
    if completed_at:
        block["completed_at"] = completed_at
    if duration_ms is not None:
        block["duration_ms"] = duration_ms
        block["total_duration_seconds"] = round(duration_ms / 1000.0, 3)
    if total_tokens is not None:
        block["total_tokens"] = total_tokens
    if input_tokens is not None:
        block["input_tokens"] = input_tokens
    if output_tokens is not None:
        block["output_tokens"] = output_tokens
    if turn_count is not None:
        block["turn_count"] = turn_count
    if ttft is not None:
        block["ttft_ms_first_turn"] = ttft
    if model:
        block["model"] = model
    if tool_calls is not None:
        block["tool_calls"] = tool_calls
        block["total_tool_calls"] = (
            total_tool_calls
            if total_tool_calls is not None
            else sum(tool_calls.values())
        )
    if tool_errors is not None:
        block["tool_errors"] = tool_errors

    block["source"] = source
    return block


def finalize_variant(variant_dir: Path, log_scan: dict | None) -> tuple[str, str]:
    """Write the consolidated ``outputs/metrics.json`` for one variant.

    Returns (host_telemetry.source, metrics_source).
    """
    outputs_dir = variant_dir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = outputs_dir / "metrics.json"

    metrics = load_json(metrics_path) or {}
    if not isinstance(metrics, dict):
        metrics = {}
    metrics = _ensure_executor_layers(metrics)

    # Parent sidecar — visible, merged-and-deleted
    notification_path = outputs_dir / "notification.json"
    notification = load_json(notification_path)
    if isinstance(notification, dict):
        metrics["notification"] = notification
    elif notification is not None:
        # Non-dict sidecar — keep it verbatim but log a warning path.
        metrics["notification"] = {"raw": notification}

    # host_telemetry from harvested sources
    eval_metadata = load_json(variant_dir.parent / "eval_metadata.json")
    metrics["host_telemetry"] = _build_host_telemetry(
        variant_dir, metrics.get("notification"), log_scan, eval_metadata
    )

    # metrics_source: single downstream tag
    if metrics["host_telemetry"].get("tool_calls"):
        metrics["metrics_source"] = "debug_log"
    else:
        metrics["metrics_source"] = "self_report"

    write_json(metrics_path, metrics)

    # Clean up sidecar (succeeded) and any legacy artifacts from prior layouts.
    if notification_path.exists():
        notification_path.unlink()
    for legacy_name in (".notification.json",):
        legacy = variant_dir / legacy_name
        if legacy.exists():
            legacy.unlink()
    legacy_execution = variant_dir / "execution.json"
    if legacy_execution.exists():
        legacy_execution.unlink()

    return metrics["host_telemetry"].get("source", "wall_clock"), metrics[
        "metrics_source"
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def verify_no_tree_escape(
    anchor: Path, baseline_dirty: list[str] | None
) -> tuple[bool, str]:
    """Return (ok, message). ok=False means the run wrote to a path OUTSIDE the
    gitignored per-variant sandbox — i.e. a skill escaped write-isolation and
    touched the real repo tree (the skill-under-test package, another eval's
    files, source code, anywhere). Correct runs write only inside the gitignored
    sandbox/, so they add nothing to `git status`.

    baseline_dirty is the list recorded at PREPARE (paths already dirty before
    executors ran); those are subtracted so pre-existing local edits are not
    mistaken for escapes. None (legacy iterations predating the snapshot) skips
    the check (ok=True). Advisory only — callers warn loudly but do not fail the
    run, so a benchmark is still produced.
    """
    if baseline_dirty is None:
        return True, ""
    escaped = sorted(_sandbox.git_dirty_paths(anchor) - set(baseline_dirty))
    if not escaped:
        return True, ""
    listing = "\n".join(f"  - {p}" for p in escaped)
    return False, (
        "WARNING: this run wrote OUTSIDE the per-variant sandbox — a skill "
        "escaped write-isolation and modified the real repo tree:\n"
        f"{listing}\n"
        "A skill under evaluation must write only inside its variant's sandbox/ "
        "copy. Restore these paths (e.g. `git checkout -- <path>`, delete stray "
        "files) before trusting this run or starting the next iteration."
    )


def finalize_iteration(iteration_dir: Path, session_log: Path | None) -> int:
    if not iteration_dir.is_dir():
        print(f"{RED}Iteration dir not found: {iteration_dir}{NC}")
        return 1

    variants = discover_variant_dirs(iteration_dir)
    if not variants:
        print(f"{YELLOW}No variant dirs found under {iteration_dir}{NC}")
        return 0

    by_variant = index_logs_by_variant(session_log, iteration_dir)
    if session_log is not None and not by_variant:
        print(
            f"{YELLOW}warn: session log directory {session_log} contained no "
            f"matching executor logs (runSubagent-skill-eval-executor-*.jsonl). "
            f"host_telemetry will fall back to notification / wall_clock.{NC}",
            file=sys.stderr,
        )

    source_counts = {"notification": 0, "debug_log": 0, "wall_clock": 0}
    metrics_counts = {"debug_log": 0, "self_report": 0}

    for vd in variants:
        ht_src, ms_src = finalize_variant(vd, by_variant.get(vd))
        source_counts[ht_src] = source_counts.get(ht_src, 0) + 1
        metrics_counts[ms_src] = metrics_counts.get(ms_src, 0) + 1

    if session_log is None:
        print(
            f"{YELLOW}note: no --session-log provided and "
            f"$VSCODE_TARGET_SESSION_LOG was unset or empty. Token/turn counts "
            f"and per-tool breakdowns are unavailable (debug_log=0).{NC}",
            file=sys.stderr,
        )

    # Defense-in-depth: confirm the run stayed inside the per-variant sandbox
    # and did not write to the real repo tree.
    iter_config = load_json(iteration_dir / "iteration_config.json") or {}
    baseline_dirty = iter_config.get("git_status_baseline")
    ok, guard_msg = verify_no_tree_escape(iteration_dir, baseline_dirty)
    if not ok:
        print(guard_msg, file=sys.stderr)

    print(
        f"{GREEN}Finalized{NC} {len(variants)} variant dirs: "
        f"host_telemetry.source={source_counts}, metrics_source={metrics_counts}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Finalize outputs/metrics.json for every variant in an iteration."
    )
    parser.add_argument(
        "iteration_dir",
        type=Path,
        help="Path to the iteration directory (e.g. evals/<skill>/workspace/iteration-1)",
    )
    parser.add_argument(
        "--session-log",
        type=Path,
        default=None,
        help="VS Code debug log directory (defaults to $VSCODE_TARGET_SESSION_LOG)",
    )
    args = parser.parse_args()

    session_log = args.session_log
    # argparse converts ``--session-log ""`` (e.g. shell-expanded empty var)
    # into ``Path("")``, which resolves to cwd and silently matches nothing.
    # Treat any falsy / empty / non-directory value as "not provided" and
    # fall back to the env var.
    if session_log is not None and str(session_log).strip() in ("", "."):
        print(
            "warn: --session-log was empty (likely an unexpanded shell variable "
            "such as $VSCODE_TARGET_SESSION_LOG); falling back to the "
            "environment and then to disk-based sources",
            file=sys.stderr,
        )
        session_log = None
    if session_log is None:
        env = os.environ.get("VSCODE_TARGET_SESSION_LOG")
        if env and env.strip():
            session_log = Path(env)
    if session_log is not None:
        session_log = session_log.resolve()
        if not session_log.is_dir():
            print(
                f"warn: --session-log {session_log} is not a directory; "
                "debug_log source will be unavailable",
                file=sys.stderr,
            )
            session_log = None

    return finalize_iteration(args.iteration_dir.resolve(), session_log)


if __name__ == "__main__":
    raise SystemExit(main())
