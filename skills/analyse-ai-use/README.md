# Analyse AI Use

Point this skill at a workspace and it tells you **how you use your AI coding tool there** — then hands back a styled HTML report with concrete ways to spend fewer tokens, fewer credits, and fewer iterations.

- [`SKILL.md`](SKILL.md) — the procedure the agent follows (scan → diagnose → render)
- [`scripts/scan.py`](scripts/scan.py) — deterministic, stdlib-only transcript reducer
- [`scripts/render.py`](scripts/render.py) — builds the self-contained HTML report
- [`REFERENCES.md`](REFERENCES.md) — sources, the token cost hierarchy, and pricing provenance

## What it does

It reads the **local session transcripts** of the AI tool it is running inside, reduces hundreds of KB of history into one compact metrics object, and produces a report covering:

- **Cost** — estimated $ spend per model, cache-write vs cache-read split, and (for Copilot Chat) real metered credit usage.
- **Usage style** — prompt length, iteration count, tool and skill habits, model mix.
- **Where tokens leak** — ordered by the official cost hierarchy (output > input > cache), each with a workspace-specific fix.

## Supported tools

The scanner detects the tool it runs inside and reports on **only that tool** — it never mixes another tool's data into the report:

- **Claude Code** — full token/cache data
- **GitHub Copilot CLI** — output tokens + end-of-session context
- **GitHub Copilot Chat** — tokens and metered credits (from the VS Code debug logs; requires recent Copilot Chat with trace logging on)

Pass `--all` to compare across tools, or `--tool <name>` to force one.

## Privacy

Everything is local. The scanner reads transcripts already on your machine and writes an HTML file in the workspace. Nothing is uploaded. Scripts are Python 3.9+ standard library only.

## Why the report is HTML, not chat

Because a long analysis is hard to read in a chat window — and cheaper to produce as a file. `render.py` builds every number, chart, and table directly from the metrics, so the agent only writes the prose analysis and never re-types a metric into chat.

## Design notes

- **Every run is from scratch** — it re-scans live transcripts each time; it never reuses a previous run's metrics or report.
- **Self-contained references** — the cost hierarchy, thresholds, and tool recommendations live in `REFERENCES.md` (kept out of `SKILL.md` so the body stays lean), sourced from the Amadeus AI-credits and Copilot-recommendations guidance.
