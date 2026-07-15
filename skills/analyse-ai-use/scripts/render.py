#!/usr/bin/env python3
"""Render an analyse-ai-use report as a single self-contained HTML file.

Numbers, charts, and tables are built here directly from the scan metrics JSON —
the model never re-types them. The model supplies only the prose analysis (a
small JSON), keeping its output tiny.

Usage:
    python3 render.py --metrics scan.json --analysis analysis.json --out report.html

analysis.json shape (all fields optional):
    {
      "usage_style": [{"tool": "claude-code", "text": "..."}],
      "whats_working": ["...", "..."],
      "token_leaks": ["...", "..."],
      "actions": [{"title": "...", "detail": "...", "metric": "...", "impact": "..."}],
      "headline": "the single highest-leverage change, one line"
    }
"""
import argparse
import html
import json
import os


TOOL_LABEL = {
    "claude-code": "Claude Code",
    "copilot-cli": "Copilot CLI",
    "copilot-chat": "Copilot Chat",
}


def esc(x):
    return html.escape(str(x)) if x is not None else ""


def fmt_int(n):
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return "—"


def fmt_tokens(n):
    if n is None:
        return "—"
    n = int(n)
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


def pct(x):
    return "—" if x is None else f"{round(x * 100)}%"


def bar_rows(counter, limit=12, unit=""):
    """Horizontal bar chart rows from a {label: count} dict."""
    items = list(counter.items())[:limit]
    if not items:
        return '<p class="muted">none</p>'
    top = max(v for _, v in items) or 1
    out = []
    for label, v in items:
        w = round(100 * v / top)
        out.append(
            f'<div class="bar-row"><span class="bar-label" title="{esc(label)}">{esc(label)}</span>'
            f'<span class="bar-track"><span class="bar-fill" style="width:{w}%"></span></span>'
            f'<span class="bar-val">{fmt_int(v)}{esc(unit)}</span></div>'
        )
    return "\n".join(out)


def table(headers, rows):
    if not rows:
        return '<p class="muted">none</p>'
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows
    )
    return f'<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def basename(path):
    return path.rsplit("/", 1)[-1] if isinstance(path, str) else path


def tool_metric_tiles(m):
    """Metric tiles for one tool. Skips tiles the tool doesn't record (null)."""
    tiles = [
        ("Sessions", fmt_int(m.get("n_sessions"))),
        ("User prompts", fmt_int(m.get("n_user_prompts"))),
        ("Assistant turns", fmt_int(m.get("n_assistant_turns"))),
        ("Prompts / session", m.get("avg_prompts_per_session", "—")),
        ("Avg prompt chars", fmt_int(m.get("avg_prompt_chars"))),
        ("Short prompts", pct((m.get("short_prompt_pct") or 0) / 100)
         if m.get("short_prompt_pct") is not None else "—"),
    ]
    if m.get("est_cost_usd") is not None:
        tiles.append(("Est. cost", f'${m.get("est_cost_usd"):,.2f}'))
    if m.get("output_tokens"):
        tiles.append(("Output tokens", fmt_tokens(m.get("output_tokens"))))
    if m.get("total_input_incl_cache"):
        tiles.append(("Input (incl. cache)", fmt_tokens(m.get("total_input_incl_cache"))))
    if m.get("cache_write"):
        cwp = m.get("cache_write_pct")
        label = f'{fmt_tokens(m.get("cache_write"))}' + (f' ({cwp}%)' if cwp else '')
        tiles.append(("Cache write", label))
    if m.get("cache_hit_ratio") is not None:
        tiles.append(("Cache hit", pct(m.get("cache_hit_ratio"))))
    if m.get("output_to_input_ratio") is not None:
        tiles.append(("Output : input", str(m.get("output_to_input_ratio"))))
    if m.get("avg_end_context_tokens") is not None:
        tiles.append(("Avg end context", fmt_tokens(m.get("avg_end_context_tokens"))))
    if m.get("credits_aiu") is not None:
        tiles.append(("Credits (AIU)", f'{m.get("credits_aiu"):,}'))
    cells = "".join(
        f'<div class="tile"><div class="tile-val">{esc(v)}</div>'
        f'<div class="tile-key">{esc(k)}</div></div>'
        for k, v in tiles
    )
    return f'<div class="tiles">{cells}</div>'


def tool_section(name, m, analysis):
    label = TOOL_LABEL.get(name, name)
    style = next((s.get("text") for s in analysis.get("usage_style", [])
                  if s.get("tool") == name), None)

    models = ", ".join(f"{esc(k)} ({fmt_int(v)})" for k, v in (m.get("models") or {}).items())

    reread_rows = [
        (esc(basename(f)), fmt_int(n), f'<span class="path">{esc(f)}</span>')
        for f, n in list((m.get("reread_files_3plus") or {}).items())[:10]
    ]
    edit_rows = [
        (esc(basename(f)), fmt_int(n), f'<span class="path">{esc(f)}</span>')
        for f, n in list((m.get("top_files_edited") or {}).items())[:10]
    ]
    session_rows = [
        (esc(s.get("title", "")[:60]), fmt_int(s.get("prompts")),
         fmt_int(s.get("assistant_turns")),
         "—" if s.get("duration_min") is None else f'{s.get("duration_min")}m',
         fmt_tokens(s.get("output_tokens")) if s.get("output_tokens") else "—")
        for s in (m.get("sessions") or [])[:20]
    ]

    style_html = f'<p class="lede">{esc(style)}</p>' if style else ""

    cost_card = ""
    cbm = m.get("cost_by_model")
    if cbm:
        cost_rows = [(esc(k), f'${v:,.2f}') for k, v in
                     sorted(cbm.items(), key=lambda kv: -kv[1])]
        note = ""
        if m.get("unpriced_models"):
            note = (f'<p class="muted small">Unpriced (no rate on file): '
                    f'{esc(", ".join(m["unpriced_models"]))}</p>')
        cost_card = (f'<div class="card"><h3>Estimated cost by model</h3>'
                     f'{table(["Model", "Est. cost"], cost_rows)}{note}</div>')

    return f"""
    <section class="tool">
      <h2>{esc(label)} <span class="muted small">· {models or "model n/a"}</span></h2>
      {style_html}
      {tool_metric_tiles(m)}
      {cost_card}
      <div class="grid2">
        <div class="card"><h3>Top tools</h3>{bar_rows(m.get("top_tools") or {})}</div>
        <div class="card"><h3>Top bash commands</h3>{bar_rows(m.get("top_bash") or {})}</div>
      </div>
      <div class="grid2">
        <div class="card"><h3>Skills used</h3>{bar_rows(m.get("skills_used") or {})}</div>
        <div class="card"><h3>Re-read files (≥3×)</h3>
          {table(["File", "Reads", "Path"], reread_rows)}</div>
      </div>
      <div class="card"><h3>Most-edited files</h3>
        {table(["File", "Edits", "Path"], edit_rows)}</div>
      <details class="card"><summary>Sessions ({len(m.get("sessions") or [])})</summary>
        {table(["Title", "Prompts", "Turns", "Duration", "Output"], session_rows)}</details>
    </section>
    """


def list_block(title, items):
    if not items:
        return ""
    lis = "".join(f"<li>{esc(x)}</li>" for x in items)
    return f'<div class="card"><h3>{esc(title)}</h3><ul>{lis}</ul></div>'


def actions_block(actions):
    if not actions:
        return ""
    cards = []
    for i, a in enumerate(actions, 1):
        meta = []
        if a.get("metric"):
            meta.append(f'<span class="chip metric">{esc(a["metric"])}</span>')
        if a.get("impact"):
            meta.append(f'<span class="chip impact">{esc(a["impact"])}</span>')
        cards.append(
            f'<div class="action"><div class="action-n">{i}</div>'
            f'<div><div class="action-title">{esc(a.get("title", ""))}</div>'
            f'<div class="action-detail">{esc(a.get("detail", ""))}</div>'
            f'<div class="chips">{"".join(meta)}</div></div></div>'
        )
    return f'<section><h2>Do this in this workspace</h2>{"".join(cards)}</section>'


CSS = """
:root{--bg:#0d1117;--panel:#161b22;--panel2:#1c2230;--border:#2a3140;--fg:#e6edf3;
--muted:#8b949e;--accent:#7c9cff;--accent2:#3fb950;--bar:#7c9cff;--chip:#22283a;}
@media(prefers-color-scheme:light){:root{--bg:#f6f8fa;--panel:#fff;--panel2:#f0f3f7;
--border:#d0d7de;--fg:#1f2328;--muted:#656d76;--accent:#4b6bff;--accent2:#1a7f37;
--bar:#4b6bff;--chip:#eef1f6;}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
.wrap{max-width:1040px;margin:0 auto;padding:40px 24px 80px;}
header.top{border-bottom:1px solid var(--border);padding-bottom:24px;margin-bottom:32px;}
header.top h1{margin:0 0 6px;font-size:28px;letter-spacing:-.02em;}
.sub{color:var(--muted);font-size:14px;}
.headline{background:linear-gradient(90deg,var(--panel2),transparent);
border-left:3px solid var(--accent);padding:16px 20px;border-radius:8px;margin:24px 0;font-size:17px;}
h2{font-size:21px;margin:40px 0 14px;letter-spacing:-.01em;}
h3{font-size:14px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);margin:0 0 12px;}
.lede{color:var(--fg);font-size:16px;margin:0 0 18px;opacity:.92;}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin:16px 0 24px;}
.tile{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:14px 16px;}
.tile-val{font-size:22px;font-weight:650;letter-spacing:-.02em;}
.tile-key{font-size:12px;color:var(--muted);margin-top:2px;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;}
@media(max-width:720px){.grid2{grid-template-columns:1fr;}}
.card{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:18px 20px;margin-bottom:16px;}
.bar-row{display:grid;grid-template-columns:150px 1fr 54px;align-items:center;gap:10px;margin:6px 0;font-size:13px;}
.bar-label{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--fg);}
.bar-track{background:var(--panel2);border-radius:6px;height:9px;overflow:hidden;}
.bar-fill{display:block;height:100%;background:var(--bar);border-radius:6px;}
.bar-val{text-align:right;color:var(--muted);font-variant-numeric:tabular-nums;}
table{width:100%;border-collapse:collapse;font-size:13px;}
th{text-align:left;color:var(--muted);font-weight:600;padding:6px 8px;border-bottom:1px solid var(--border);}
td{padding:6px 8px;border-bottom:1px solid var(--border);vertical-align:top;}
td:nth-child(2),th:nth-child(2){font-variant-numeric:tabular-nums;}
.path{color:var(--muted);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;word-break:break-all;}
.muted{color:var(--muted);}.small{font-size:13px;font-weight:400;}
ul{margin:0;padding-left:20px;}li{margin:6px 0;}
details.card summary{cursor:pointer;font-size:14px;font-weight:600;color:var(--muted);}
details.card[open] summary{margin-bottom:12px;}
.action{display:flex;gap:14px;background:var(--panel);border:1px solid var(--border);
border-radius:12px;padding:16px 18px;margin-bottom:12px;}
.action-n{flex:0 0 30px;height:30px;border-radius:50%;background:var(--accent);color:#fff;
display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;}
.action-title{font-weight:650;font-size:16px;margin-bottom:4px;}
.action-detail{color:var(--fg);opacity:.9;margin-bottom:10px;}
.chips{display:flex;gap:8px;flex-wrap:wrap;}
.chip{font-size:12px;padding:3px 10px;border-radius:20px;background:var(--chip);color:var(--muted);}
.chip.metric{color:var(--accent);}.chip.impact{color:var(--accent2);}
footer{margin-top:48px;padding-top:20px;border-top:1px solid var(--border);color:var(--muted);font-size:12px;}
"""


def build_html(metrics, analysis, generated_at):
    ws = metrics.get("workspace", "")
    scanned = metrics.get("scanned_tools", [])
    tools = metrics.get("tools", {})

    scanned_labels = ", ".join(TOOL_LABEL.get(t, t) for t in scanned)
    headline = analysis.get("headline")
    headline_html = (
        f'<div class="headline"><strong>Highest-leverage change:</strong> {esc(headline)}</div>'
        if headline else ""
    )

    tool_html = "".join(tool_section(n, m, analysis) for n, m in tools.items())

    working = list_block("What's working", analysis.get("whats_working"))
    leaks = list_block("Where tokens leak", analysis.get("token_leaks"))
    analysis_html = ""
    if working or leaks:
        analysis_html = f'<section><h2>Analysis</h2><div class="grid2">{working}{leaks}</div></section>'

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Usage Report — {esc(basename(ws))}</title>
<style>{CSS}</style></head>
<body><div class="wrap">
<header class="top">
  <h1>AI Usage Report</h1>
  <div class="sub">{esc(ws)} · {esc(scanned_labels) or "no tools"} · {esc(generated_at)}</div>
</header>
{headline_html}
{tool_html}
{analysis_html}
{actions_block(analysis.get("actions"))}
<footer>Generated by the <strong>analyse-ai-use</strong> skill · metrics derived from local session transcripts, which never left this machine.</footer>
</div></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", required=True)
    ap.add_argument("--analysis", default=None,
                    help="JSON of prose sections; omit for a numbers-only report")
    ap.add_argument("--out", required=True)
    ap.add_argument("--generated-at", default="", help="timestamp string for the header")
    args = ap.parse_args()

    with open(args.metrics, encoding="utf-8") as fh:
        metrics = json.load(fh)
    analysis = {}
    if args.analysis and os.path.exists(args.analysis):
        with open(args.analysis, encoding="utf-8") as fh:
            analysis = json.load(fh)

    html_doc = build_html(metrics, analysis, args.generated_at)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(html_doc)
    print(args.out)


if __name__ == "__main__":
    main()
