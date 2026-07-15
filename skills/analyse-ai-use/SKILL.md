---
name: analyse-ai-use
description: "Analyse how you use AI coding tools in this workspace and produce a styled HTML report with token-saving, iteration-cutting advice. Scans the session transcripts of the tool it runs inside (Claude Code, GitHub Copilot CLI, or Copilot Chat) and characterises your usage style. Triggers: user says 'analyse me', 'analyse my AI usage', 'how do I use AI here', or wants tips to save tokens / cut iterations in this workspace."
argument-hint: "Optionally: --all to compare across tools, or --tool <claude-code|copilot-cli|copilot-chat>"
compatibility: Requires Python 3.9+ (standard library only). Reads local session transcripts; nothing leaves the machine.
disable-model-invocation: false
user-invocable: true
license: MIT
tags:
  - ai-usage
  - token-optimisation
  - cost-analysis
  - usage-report
  - observability
metadata:
  author: Vidit Tripathi
  version: "1.0.0"
---

# Analyse AI Use

Scan this workspace's AI session transcripts, characterise how the user works, and hand back a **self-contained HTML report**: their usage style plus concrete, workspace-specific changes that save tokens and cut iterations.

The output is HTML, not a chat dump — easier for a human to read, and cheaper: `render.py` builds every number, chart, and table straight from the scan JSON, so you write only the prose analysis and never re-type a metric into chat.

The `scan.py` reduction is the point — it turns hundreds of KB of raw transcripts into one compact metrics object, so the analysis costs a fraction of the tokens that reading transcripts would.

## Bundled scripts

- `scripts/scan.py`: deterministic, stdlib-only reducer. Detects the host tool, reads its local transcripts for this workspace, and emits one compact metrics JSON. Usage: `python3 skills/analyse-ai-use/scripts/scan.py --cwd "$PWD" --save <metrics.json>`.
- `scripts/render.py`: builds the self-contained HTML report from the metrics JSON plus your prose analysis JSON. Usage: `python3 skills/analyse-ai-use/scripts/render.py --metrics <metrics.json> --analysis <analysis.json> --out <report.html>`.

## Supported tools

- **claude-code** — `~/.claude/projects/<slug>/*.jsonl` (full token/cache data)
- **copilot-cli** — `~/.copilot/session-state/<uuid>/` (output tokens + end-of-session context)
- **copilot-chat** — VSCode `GitHub.copilot-chat/transcripts/*.jsonl` for prompts/tools, plus the sibling `debug-logs/<id>/main.jsonl` for token & credit usage (input/output/cached tokens and metered AIU credits). Token data needs Copilot Chat's trace logging, which recent versions (~v0.52+) enable by default; older sessions predate it, so `token_data_coverage` reports how many sessions actually carried tokens.

**Scope: the scanner reports only the tool it runs inside.** `scan.py` detects the host from the environment (`CLAUDECODE` → claude-code, `COPILOT_CLI_*` → copilot-cli, else VSCode → copilot-chat) and scans just that tool. Invoked from Copilot Chat you get Copilot Chat data only — never another tool's. If the host can't be detected, the scan returns an `"error"` (it will **not** silently scan every tool); relay it and stop, or re-run with an explicit `--tool`. Only override when the user explicitly asks to compare across tools (`--all`) or names a specific tool (`--tool <name>`).

## Steps

**Every run is from scratch.** Never reuse a metrics file, analysis file, or HTML report from a previous run — always re-scan, re-analyse, and re-render on live transcripts. The intermediate files below are throwaway scratch for *this* run only; the scan always reads raw transcripts fresh (it never reads an old metrics file).

0. **Start clean.** Delete any artifacts left by a prior run so nothing stale can be picked up:
   ```bash
   rm -f "$PWD/.analyse-ai-use.metrics.json" "$PWD/.analyse-ai-use.analysis.json" "$PWD/ai-usage-report.html"
   ```

1. **Reduce.** Run the analyzer from the current workspace root, saving the metrics for the renderer:
   ```bash
   python3 skills/analyse-ai-use/scripts/scan.py --cwd "$PWD" --save "$PWD/.analyse-ai-use.metrics.json" >/dev/null
   ```
   Then read `$PWD/.analyse-ai-use.metrics.json`: `{"workspace", "host_tool", "scanned_tools", "tools": {<tool>: <metrics>, ...}}`. If it has an `"error"` key, relay it and stop. Otherwise this JSON is your only evidence; do **not** read raw transcripts (that defeats the skill). Read every field of every tool block before writing anything.

2. **Diagnose.** For **each tool in the output**, map its metrics to the diagnostics below. Every claim must cite a number from the scan — no ungrounded advice. Reach a diagnosis, per tool, for each of: prompt style, tool/skill habits, token efficiency (only where token fields are present — check `token_data_coverage` for copilot-chat), and iteration count. If more than one tool is present, add one **cross-tool** read: where the same workspace is used differently, and which tool fits which task here.

3. **Write the analysis JSON.** Write your prose — and only prose — to `$PWD/.analyse-ai-use.analysis.json` in the shape under *Analysis JSON* below. Do **not** put raw metrics here; the renderer already has them. This file is the entirety of what you author.

4. **Render + hand off.** Build the HTML:
   ```bash
   python3 skills/analyse-ai-use/scripts/render.py \
     --metrics "$PWD/.analyse-ai-use.metrics.json" \
     --analysis "$PWD/.analyse-ai-use.analysis.json" \
     --out "$PWD/ai-usage-report.html" --generated-at "$(date '+%Y-%m-%d %H:%M')"
   ```
   Then delete the two intermediate JSON files (`rm -f "$PWD/.analyse-ai-use.metrics.json" "$PWD/.analyse-ai-use.analysis.json"`) — only the HTML is meant to persist. In chat give the user **only**: the report path, a one-line headline finding, and the top 1–2 actions. Do not restate the full report in chat — that's what the HTML is for. Offer to open it (e.g. `open`/`xdg-open`/VSCode preview).

## Diagnostics — read each metric this way

Not every tool populates every field (`avg_end_context_tokens` is Copilot-CLI-only; `credits_aiu` is copilot-chat-only; copilot-chat token fields depend on `token_data_coverage`). A `null` means the tool doesn't record it — don't infer from absence.

**Cost-hierarchy ordering.** Order `token_leaks` and `actions` by token *cost*, not raw count: **output > input > compounding cache** (rationale and sources in [REFERENCES.md](REFERENCES.md)). Cache-write is the real agent-run cost lever, so a high `cache_write_pct` outranks a large-but-cheap `cache_read`.

- **`est_cost_usd` / `cost_by_model`** — estimated $ spend (list-price approximation, not billing). The most legible cost signal for a human; lead the report with it. `unpriced_models` were excluded (no rate on file).
- **`cache_write` / `cache_write_pct`** — cache-write is file-reads pulled into context — the dominant cost in agent runs. High `cache_write_pct` → recommend pinning hot files or a knowledge-graph tool over repeated file discovery (see the Graphify example in REFERENCES.md).
- **`cache_hit_ratio`** (Claude, copilot-chat) — fraction of input served from cache. Below ~0.7 means context churn (frequent re-reads, model switches, long gaps). High is good and cheap.
- **`credits_aiu`** (copilot-chat) — real metered credit usage (AIU) across the sessions. The truest cost signal available; pair it with `token_data_coverage` (how many sessions actually recorded tokens) so you don't read it as the full picture when logging was off for older sessions.
- **`avg_end_context_tokens`** (Copilot CLI) — how full the context window is by session end. Amadeus guidance says plan a reset around **~100k tokens** (REFERENCES.md); consistently above that means sessions run long without a reset, inflating every turn's cost.
- **`output_to_input_ratio`** — very low (<0.02) means huge context ingested to emit little; a sign of over-broad reads or bloated context relative to work done.
- **`avg_prompt_chars` + `short_prompt_pct`** — high short-prompt % (>40) signals terse, under-specified prompts that force clarifying round-trips. Very high avg chars can mean over-stuffed prompts.
- **`avg_prompts_per_session` vs `n_assistant_turns`** — many assistant turns per user prompt = long autonomous runs (good if converging); many *user* prompts with low output = back-and-forth thrash (iteration waste).
- **`reread_files_3plus`** — same file read ≥3× across sessions. Prime candidate for a `.github/copilot-instructions.md` / CLAUDE.md pin so it isn't re-fetched every time.
- **`top_tools` / `top_bash`** — repeated identical bash prefixes = candidates for a script, alias, or allowlist (fewer confirmations, fewer turns).
- **`skills_used`** — which skills fire, and gaps where a manual pattern should become a skill.
- **`models`** — model mix; flag if an expensive model does cheap mechanical work.
- **`prompt_samples`** — read these to characterise *voice and intent* (vague vs precise, feature vs fix vs explore). This is your qualitative evidence for the "usage style" section.

## Analysis JSON

Write exactly this shape to `$PWD/.analyse-ai-use.analysis.json`. Prose only — the renderer supplies all numbers, charts, tiles, and tables from the metrics. Every field is optional; omit what doesn't apply (e.g. drop token-leak items for a copilot-chat-only run).

```json
{
  "headline": "The single highest-leverage change, one sentence — the most important line in the report.",
  "usage_style": [
    {"tool": "claude-code", "text": "3–5 sentences on how they work with THIS tool, grounded in prompt_samples and the ratios; name the pattern (e.g. 'terse-prompt, long-autonomous-run')."}
  ],
  "whats_working": ["2–3 efficient habits, each citing a number and the tool."],
  "token_leaks": ["Biggest inefficiencies, each naming the metric + tool, ordered by the cost hierarchy (output > input > cache)."],
  "actions": [
    {"title": "Short imperative", "detail": "The concrete change in THIS workspace — a .github/copilot-instructions.md/CLAUDE.md entry, a bash prefix to allowlist, a pattern to turn into a skill/template, a file to pin.", "metric": "cache_write_pct", "impact": "~$4/session"}
  ]
}
```

Rules: one `usage_style` entry per tool present. Every `actions` item must be workspace-specific and name the `metric` it targets — generic AI advice is a no-op and must be cut. Order `actions` by the cost hierarchy above (highest-cost lever first); prefer `impact` in `$` when `est_cost_usd` is present, else tokens. When a leak matches an internal remedy in [REFERENCES.md](REFERENCES.md) (e.g. Graphify for cache-write), name it.
