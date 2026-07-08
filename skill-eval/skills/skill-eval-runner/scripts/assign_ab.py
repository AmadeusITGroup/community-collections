#!/usr/bin/env python3
"""Assign A/B labels for blind comparator runs (PHASE 3b pre-step).

For each eval in the iteration, picks the right variant pair and randomly
assigns the two ``response.md`` paths to ``A`` / ``B``. Writes
``ab_assignment.json`` per eval and prints a comparator manifest on stdout.

Pairing rules:

| Iteration mode                      | Pairing                          | comparison_mode |
|-------------------------------------|----------------------------------|-----------------|
| Iteration 1 (baseline only)         | current_skill vs without_skill   | baseline        |
| New eval in iteration N≥2           | current_skill vs without_skill   | baseline        |
| Existing eval in iteration N≥2      | current_skill vs previous_skill  | regression      |

``without_skill`` for regression evals is sourced from
``iteration_config.baseline_iteration``; ``previous_skill`` from
``iteration_config.previous_iteration``.

Determinism: uses ``random.Random(ab_seed + eval_id)`` so re-runs are
byte-identical.

Usage::

    python assign_ab.py evals/<skill>/workspace/iteration-2
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
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


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def find_eval_dir(iteration_dir: Path, eval_id: int) -> Path | None:
    if not iteration_dir.is_dir():
        return None
    for d in iteration_dir.iterdir():
        if not d.is_dir() or not d.name.startswith("eval-"):
            continue
        m = re.match(r"eval-(\d+)-", d.name)
        if m and int(m.group(1)) == eval_id:
            return d
    return None


def assign_ab(iteration_dir: Path) -> int:
    iteration_dir = iteration_dir.resolve()
    config = load_json(iteration_dir / "iteration_config.json")
    if config is None:
        print(f"{RED}iteration_config.json missing in {iteration_dir}{NC}")
        return 1

    classification = config.get("eval_classification", {})
    existing_ids = set(classification.get("existing", []))
    new_ids = set(classification.get("new", []))

    ab_seed = config.get("ab_seed")
    if ab_seed is None:
        print(
            f"{RED}iteration_config.json missing 'ab_seed' — re-run "
            f"prepare_workspace.py{NC}"
        )
        return 1

    baseline_iteration = config.get("baseline_iteration")
    baseline_path = config.get("baseline_path")
    previous_iteration = config.get("previous_iteration")
    previous_path = config.get("previous_path")

    baseline_dir = (iteration_dir / baseline_path).resolve() if baseline_path else None
    previous_dir = (iteration_dir / previous_path).resolve() if previous_path else None

    manifest: list[dict] = []
    written = 0

    for eval_dir in sorted(iteration_dir.iterdir()):
        if not eval_dir.is_dir() or not eval_dir.name.startswith("eval-"):
            continue
        m = re.match(r"eval-(\d+)-", eval_dir.name)
        if not m:
            continue
        eval_id = int(m.group(1))

        is_existing = eval_id in existing_ids
        is_new = eval_id in new_ids

        # Default classification: anything not flagged "existing" is treated as
        # baseline (covers iteration 1, mixed-mode new evals, and unclassified).
        if is_existing:
            mode = "regression"
        else:
            mode = "baseline"
            if not is_new:
                # Unclassified eval — fall back to baseline pairing
                pass

        current_response = eval_dir / "current_skill" / "outputs" / "response.md"
        if not current_response.exists():
            print(f"{YELLOW}skip eval {eval_id}: missing {current_response}{NC}")
            continue

        if mode == "regression":
            if previous_dir is None:
                print(
                    f"{RED}eval {eval_id} marked existing but no "
                    f"previous_path in iteration_config.json{NC}"
                )
                return 1
            prev_eval = find_eval_dir(previous_dir, eval_id)
            if prev_eval is None:
                print(f"{RED}eval {eval_id}: no matching dir in {previous_dir}{NC}")
                return 1
            other_response = prev_eval / "current_skill" / "outputs" / "response.md"
            other_variant = "previous_skill"
            comparison_mode = "regression"
        else:
            # baseline — without_skill lives either in this iteration (new)
            # or in baseline_iteration (reused).
            local_wo = eval_dir / "without_skill" / "outputs" / "response.md"
            if local_wo.exists():
                other_response = local_wo
            elif baseline_dir is not None:
                base_eval = find_eval_dir(baseline_dir, eval_id)
                if base_eval is None:
                    print(
                        f"{RED}eval {eval_id}: no without_skill locally and "
                        f"none in baseline {baseline_dir}{NC}"
                    )
                    return 1
                other_response = base_eval / "without_skill" / "outputs" / "response.md"
            else:
                print(f"{RED}eval {eval_id}: no without_skill response found{NC}")
                return 1
            if not other_response.exists():
                print(f"{RED}eval {eval_id}: missing {other_response}{NC}")
                return 1
            other_variant = "without_skill"
            comparison_mode = "baseline"

        rng = random.Random(int(ab_seed) + eval_id)
        flip = rng.random() < 0.5
        if flip:
            a_path, a_variant = current_response, "current_skill"
            b_path, b_variant = other_response, other_variant
        else:
            a_path, a_variant = other_response, other_variant
            b_path, b_variant = current_response, "current_skill"

        assignment: dict[str, Any] = {
            "A": str(a_path),
            "B": str(b_path),
            "variant_A": a_variant,
            "variant_B": b_variant,
            "comparison_mode": comparison_mode,
        }
        if baseline_iteration is not None:
            assignment["baseline_iteration"] = baseline_iteration
        if previous_iteration is not None:
            assignment["previous_iteration"] = previous_iteration

        write_json(eval_dir / "ab_assignment.json", assignment)
        manifest.append(
            {
                "eval_id": eval_id,
                "eval_dir": str(eval_dir),
                "comparison_mode": comparison_mode,
                "A": str(a_path),
                "B": str(b_path),
                "variant_A": a_variant,
                "variant_B": b_variant,
            }
        )
        written += 1

    print(json.dumps({"assignments": manifest}, indent=2))
    print(f"{GREEN}Wrote {written} ab_assignment.json files.{NC}", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assign blind A/B labels for comparator inputs."
    )
    parser.add_argument(
        "iteration_dir",
        type=Path,
        help="Path to the iteration directory (e.g. evals/<skill>/workspace/iteration-2)",
    )
    args = parser.parse_args()
    return assign_ab(args.iteration_dir)


if __name__ == "__main__":
    raise SystemExit(main())
