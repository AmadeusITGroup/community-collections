#!/usr/bin/env python3
"""
GitHub Pull Requests Triage Script

Exports open PRs, labels, and templates from a GitHub repository,
then generates triage proposals including:
- Proposed labels
- Proposed priority (critical/high/medium/low)
- Proposed comments for template non-adherence
- Duplicate detection
"""

import argparse
import json
import os
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


# Priority levels
PRIORITY_CRITICAL = "critical"
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

# Keywords for priority detection
PRIORITY_KEYWORDS = {
    PRIORITY_CRITICAL: [
        r"\bcritical\b", r"\burgent\b", r"\bsecurity\b", r"\bvulnerability\b",
        r"\bCVE-\d+", r"\bhotfix\b", r"\bproduction\s*(fix|patch)",
        r"\bblocking\b", r"\bbreaking\s*change\b",
    ],
    PRIORITY_HIGH: [
        r"\bhigh\s*priority\b", r"\bimportant\b", r"\bregression\b",
        r"\bbug\s*fix\b", r"\bfix(es)?\b", r"\bcrash\b", r"\berror\b",
    ],
    PRIORITY_MEDIUM: [
        r"\bmedium\s*priority\b", r"\benhancement\b", r"\bimprovement\b",
        r"\bfeature\b", r"\brefactor\b",
    ],
    PRIORITY_LOW: [
        r"\blow\s*priority\b", r"\bminor\b", r"\btypo\b", r"\bdocumentation\b",
        r"\bdocs?\b", r"\bchore\b", r"\bcleanup\b", r"\bstyle\b",
    ],
}

# Similarity threshold for duplicate detection (0.0 to 1.0)
DUPLICATE_SIMILARITY_THRESHOLD = 0.7


@dataclass
class Proposal:
    number: int
    url: str
    title: str
    proposed_labels: List[str]
    proposed_priority: str
    proposed_comment: str
    reasons: List[str]
    already_triaged: bool
    potential_duplicates: List[Dict[str, Any]] = field(default_factory=list)


def _run(cmd: Sequence[str]) -> Tuple[int, str, str]:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def _ensure_gh_auth() -> None:
    code, _, _ = _run(["gh", "auth", "status"])
    if code != 0:
        raise RuntimeError("gh is not authenticated. Run: gh auth login")


def _gh_api_json(api_path: str, fields: Optional[Dict[str, str]] = None, paginate: bool = False) -> Any:
    cmd = ["gh", "api", api_path, "-H", "Accept: application/vnd.github+json"]
    if paginate:
        cmd.extend(["--paginate", "--slurp"])
    if fields:
        for k, v in fields.items():
            cmd.extend(["-F", f"{k}={v}"])

    code, out, err = _run(cmd)
    if code != 0:
        raise RuntimeError(f"gh api failed for {api_path}: {err.strip()}")

    data = json.loads(out) if out.strip() else None

    if paginate and isinstance(data, list):
        flattened: List[Any] = []
        for page in data:
            if isinstance(page, list):
                flattened.extend(page)
            else:
                flattened.append(page)
        return flattened

    return data


def _try_gh_api_raw(api_path: str) -> Optional[bytes]:
    cmd = ["gh", "api", api_path, "-H", "Accept: application/vnd.github.raw"]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        return None
    return proc.stdout


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_markdown_headings(text: str) -> List[str]:
    headings: List[str] = []
    for line in text.splitlines():
        m = re.match(r"^##+\s+(.*)\s*$", line)
        if not m:
            continue
        title = m.group(1).strip()
        if title:
            headings.append(title)
    return headings


def _normalize_label(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def _pick_existing_label(available: Sequence[str], patterns: Sequence[str]) -> Optional[str]:
    norm_map = {_normalize_label(l): l for l in available}
    for pat in patterns:
        rx = re.compile(pat, re.IGNORECASE)
        for norm, original in norm_map.items():
            if rx.search(norm):
                return original
    return None


def _detect_priority(title: str, body: str, labels: Sequence[str]) -> str:
    """Detect priority based on keywords in title, body, and existing labels."""
    text = f"{title} {body} {' '.join(labels)}".lower()
    
    for priority in [PRIORITY_CRITICAL, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW]:
        for pattern in PRIORITY_KEYWORDS[priority]:
            if re.search(pattern, text, re.IGNORECASE):
                return priority
    
    return PRIORITY_MEDIUM  # Default priority


def _normalize_text_for_similarity(text: str) -> str:
    """Normalize text for similarity comparison."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _compute_similarity(text1: str, text2: str) -> float:
    """Compute similarity ratio between two texts."""
    norm1 = _normalize_text_for_similarity(text1)
    norm2 = _normalize_text_for_similarity(text2)
    return SequenceMatcher(None, norm1, norm2).ratio()


def _find_duplicates(
    pr: Dict[str, Any],
    all_prs: Sequence[Dict[str, Any]],
    threshold: float = DUPLICATE_SIMILARITY_THRESHOLD,
) -> List[Dict[str, Any]]:
    """Find potential duplicate PRs based on title and body similarity."""
    current_number = pr.get("number")
    current_title = str(pr.get("title") or "")
    current_body = str(pr.get("body") or "")
    current_text = f"{current_title} {current_body}"
    
    duplicates: List[Dict[str, Any]] = []
    
    for other in all_prs:
        other_number = other.get("number")
        if other_number == current_number:
            continue
        
        other_title = str(other.get("title") or "")
        other_body = str(other.get("body") or "")
        other_text = f"{other_title} {other_body}"
        
        # Check title similarity first (faster)
        title_sim = _compute_similarity(current_title, other_title)
        if title_sim >= threshold:
            duplicates.append({
                "number": other_number,
                "url": other.get("html_url", ""),
                "title": other_title,
                "similarity": round(title_sim, 2),
                "match_type": "title",
            })
            continue
        
        # Check full text similarity for high title similarity
        if title_sim >= 0.5:
            full_sim = _compute_similarity(current_text, other_text)
            if full_sim >= threshold:
                duplicates.append({
                    "number": other_number,
                    "url": other.get("html_url", ""),
                    "title": other_title,
                    "similarity": round(full_sim, 2),
                    "match_type": "content",
                })
    
    # Sort by similarity descending
    duplicates.sort(key=lambda x: x["similarity"], reverse=True)
    return duplicates[:5]  # Return top 5 potential duplicates


def _is_already_triaged(pr: Dict[str, Any], triage_label_patterns: Sequence[str]) -> bool:
    """Check if a PR appears to have been already triaged."""
    labels = [str(l.get("name", "")).lower() for l in (pr.get("labels") or []) if isinstance(l, dict)]
    
    if not labels:
        return False
    
    # If PR has labels that are NOT just "needs-triage" type labels, consider it triaged
    triage_patterns = [re.compile(p, re.IGNORECASE) for p in triage_label_patterns]
    
    non_triage_labels = []
    for label in labels:
        is_triage_label = any(p.search(label) for p in triage_patterns)
        if not is_triage_label:
            non_triage_labels.append(label)
    
    # If there are substantive labels (not just triage-related), consider it triaged
    return len(non_triage_labels) > 0


def _download_pr_templates(repo: str, out_dir: Path) -> List[Path]:
    templates_dir = out_dir / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    downloaded: List[Path] = []

    listing = None
    try:
        listing = _gh_api_json(f"repos/{repo}/contents/.github/PULL_REQUEST_TEMPLATE")
    except Exception:
        listing = None

    if isinstance(listing, list):
        for item in listing:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "file":
                continue
            name = item.get("name")
            if not name:
                continue
            raw = _try_gh_api_raw(f"repos/{repo}/contents/.github/PULL_REQUEST_TEMPLATE/{name}")
            if raw is None:
                continue
            target = templates_dir / name
            target.write_bytes(raw)
            downloaded.append(target)

    for path in [
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/pull_request_template.md",
        "PULL_REQUEST_TEMPLATE.md",
        "pull_request_template.md",
    ]:
        raw = _try_gh_api_raw(f"repos/{repo}/contents/{path}")
        if raw is None:
            continue
        target = templates_dir / Path(path).name
        target.write_bytes(raw)
        downloaded.append(target)

    return downloaded


def _list_open_prs(repo: str) -> List[Dict[str, Any]]:
    items = _gh_api_json(
        f"repos/{repo}/pulls?state=open",
        paginate=True,
    )
    return list(items or [])


def _list_labels(repo: str) -> List[Dict[str, Any]]:
    items = _gh_api_json(
        f"repos/{repo}/labels",
        paginate=True,
    )
    return list(items or [])


def _make_proposals(
    prs: Sequence[Dict[str, Any]],
    available_labels: Sequence[str],
    template_paths: Sequence[Path],
) -> List[Proposal]:
    markdown_templates = [p for p in template_paths if p.suffix.lower() in {".md", ".markdown"}]
    template_headings: List[str] = []
    if markdown_templates:
        template_headings = _extract_markdown_headings(_read_text(markdown_templates[0]))

    needs_info_label = _pick_existing_label(
        available_labels,
        patterns=[r"needs.*info", r"more.*info", r"missing.*info", r"needs.*details", r"incomplete", r"needs.*template"],
    )
    needs_triage_label = _pick_existing_label(available_labels, patterns=[r"triage", r"needs.*triage"])
    
    # Patterns that indicate triage-related labels (not substantive labels)
    triage_label_patterns = [
        r"triage", r"needs.*triage", r"needs.*info", r"needs.*review",
        r"pending", r"awaiting", r"stale", r"wontfix", r"duplicate",
    ]
    
    # Priority label patterns
    priority_label_map = {
        PRIORITY_CRITICAL: _pick_existing_label(available_labels, [r"critical", r"p0", r"priority.*0", r"urgent"]),
        PRIORITY_HIGH: _pick_existing_label(available_labels, [r"high", r"p1", r"priority.*1"]),
        PRIORITY_MEDIUM: _pick_existing_label(available_labels, [r"medium", r"p2", r"priority.*2"]),
        PRIORITY_LOW: _pick_existing_label(available_labels, [r"low", r"p3", r"priority.*3", r"minor"]),
    }

    proposals: List[Proposal] = []
    for pr in prs:
        number = int(pr.get("number"))
        title = str(pr.get("title") or "")
        url = str(pr.get("html_url") or "")
        body = str(pr.get("body") or "")
        existing_labels = [str(l.get("name")) for l in (pr.get("labels") or []) if isinstance(l, dict) and l.get("name")]

        # Check if already triaged
        already_triaged = _is_already_triaged(pr, triage_label_patterns)
        
        # Find potential duplicates
        potential_duplicates = _find_duplicates(pr, prs)
        
        # Detect priority
        proposed_priority = _detect_priority(title, body, existing_labels)

        reasons: List[str] = []
        proposed_labels: List[str] = []
        proposed_comment = ""

        # Skip detailed triage for already-triaged PRs
        if already_triaged:
            reasons.append("PR appears already triaged (has substantive labels)")
            proposals.append(
                Proposal(
                    number=number,
                    url=url,
                    title=title,
                    proposed_labels=[],
                    proposed_priority=proposed_priority,
                    proposed_comment="",
                    reasons=reasons,
                    already_triaged=True,
                    potential_duplicates=potential_duplicates,
                )
            )
            continue

        # Propose triage label if no labels
        if not existing_labels and needs_triage_label:
            proposed_labels.append(needs_triage_label)
            reasons.append("Pull request has no labels")

        # Propose priority label if available
        priority_label = priority_label_map.get(proposed_priority)
        if priority_label and priority_label not in existing_labels:
            proposed_labels.append(priority_label)
            reasons.append(f"Detected priority: {proposed_priority}")

        # Check template adherence
        missing_sections: List[str] = []
        if template_headings:
            for h in template_headings:
                if re.search(re.escape(h), body, re.IGNORECASE) is None:
                    missing_sections.append(h)

        if missing_sections:
            reasons.append("Pull request appears not to follow the pull request template")
            if needs_info_label and needs_info_label not in proposed_labels:
                proposed_labels.append(needs_info_label)

            missing_preview = ", ".join(missing_sections[:6])
            proposed_comment = (
                "Thanks for the pull request. To help us review it faster, could you please update the PR description to follow the "
                "repository's PR template and include the missing sections"
                f" (for example: {missing_preview})"
                "? Thanks!"
            )

        # Note potential duplicates
        if potential_duplicates:
            dup_nums = ", ".join(f"#{d['number']}" for d in potential_duplicates[:3])
            reasons.append(f"Potential duplicates: {dup_nums}")

        proposals.append(
            Proposal(
                number=number,
                url=url,
                title=title,
                proposed_labels=proposed_labels,
                proposed_priority=proposed_priority,
                proposed_comment=proposed_comment,
                reasons=reasons,
                already_triaged=False,
                potential_duplicates=potential_duplicates,
            )
        )

    return proposals


def _bash_quote(s: str) -> str:
    return shlex.quote(s)


def _write_apply_script(repo: str, proposals: Sequence[Proposal], out_dir: Path) -> Path:
    path = out_dir / "apply.sh"
    lines: List[str] = []
    lines.append("#!/usr/bin/env bash")
    lines.append("set -euo pipefail")
    lines.append("")
    lines.append(f"REPO={_bash_quote(repo)}")
    lines.append("")

    for p in proposals:
        if p.proposed_labels:
            cmd = ["gh", "pr", "edit", "-R", "${REPO}", str(p.number)]
            for label in p.proposed_labels:
                cmd.extend(["--add-label", label])
            lines.append(" ".join(_bash_quote(x) if x != "${REPO}" else x for x in cmd))

        if p.proposed_comment.strip():
            comment = _bash_quote(p.proposed_comment)
            lines.append(f"gh pr comment -R ${REPO} {p.number} --body {comment}")

        if p.proposed_labels or p.proposed_comment.strip():
            lines.append("")

    path.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    os.chmod(path, 0o755)
    return path


def _write_report(repo: str, proposals: Sequence[Proposal], out_dir: Path) -> Path:
    path = out_dir / "report.md"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Separate triaged vs needs-triage
    needs_triage = [p for p in proposals if not p.already_triaged]
    already_triaged = [p for p in proposals if p.already_triaged]
    with_duplicates = [p for p in proposals if p.potential_duplicates]

    lines: List[str] = []
    lines.append(f"# Pull Requests Triage Report for `{repo}`")
    lines.append("")
    lines.append(f"Generated: {now}")
    lines.append("")
    
    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total open PRs:** {len(proposals)}")
    lines.append(f"- **Needs triage:** {len(needs_triage)}")
    lines.append(f"- **Already triaged:** {len(already_triaged)}")
    lines.append(f"- **Potential duplicates found:** {len(with_duplicates)}")
    lines.append("")
    
    # Priority breakdown
    priority_counts = {PRIORITY_CRITICAL: 0, PRIORITY_HIGH: 0, PRIORITY_MEDIUM: 0, PRIORITY_LOW: 0}
    for p in needs_triage:
        priority_counts[p.proposed_priority] = priority_counts.get(p.proposed_priority, 0) + 1
    
    lines.append("### Priority Breakdown (needs triage)")
    lines.append("")
    lines.append(f"- 🔴 **Critical:** {priority_counts[PRIORITY_CRITICAL]}")
    lines.append(f"- 🟠 **High:** {priority_counts[PRIORITY_HIGH]}")
    lines.append(f"- 🟡 **Medium:** {priority_counts[PRIORITY_MEDIUM]}")
    lines.append(f"- 🟢 **Low:** {priority_counts[PRIORITY_LOW]}")
    lines.append("")

    # PRs needing triage
    lines.append("## PRs Needing Triage")
    lines.append("")
    if needs_triage:
        lines.append("| PR | Title | Priority | Proposed Labels | Duplicates | Reasons |")
        lines.append("|---:|---|:---:|---|---|---|")
        for p in sorted(needs_triage, key=lambda x: [PRIORITY_CRITICAL, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW].index(x.proposed_priority)):
            labels = ", ".join(p.proposed_labels) if p.proposed_labels else "-"
            reasons = "; ".join(p.reasons) if p.reasons else "-"
            pr_link = f"[{p.number}]({p.url})" if p.url else str(p.number)
            title = p.title.replace("|", "\\|")[:60]
            if len(p.title) > 60:
                title += "..."
            dups = ", ".join(f"#{d['number']}" for d in p.potential_duplicates[:3]) if p.potential_duplicates else "-"
            priority_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(p.proposed_priority, "⚪")
            lines.append(f"| {pr_link} | {title} | {priority_emoji} {p.proposed_priority} | {labels} | {dups} | {reasons} |")
    else:
        lines.append("*No PRs need triage.*")
    lines.append("")

    # Potential duplicates section
    if with_duplicates:
        lines.append("## Potential Duplicates")
        lines.append("")
        lines.append("| PR | Title | Similar To | Similarity |")
        lines.append("|---:|---|---|---:|")
        for p in with_duplicates:
            pr_link = f"[{p.number}]({p.url})" if p.url else str(p.number)
            title = p.title.replace("|", "\\|")[:50]
            for dup in p.potential_duplicates[:2]:
                dup_link = f"[#{dup['number']}]({dup['url']})" if dup.get('url') else f"#{dup['number']}"
                sim_pct = f"{int(dup['similarity'] * 100)}%"
                lines.append(f"| {pr_link} | {title} | {dup_link} | {sim_pct} |")
        lines.append("")

    # Already triaged section
    if already_triaged:
        lines.append("## Already Triaged (skipped)")
        lines.append("")
        lines.append(f"*{len(already_triaged)} PRs were skipped because they already have substantive labels.*")
        lines.append("")
        lines.append("<details>")
        lines.append("<summary>View skipped PRs</summary>")
        lines.append("")
        lines.append("| PR | Title |")
        lines.append("|---:|---|")
        for p in already_triaged[:20]:
            pr_link = f"[{p.number}]({p.url})" if p.url else str(p.number)
            title = p.title.replace("|", "\\|")[:60]
            lines.append(f"| {pr_link} | {title} |")
        if len(already_triaged) > 20:
            lines.append(f"| ... | *and {len(already_triaged) - 20} more* |")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append("- This report is auto-generated. Review proposals before applying them.")
    lines.append("- Run `bash ./apply.sh` to apply proposed labels/comments via `gh`.")
    lines.append("- Edit `proposals.json` to refine proposals before applying.")
    lines.append("- Already-triaged PRs are excluded from `apply.sh`.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Export GitHub PRs/labels/templates and generate a triage report + apply script.")
    parser.add_argument("--repo", required=True, help="GitHub repository in OWNER/REPO format")
    parser.add_argument("--out", required=True, help="Output directory")
    args = parser.parse_args()

    _ensure_gh_auth()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    labels = _list_labels(args.repo)
    prs = _list_open_prs(args.repo)
    template_paths = _download_pr_templates(args.repo, out_dir)

    _write_json(out_dir / "labels.json", labels)
    _write_json(out_dir / "pulls.json", prs)

    available_label_names = [str(l.get("name")) for l in labels if isinstance(l, dict) and l.get("name")]
    proposals = _make_proposals(prs, available_label_names, template_paths)
    proposals_json = [
        {
            "number": p.number,
            "url": p.url,
            "title": p.title,
            "proposed_labels": p.proposed_labels,
            "proposed_priority": p.proposed_priority,
            "proposed_comment": p.proposed_comment,
            "reasons": p.reasons,
            "already_triaged": p.already_triaged,
            "potential_duplicates": p.potential_duplicates,
        }
        for p in proposals
    ]

    _write_json(out_dir / "proposals.json", proposals_json)
    _write_report(args.repo, proposals, out_dir)
    
    # Only include non-triaged PRs in apply script
    actionable_proposals = [p for p in proposals if not p.already_triaged and (p.proposed_labels or p.proposed_comment)]
    _write_apply_script(args.repo, actionable_proposals, out_dir)
    
    # Print summary
    needs_triage = [p for p in proposals if not p.already_triaged]
    print(f"Triage complete for {args.repo}")
    print(f"  Total open PRs: {len(proposals)}")
    print(f"  Needs triage: {len(needs_triage)}")
    print(f"  Already triaged (skipped): {len(proposals) - len(needs_triage)}")
    print(f"  Actionable proposals: {len(actionable_proposals)}")
    print(f"\nOutputs written to: {out_dir}/")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
