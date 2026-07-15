#!/usr/bin/env python3
"""Reduce a workspace's AI-coding-tool session transcripts to compact usage metrics.

Supports multiple tools; each reader emits the SAME metrics schema so the report
can compare across them. The raw transcripts never enter the model context — only
this reduction does.

Tools scanned:
  claude-code   ~/.claude/projects/<path-slug>/*.jsonl                     (matched by path slug)
  copilot-cli   ~/.copilot/session-state/<uuid>/                           (matched by workspace.yaml cwd)
  copilot-chat  ~/.vscode-server/.../GitHub.copilot-chat/transcripts/*     (matched by dominant referenced path)

By default the scanner scans ONLY the tool it is running inside (detected from
env: CLAUDECODE -> claude-code, COPILOT_CLI_* -> copilot-cli). Pass --all to
scan every tool, or --tool to force one.

Usage:
    python3 scan.py                       # host tool only, workspace from $PWD
    python3 scan.py --all                 # every supported tool
    python3 scan.py --cwd /path/to/repo   # explicit workspace root
    python3 scan.py --tool copilot-chat   # force one tool (repeatable)
    python3 scan.py --sessions N          # only the N most recent sessions per tool
"""
import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime


# ---------------------------------------------------------------- helpers

def parse_ts(s):
    if not isinstance(s, str):
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def empty_metrics():
    return {
        "n_sessions": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read": 0,
        "cache_create": 0,
        "context_tokens_last": [],   # per-session end-of-session context size, when known
        "n_user_prompts": 0,
        "n_assistant_turns": 0,
        "prompt_chars": [],
        "prompt_samples": [],
        "models": Counter(),
        "tools": Counter(),
        "skills": Counter(),
        "files_read": Counter(),
        "files_edited": Counter(),
        "bash_cmds": Counter(),
        "credits": 0.0,              # copilot metered usage (AIU), when recorded
        "n_token_sessions": 0,       # sessions that actually carried token data
        # per-model token split {model: {input, output, cache_write, cache_read}}
        # — cache-write is the dominant cost driver in agent runs, so we keep the
        # four classes separate rather than collapsing them (see REFERENCES.md).
        "model_tokens": {},
        "sessions": [],              # per-session summaries
    }


def bash_prefix(cmd):
    return " ".join(cmd.strip().split()[0:2])


# Anthropic list prices, USD per million tokens, by model family. Used to turn
# per-model token counts into an estimated dollar cost. Sourced from the Amadeus
# "AI Credits & Token Optimisation" study (see REFERENCES.md); update there.
MODEL_PRICES = {
    # Anthropic (cache_write = 5m-write rate)
    "opus":     {"input": 5.0,  "output": 25.0, "cache_write": 6.25, "cache_read": 0.50},
    "sonnet":   {"input": 3.0,  "output": 15.0, "cache_write": 3.75, "cache_read": 0.30},
    "haiku":    {"input": 0.80, "output": 4.0,  "cache_write": 1.0,  "cache_read": 0.08},
    # OpenAI (used by Copilot Chat; cache_write == input, cached reads discounted)
    "gpt-5":    {"input": 1.25, "output": 10.0, "cache_write": 1.25, "cache_read": 0.125},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "cache_write": 0.15, "cache_read": 0.075},
    "gpt-4o":   {"input": 2.5,  "output": 10.0, "cache_write": 2.5,  "cache_read": 1.25},
    "o4-mini":  {"input": 1.10, "output": 4.4,  "cache_write": 1.10, "cache_read": 0.275},
}

# Longest family key first so 'gpt-4o-mini' wins over 'gpt-4o'.
_PRICE_FAMILIES = sorted(MODEL_PRICES, key=len, reverse=True)


def price_for_model(model):
    """Match a model id (e.g. 'claude-opus-4-8', 'gpt-5.3-codex') to a price row, or None.

    Prices are best-effort list rates for a cost *estimate* (see REFERENCES.md);
    a mini/nano variant without its own row is approximated by its family."""
    if not model:
        return None
    ml = model.lower()
    for family in _PRICE_FAMILIES:
        if family in ml:
            return MODEL_PRICES[family]
    return None


def add_model_tokens(m, model, inp=0, out=0, cache_write=0, cache_read=0):
    if not model:
        return
    row = m["model_tokens"].setdefault(
        model, {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0})
    row["input"] += inp or 0
    row["output"] += out or 0
    row["cache_write"] += cache_write or 0
    row["cache_read"] += cache_read or 0


def finalize(m):
    """Turn a raw metrics accumulator into the JSON-serializable report block."""
    tot_in_cache = m["input_tokens"] + m["cache_read"] + m["cache_create"]
    cache_hit = (m["cache_read"] / tot_in_cache) if tot_in_cache else None
    reread = {f: n for f, n in m["files_read"].items() if n >= 3}
    pc = m["prompt_chars"]

    # Estimated $ cost, per model, from the per-model token split (see REFERENCES.md).
    # Only models with a known price row contribute; others are listed as unpriced.
    cost_by_model = {}
    est_cost = 0.0
    unpriced = []
    for model, tk in m["model_tokens"].items():
        row = price_for_model(model)
        if not row:
            if any(tk.values()):
                unpriced.append(model)
            continue
        c = (tk["input"] * row["input"] + tk["output"] * row["output"]
             + tk["cache_write"] * row["cache_write"]
             + tk["cache_read"] * row["cache_read"]) / 1_000_000
        cost_by_model[model] = round(c, 2)
        est_cost += c

    return {
        "n_sessions": m["n_sessions"],
        "input_tokens": m["input_tokens"],
        "output_tokens": m["output_tokens"],
        "cache_read": m["cache_read"],
        "cache_write": m["cache_create"],
        "total_input_incl_cache": tot_in_cache,
        "cache_hit_ratio": round(cache_hit, 3) if cache_hit is not None else None,
        # cache-write share of total input — the dominant cost lever (REFERENCES.md).
        "cache_write_pct": round(100 * m["cache_create"] / tot_in_cache)
        if tot_in_cache else None,
        "est_cost_usd": round(est_cost, 2) if est_cost else None,
        "cost_by_model": cost_by_model or None,
        "unpriced_models": unpriced or None,
        "output_to_input_ratio": round(m["output_tokens"] / tot_in_cache, 4)
        if tot_in_cache else None,
        "avg_end_context_tokens": round(sum(m["context_tokens_last"]) / len(m["context_tokens_last"]))
        if m["context_tokens_last"] else None,
        "n_user_prompts": m["n_user_prompts"],
        "n_assistant_turns": m["n_assistant_turns"],
        "avg_prompts_per_session": round(m["n_user_prompts"] / m["n_sessions"], 1)
        if m["n_sessions"] else 0,
        "avg_prompt_chars": round(sum(pc) / len(pc)) if pc else 0,
        "short_prompt_pct": round(100 * sum(1 for c in pc if c < 60) / len(pc)) if pc else 0,
        "models": dict(m["models"]),
        "top_tools": dict(m["tools"].most_common(20)),
        "skills_used": dict(m["skills"].most_common(20)),
        "top_files_read": dict(m["files_read"].most_common(15)),
        "reread_files_3plus": reread,
        "top_files_edited": dict(m["files_edited"].most_common(15)),
        "top_bash": dict(m["bash_cmds"].most_common(20)),
        "credits_aiu": round(m["credits"], 2) if m["credits"] else None,
        "token_data_coverage": (f"{m['n_token_sessions']}/{m['n_sessions']} sessions"
                                if m["n_token_sessions"] else None),
        "sessions": m["sessions"],
        "prompt_samples": m["prompt_samples"][:80],
    }


def add_session_summary(m, title, prompts, turns, start, end, out_tokens):
    dur = round((end - start).total_seconds() / 60, 1) if (start and end) else None
    m["sessions"].append({
        "title": title or "(untitled)",
        "prompts": prompts,
        "assistant_turns": turns,
        "duration_min": dur,
        "output_tokens": out_tokens,
    })


# ---------------------------------------------------------------- claude-code

def slugify(path):
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def claude_project_dir(cwd):
    projects = os.path.expanduser("~/.claude/projects")
    if not os.path.isdir(projects):
        return None
    slug = slugify(os.path.abspath(cwd))
    exact = os.path.join(projects, slug)
    if os.path.isdir(exact):
        return exact
    best = None
    for name in os.listdir(projects):
        full = os.path.join(projects, name)
        if os.path.isdir(full) and slug.startswith(name):
            if best is None or len(name) > len(os.path.basename(best)):
                best = full
    return best


def claude_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(x.get("text", "") for x in content
                         if isinstance(x, dict) and x.get("type") == "text")
    return ""


def scan_claude(cwd, max_sessions):
    pdir = claude_project_dir(cwd)
    m = empty_metrics()
    if not pdir:
        return None
    files = [os.path.join(pdir, f) for f in os.listdir(pdir) if f.endswith(".jsonl")]
    files.sort(key=os.path.getmtime, reverse=True)
    if max_sessions:
        files = files[:max_sessions]
    for path in files:
        title = None
        s_prompts = s_turns = s_out = 0
        s_start = s_end = None
        seen_content = False
        for line in open(path, encoding="utf-8", errors="replace"):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            t = d.get("type")
            ts = parse_ts(d.get("timestamp"))
            if ts:
                s_start = ts if s_start is None or ts < s_start else s_start
                s_end = ts if s_end is None or ts > s_end else s_end
            if t == "ai-title" and d.get("aiTitle"):
                title = d["aiTitle"]
            if d.get("attributionSkill"):
                m["skills"][d["attributionSkill"]] += 1
            if t == "user" and not d.get("isMeta"):
                txt = claude_text(d.get("message", {}).get("content"))
                if txt.strip():
                    seen_content = True
                    s_prompts += 1
                    m["n_user_prompts"] += 1
                    m["prompt_chars"].append(len(txt))
                    if len(m["prompt_samples"]) < 80:
                        m["prompt_samples"].append(txt[:400])
            if t == "assistant":
                seen_content = True
                msg = d.get("message", {})
                s_turns += 1
                m["n_assistant_turns"] += 1
                model = msg.get("model")
                if model:
                    m["models"][model] += 1
                u = msg.get("usage", {}) or {}
                inp = u.get("input_tokens", 0) or 0
                out = u.get("output_tokens", 0) or 0
                cr = u.get("cache_read_input_tokens", 0) or 0
                cw = u.get("cache_creation_input_tokens", 0) or 0
                m["input_tokens"] += inp
                m["output_tokens"] += out
                s_out += out
                m["cache_read"] += cr
                m["cache_create"] += cw
                add_model_tokens(m, model, inp, out, cw, cr)
                for c in msg.get("content", []):
                    if isinstance(c, dict) and c.get("type") == "tool_use":
                        name = c.get("name", "?")
                        m["tools"][name] += 1
                        inp = c.get("input", {}) or {}
                        if name == "Read" and inp.get("file_path"):
                            m["files_read"][inp["file_path"]] += 1
                        elif name in ("Edit", "Write") and inp.get("file_path"):
                            m["files_edited"][inp["file_path"]] += 1
                        elif name == "Bash" and inp.get("command"):
                            m["bash_cmds"][bash_prefix(inp["command"])] += 1
                        elif name == "Skill" and inp.get("skill"):
                            m["skills"][inp["skill"]] += 1
        if seen_content:
            m["n_sessions"] += 1
            add_session_summary(m, title, s_prompts, s_turns, s_start, s_end, s_out)
    return finalize(m) if m["n_sessions"] else None


# ---------------------------------------------------------------- copilot-cli

def copilot_yaml_field(path, key):
    for line in open(path, encoding="utf-8", errors="replace"):
        if line.startswith(key + ":"):
            return line.split(":", 1)[1].strip()
    return None


def scan_copilot(cwd, max_sessions):
    root = os.path.expanduser("~/.copilot/session-state")
    if not os.path.isdir(root):
        return None
    target = os.path.abspath(cwd)
    dirs = []
    for name in os.listdir(root):
        wf = os.path.join(root, name, "workspace.yaml")
        ev = os.path.join(root, name, "events.jsonl")
        if not (os.path.exists(wf) and os.path.exists(ev)):
            continue
        if copilot_yaml_field(wf, "cwd") == target:
            dirs.append((root, name, wf, ev))
    dirs.sort(key=lambda x: os.path.getmtime(x[3]), reverse=True)
    if max_sessions:
        dirs = dirs[:max_sessions]

    m = empty_metrics()
    for _, name, wf, ev in dirs:
        consume_copilot_events(m, ev, copilot_yaml_field(wf, "summary"))
    return finalize(m) if m["n_sessions"] else None


# Read-tool names differ across Copilot surfaces (CLI uses `view`, chat uses
# `read_file`); accept both so file-read counts are comparable.
COPILOT_READ_TOOLS = ("view", "read_file")
COPILOT_EDIT_TOOLS = ("apply_patch", "create_file", "insert_edit_into_file",
                      "replace_string_in_file", "multi_replace_string_in_file")
COPILOT_BASH_TOOLS = ("bash", "run_in_terminal")


def read_copilot_chat_tokens(main_path):
    """Copilot Chat records token/credit usage NOT in the transcript but in the
    sibling debug-logs/<id>/main.jsonl, one `llm_request` per model call. Returns
    per-session totals, or None if the file is absent/a stub (trace logging off).
    Recent Copilot Chat (~v0.52+) writes these by default; older sessions don't."""
    if not main_path or not os.path.exists(main_path):
        return None
    inp = out = cache = 0
    aiu = 0
    reqs = 0
    per_model = {}   # {model: (input, output, cache_read)} — cachedTokens is a read
    for line in open(main_path, encoding="utf-8", errors="replace"):
        if '"llm_request"' not in line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") != "llm_request":
            continue
        a = e.get("attrs", {}) if isinstance(e.get("attrs"), dict) else {}
        reqs += 1
        ri = a.get("inputTokens", 0) or 0
        ro = a.get("outputTokens", 0) or 0
        rc = a.get("cachedTokens", 0) or 0
        inp += ri
        out += ro
        cache += rc
        aiu += a.get("copilotUsageNanoAiu", 0) or 0
        mdl = a.get("model")
        if mdl:
            p = per_model.setdefault(mdl, [0, 0, 0])
            p[0] += ri
            p[1] += ro
            p[2] += rc
    if not reqs:
        return None
    return {"input": inp, "output": out, "cache": cache,
            "credits": aiu / 1e9, "requests": reqs, "per_model": per_model}


def consume_copilot_events(m, ev_path, title, token_source=None):
    """Fold one Copilot events/transcript JSONL (CLI or chat share the schema)
    into the metrics accumulator `m`. One file == one session. `token_source`,
    if given, is a debug-logs main.jsonl path whose per-request token/credit
    totals are folded in (Copilot Chat keeps tokens there, not in the transcript)."""
    s_prompts = s_turns = s_out = 0
    s_start = s_end = None
    end_ctx = None
    for line in open(ev_path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        t = e.get("type")
        data = e.get("data", {}) if isinstance(e.get("data"), dict) else {}
        ts = parse_ts(e.get("timestamp")) or parse_ts(data.get("startTime"))
        if ts:
            s_start = ts if s_start is None or ts < s_start else s_start
            s_end = ts if s_end is None or ts > s_end else s_end
        if t in ("session.start", "session.model_change"):
            model = data.get("newModel") or data.get("model")
            if model:
                m["models"][model] += 1
        elif t == "user.message":
            txt = data.get("content", "") or ""
            if txt.strip():
                s_prompts += 1
                m["n_user_prompts"] += 1
                m["prompt_chars"].append(len(txt))
                if len(m["prompt_samples"]) < 80:
                    m["prompt_samples"].append(txt[:400])
        elif t == "assistant.message":
            s_turns += 1
            m["n_assistant_turns"] += 1
            out = data.get("outputTokens", 0) or 0
            m["output_tokens"] += out
            s_out += out
            for tr in data.get("toolRequests", []) or []:
                tname = tr.get("name", "?")
                m["tools"][tname] += 1
                args = tr.get("arguments", {}) or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                if not isinstance(args, dict):
                    args = {}
                path = args.get("path") or args.get("file") or args.get("filePath")
                if path and ("/.vscode-server/" in path or "/.claude/" in path):
                    path = None  # tool-internal scratch files, not user code
                if tname in COPILOT_BASH_TOOLS and args.get("command"):
                    m["bash_cmds"][bash_prefix(args["command"])] += 1
                elif tname in COPILOT_READ_TOOLS and path:
                    m["files_read"][path] += 1
                elif tname in COPILOT_EDIT_TOOLS and path:
                    m["files_edited"][path] += 1
                elif tname == "skill" and args.get("skill"):
                    m["skills"][args["skill"]] += 1
        elif t == "session.shutdown":
            end_ctx = data.get("currentTokens") or data.get("conversationTokens")

    # Copilot Chat: real token/credit usage lives in the sibling main.jsonl.
    tok = read_copilot_chat_tokens(token_source) if token_source else None
    if tok:
        m["input_tokens"] += tok["input"]
        m["cache_read"] += tok["cache"]
        m["credits"] += tok["credits"]
        if not s_out:                      # prefer transcript's per-turn out; else main.jsonl
            m["output_tokens"] += tok["output"]
            s_out = tok["output"]
        for mdl, (ri, ro, rc) in tok["per_model"].items():
            add_model_tokens(m, mdl, inp=ri, out=ro, cache_read=rc)

    if s_prompts or s_turns:
        m["n_sessions"] += 1
        if tok:
            m["n_token_sessions"] += 1
        if end_ctx:
            m["context_tokens_last"].append(end_ctx)
        add_session_summary(m, title, s_prompts, s_turns, s_start, s_end, s_out)


# ---------------------------------------------------------------- copilot-chat

def scan_copilot_chat(cwd, max_sessions):
    """VSCode Copilot chat transcripts. No workspace.yaml exists, so match a
    transcript to the target workspace by the file path it most references."""
    base = os.path.expanduser("~/.vscode-server/data/User/workspaceStorage")
    if not os.path.isdir(base):
        return None
    target = os.path.abspath(cwd)
    path_re = re.compile(r"/[A-Za-z0-9_.\-/]+")
    matched = []
    for ws in os.listdir(base):
        tdir = os.path.join(base, ws, "GitHub.copilot-chat", "transcripts")
        if not os.path.isdir(tdir):
            continue
        for fn in os.listdir(tdir):
            if not fn.endswith(".jsonl"):
                continue
            ev = os.path.join(tdir, fn)
            # Cheap gate: only score files that mention the target at all.
            try:
                with open(ev, encoding="utf-8", errors="replace") as fh:
                    head = fh.read(200000)
            except Exception:
                continue
            if target not in head:
                continue
            # Confirm target is the dominant referenced root, so a transcript
            # that merely name-drops another repo doesn't get miscounted.
            counts = Counter()
            for mtch in path_re.findall(head):
                if mtch.startswith(target):
                    counts["__target__"] += 1
                counts[mtch[: len(target)]] += 1
            if counts.get("__target__", 0) >= 3:
                matched.append(ev)
    matched.sort(key=os.path.getmtime, reverse=True)
    if max_sessions:
        matched = matched[:max_sessions]

    m = empty_metrics()
    for ev in matched:
        # token/credit data lives in the sibling debug-logs/<session-id>/main.jsonl
        sid = os.path.basename(ev)[:-6]  # strip ".jsonl"
        root = ev.split("/transcripts/")[0]
        main_path = os.path.join(root, "debug-logs", sid, "main.jsonl")
        consume_copilot_events(m, ev, None, token_source=main_path)
    return finalize(m) if m["n_sessions"] else None


# ---------------------------------------------------------------- main

READERS = {
    "claude-code": scan_claude,
    "copilot-cli": scan_copilot,
    "copilot-chat": scan_copilot_chat,
}


def detect_host_tool():
    """Which tool are we running inside? Returns a tool name or None.

    Order matters: Claude Code also runs inside VSCode, so its explicit marker
    is checked before the generic VSCode branch. Copilot Chat sets neither the
    Claude nor the Copilot-CLI markers but does run inside VSCode."""
    if os.environ.get("CLAUDECODE") or os.environ.get("CLAUDE_CODE_ENTRYPOINT"):
        return "claude-code"
    if any(k.startswith("COPILOT_CLI") for k in os.environ):
        return "copilot-cli"
    if os.environ.get("VSCODE_IPC_HOOK_CLI") or os.environ.get("VSCODE_PID"):
        # In VSCode, not Claude, not Copilot CLI -> Copilot Chat.
        return "copilot-chat"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", default=os.getcwd())
    ap.add_argument("--tool", action="append", choices=list(READERS), default=None)
    ap.add_argument("--all", action="store_true", help="scan every tool, not just the host")
    ap.add_argument("--sessions", type=int, default=0)
    ap.add_argument("--save", metavar="PATH", default=None,
                    help="also write the metrics JSON to PATH (for the HTML renderer)")
    args = ap.parse_args()

    host = detect_host_tool()
    if args.tool:
        which = args.tool
    elif args.all:
        which = list(READERS)
    elif host:
        which = [host]
    else:
        which = None  # ambiguous: refuse to guess (see below)

    out = {
        "workspace": os.path.abspath(args.cwd),
        "host_tool": host,
        "scanned_tools": which or [],
        "tools": {},
    }

    # A null host with no explicit scope must NOT silently scan every tool —
    # that is how another tool's data leaks into a single-tool report. Fail loud.
    if which is None:
        out["error"] = ("could not detect the host tool from the environment; "
                        "re-run with --tool <claude-code|copilot-cli|copilot-chat> "
                        "or --all to compare across tools")
        payload = json.dumps(out, indent=2)
        if args.save:
            with open(args.save, "w", encoding="utf-8") as fh:
                fh.write(payload)
        print(payload)
        return

    for name in which:
        block = READERS[name](args.cwd, args.sessions)
        if block:
            out["tools"][name] = block

    if not out["tools"]:
        out["error"] = "no transcripts found for this workspace in the scanned tool(s)"
    payload = json.dumps(out, indent=2)
    if args.save:
        with open(args.save, "w", encoding="utf-8") as fh:
            fh.write(payload)
    print(payload)


if __name__ == "__main__":
    main()
