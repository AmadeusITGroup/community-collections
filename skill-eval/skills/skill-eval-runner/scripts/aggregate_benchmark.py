#!/usr/bin/env python3
"""Aggregate evaluation results into benchmark.json and benchmark.md.

Reads each variant's ``grading.json`` (expectations + claims + eval_feedback),
``outputs/metrics.json`` (self_report + host_telemetry + user_notes, written by
``finalize_metrics.py``), and the per-eval ``comparison.json`` from a workspace
iteration directory and produces consolidated benchmark outputs.

Usage:
    python aggregate_benchmark.py evals/<skill>/workspace/iteration-1 \\
        --skill-name <skill>

    # For iteration 2+ with baseline reuse:
    python aggregate_benchmark.py evals/<skill>/workspace/iteration-2 \\
        --skill-name <skill> \\
        --baseline-iteration evals/<skill>/workspace/iteration-1
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

if sys.stdout.isatty() and not os.environ.get("CI"):
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    NC = "\033[0m"
else:
    RED = GREEN = YELLOW = NC = ""

SEPARATOR = "━" * 60

CONFIGURATIONS = ("current_skill", "without_skill", "previous_skill")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def calculate_stats(values: list[float]) -> dict:
    if not values:
        return {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0}
    n = len(values)
    mean = sum(values) / n
    if n > 1:
        variance = sum((v - mean) ** 2 for v in values) / (n - 1)
        stddev = math.sqrt(variance)
    else:
        stddev = 0.0
    return {
        "mean": round(mean, 4),
        "stddev": round(stddev, 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def expectation_match_key(text: str | None) -> str:
    """Normalized key for pairing the same expectation across variants.

    Graders sometimes keep the leading ``[auto] `` prefix and sometimes strip
    it, so exact-string matching would fail to line up the same expectation
    across variants (surfacing as phantom "No data" cells in the report).
    Strip the prefix and collapse whitespace so matching is prefix- and
    spacing-insensitive.
    """
    s = re.sub(r"^\s*\[auto\]\s*", "", str(text or ""), flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", s).strip()


def _find_baseline_eval_dir(baseline_dir: Path, eval_id: int) -> Path | None:
    """Find an eval directory in baseline_dir matching eval_id."""
    for d in baseline_dir.iterdir():
        if not d.is_dir() or not d.name.startswith("eval-"):
            continue
        match = re.match(r"eval-(\d+)-", d.name)
        if match and int(match.group(1)) == eval_id:
            return d
    return None


# ---------------------------------------------------------------------------
# Core aggregation
# ---------------------------------------------------------------------------


def discover_eval_dirs(iteration_dir: Path) -> list[Path]:
    return sorted(
        d for d in iteration_dir.iterdir() if d.is_dir() and d.name.startswith("eval-")
    )


def build_runs(
    eval_dirs: list[Path],
    baseline_dir: Path | None = None,
    iteration_config: dict | None = None,
) -> list[dict]:
    runs: list[dict] = []
    default_baseline_iter = (
        iteration_config.get("baseline_iteration") if iteration_config else None
    )

    for idx, eval_dir in enumerate(eval_dirs, start=1):
        meta = load_json(eval_dir / "eval_metadata.json")
        fallback_name = eval_dir.name.removeprefix("eval-")
        eval_id = meta.get("id", idx) if meta else idx
        eval_name = meta.get("name", fallback_name) if meta else fallback_name
        eval_mode = meta.get("eval_mode", "baseline") if meta else "baseline"
        eval_baseline_iter = (
            meta.get("baseline_iteration") if meta else None
        ) or default_baseline_iter

        for config in CONFIGURATIONS:
            config_dir = eval_dir / config
            source_iteration = None

            # current_skill: always in this iteration's eval_dir (no rewrite).
            # without_skill: for regression evals, source from the sticky baseline
            #                iteration. For baseline evals, use the local dir.
            # previous_skill: only exists for regression evals; it's N-1's
            #                 current_skill, reached via meta.previous_path.
            if config == "without_skill" and eval_mode == "regression":
                resolved = None
                if meta and meta.get("baseline_path"):
                    # baseline_path is written by prepare_workspace.py as
                    # "../iteration-N/<eval-dir>" — relative to the iteration
                    # dir (eval_dir.parent), not eval_dir itself.
                    candidate = (eval_dir.parent / meta["baseline_path"]).resolve()
                    if candidate.is_dir():
                        resolved = candidate
                if resolved is None and baseline_dir:
                    resolved = _find_baseline_eval_dir(baseline_dir, eval_id)
                if resolved is None:
                    continue
                config_dir = resolved / "without_skill"
                source_iteration = eval_baseline_iter
            elif config == "previous_skill":
                if eval_mode != "regression":
                    continue
                if not meta or not meta.get("previous_path"):
                    continue
                candidate = (eval_dir.parent / meta["previous_path"]).resolve()
                if not candidate.is_dir():
                    continue
                # previous_skill is N-1's current_skill dir.
                config_dir = candidate / "current_skill"
                source_iteration = meta.get("previous_iteration")

            grading = load_json(config_dir / "grading.json")
            if grading is None:
                continue

            summary = grading.get("summary", {})
            # New layout: outputs/metrics.json is the single source of truth
            # for execution telemetry, owned by finalize_metrics.py. Contains
            # self_report (executor) + host_telemetry (harvester) + optional
            # notification block + user_notes (pass-through from executor).
            metrics = load_json(config_dir / "outputs" / "metrics.json") or {}
            host_telemetry = metrics.get("host_telemetry") or {}
            self_report = metrics.get("self_report") or {}

            # Prefer log-derived (host_telemetry) tool counts when present,
            # fall back to executor self_report.
            total_tool_calls = host_telemetry.get("total_tool_calls")
            if total_tool_calls is None:
                total_tool_calls = self_report.get("total_tool_calls")

            result = {
                "pass_rate": summary.get("pass_rate", 0.0),
                "passed": summary.get("passed", 0),
                "failed": summary.get("failed", 0),
                "total": summary.get("total", 0),
                "time_seconds": host_telemetry.get("total_duration_seconds")
                or ((host_telemetry.get("duration_ms") or 0) / 1000.0),
                "tokens": host_telemetry.get("total_tokens") or 0,
                "model": host_telemetry.get("model"),
                "total_tool_calls": total_tool_calls,
                "total_steps": self_report.get("total_steps"),
                "tool_errors": host_telemetry.get("tool_errors"),
                "output_chars": self_report.get("output_chars"),
                "metrics_source": metrics.get("metrics_source"),
                "source": host_telemetry.get("source"),
            }

            expectations = [
                {
                    "text": exp.get("text", ""),
                    "passed": exp.get("passed", False),
                    "evidence": exp.get("evidence", []),
                }
                for exp in grading.get("expectations", [])
            ]

            run = {
                "eval_id": eval_id,
                "eval_name": eval_name,
                "configuration": config,
                "result": result,
                "expectations": expectations,
            }
            if source_iteration is not None:
                run["source_iteration"] = source_iteration

            runs.append(run)
    return runs


def build_run_summary(runs: list[dict]) -> dict:
    base_metrics = ("pass_rate", "time_seconds", "tokens", "tool_calls", "steps")
    config_metrics: dict[str, dict[str, list[float]]] = {
        config: {m: [] for m in base_metrics} for config in CONFIGURATIONS
    }

    for run in runs:
        config = run["configuration"]
        if config not in config_metrics:
            continue
        result = run["result"]
        config_metrics[config]["pass_rate"].append(result["pass_rate"])
        config_metrics[config]["time_seconds"].append(result["time_seconds"])
        config_metrics[config]["tokens"].append(float(result["tokens"]))
        if result.get("total_tool_calls") is not None:
            config_metrics[config]["tool_calls"].append(
                float(result["total_tool_calls"])
            )
        if result.get("total_steps") is not None:
            config_metrics[config]["steps"].append(float(result["total_steps"]))

    summary: dict = {}
    for config in CONFIGURATIONS:
        # Skip empty previous_skill bucket to keep summary clean for baseline-only runs.
        if config == "previous_skill" and not config_metrics[config]["pass_rate"]:
            continue
        bucket = {
            metric: calculate_stats(config_metrics[config][metric])
            for metric in ("pass_rate", "time_seconds", "tokens")
        }
        for opt in ("tool_calls", "steps"):
            if config_metrics[config][opt]:
                bucket[opt] = calculate_stats(config_metrics[config][opt])
        summary[config] = bucket

    ws = summary.get("current_skill", {})
    wos = summary.get("without_skill", {})
    delta: dict[str, str] = {}
    for metric in ("pass_rate", "time_seconds", "tokens"):
        ws_mean = ws.get(metric, {}).get("mean", 0.0)
        wos_mean = wos.get(metric, {}).get("mean", 0.0)
        diff = ws_mean - wos_mean
        sign = "+" if diff >= 0 else ""
        delta[metric] = f"{sign}{round(diff, 4)}"

    summary["delta"] = delta
    return summary


def build_regression_delta(
    runs: list[dict], previous_dir: Path | None
) -> dict[str, str] | None:
    """Compute current_skill vs previous iteration's current_skill delta."""
    if not previous_dir:
        return None
    prev_benchmark = load_json(previous_dir / "benchmark.json")
    if not prev_benchmark:
        return None

    prev_summary = prev_benchmark.get("run_summary", {}).get("current_skill", {})
    if not prev_summary:
        return None

    current_ws_rates = [
        r["result"]["pass_rate"] for r in runs if r["configuration"] == "current_skill"
    ]
    if not current_ws_rates:
        return None

    reg_delta: dict[str, str] = {}
    for metric in ("pass_rate", "time_seconds", "tokens"):
        prev_mean = prev_summary.get(metric, {}).get("mean", 0.0)
        if metric == "tokens":
            current_vals = [
                float(r["result"]["tokens"])
                for r in runs
                if r["configuration"] == "current_skill"
            ]
        else:
            current_vals = [
                r["result"][metric]
                for r in runs
                if r["configuration"] == "current_skill"
            ]
        cur_mean = sum(current_vals) / len(current_vals) if current_vals else 0.0
        diff = cur_mean - prev_mean
        sign = "+" if diff >= 0 else ""
        reg_delta[metric] = f"{sign}{round(diff, 4)}"

    return reg_delta


def build_comparisons(eval_dirs: list[Path]) -> dict:
    wins = {
        "current_skill_wins": 0,
        "without_skill_wins": 0,
        "ties": 0,
    }
    regression = {
        "current_wins": 0,
        "previous_wins": 0,
        "regression_ties": 0,
    }
    has_regression = False

    for eval_dir in eval_dirs:
        comp = load_json(eval_dir / "comparison.json")
        if comp is None:
            continue

        comp_mode = comp.get("comparison_mode", "baseline")
        winner = (comp.get("winner_variant") or "").lower()

        if comp_mode == "regression":
            has_regression = True
            if winner == "current_skill":
                regression["current_wins"] += 1
            elif winner == "previous_skill":
                regression["previous_wins"] += 1
            else:
                regression["regression_ties"] += 1
        else:
            if winner == "current_skill":
                wins["current_skill_wins"] += 1
            elif winner == "without_skill":
                wins["without_skill_wins"] += 1
            else:
                wins["ties"] += 1

    if has_regression:
        wins.update(regression)
    return wins


def build_per_eval_comparisons(eval_dirs: list[Path]) -> list[dict]:
    """Surface the comparator's per-eval reasoning, winner and rubric scores.

    This is what ``skill-eval-analyzer`` uses to cross-reference grader
    verdicts with the blind comparator — previously reconstructed via shell
    loops.  Also emits a per-expectation cross-variant breakdown built from
    each variant's ``grading.json``.
    """
    out: list[dict] = []
    for eval_dir in eval_dirs:
        comp = load_json(eval_dir / "comparison.json")
        if comp is None:
            continue
        meta = load_json(eval_dir / "eval_metadata.json") or {}

        # Per-expectation cross-variant status
        per_expectation: list[dict] = []
        grading_by_variant: dict[str, dict] = {}

        # current_skill and (baseline-mode) without_skill live locally.
        for variant_dir in eval_dir.iterdir():
            if not variant_dir.is_dir():
                continue
            if variant_dir.name not in (
                "current_skill",
                "without_skill",
                "previous_skill",
            ):
                continue
            g = load_json(variant_dir / "grading.json")
            if g:
                grading_by_variant[variant_dir.name] = g

        # Regression evals: without_skill grading lives under baseline_path,
        # previous_skill grading under previous_path/current_skill.
        eval_mode = meta.get("eval_mode", "baseline")
        if eval_mode == "regression":
            if "without_skill" not in grading_by_variant and meta.get("baseline_path"):
                baseline_eval = (eval_dir.parent / meta["baseline_path"]).resolve()
                g = load_json(baseline_eval / "without_skill" / "grading.json")
                if g:
                    grading_by_variant["without_skill"] = g
            if "previous_skill" not in grading_by_variant and meta.get("previous_path"):
                previous_eval = (eval_dir.parent / meta["previous_path"]).resolve()
                g = load_json(previous_eval / "current_skill" / "grading.json")
                if g:
                    grading_by_variant["previous_skill"] = g

        # Pair expectations across variants by a normalized match key so a
        # dropped/kept `[auto]` prefix doesn't split one expectation into two
        # rows. `keys` preserves first-seen order; `display_by_key` remembers a
        # human-readable label per key.
        keys: list[str] = []
        seen: set[str] = set()
        display_by_key: dict[str, str] = {}
        for g in grading_by_variant.values():
            for exp in g.get("expectations", []):
                t = exp.get("text")
                if not t:
                    continue
                k = expectation_match_key(t)
                if k not in seen:
                    keys.append(k)
                    seen.add(k)
                    display_by_key[k] = t

        for key in keys:
            row: dict = {"text": display_by_key.get(key, key)}
            for variant, g in grading_by_variant.items():
                for exp in g.get("expectations", []):
                    if expectation_match_key(exp.get("text")) == key:
                        row[variant] = {
                            "passed": exp.get("passed"),
                            "evidence": exp.get("evidence", []),
                        }
                        break
            per_expectation.append(row)

        out.append(
            {
                "eval_id": meta.get("id"),
                "eval_name": meta.get("name", eval_dir.name),
                "comparison_mode": comp.get("comparison_mode", "baseline"),
                "winner_variant": comp.get("winner_variant"),
                "winner": comp.get("winner"),
                "reasoning": comp.get("reasoning"),
                "assignment": comp.get("assignment"),
                "rubric_scores": {
                    k: (comp.get("rubric", {}).get(k, {}) or {}).get("overall_score")
                    for k in ("A", "B")
                },
                "baseline_iteration": comp.get("baseline_iteration"),
                "previous_iteration": comp.get("previous_iteration"),
                "per_expectation": per_expectation,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Grading path validation (A3)
# ---------------------------------------------------------------------------


def detect_misplaced_grading(eval_dirs: list[Path]) -> list[Path]:
    """Return paths to grading.json files that are under {variant}/outputs/ when
    they should live at the variant root. A silently misplaced file causes the
    aggregator to skip that variant entirely and report a 0% pass rate.
    """
    misplaced: list[Path] = []
    for eval_dir in eval_dirs:
        for variant_dir in eval_dir.iterdir():
            if not variant_dir.is_dir():
                continue
            if variant_dir.name not in (
                "current_skill",
                "without_skill",
                "previous_skill",
            ):
                continue
            bad = variant_dir / "outputs" / "grading.json"
            good = variant_dir / "grading.json"
            if bad.exists() and not good.exists():
                misplaced.append(bad)
    return misplaced


def fix_misplaced_grading(paths: list[Path]) -> list[tuple[Path, Path]]:
    """Move each misplaced grading.json up to the variant root. Returns the
    list of (src, dest) pairs that were moved successfully.
    """
    moved: list[tuple[Path, Path]] = []
    for bad in paths:
        good = bad.parent.parent / "grading.json"
        if good.exists():
            # Should not happen because detect_misplaced_grading filters these,
            # but guard regardless so we never overwrite existing data.
            continue
        bad.rename(good)
        moved.append((bad, good))
    return moved


# ---------------------------------------------------------------------------
# Derived analytic views (B1, B2)
# ---------------------------------------------------------------------------


_SEVERITY_THRESHOLDS = (
    (0.5, "blocking"),
    (0.3, "major"),
    (0.0, "minor"),
)


def _severity_from_gap(gap: float) -> str:
    abs_gap = abs(gap)
    for threshold, label in _SEVERITY_THRESHOLDS:
        if abs_gap >= threshold:
            return label
    return "minor"


def _pass_rate_by_variant(runs: list[dict]) -> dict[tuple[int, str], float]:
    """Index pass_rate by (eval_id, configuration)."""
    out: dict[tuple[int, str], float] = {}
    for run in runs:
        eid = run.get("eval_id")
        cfg = run.get("configuration")
        if eid is None or not cfg:
            continue
        out[(eid, cfg)] = run.get("result", {}).get("pass_rate", 0.0)
    return out


def _resolve_variant_score(comp: dict, variant: str) -> float | None:
    """Return the comparator rubric overall_score assigned to ``variant``."""
    assignment = comp.get("assignment") or {}
    for slot in ("A", "B"):
        if assignment.get(slot) == variant:
            return (comp.get("rubric_scores") or {}).get(slot)
    return None


def build_contradictions(
    runs: list[dict], per_eval_comparisons: list[dict]
) -> list[dict]:
    """Flag evals where grader pass_rate and comparator winner disagree by a wide margin.

    Baseline mode — alternate variant is ``without_skill``.
    Regression mode — alternate variant is ``previous_skill``.

    Thresholds: gap >= 0.20 in grader pass_rate but comparator chose the other
    side (or tied). Severity scales with the magnitude of the gap.
    """
    rates = _pass_rate_by_variant(runs)
    out: list[dict] = []
    for comp in per_eval_comparisons:
        eid = comp.get("eval_id")
        if eid is None:
            continue
        mode = comp.get("comparison_mode", "baseline")
        alternate = "without_skill" if mode == "baseline" else "previous_skill"
        cs_rate = rates.get((eid, "current_skill"))
        alt_rate = rates.get((eid, alternate))
        if cs_rate is None or alt_rate is None:
            continue
        gap = cs_rate - alt_rate
        winner = (comp.get("winner_variant") or "").lower()
        is_tie = winner in ("", "tie")
        # Contradiction when grader and comparator disagree by >= 0.20.
        if gap >= 0.20 and (winner == alternate or is_tie):
            grader_preferred = "current_skill"
        elif gap <= -0.20 and winner == "current_skill":
            grader_preferred = alternate
        else:
            continue
        out.append(
            {
                "eval_id": eid,
                "eval_name": comp.get("eval_name"),
                "comparison_mode": mode,
                "current_skill_pass_rate": round(cs_rate, 4),
                "alternate_pass_rate": round(alt_rate, 4),
                "alternate_variant": alternate,
                "grader_preferred": grader_preferred,
                "comparator_winner": comp.get("winner_variant"),
                "rubric_scores": {
                    "current_skill": _resolve_variant_score(comp, "current_skill"),
                    alternate: _resolve_variant_score(comp, alternate),
                },
                "reasoning": comp.get("reasoning"),
                "severity": _severity_from_gap(gap),
            }
        )
    # Sort by severity descending, then by absolute gap.
    severity_order = {"blocking": 0, "major": 1, "minor": 2}
    out.sort(
        key=lambda r: (
            severity_order.get(r["severity"], 99),
            -abs(r["current_skill_pass_rate"] - r["alternate_pass_rate"]),
        )
    )
    return out


def build_skill_regressions(runs: list[dict], per_eval_comparisons: list[dict]) -> dict:
    """Evals where the skill does worse than the baseline or previous iteration.

    An eval lands in a bucket when the blind comparator preferred the alternate
    variant (``without_skill`` for baseline mode, ``previous_skill`` for
    regression mode). Sorted by pass-rate delta (worst regressions first).
    """
    rates = _pass_rate_by_variant(runs)
    vs_baseline: list[dict] = []
    vs_previous: list[dict] = []
    for comp in per_eval_comparisons:
        eid = comp.get("eval_id")
        if eid is None:
            continue
        mode = comp.get("comparison_mode", "baseline")
        winner = (comp.get("winner_variant") or "").lower()
        alternate = "without_skill" if mode == "baseline" else "previous_skill"
        if winner != alternate:
            continue
        cs_rate = rates.get((eid, "current_skill"), 0.0) or 0.0
        alt_rate = rates.get((eid, alternate), 0.0) or 0.0
        delta = round(cs_rate - alt_rate, 4)
        reasoning = comp.get("reasoning") or ""
        entry = {
            "eval_id": eid,
            "eval_name": comp.get("eval_name"),
            "current_pass_rate": round(cs_rate, 4),
            "alternate_pass_rate": round(alt_rate, 4),
            "alternate_variant": alternate,
            "pass_rate_delta": delta,
            "severity": _severity_from_gap(delta),
            "comparator_reasoning": reasoning,
        }
        if mode == "baseline":
            vs_baseline.append(entry)
        else:
            vs_previous.append(entry)
    vs_baseline.sort(key=lambda e: e["pass_rate_delta"])
    vs_previous.sort(key=lambda e: e["pass_rate_delta"])
    return {"vs_baseline": vs_baseline, "vs_previous": vs_previous}


_POSITIVE_CUES = re.compile(
    r"(preferred|no contradictions|all \d+ evals|strongly positive"
    r"|agrees with grader|\bwins\b|improvement|improved|\+\d)",
    re.IGNORECASE,
)


def _derive_intent(category: str, text: str, metrics: dict | None) -> str:
    """Map a note's category (+ optional metrics.impact) onto an intent bucket.

    The analyzer agent is asked to emit `intent` directly; this fallback runs
    only when the field is absent (legacy notes). Keep the heuristic narrow —
    any drift should be corrected in the analyzer prompt, not here.
    """
    metrics = metrics or {}
    impact = str(metrics.get("impact") or metrics.get("severity") or "").lower()
    if category in (
        "non_discriminating",
        "skill_hurts",
        "regression",
        "contradiction",
        "broken",
    ):
        return "action_needed"
    if category == "skill_feedback":
        return "action_needed" if impact in ("blocking", "major") else "pattern"
    if category in ("skill_value", "improvement", "cost_saving"):
        return "positive_signal"
    if category == "new_eval":
        return "pattern"
    if category == "observation":
        return "positive_signal" if _POSITIVE_CUES.search(text or "") else "pattern"
    return "pattern"


def _derive_headline(text: str) -> str:
    """Short imperative-mood title — first sentence up to 90 chars."""
    t = (text or "").strip()
    if not t:
        return "Observation"
    dot = t.find(". ")
    if 8 < dot < 90:
        return t[:dot]
    return t if len(t) <= 90 else t[:87] + "\u2026"


def _normalize_note(item: str | dict) -> dict:
    """Normalize a note to structured format. Accepts both strings and dicts.

    Legacy notes (strings, or dicts lacking `intent`/`headline`/`suggestion`)
    get heuristic derivation so the frontend's grouped-callouts renderer
    always has a stable shape. Analyzer-emitted fields win.
    """
    if isinstance(item, dict) and "category" in item and "text" in item:
        note = dict(item)  # shallow copy — don't mutate caller state
    else:
        note = {"category": "observation", "text": str(item)}

    category = note.get("category") or "observation"
    text = note.get("text") or ""
    raw_metrics = note.get("metrics")
    metrics: dict = raw_metrics if isinstance(raw_metrics, dict) else {}

    if not note.get("intent"):
        note["intent"] = _derive_intent(category, text, metrics)
    if not note.get("headline"):
        note["headline"] = _derive_headline(text)
    # `suggestion` is optional; only emit a default for action_needed notes
    # when the analyzer didn't provide one.
    if note["intent"] == "action_needed" and not note.get("suggestion"):
        if category == "non_discriminating":
            note["suggestion"] = "Reconsider or replace with signal-carrying variants."
        elif category == "skill_hurts":
            note["suggestion"] = (
                "Inspect the comparator reasoning and adjust the skill to "
                "cover the regressed case."
            )

    return note


SKILL_FEEDBACK_CATEGORIES = (
    "missing_from_skill",
    "ambiguous_instructions",
    "broken_references",
    "outdated_or_wrong",
)
IMPACT_LEVELS = ("blocking", "major", "minor")


def _load_user_notes(variant_dir: Path) -> dict | None:
    """Return user_notes from ``variant_dir/outputs/metrics.json``.

    finalize_metrics.py guarantees the key exists (possibly with empty lists)
    once it runs. Missing file or non-dict payload → None so callers can skip.
    """
    metrics = load_json(variant_dir / "outputs" / "metrics.json")
    if not isinstance(metrics, dict):
        return None
    notes = metrics.get("user_notes")
    if not isinstance(notes, dict):
        return None
    return notes


def _build_skill_feedback_rollup(
    eval_dirs: list[Path],
    previous_dir: Path | None,
) -> dict:
    """Aggregate executor-written skill feedback across evals.

    Source: each eval's ``current_skill/outputs/metrics.json.user_notes``
    (written by the executor, untouched by the grader). ``without_skill``
    contributes ``response_risks`` / ``missing_inputs`` but never
    ``skill_feedback`` (baseline doesn't read the skill).
    """
    totals = {cat: 0 for cat in SKILL_FEEDBACK_CATEGORIES}
    by_impact = {lvl: 0 for lvl in IMPACT_LEVELS}
    items: list[dict] = []
    ref_counter: dict[str, dict] = {}
    response_risks: list[dict] = []
    missing_inputs: list[dict] = []

    for eval_dir in eval_dirs:
        meta = load_json(eval_dir / "eval_metadata.json") or {}
        eval_id = meta.get("id")
        eval_name = meta.get("name", eval_dir.name)

        # skill_feedback: current_skill only
        cs_uns = _load_user_notes(eval_dir / "current_skill")
        if cs_uns:
            sf = cs_uns.get("skill_feedback") or {}
            for category in SKILL_FEEDBACK_CATEGORIES:
                for entry in sf.get(category) or []:
                    if not isinstance(entry, dict):
                        continue
                    topic = entry.get("topic") or ""
                    impact = entry.get("impact") or "minor"
                    reference = entry.get("reference") or ""
                    if impact not in by_impact:
                        impact = "minor"
                    totals[category] += 1
                    by_impact[impact] += 1
                    items.append(
                        {
                            "category": category,
                            "topic": topic,
                            "impact": impact,
                            "reference": reference,
                            "eval_id": eval_id,
                            "eval_name": eval_name,
                        }
                    )
                    if reference:
                        bucket = ref_counter.setdefault(
                            reference,
                            {"reference": reference, "count": 0, "eval_ids": []},
                        )
                        bucket["count"] += 1
                        if eval_id is not None and eval_id not in bucket["eval_ids"]:
                            bucket["eval_ids"].append(eval_id)

        # response_risks + missing_inputs: both variants contribute
        for variant in ("current_skill", "without_skill", "previous_skill"):
            uns = _load_user_notes(eval_dir / variant)
            if not uns:
                continue
            for risk in uns.get("response_risks") or []:
                if not isinstance(risk, dict):
                    continue
                response_risks.append(
                    {
                        **risk,
                        "eval_id": eval_id,
                        "eval_name": eval_name,
                        "variant": variant,
                    }
                )
            for mi in uns.get("missing_inputs") or []:
                missing_inputs.append(
                    {
                        "input": str(mi),
                        "eval_id": eval_id,
                        "eval_name": eval_name,
                        "variant": variant,
                    }
                )

    top_references = sorted(
        ref_counter.values(), key=lambda r: (-r["count"], r["reference"])
    )[:10]

    # B3: pre-compute items grouped by impact and deduped on (category, topic).
    by_impact_items: dict[str, list[dict]] = {lvl: [] for lvl in IMPACT_LEVELS}
    dedup: dict[tuple[str, str, str], dict] = {}
    for it in items:
        key = (
            it.get("impact") or "minor",
            it.get("category") or "",
            it.get("topic") or "",
        )
        bucket = dedup.get(key)
        if bucket is None:
            bucket = {
                "category": it.get("category"),
                "topic": it.get("topic"),
                "reference": it.get("reference"),
                "eval_ids": [],
                "eval_names": [],
            }
            dedup[key] = bucket
            impact = it.get("impact") or "minor"
            if impact not in by_impact_items:
                impact = "minor"
            by_impact_items[impact].append(bucket)
        eid = it.get("eval_id")
        if eid is not None and eid not in bucket["eval_ids"]:
            bucket["eval_ids"].append(eid)
            en = it.get("eval_name")
            if en and en not in bucket["eval_names"]:
                bucket["eval_names"].append(en)
        # Keep the first non-empty reference encountered.
        if not bucket.get("reference") and it.get("reference"):
            bucket["reference"] = it.get("reference")
    # Sort each impact bucket by eval-fan-out descending, then by topic for stability.
    for lvl in IMPACT_LEVELS:
        by_impact_items[lvl].sort(
            key=lambda b: (-len(b.get("eval_ids") or []), (b.get("topic") or ""))
        )

    rollup: dict = {
        "totals": totals,
        "by_impact": by_impact,
        "by_impact_items": by_impact_items,
        "top_references": top_references,
        "items": items,
        "response_risks": response_risks,
        "missing_inputs": missing_inputs,
    }

    # Delta vs previous iteration's rollup (only compare category totals).
    if previous_dir:
        prev_bm = load_json(previous_dir / "benchmark.json")
        prev_rollup = (prev_bm or {}).get("skill_feedback_rollup") or {}
        prev_totals = prev_rollup.get("totals") or {}
        rollup["delta_vs_previous"] = {
            cat: totals[cat] - int(prev_totals.get(cat, 0) or 0)
            for cat in SKILL_FEEDBACK_CATEGORIES
        }

    return rollup


def collect_notes(iteration_dir: Path, eval_dirs: list[Path]) -> list[dict]:
    notes: list[dict] = []

    analyzer = load_json(iteration_dir / "analyzer_notes.json")
    if isinstance(analyzer, list):
        notes.extend(_normalize_note(n) for n in analyzer)

    for eval_dir in eval_dirs:
        comp = load_json(eval_dir / "comparison.json")
        if comp and comp.get("notes"):
            notes.append(_normalize_note(comp["notes"]))
        meta = load_json(eval_dir / "eval_metadata.json")
        if meta and meta.get("notes"):
            notes.append(_normalize_note(meta["notes"]))
    return notes


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------


def generate_markdown(benchmark: dict) -> str:
    lines: list[str] = []
    meta = benchmark["metadata"]
    lines.append(f"# Benchmark: {meta['skill_name']}")
    lines.append("")
    lines.append(f"**Generated:** {meta['timestamp']}")
    lines.append(f"**Evals run:** {len(meta['evals_run'])}")
    if meta.get("iteration"):
        lines.append(f"**Iteration:** {meta['iteration']}")
    if meta.get("comparison_mode") and meta["comparison_mode"] != "baseline":
        lines.append(
            f"**Mode:** {meta['comparison_mode']} (baseline from iteration {meta.get('baseline_iteration', '?')})"
        )
    lines.append("")

    summary = benchmark.get("run_summary", {})
    lines.append("## Summary")
    lines.append("")

    has_prev = "previous_skill" in summary
    has_reg = "regression_delta" in summary
    header = "| Metric | current_skill | without_skill |"
    sep = "|--------|---------------|--------------|"
    if has_prev:
        header += " previous_skill |"
        sep += "---------------|"
    header += " Delta |"
    sep += "-------|"
    if has_reg:
        header += " vs Previous |"
        sep += "-------------|"
    lines.append(header)
    lines.append(sep)

    def _stat_cell(section: dict, metric: str) -> str:
        s = section.get(metric, {})
        return f"{s.get('mean', 'N/A')} (±{s.get('stddev', 'N/A')})"

    for metric in ("pass_rate", "time_seconds", "tokens"):
        ws_str = _stat_cell(summary.get("current_skill", {}), metric)
        wos_str = _stat_cell(summary.get("without_skill", {}), metric)
        row = f"| {metric} | {ws_str} | {wos_str} |"
        if has_prev:
            prev_str = _stat_cell(summary.get("previous_skill", {}), metric)
            row += f" {prev_str} |"
        delta = summary.get("delta", {}).get(metric, "N/A")
        row += f" {delta} |"
        if has_reg:
            reg = summary.get("regression_delta", {}).get(metric, "N/A")
            row += f" {reg} |"
        lines.append(row)

    lines.append("")

    comp = benchmark.get("comparisons", {})
    lines.append("## Comparisons")
    lines.append("")
    lines.append(f"- **current_skill wins:** {comp.get('current_skill_wins', 0)}")
    lines.append(f"- **without_skill wins:** {comp.get('without_skill_wins', 0)}")
    lines.append(f"- **ties:** {comp.get('ties', 0)}")

    if comp.get("current_wins") is not None:
        lines.append("")
        lines.append("### Regression (current vs previous iteration)")
        lines.append("")
        lines.append(f"- **current wins:** {comp.get('current_wins', 0)}")
        lines.append(f"- **previous wins:** {comp.get('previous_wins', 0)}")
        lines.append(f"- **regression ties:** {comp.get('regression_ties', 0)}")

    lines.append("")

    lines.append("## Per-Eval Results")
    lines.append("")
    lines.append(
        "| Eval | Config | Pass Rate | Passed | Failed | Time (s) | Tokens | Source |"
    )
    lines.append(
        "|------|--------|-----------|--------|--------|----------|--------|--------|"
    )

    for run in benchmark.get("runs", []):
        r = run["result"]
        source = (
            f"iter {run['source_iteration']}" if run.get("source_iteration") else ""
        )
        lines.append(
            f"| {run['eval_name']} | {run['configuration']} "
            f"| {r['pass_rate']:.2f} | {r['passed']} | {r['failed']} "
            f"| {r['time_seconds']:.1f} | {r['tokens']} | {source} |"
        )

    lines.append("")

    # B4: Contradictions section
    contradictions = benchmark.get("contradictions") or []
    if contradictions:
        lines.append("## Contradictions")
        lines.append("")
        lines.append(
            "Evals where the grader pass_rate and the blind comparator disagree "
            "by a wide margin."
        )
        lines.append("")
        lines.append(
            "| # | Eval | Current | Alternate | Variant | Comparator Winner | Severity |"
        )
        lines.append(
            "|---|------|---------|-----------|---------|-------------------|----------|"
        )
        for c in contradictions:
            lines.append(
                f"| {c.get('eval_id', '?')} "
                f"| {c.get('eval_name', '')} "
                f"| {c.get('current_skill_pass_rate', 0):.2f} "
                f"| {c.get('alternate_pass_rate', 0):.2f} "
                f"| {c.get('alternate_variant', '')} "
                f"| {c.get('comparator_winner') or 'tie'} "
                f"| {c.get('severity', '')} |"
            )
        lines.append("")

    # B4: Skill Regressions section (per non-empty bucket)
    regressions = benchmark.get("skill_regressions") or {}
    reg_buckets = [
        ("vs_baseline", "vs Baseline (without_skill)"),
        ("vs_previous", "vs Previous (previous_skill)"),
    ]
    any_reg = any(regressions.get(k) for k, _ in reg_buckets)
    if any_reg:
        lines.append("## Skill Regressions")
        lines.append("")
        lines.append(
            "Evals where the blind comparator preferred the alternate variant "
            "over `current_skill`."
        )
        lines.append("")
        for key, heading in reg_buckets:
            bucket = regressions.get(key) or []
            if not bucket:
                continue
            lines.append(f"### {heading}")
            lines.append("")
            lines.append("| # | Eval | Current | Alternate | Delta | Reasoning |")
            lines.append("|---|------|---------|-----------|-------|-----------|")
            for e in bucket:
                delta = e.get("pass_rate_delta", 0.0) or 0.0
                delta_str = f"{'+' if delta >= 0 else ''}{delta:.2f}"
                reasoning = (e.get("comparator_reasoning") or "").strip()
                if len(reasoning) > 160:
                    reasoning = reasoning[:157] + "..."
                reasoning = reasoning.replace("|", "\\|").replace("\n", " ")
                lines.append(
                    f"| {e.get('eval_id', '?')} "
                    f"| {e.get('eval_name', '')} "
                    f"| {e.get('current_pass_rate', 0):.2f} "
                    f"| {e.get('alternate_pass_rate', 0):.2f} "
                    f"| {delta_str} "
                    f"| {reasoning} |"
                )
            lines.append("")

    notes = benchmark.get("notes", [])
    if notes:
        lines.append("## Notes")
        lines.append("")
        for note in notes:
            if isinstance(note, dict):
                cat = note.get("category", "observation").upper().replace("_", " ")
                text = note.get("text", "")
                lines.append(f"- **[{cat}]** {text}")
            else:
                lines.append(f"- {note}")
        lines.append("")

    rollup = benchmark.get("skill_feedback_rollup") or {}
    totals = rollup.get("totals") or {}
    if any(totals.values()):
        lines.append("## Skill Feedback Rollup")
        lines.append("")
        for cat in SKILL_FEEDBACK_CATEGORIES:
            count = totals.get(cat, 0)
            lines.append(f"- **{cat}:** {count}")
        by_impact = rollup.get("by_impact") or {}
        if any(by_impact.values()):
            impact_str = ", ".join(
                f"{lvl}={by_impact.get(lvl, 0)}" for lvl in IMPACT_LEVELS
            )
            lines.append(f"- **by impact:** {impact_str}")
        top_refs = rollup.get("top_references") or []
        if top_refs:
            lines.append("")
            lines.append("### Top flagged references")
            lines.append("")
            for r in top_refs:
                lines.append(
                    f"- `{r['reference']}` — {r['count']} eval(s) "
                    f"({', '.join(str(i) for i in r['eval_ids'])})"
                )

        # B4: Skill Feedback by Impact — deduped (category, topic) per level
        by_impact_items = rollup.get("by_impact_items") or {}
        impact_headings = [
            ("blocking", "Blocking"),
            ("major", "Major"),
            ("minor", "Minor"),
        ]
        if any(by_impact_items.get(lvl) for lvl, _ in impact_headings):
            lines.append("")
            lines.append("### By Impact")
            lines.append("")
            for lvl, heading in impact_headings:
                bucket = by_impact_items.get(lvl) or []
                if not bucket:
                    continue
                lines.append(f"#### {heading}")
                lines.append("")
                for it in bucket:
                    eids = it.get("eval_ids") or []
                    eids_str = (
                        f" (evals: {', '.join(f'#{i}' for i in eids)})" if eids else ""
                    )
                    ref = it.get("reference")
                    ref_str = f" [`{ref}`]" if ref else ""
                    topic = (it.get("topic") or "").strip() or "(no topic)"
                    cat = it.get("category") or ""
                    lines.append(f"- **{topic}** — _{cat}_{eids_str}{ref_str}")
                lines.append("")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate eval results into benchmark.json and benchmark.md."
    )
    parser.add_argument(
        "iteration_dir",
        type=Path,
        help="Path to the workspace iteration directory (e.g. evals/<skill>/workspace/iteration-1)",
    )
    parser.add_argument(
        "--skill-name",
        required=True,
        help="Name of the skill being evaluated",
    )
    parser.add_argument(
        "--baseline-iteration",
        type=Path,
        default=None,
        help=(
            "Path to the iteration that supplied the without_skill baseline "
            "for existing evals (e.g. evals/<skill>/workspace/iteration-1)"
        ),
    )
    parser.add_argument(
        "--previous-iteration",
        type=Path,
        default=None,
        help=(
            "Path to the N-1 iteration used for the regression comparator "
            "(e.g. evals/<skill>/workspace/iteration-2). Required when the "
            "current iteration has any regression evals."
        ),
    )
    parser.add_argument(
        "--fix-grading-paths",
        action="store_true",
        help=(
            "When grading.json files are found under {variant}/outputs/ "
            "instead of the variant root, move them to the correct location "
            "instead of aborting."
        ),
    )
    args = parser.parse_args()

    iteration_dir: Path = args.iteration_dir.resolve()
    if not iteration_dir.is_dir():
        print(f"{RED}Directory not found: {iteration_dir}{NC}")
        return 1

    baseline_dir: Path | None = (
        args.baseline_iteration.resolve() if args.baseline_iteration else None
    )
    previous_dir: Path | None = (
        args.previous_iteration.resolve() if args.previous_iteration else None
    )

    print(SEPARATOR)
    print(f"Aggregating benchmark for: {args.skill_name}")
    print(SEPARATOR)

    # Load iteration config
    iteration_config = load_json(iteration_dir / "iteration_config.json")

    eval_dirs = discover_eval_dirs(iteration_dir)
    if not eval_dirs:
        print(f"{RED}No eval-* directories found in {iteration_dir}{NC}")
        return 1

    print(f"Found {len(eval_dirs)} eval(s): {', '.join(d.name for d in eval_dirs)}")
    if iteration_config:
        mode = iteration_config.get("mode", "baseline")
        print(f"Iteration mode: {mode}")
        if baseline_dir:
            print(f"Baseline (without_skill reuse): {baseline_dir}")
        if previous_dir:
            print(f"Previous (regression N-1): {previous_dir}")

    # A3: catch the silent-0% bug caused by grading.json landing under
    # {variant}/outputs/ instead of at the variant root.
    misplaced = detect_misplaced_grading(eval_dirs)
    if misplaced:
        if args.fix_grading_paths:
            moved = fix_misplaced_grading(misplaced)
            print(f"{YELLOW}Relocated {len(moved)} misplaced grading.json file(s):{NC}")
            for src, dest in moved:
                print(f"  - {src.relative_to(iteration_dir)}")
                print(f"    -> {dest.relative_to(iteration_dir)}")
        else:
            lines = [
                f"{RED}ERROR: grading.json written to the wrong path in "
                f"{len(misplaced)} variant(s):{NC}"
            ]
            for p in misplaced:
                lines.append(f"  - {p.relative_to(iteration_dir)}")
            lines.append("")
            lines.append(
                "Expected location: <variant>/grading.json "
                "(sibling of outputs/, never a child)."
            )
            lines.append(
                "Re-run with --fix-grading-paths to move them automatically, "
                "or fix manually, e.g.:"
            )
            sample = misplaced[0]
            lines.append(f"  mv {sample} {sample.parent.parent / 'grading.json'}")
            print("\n".join(lines))
            return 2

    runs = build_runs(eval_dirs, baseline_dir, iteration_config)
    if not runs:
        print(f"{YELLOW}Warning: no grading.json files found in any eval directory{NC}")

    run_summary = build_run_summary(runs)

    # Regression delta is computed against the previous iteration (N-1),
    # not the baseline iteration.
    reg_delta = build_regression_delta(runs, previous_dir)
    if reg_delta:
        run_summary["regression_delta"] = reg_delta

    comparisons = build_comparisons(eval_dirs)
    per_eval_comparisons = build_per_eval_comparisons(eval_dirs)
    contradictions = build_contradictions(runs, per_eval_comparisons)
    skill_regressions = build_skill_regressions(runs, per_eval_comparisons)
    skill_feedback_rollup = _build_skill_feedback_rollup(eval_dirs, previous_dir)
    notes = collect_notes(iteration_dir, eval_dirs)

    seen_ids: list[int] = []
    for run in runs:
        if run["eval_id"] not in seen_ids:
            seen_ids.append(run["eval_id"])

    # Build metadata with iteration info
    metadata: dict = {
        "skill_name": args.skill_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "evals_run": seen_ids,
    }
    if iteration_config:
        metadata["iteration"] = iteration_config.get("iteration")
        metadata["comparison_mode"] = iteration_config.get("mode", "baseline")
        if iteration_config.get("baseline_iteration"):
            metadata["baseline_iteration"] = iteration_config["baseline_iteration"]
        if iteration_config.get("previous_iteration"):
            metadata["previous_iteration"] = iteration_config["previous_iteration"]
        if iteration_config.get("skill_version"):
            metadata["skill_version"] = iteration_config["skill_version"]
        new_evals = iteration_config.get("eval_classification", {}).get("new", [])
        if new_evals:
            metadata["new_evals"] = new_evals

    benchmark = {
        "metadata": metadata,
        "runs": runs,
        "run_summary": run_summary,
        "comparisons": comparisons,
        "per_eval_comparisons": per_eval_comparisons,
        "contradictions": contradictions,
        "skill_regressions": skill_regressions,
        "skill_feedback_rollup": skill_feedback_rollup,
        "notes": notes,
    }

    benchmark_json_path = iteration_dir / "benchmark.json"
    benchmark_json_path.write_text(
        json.dumps(benchmark, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"  {GREEN}✓{NC} {benchmark_json_path}")

    benchmark_md_path = iteration_dir / "benchmark.md"
    benchmark_md_path.write_text(
        generate_markdown(benchmark),
        encoding="utf-8",
    )
    print(f"  {GREEN}✓{NC} {benchmark_md_path}")

    print()
    ws = run_summary.get("current_skill", {})
    wos = run_summary.get("without_skill", {})
    delta = run_summary.get("delta", {})

    print(f"  current_skill pass_rate={ws.get('pass_rate', {}).get('mean', 'N/A')}")
    print(f"  without_skill pass_rate={wos.get('pass_rate', {}).get('mean', 'N/A')}")
    print(f"  delta         pass_rate={delta.get('pass_rate', 'N/A')}")

    if reg_delta:
        print(
            f"  regression    pass_rate={reg_delta.get('pass_rate', 'N/A')} "
            f"(vs previous iteration)"
        )

    print()
    print(
        f"  comparisons: "
        f"current_skill={comparisons['current_skill_wins']} "
        f"without_skill={comparisons['without_skill_wins']} "
        f"ties={comparisons['ties']}"
    )
    if comparisons.get("current_wins") is not None:
        print(
            f"  regression:  "
            f"current={comparisons['current_wins']} "
            f"previous={comparisons['previous_wins']} "
            f"ties={comparisons['regression_ties']}"
        )

    if contradictions:
        print(f"  contradictions: {len(contradictions)}")
    reg_baseline = len(skill_regressions.get("vs_baseline") or [])
    reg_previous = len(skill_regressions.get("vs_previous") or [])
    if reg_baseline or reg_previous:
        print(
            f"  skill_regressions: vs_baseline={reg_baseline} vs_previous={reg_previous}"
        )

    print(SEPARATOR)
    print(f"{GREEN}Benchmark complete.{NC}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
