#!/usr/bin/env python3
"""Prepare workspace for a skill evaluation run (PHASE 1).

Creates the iteration directory structure, classifies evals as baseline
or regression, and writes iteration_config.json + per-eval metadata.

Usage:
    python prepare_workspace.py skill-name
    python prepare_workspace.py skill-name --eval-id 5
    python prepare_workspace.py skill-name --repo-root /path/to/repo
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

from eval_paths import (
    canonical_eval_dir,
    colocated_eval_dir,
    resolve_eval_dir,
)

import _sandbox

REPO_ROOT = Path(__file__).resolve().parents[3]

if sys.stdout.isatty() and not os.environ.get("CI"):
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    NC = "\033[0m"
else:
    RED = GREEN = YELLOW = NC = ""

SEPARATOR = "━" * 51


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def get_skill_metadata_version(repo_root: Path, skill_name: str) -> str | None:
    """Extract metadata.version from a skill's SKILL.md frontmatter.

    Parses the YAML frontmatter (between ``---`` delimiters) and looks
    for a ``version:`` field under ``metadata:``.  Returns ``None`` if the
    file doesn't exist, has no frontmatter, or lacks a metadata version.
    """
    skill_md = repo_root / "skills" / skill_name / "SKILL.md"
    if not skill_md.exists():
        return None

    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None

    end = text.find("---", 3)
    if end == -1:
        return None

    frontmatter = text[3:end]

    in_metadata = False
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        is_top_level = not line.startswith((" ", "\t"))
        if is_top_level:
            if stripped.startswith("metadata:"):
                in_metadata = True
            else:
                in_metadata = False
            continue
        if in_metadata and stripped.startswith("version:"):
            raw = stripped.split(":", 1)[1].strip()
            if raw and raw[0] not in ('"', "'"):
                raw = re.sub(r"\s+#.*$", "", raw).strip()
            value = raw.strip("\"'")
            return value if value else None

    return None


def determine_next_iteration(workspace_dir: Path) -> int:
    """Scan workspace for iteration-N directories and return N+1."""
    max_iter = 0
    if workspace_dir.is_dir():
        for d in workspace_dir.iterdir():
            if d.is_dir():
                match = re.match(r"iteration-(\d+)$", d.name)
                if match:
                    max_iter = max(max_iter, int(match.group(1)))
    return max_iter + 1


def find_iteration_eval_ids_with_current_skill(iteration_dir: Path) -> set[int]:
    """Scan an iteration dir for eval IDs with a grading.json under current_skill/."""
    valid_ids: set[int] = set()
    if not iteration_dir.is_dir():
        return valid_ids
    for d in iteration_dir.iterdir():
        if not d.is_dir() or not d.name.startswith("eval-"):
            continue
        match = re.match(r"eval-(\d+)-", d.name)
        if not match:
            continue
        eval_id = int(match.group(1))
        if (d / "current_skill" / "grading.json").exists():
            valid_ids.add(eval_id)
    return valid_ids


def find_latest_baseline_iteration(
    workspace_dir: Path, current_iteration_num: int, eval_ids: list[int]
) -> tuple[int | None, dict[int, int]]:
    """Scan iterations descending for the latest without_skill grading per eval.

    Returns ``(baseline_iteration_num, per_eval_source)`` where
    ``per_eval_source`` maps eval_id -> iteration_num that supplied its
    without_skill baseline. ``baseline_iteration_num`` is the max of the
    per-eval sources (most recent iteration still acting as a baseline).
    """
    per_eval: dict[int, int] = {}
    eval_id_set = set(eval_ids)
    for n in range(current_iteration_num - 1, 0, -1):
        iter_dir = workspace_dir / f"iteration-{n}"
        if not iter_dir.is_dir():
            continue
        for d in iter_dir.iterdir():
            if not d.is_dir() or not d.name.startswith("eval-"):
                continue
            match = re.match(r"eval-(\d+)-", d.name)
            if not match:
                continue
            eid = int(match.group(1))
            if eid not in eval_id_set or eid in per_eval:
                continue
            if (d / "without_skill" / "grading.json").exists():
                per_eval[eid] = n
        if len(per_eval) == len(eval_id_set):
            break
    if not per_eval:
        return None, {}
    return max(per_eval.values()), per_eval


def find_eval_dir_name(iteration_dir: Path, eval_id: int) -> str | None:
    """Find the directory name in iteration_dir matching eval_id."""
    if not iteration_dir.is_dir():
        return None
    for d in iteration_dir.iterdir():
        if not d.is_dir() or not d.name.startswith("eval-"):
            continue
        match = re.match(r"eval-(\d+)-", d.name)
        if match and int(match.group(1)) == eval_id:
            return d.name
    return None


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def prepare_workspace(
    repo_root: Path,
    skill_name: str,
    eval_id_filter: int | None = None,
) -> int:
    evals_dir = resolve_eval_dir(repo_root, skill_name)
    if evals_dir is None:
        canonical = canonical_eval_dir(repo_root, skill_name)
        colocated = colocated_eval_dir(repo_root, skill_name)
        print(
            f"{RED}Error: evals.json not found for '{skill_name}'. Looked in "
            f"{canonical} (canonical) and {colocated} (colocated).{NC}"
        )
        return 1
    evals_path = evals_dir / "evals.json"
    workspace_dir = evals_dir / "workspace"

    # ── Step 1: Load evals.json ──────────────────────────────────────────
    if not evals_path.exists():
        print(f"{RED}Error: evals.json not found at {evals_path}{NC}")
        return 1

    evals_data = load_json(evals_path)
    if evals_data is None:
        print(f"{RED}Error: could not parse {evals_path}{NC}")
        return 1

    all_evals = evals_data.get("evals", [])
    evals_skill_version = evals_data.get("skill_version") or evals_data.get("version")

    # Filter to a single eval if --eval-id was provided
    if eval_id_filter is not None:
        all_evals = [e for e in all_evals if e.get("id") == eval_id_filter]
        if not all_evals:
            print(f"{RED}Error: no eval with id={eval_id_filter} in {evals_path}{NC}")
            return 1

    if not all_evals:
        print(f"{RED}Error: no evals found in {evals_path}{NC}")
        return 1

    # ── Step 2: Check staleness ──────────────────────────────────────────
    skill_version = get_skill_metadata_version(repo_root, skill_name)
    if evals_skill_version and skill_version:
        if evals_skill_version == skill_version:
            version_label = f"skill v{skill_version}, evals target v{evals_skill_version} {GREEN}\u2713{NC}"
        else:
            version_label = (
                f"skill v{skill_version}, evals target v{evals_skill_version} "
                f"{YELLOW}\u26a0 mismatch{NC}"
            )
            print(
                f"{YELLOW}Warning: skill version ({skill_version}) does not match "
                f"evals target ({evals_skill_version}). Proceeding anyway.{NC}"
            )
    elif evals_skill_version:
        version_label = f"evals target v{evals_skill_version}"
    elif skill_version:
        version_label = f"skill v{skill_version}"
    else:
        version_label = "version unknown"

    # ── Step 3: Determine next iteration ─────────────────────────────────
    iteration_num = determine_next_iteration(workspace_dir)
    previous_iteration_num = iteration_num - 1 if iteration_num > 1 else None
    previous_iteration_dir = (
        workspace_dir / f"iteration-{previous_iteration_num}"
        if previous_iteration_num
        else None
    )

    # ── Step 4: Classify evals ───────────────────────────────────────────
    existing_ids: list[int] = []
    new_ids: list[int] = []
    baseline_iteration_num: int | None = None
    per_eval_baseline: dict[int, int] = {}

    if iteration_num > 1:
        # "existing" = previous iteration has a current_skill grading.
        # This drives the regression comparator pairing.
        prev_skill_eval_ids = find_iteration_eval_ids_with_current_skill(
            previous_iteration_dir
        )
        for ev in all_evals:
            eid = ev.get("id")
            if eid in prev_skill_eval_ids:
                existing_ids.append(eid)
            else:
                new_ids.append(eid)

        if existing_ids and not new_ids:
            mode = "regression"
        elif new_ids and not existing_ids:
            mode = "baseline"
        else:
            mode = "mixed"

        # Separate concept: latest iteration with a usable without_skill
        # grading per existing eval. Used only to reuse the grounding baseline.
        if existing_ids:
            baseline_iteration_num, per_eval_baseline = find_latest_baseline_iteration(
                workspace_dir, iteration_num, existing_ids
            )
    else:
        for ev in all_evals:
            new_ids.append(ev.get("id"))
        mode = "baseline"

    total_executors = 2 * len(new_ids) + len(existing_ids)
    skipped_without_skill = len(existing_ids)

    # ── Step 5 & 6: Create workspace structure + iteration_config.json ───
    iteration_dir = workspace_dir / f"iteration-{iteration_num}"
    iteration_dir.mkdir(parents=True, exist_ok=True)

    # Stable per-iteration A/B seed so assign_ab.py is deterministic on re-runs.
    ab_seed = secrets.randbits(32)

    iteration_config: dict = {
        "iteration": iteration_num,
        "mode": mode,
        "eval_classification": {
            "existing": existing_ids,
            "new": new_ids,
        },
        "total_executors": total_executors,
        "skipped_without_skill": skipped_without_skill,
        "ab_seed": ab_seed,
        "git_status_baseline": sorted(_sandbox.git_dirty_paths(evals_dir)),
    }
    if skill_version:
        iteration_config["skill_version"] = skill_version
    if previous_iteration_num is not None:
        iteration_config["previous_iteration"] = previous_iteration_num
        iteration_config["previous_path"] = f"../iteration-{previous_iteration_num}"
    if baseline_iteration_num is not None:
        iteration_config["baseline_iteration"] = baseline_iteration_num
        iteration_config["baseline_path"] = f"../iteration-{baseline_iteration_num}"

    config_path = iteration_dir / "iteration_config.json"
    config_path.write_text(
        json.dumps(iteration_config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # ── Step 7: Create per-eval directories + eval_metadata.json ─────────
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    eval_dirs_created: list[tuple[str, str]] = []  # (dir_name, classification)

    for ev in all_evals:
        eid = ev.get("id")
        ename = ev.get("name", "unnamed")
        dir_name = f"eval-{eid}-{ename}"
        eval_dir = iteration_dir / dir_name
        eval_dir.mkdir(parents=True, exist_ok=True)

        is_regression = eid in existing_ids
        classification = "regression" if is_regression else "baseline"
        eval_dirs_created.append((dir_name, classification))

        declared_files = ev.get("files", [])

        # current_skill always runs; without_skill only for baseline/new evals
        # (regression reuses the baseline iteration's without_skill data).
        variants = ["current_skill"]
        if not is_regression:
            variants.append("without_skill")

        # Give each variant an outputs/ dir AND a private, writable sandbox/ that
        # acts as the skill's repository root for this run. Declared input files
        # are staged inside the sandbox; the executor also writes every file it
        # PRODUCES there (self-computed output paths, brand-new files, anything),
        # so a file-writing skill cannot corrupt the real tree or race the other
        # variant. stage_sandbox() creates the sandbox for every variant even when
        # the eval declares no inputs, so a skill that only produces output still
        # has a home. eval_metadata.files is repointed at the current_skill copies.
        staged_files = declared_files
        for variant in variants:
            (eval_dir / variant / "outputs").mkdir(parents=True, exist_ok=True)
            resolved = _sandbox.stage_sandbox(
                evals_dir=evals_dir,
                variant_dir=eval_dir / variant,
                declared_files=declared_files,
            )
            if variant == "current_skill":
                staged_files = resolved

        # Build eval_metadata.json
        meta: dict = {
            "id": eid,
            "name": ename,
            "prompt": ev.get("prompt", ""),
            "expectations": ev.get("expectations", []),
            "files": staged_files,
            "sandbox_dir": "current_skill/sandbox",
            "iteration": iteration_num,
            "prepared_at": now_iso,
            "eval_mode": "regression" if is_regression else "baseline",
        }

        if is_regression:
            src_iter = per_eval_baseline.get(eid, baseline_iteration_num)
            if src_iter is not None:
                meta["baseline_iteration"] = src_iter
                baseline_dir_name = find_eval_dir_name(
                    workspace_dir / f"iteration-{src_iter}", eid
                )
                if baseline_dir_name:
                    meta["baseline_path"] = (
                        f"../iteration-{src_iter}/{baseline_dir_name}"
                    )
            if previous_iteration_num is not None:
                meta["previous_iteration"] = previous_iteration_num
                prev_dir_name = find_eval_dir_name(previous_iteration_dir, eid)
                if prev_dir_name:
                    meta["previous_path"] = (
                        f"../iteration-{previous_iteration_num}/{prev_dir_name}"
                    )

        meta_path = eval_dir / "eval_metadata.json"
        meta_path.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    # ── Output summary ───────────────────────────────────────────────────
    print(SEPARATOR)
    print(f"Preparing workspace: {skill_name}")
    print(SEPARATOR)
    print(f"Evals loaded: {len(all_evals)} test cases ({version_label})")

    if iteration_num > 1:
        print(f"Iteration: {iteration_num} (previous: {previous_iteration_num})")
        if baseline_iteration_num is not None:
            print(f"Baseline reuse: iteration {baseline_iteration_num}")
    else:
        print(f"Iteration: {iteration_num}")

    # Mode line
    if mode == "regression":
        mode_detail = f"{len(existing_ids)} existing, {len(new_ids)} new"
    elif mode == "baseline":
        mode_detail = f"{len(new_ids)} new"
    else:
        mode_detail = f"{len(existing_ids)} existing, {len(new_ids)} new"
    print(f"Mode: {mode} ({mode_detail})")

    # Executors line
    parts: list[str] = []
    if existing_ids:
        parts.append(f"{len(existing_ids)} current_skill only")
    if new_ids:
        parts.append(f"{len(new_ids)} current_skill + {len(new_ids)} without_skill")
    print(f"Executors needed: {total_executors} ({' + '.join(parts)})")

    if skipped_without_skill > 0:
        print(f"Skipped without_skill: {skipped_without_skill}")

    # Tree view
    print()
    print("Workspace created:")
    iteration_dir = workspace_dir / f"iteration-{iteration_num}"
    try:
        rel_iteration = f"{iteration_dir.relative_to(repo_root)}/"
    except ValueError:
        rel_iteration = f"{iteration_dir}/"
    print(f"  {rel_iteration}")
    print("  \u251c\u2500\u2500 iteration_config.json")

    for i, (dir_name, classification) in enumerate(eval_dirs_created):
        is_last = i == len(eval_dirs_created) - 1
        connector = "\u2514\u2500\u2500" if is_last else "\u251c\u2500\u2500"
        label = f"[{classification}]"
        print(f"  {connector} {dir_name}/   {label}")

    print()
    print(SEPARATOR)
    print(
        f"{GREEN}Ready for PHASE 2.{NC} Run executors for {len(all_evals)} eval cases."
    )
    print(SEPARATOR)

    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare workspace for a skill evaluation run (PHASE 1)."
    )
    parser.add_argument(
        "skill_name",
        help="Name of the skill to evaluate (must match the directory name under skills/)",
    )
    parser.add_argument(
        "--eval-id",
        type=int,
        default=None,
        metavar="N",
        help="Run only a single eval case by ID",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (defaults to 3 levels up from script location)",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve() if args.repo_root else REPO_ROOT
    return prepare_workspace(repo_root, args.skill_name, args.eval_id)


if __name__ == "__main__":
    raise SystemExit(main())
