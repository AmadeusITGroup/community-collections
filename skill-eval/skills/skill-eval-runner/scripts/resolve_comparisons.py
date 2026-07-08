#!/usr/bin/env python3
"""Resolve blind A/B comparator outputs into named-variant verdicts (PHASE 3b post-step).

For each ``comparison.json`` in the iteration:

1. Read the blind ``winner`` (∈ ``{"A", "B", "TIE"}``).
2. Read the matching ``ab_assignment.json``.
3. Merge ``assignment``, ``winner_variant``, ``comparison_mode``,
   ``baseline_iteration``, ``previous_iteration`` into the comparison file.

Validates strictly: any corrupt input causes a non-zero exit and the file is
left untouched.

Usage::

    python resolve_comparisons.py evals/<skill>/workspace/iteration-2
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

if sys.stdout.isatty() and not os.environ.get("CI"):
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    NC = "\033[0m"
else:
    RED = GREEN = YELLOW = NC = ""

VALID_WINNERS = {"A", "B", "TIE"}
VALID_VARIANTS = {"current_skill", "previous_skill", "without_skill"}
VALID_MODES = {"baseline", "regression"}


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def resolve_iteration(iteration_dir: Path) -> int:
    iteration_dir = iteration_dir.resolve()
    if not iteration_dir.is_dir():
        print(f"{RED}Iteration dir not found: {iteration_dir}{NC}")
        return 1

    failures: list[str] = []
    resolved = 0
    skipped = 0

    for eval_dir in sorted(iteration_dir.iterdir()):
        if not eval_dir.is_dir() or not eval_dir.name.startswith("eval-"):
            continue

        comp_path = eval_dir / "comparison.json"
        ab_path = eval_dir / "ab_assignment.json"

        if not comp_path.exists():
            skipped += 1
            continue

        if not ab_path.exists():
            failures.append(f"{eval_dir.name}: missing ab_assignment.json")
            continue

        comp = load_json(comp_path)
        ab = load_json(ab_path)

        if not isinstance(comp, dict) or not isinstance(ab, dict):
            failures.append(f"{eval_dir.name}: corrupt JSON")
            continue

        winner = comp.get("winner")
        if winner not in VALID_WINNERS:
            failures.append(
                f"{eval_dir.name}: invalid winner={winner!r} "
                f"(expected one of {sorted(VALID_WINNERS)})"
            )
            continue

        variant_a = ab.get("variant_A")
        variant_b = ab.get("variant_B")
        comparison_mode = ab.get("comparison_mode")

        if variant_a not in VALID_VARIANTS or variant_b not in VALID_VARIANTS:
            failures.append(
                f"{eval_dir.name}: invalid variants in ab_assignment.json "
                f"(A={variant_a!r}, B={variant_b!r})"
            )
            continue

        if comparison_mode not in VALID_MODES:
            failures.append(
                f"{eval_dir.name}: invalid comparison_mode={comparison_mode!r}"
            )
            continue

        if winner == "A":
            winner_variant = variant_a
        elif winner == "B":
            winner_variant = variant_b
        else:
            winner_variant = "tie"

        comp["assignment"] = {"A": variant_a, "B": variant_b}
        comp["winner_variant"] = winner_variant
        comp["comparison_mode"] = comparison_mode
        if "baseline_iteration" in ab:
            comp["baseline_iteration"] = ab["baseline_iteration"]
        if "previous_iteration" in ab:
            comp["previous_iteration"] = ab["previous_iteration"]

        write_json(comp_path, comp)
        resolved += 1

    if failures:
        for f in failures:
            print(f"{RED}{f}{NC}", file=sys.stderr)
        print(
            f"{RED}resolve_comparisons: {len(failures)} failure(s); "
            f"resolved {resolved}, skipped {skipped}{NC}",
            file=sys.stderr,
        )
        return 1

    print(
        f"{GREEN}Resolved {resolved} comparisons "
        f"({skipped} eval(s) had no comparison.json yet).{NC}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve blind A/B comparator outputs."
    )
    parser.add_argument(
        "iteration_dir",
        type=Path,
        help="Path to the iteration directory.",
    )
    args = parser.parse_args()
    return resolve_iteration(args.iteration_dir)


if __name__ == "__main__":
    raise SystemExit(main())
