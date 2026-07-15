# analyse-ai-use — references & tuning knobs

External sources and the numbers derived from them. Kept out of `SKILL.md` so the
skill body stays lean; consult this only when interpreting cost/hierarchy fields
or updating prices. The scanner's `MODEL_PRICES` table and thresholds trace here.

## Amadeus guidance (Confluence)

These links require an Amadeus Confluence login; they are for human readers, not
fetched at runtime.

- **[GitHub Copilot Recommendations](https://amadeus.atlassian.net/wiki/spaces/AMAM/pages/3756030499/GitHub+Copilot+Recommendations)**
  Golden rules, model/reasoning escalation table, context hygiene, tools/skills
  minimalism, observability. Source of the **~100k-token context-reset threshold**.
- **[AI Credits & Token Optimisation For Coding Agents](https://amadeus.atlassian.net/wiki/spaces/GATSR/pages/3741485744/AI+Credits+Token+Optimisation+For+Coding+Agents)**
  Monthly credit allowances and the **token cost hierarchy** (below). Parent of:
  - **[Token Optimisation Study](https://amadeus.atlassian.net/wiki/spaces/GATSR/pages/3742933966/Token+Optimisation+Study)**
    - **[Graphify](https://amadeus.atlassian.net/wiki/spaces/GATSR/pages/3763718082/Graphify)** — prebuilt codebase knowledge graph; measured
      cache-write 10.86M → 2.23M by answering structural questions from the graph
      instead of reading files into context.
    - **[Caveman](https://amadeus.atlassian.net/wiki/spaces/GATSR/pages/3763742070/Caveman)** — output-token compressor; the study's headline
      saving was confounded (cheaper second model + single non-deterministic run),
      so it neither proved nor disproved a benefit.

## Token cost hierarchy — drives advice ordering

From the AI Credits page. Order `token_leaks` and `actions` by this, highest first:

1. **Output** — highest per-token cost; generation + reasoning. Terser responses,
   lower reasoning levels, smaller diffs.
2. **Input** — prompts, tool descriptions, project context. Tighter prompts and
   fewer just-in-case tools; improves cache reuse downstream.
3. **Cache** — cheap per token but **compounds** over long sessions. Controlled
   indirectly by fixing input/output and by resetting bloated context.

**Cache-write is the real agent-run cost lever** (the Graphify study hinges on it):
it's file-reads pulled into context. High `cache_write_pct` → recommend pinning hot
files / a knowledge-graph tool over repeated file discovery.

## Monthly credit allowances (context for `credits_aiu`)

GitHub Copilot 10,000 · Kiro 1,000 · Windsurf 1,000 · Claude Code $100 (not credits).
Not comparable across providers. Use to frame Copilot Chat AIU spend as a % of budget.

## Internal optimisation tools (single source of truth for what to recommend)

This section — not the Confluence summaries above — decides what the report
recommends. The summaries are provenance only; don't derive a verdict from them.

- **Graphify** — *recommend* when `cache_write_pct` is high from repeated file
  discovery (see `reread_files_3plus`). Evidence-backed cache-write win.
- **Headroom** — *recommend* for input-token reduction. ⚠️ open-source version has
  security risks; recommend only the internal build when available.
- **Caveman** — *do not recommend as a proven fix.* Its one study was inconclusive
  (confounded by model choice), so there is no evidence it helps. If a session is
  output-heavy, recommend the direct levers instead — terser responses, lower
  reasoning, smaller diffs — and at most mention Caveman as "unproven, worth a
  controlled trial," never as a fix. Not recommending it is the correct default.

## `MODEL_PRICES` — cost estimate rates (USD / 1M tokens)

Best-effort list prices in `scan.py` for an **estimate**, not billing. Update here
and in `scan.py` together when rates change. Anthropic cache_write = 5-minute write
rate. Unmatched models are reported under `unpriced_models` and excluded from cost.
