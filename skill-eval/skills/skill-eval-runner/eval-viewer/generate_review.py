#!/usr/bin/env python3
"""Generate a unified HTML report merging iteration review and progression data.

Usage:
    python generate_review.py <workspace> --skill-name <name> [options]

Options:
    --iteration N       Target iteration number (default: latest found)
    --static <path>     Write standalone HTML file instead of serving
    --port <port>       HTTP server port (default: 3117)
"""

from __future__ import annotations

import argparse
import base64
import http.server
import json
import mimetypes
import os
import re
import sys
import tempfile
import threading
import webbrowser
from pathlib import Path

from copilot_usage import CopilotUsageError, load_copilot_usage, load_task_names

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEXT_EXTENSIONS = {
    ".md",
    ".json",
    ".py",
    ".yaml",
    ".yml",
    ".txt",
    ".csv",
    ".tsv",
    ".xml",
    ".html",
    ".css",
    ".js",
    ".ts",
    ".sh",
    ".bash",
    ".zsh",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".log",
    ".env",
    ".sql",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico"}
PDF_EXTENSIONS = {".pdf"}
METADATA_FILES = {"transcript.md", "user_notes.md", "metrics.json"}

TEMPLATE_NAME = "review-template.html"
USAGE_SUMMARY_SCHEMA_VERSION = 1
USAGE_SUMMARY_COUNTERS = {
    "input_tokens",
    "input_cached_tokens",
    "input_cache_creation_tokens",
    "input_cache_write_tokens",
    "output_tokens",
    "output_reasoning_tokens",
    "total_tokens",
    "total_api_duration_ms",
}
USAGE_SUMMARY_ROLES = {
    "executor",
    "grader",
    "comparator",
    "comparator-recovery",
    "recovery",
}
USAGE_SUMMARY_VARIANTS = {"current_skill", "without_skill", "previous_skill"}
USAGE_SUMMARY_OTHER_LABELS = {
    "Runner",
    "Executor",
    "Analyzer",
    "Comparator",
    "Grader",
    "Recovery",
    "Other agent",
}
USAGE_SUMMARY_MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}\Z")
USAGE_SUMMARY_EVAL_RE = re.compile(r"eval-\d+\Z")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict | None:
    """Load a JSON file, returning None on missing file or parse error."""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


# ---------------------------------------------------------------------------
# File embedding (from generate_review.py)
# ---------------------------------------------------------------------------


def embed_file(path: Path) -> dict:
    """Read a file and return a dict with type/content suitable for embedding."""
    suffix = path.suffix.lower()
    name = path.name

    if suffix in TEXT_EXTENSIONS:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            text = "[Could not read file]"
        return {"type": "text", "name": name, "content": text}

    raw = path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"

    if suffix in IMAGE_EXTENSIONS:
        return {"type": "image", "name": name, "data_uri": f"data:{mime};base64,{b64}"}

    if suffix in PDF_EXTENSIONS:
        return {"type": "pdf", "name": name, "data_uri": f"data:{mime};base64,{b64}"}

    return {
        "type": "binary",
        "name": name,
        "data_uri": f"data:{mime};base64,{b64}",
        "size": len(raw),
    }


# ---------------------------------------------------------------------------
# Run discovery and building (from generate_review.py)
# ---------------------------------------------------------------------------


def find_runs(workspace: Path) -> list[Path]:
    """Recursively find directories containing an outputs/ subdirectory.

    Never descends into a per-variant ``sandbox/``: that is the skill's private,
    writable repository root for a run, and meta-evals that exercise the runner
    itself can stage a whole nested eval workspace inside it (with its own
    ``eval-<id>/<variant>/outputs/``). Those fixture outputs carry their own
    ``eval_metadata.json`` and would otherwise be mistaken for real runs and
    collide with the real eval of the same id in the report.
    """
    runs: list[Path] = []
    if not workspace.is_dir():
        return runs
    for dirpath, dirnames, _ in os.walk(workspace):
        # Prune sandboxes in place so os.walk never enters them.
        dirnames[:] = [d for d in dirnames if d != "sandbox"]
        if "outputs" in dirnames:
            runs.append(Path(dirpath))
    runs.sort()
    return runs


def _find_eval_metadata(run_dir: Path) -> dict:
    """Look for eval_metadata.json in run_dir or its parent."""
    meta = _load_json(run_dir / "eval_metadata.json")
    if meta:
        return meta
    meta = _load_json(run_dir.parent / "eval_metadata.json")
    if meta:
        return meta
    return {}


def build_run(workspace: Path, run_dir: Path) -> dict:
    """Build a run dict with prompt, outputs, grading, comparison."""
    rel = run_dir.relative_to(workspace)
    metadata = _find_eval_metadata(run_dir)

    # Collect output files
    outputs_dir = run_dir / "outputs"
    output_files: list[dict] = []
    if outputs_dir.is_dir():
        for f in sorted(outputs_dir.iterdir()):
            if f.is_file() and f.name not in METADATA_FILES:
                output_files.append(embed_file(f))

    # Grading (expectations + claims + eval_feedback only)
    grading = _load_json(run_dir / "grading.json")

    # Execution telemetry (self_report + host_telemetry + user_notes).
    # Lives in outputs/metrics.json, owned by finalize_metrics.py.
    metrics = _load_json(run_dir / "outputs" / "metrics.json")

    # Comparison (in parent eval dir)
    comparison = _load_json(run_dir.parent / "comparison.json")

    # Determine variant from directory name
    variant = run_dir.name  # e.g. "current_skill" or "without_skill"

    # Eval name: prefer metadata name, fall back to parent directory name
    dir_name = (
        run_dir.parent.name
        if variant in ("current_skill", "without_skill")
        else run_dir.name
    )
    eval_name = metadata.get("name", dir_name)

    return {
        "path": str(rel),
        "eval_name": eval_name,
        "variant": variant,
        "eval_id": metadata.get("id", metadata.get("eval_id")),
        "prompt": metadata.get("prompt", ""),
        "expectations": metadata.get("expectations", []),
        "outputs": output_files,
        "grading": grading,
        "metrics": metrics,
        "comparison": comparison,
    }


# ---------------------------------------------------------------------------
# Iteration discovery (from generate_progression.py)
# ---------------------------------------------------------------------------


def discover_iterations(workspace: Path) -> list[tuple[int, Path]]:
    """Return sorted list of (iteration_number, path) tuples."""
    iterations: list[tuple[int, Path]] = []
    if not workspace.is_dir():
        return iterations
    for d in workspace.iterdir():
        if not d.is_dir():
            continue
        match = re.match(r"iteration-(\d+)$", d.name)
        if match:
            iterations.append((int(match.group(1)), d))
    iterations.sort(key=lambda x: x[0])
    return iterations


# ---------------------------------------------------------------------------
# Progression data (from generate_progression.py, extended with notes)
# ---------------------------------------------------------------------------


def build_progression_data(workspace: Path, skill_name: str) -> dict:
    """Build cross-iteration progression data from all benchmark.json files."""
    iterations = discover_iterations(workspace)
    data: dict = {"skill_name": skill_name, "iterations": []}

    for num, path in iterations:
        benchmark = _load_json(path / "benchmark.json")
        if not benchmark:
            continue

        meta = benchmark.get("metadata", {})
        rs = benchmark.get("run_summary", {})

        eval_seen: dict[int, dict] = {}
        for run in benchmark.get("runs", []):
            eid = run["eval_id"]
            if eid not in eval_seen:
                eval_seen[eid] = {"eval_id": eid, "eval_name": run["eval_name"]}
            cfg = run["configuration"]
            if cfg == "current_skill":
                eval_seen[eid]["current_skill_pass_rate"] = run["result"]["pass_rate"]
                eval_seen[eid]["time_seconds"] = run["result"]["time_seconds"]
                eval_seen[eid]["tokens"] = run["result"]["tokens"]
            elif cfg == "without_skill":
                eval_seen[eid]["without_skill_pass_rate"] = run["result"]["pass_rate"]
            elif cfg == "previous_skill":
                eval_seen[eid]["previous_skill_pass_rate"] = run["result"]["pass_rate"]

        data["iterations"].append(
            {
                "iteration": num,
                "timestamp": meta.get("timestamp", ""),
                "comparison_mode": meta.get("comparison_mode", "baseline"),
                "previous_iteration": meta.get("previous_iteration"),
                "run_summary": rs,
                "comparisons": benchmark.get("comparisons", {}),
                "per_eval": list(eval_seen.values()),
                "notes": benchmark.get("notes", []),
            }
        )

    return data


# ---------------------------------------------------------------------------
# Unified report data builder
# ---------------------------------------------------------------------------


def build_iteration_runs(workspace_root: Path, iter_num: int) -> list[dict]:
    """Build the list of runs for a single iteration, with outputs embedded."""
    iter_dir = workspace_root / f"iteration-{iter_num}"
    if not iter_dir.is_dir():
        return []
    return [build_run(iter_dir, r) for r in find_runs(iter_dir)]


def _resolve_embed_iterations(workspace_root: Path, served_iteration: int) -> list[int]:
    """Decide which iterations' runs should be embedded up-front.

    - baseline mode: just the served iteration.
    - regression/mixed mode: served iteration + its baseline + the previous iteration
      (so the Review tab can render the 3-column regression layout without waiting
      for a lazy fetch).
    """
    served_dir = workspace_root / f"iteration-{served_iteration}"
    config = _load_json(served_dir / "iteration_config.json") or {}
    mode = config.get("mode", "baseline")

    wanted: set[int] = {served_iteration}
    if mode != "baseline":
        baseline_iter = config.get("baseline_iteration") or 1
        wanted.add(int(baseline_iter))
        if served_iteration > 1:
            wanted.add(served_iteration - 1)

    existing = {n for n, _ in discover_iterations(workspace_root)}
    return sorted(wanted & existing)


def _usage_counter_fields(source: dict) -> dict:
    return {
        key: value
        for key, value in source.items()
        if key in USAGE_SUMMARY_COUNTERS and type(value) is int and value >= 0
    }


def _usage_models(source: object) -> list[str]:
    if not isinstance(source, list):
        return []
    return sorted(
        {
            model
            for model in source
            if isinstance(model, str) and USAGE_SUMMARY_MODEL_RE.fullmatch(model)
        }
    )


def _sanitize_usage_summary(value: object) -> dict:
    if not isinstance(value, dict):
        raise CopilotUsageError(
            "Saved Copilot usage summary has an unsupported structure"
        )
    if (
        type(value.get("schema_version")) is not int
        or value["schema_version"] != USAGE_SUMMARY_SCHEMA_VERSION
        or value.get("source") != "copilot-cli"
        or type(value.get("eval_count")) is not int
        or value["eval_count"] < 0
        or not isinstance(value.get("session"), dict)
        or not isinstance(value.get("eval_agents"), list)
        or not isinstance(value.get("other_agents"), list)
    ):
        raise CopilotUsageError(
            "Saved Copilot usage summary has an unsupported structure"
        )

    session_source = value["session"]
    session = {"models": _usage_models(session_source.get("models"))}
    session.update(_usage_counter_fields(session_source))

    eval_agents = []
    for raw_agent in value["eval_agents"]:
        if not isinstance(raw_agent, dict):
            continue
        eval_id = raw_agent.get("eval_id")
        role = raw_agent.get("role")
        if (
            not isinstance(eval_id, str)
            or not USAGE_SUMMARY_EVAL_RE.fullmatch(eval_id)
            or not isinstance(role, str)
            or role not in USAGE_SUMMARY_ROLES
        ):
            continue
        agent = {
            "eval_id": eval_id,
            "role": role,
            "models": _usage_models(raw_agent.get("models")),
        }
        variant = raw_agent.get("variant")
        if isinstance(variant, str) and variant in USAGE_SUMMARY_VARIANTS:
            agent["variant"] = variant
        agent.update(_usage_counter_fields(raw_agent))
        eval_agents.append(agent)

    other_agents = []
    for raw_agent in value["other_agents"]:
        if not isinstance(raw_agent, dict):
            continue
        label = raw_agent.get("label")
        if (
            not isinstance(label, str)
            or label not in USAGE_SUMMARY_OTHER_LABELS
        ):
            label = "Other agent"
        agent = {"label": label, "models": _usage_models(raw_agent.get("models"))}
        agent.update(_usage_counter_fields(raw_agent))
        other_agents.append(agent)

    eval_agents.sort(
        key=lambda agent: (
            agent["eval_id"],
            agent["role"],
            agent.get("variant", ""),
        )
    )
    other_agents.sort(key=lambda agent: (agent["label"], agent["models"]))
    return {
        "schema_version": USAGE_SUMMARY_SCHEMA_VERSION,
        "source": "copilot-cli",
        "eval_count": value["eval_count"],
        "session": session,
        "eval_agents": eval_agents,
        "other_agents": other_agents,
    }


def _load_usage_summaries(workspace_root: Path) -> dict[str, dict]:
    summaries: dict[str, dict] = {}
    for iteration, iteration_dir in discover_iterations(workspace_root):
        path = iteration_dir / "usage_summary.json"
        if not path.is_file():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CopilotUsageError(
                "Saved Copilot usage summary could not be read"
            ) from exc
        summaries[str(iteration)] = _sanitize_usage_summary(value)
    return summaries


def build_report_data(
    workspace_root: Path,
    served_iteration: int,
    skill_name: str,
    embed_all: bool = False,
    usage_summary_override: dict[str, dict] | None = None,
) -> dict:
    """Build the full embedded data payload for the report template.

    Combines:
    1. Progression data for all iterations
    2. Full benchmark.json per iteration
    3. Embedded outputs for the resolved set of iterations (served + regression extras).
       When embed_all=True (static export), every iteration's runs are embedded.
    4. Previous iteration feedback
    5. iteration_config for the served iteration (exposes baseline_iteration to JS)
    """
    # 1. Progression data for all iterations
    progression = build_progression_data(workspace_root, skill_name)

    # 2. Full benchmark.json per iteration
    benchmarks: dict[str, dict] = {}
    for num, path in discover_iterations(workspace_root):
        bm = _load_json(path / "benchmark.json")
        if bm:
            benchmarks[str(num)] = bm

    # 3. Embedded outputs for resolved iterations
    if embed_all:
        embed_iters = [n for n, _ in discover_iterations(workspace_root)]
    else:
        embed_iters = _resolve_embed_iterations(workspace_root, served_iteration)
    iteration_runs: dict[str, list[dict]] = {
        str(n): build_iteration_runs(workspace_root, n) for n in embed_iters
    }

    # 4. Previous feedback
    prev_fb: dict | None = None
    if served_iteration > 1:
        prev_dir = workspace_root / f"iteration-{served_iteration - 1}"
        prev_fb = _load_json(prev_dir / "feedback.json")

    # 5. Served iteration_config (for regression resolution on the frontend)
    served_config = (
        _load_json(
            workspace_root / f"iteration-{served_iteration}" / "iteration_config.json"
        )
        or {}
    )

    iteration_usage_summaries = _load_usage_summaries(workspace_root)
    if usage_summary_override:
        iteration_usage_summaries.update(usage_summary_override)

    return {
        "skill_name": skill_name,
        "served_iteration": served_iteration,
        "served_iteration_config": served_config,
        "iterations": progression["iterations"],
        "iteration_benchmarks": benchmarks,
        "iteration_runs": iteration_runs,
        "embedded_iterations": embed_iters,
        "iteration_usage_summaries": iteration_usage_summaries,
        "previous_feedback": prev_fb,
    }


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------


def inline_src_assets(template: str, src_dir: Path) -> str:
    """Concatenate src/styles/**/*.css and src/scripts/**/*.js into template markers.

    Files are sorted alphabetically so numeric prefixes (00-, 10-, 20-) give a
    deterministic load order. Each file is wrapped in a header comment with its
    relative path — helps devtools debugging inside the concatenated blob.
    Missing src_dir or empty globs collapse to an empty string (no-op).
    """

    def concat(glob: str) -> str:
        if not src_dir.is_dir():
            return ""
        files = sorted(src_dir.glob(glob))
        return "\n\n".join(
            f"/* \u2500\u2500 {p.relative_to(src_dir)} \u2500\u2500 */\n{p.read_text(encoding='utf-8')}"
            for p in files
            if p.is_file()
        )

    template = template.replace("/*{{SRC_CSS}}*/", concat("styles/**/*.css"))
    template = template.replace("/*{{SRC_JS}}*/", concat("scripts/**/*.js"))
    return template


def generate_html(report_data: dict) -> str:
    """Read review-template.html, inline src/ assets, inject the data payload."""
    here = Path(__file__).parent
    template = (here / TEMPLATE_NAME).read_text(encoding="utf-8")
    template = inline_src_assets(template, here / "src")
    payload = json.dumps(report_data, ensure_ascii=False)
    # The JSON is injected into a <script> block AS JavaScript source (assigned to a
    # const, not JSON.parse'd), so two classes of character must be neutralized.
    # Both are rewritten to JSON unicode escapes: valid JSON that decodes back to the
    # original character in the browser, so the embedded data round-trips.
    #   1. "<" -> "\u003c": stops the HTML tokenizer from ever seeing </script>,
    #      <!--, or <script (which would close the tag early and blank the page).
    #      Escaping "<" avoids the illegal JSON escape "\!" that "<\!--" would add.
    #   2. U+2028 / U+2029 (LINE / PARAGRAPH SEPARATOR): valid inside JSON strings
    #      but are line terminators in JS source, so ensure_ascii=False can emit raw
    #      ones that cause a SyntaxError. They are referenced by codepoint via
    #      str.translate so no invisible characters live in this source file.
    payload = payload.replace("<", "\\u003c").translate(
        {0x2028: "\\u2028", 0x2029: "\\u2029"}
    )
    injection = f"const EMBEDDED_DATA = {payload};"
    return template.replace("/*__EMBEDDED_DATA__*/", injection)


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------


class ReportHandler(http.server.BaseHTTPRequestHandler):
    """Serves the unified report with live feedback API."""

    workspace_root: Path = Path(".")
    served_iteration: int = 1
    skill_name: str = ""

    def log_message(self, format: str, *args: object) -> None:
        pass  # suppress default logging

    def _send_json(self, data: dict | list | None, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/" or self.path == "":
            report_data = build_report_data(
                self.workspace_root, self.served_iteration, self.skill_name
            )
            html = generate_html(report_data)
            self._send_html(html)
        elif self.path == "/api/feedback":
            served_dir = self.workspace_root / f"iteration-{self.served_iteration}"
            fb = _load_json(served_dir / "feedback.json")
            self._send_json(fb or {})
        else:
            m = re.match(r"^/api/iteration/(\d+)/runs$", self.path)
            if m:
                n = int(m.group(1))
                iter_dir = self.workspace_root / f"iteration-{n}"
                if not iter_dir.is_dir():
                    self._send_json({"error": f"iteration {n} not found"}, status=404)
                    return
                self._send_json(build_iteration_runs(self.workspace_root, n))
                return
            self.send_error(404)

    def do_POST(self) -> None:
        if self.path == "/api/feedback":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                served_dir = self.workspace_root / f"iteration-{self.served_iteration}"
                fb_path = served_dir / "feedback.json"
                fb_path.write_text(
                    json.dumps(data, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                self._send_json({"status": "saved"})
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
        else:
            self.send_error(404)


def serve(
    workspace_root: Path, served_iteration: int, skill_name: str, port: int
) -> None:
    """Start an HTTP server and open a browser."""
    ReportHandler.workspace_root = workspace_root
    ReportHandler.served_iteration = served_iteration
    ReportHandler.skill_name = skill_name

    server = http.server.HTTPServer(("127.0.0.1", port), ReportHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"Report viewer serving at {url}")
    print(f"  Skill: {skill_name}")
    print(f"  Iteration: {served_iteration}")
    print(f"  Workspace: {workspace_root}")
    print("Press Ctrl+C to stop.")

    # Open browser after short delay
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        server.shutdown()


# ---------------------------------------------------------------------------
# Auto-detect latest iteration
# ---------------------------------------------------------------------------


def _latest_iteration(workspace: Path) -> int | None:
    """Return the highest iteration number found, or None."""
    iterations = discover_iterations(workspace)
    if not iterations:
        return None
    return iterations[-1][0]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate unified eval report (review + progression)"
    )
    parser.add_argument(
        "workspace",
        type=Path,
        help="Path to skill workspace root (e.g. evals/<skill>/workspace) containing iteration-* directories",
    )
    parser.add_argument(
        "--skill-name", required=True, help="Name of the skill being evaluated"
    )
    parser.add_argument(
        "--iteration",
        type=int,
        default=None,
        help="Target iteration number (default: latest found)",
    )
    parser.add_argument(
        "--static",
        type=Path,
        default=None,
        help="Write standalone HTML file instead of serving",
    )
    parser.add_argument(
        "--usage-output-file",
        type=Path,
        default=None,
        help=(
            "Copilot CLI final usage JSON to normalize and embed in a static "
            "report (requires --static)"
        ),
    )
    parser.add_argument(
        "--copilot-events-file",
        type=Path,
        default=None,
        help=(
            "Copilot CLI session events.jsonl used only to attribute sub-agent "
            "usage to eval cases (requires --usage-output-file)"
        ),
    )
    parser.add_argument(
        "--port", type=int, default=3117, help="HTTP server port (default: 3117)"
    )
    args = parser.parse_args()
    if args.usage_output_file is not None and args.static is None:
        parser.error("--usage-output-file requires --static")
    if args.copilot_events_file is not None and args.usage_output_file is None:
        parser.error("--copilot-events-file requires --usage-output-file")

    workspace = args.workspace.resolve()
    if not workspace.is_dir():
        print(f"Error: workspace directory not found: {workspace}", file=sys.stderr)
        sys.exit(1)

    # Determine iteration
    iteration = args.iteration
    if iteration is None:
        iteration = _latest_iteration(workspace)
        if iteration is None:
            print(
                "Error: no iteration-* directories found in workspace.",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"Auto-detected latest iteration: {iteration}")

    served_dir = workspace / f"iteration-{iteration}"
    if not served_dir.is_dir():
        print(f"Error: iteration directory not found: {served_dir}", file=sys.stderr)
        sys.exit(1)

    usage_summary: dict | None = None
    usage_sidecar: Path | None = None
    usage_summary_override: dict[str, dict] | None = None
    try:
        if args.usage_output_file is not None:
            task_names = None
            if args.copilot_events_file is not None:
                try:
                    task_names = load_task_names(args.copilot_events_file)
                except CopilotUsageError as exc:
                    print(
                        f"Warning: {exc}; usage is reported without per-eval "
                        "attribution",
                        file=sys.stderr,
                    )
            usage_summary = load_copilot_usage(
                args.usage_output_file, served_dir, task_names=task_names
            )
            if task_names is not None and not usage_summary["eval_agents"]:
                print(
                    f"Warning: none of the {len(task_names)} named sub-agents in "
                    "the events file matched the eval naming convention; usage "
                    "is grouped by role",
                    file=sys.stderr,
                )
            usage_sidecar = served_dir / "usage_summary.json"
            usage_summary_override = {str(iteration): usage_summary}

        if args.static:
            # Static mode: embed all iterations so the exported HTML is self-contained.
            report_data = build_report_data(
                workspace,
                iteration,
                args.skill_name,
                embed_all=True,
                usage_summary_override=usage_summary_override,
            )
            html = generate_html(report_data)
            out = args.static.resolve()
            if usage_summary is not None and usage_sidecar is not None:
                summary_text = (
                    json.dumps(
                        usage_summary,
                        indent=2,
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )
                _write_files_atomically(
                    [(usage_sidecar, summary_text), (out, html)]
                )
            else:
                out.write_text(html, encoding="utf-8")
            print(f"Wrote standalone HTML to {out}")
        else:
            if usage_summary is not None and usage_sidecar is not None:
                summary_text = (
                    json.dumps(
                        usage_summary,
                        indent=2,
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )
                _write_files_atomically([(usage_sidecar, summary_text)])
            serve(workspace, iteration, args.skill_name, args.port)
    except CopilotUsageError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except OSError:
        print(
            "Error: could not write the usage summary or report output",
            file=sys.stderr,
        )
        sys.exit(1)


def _write_files_atomically(files: list[tuple[Path, str]]) -> None:
    staged: list[tuple[Path, Path]] = []
    try:
        for output_path, content in files:
            fd, temp_name = tempfile.mkstemp(
                prefix=f".{output_path.name}.",
                suffix=".tmp",
                dir=str(output_path.parent),
            )
            temp_path = Path(temp_name)
            staged.append((temp_path, output_path))
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
        for temp_path, output_path in staged:
            os.replace(temp_path, output_path)
    finally:
        for temp_path, _output_path in staged:
            if temp_path.exists():
                temp_path.unlink()


if __name__ == "__main__":
    main()
