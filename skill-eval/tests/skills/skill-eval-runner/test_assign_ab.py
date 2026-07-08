"""Unit tests for assign_ab.py — blind A/B assignment for the comparator.

Two properties matter most here:
- **Determinism**: the same ``ab_seed`` + ``eval_id`` must always yield the
  same A/B orientation, so a re-run produces byte-identical assignments.
- **Correct pairing per mode**: baseline evals pair current_skill vs
  without_skill; regression evals pair current_skill vs previous_skill.

Tests build a tiny workspace on disk because ``assign_ab`` walks the
iteration directory. Stdlib unittest only.
"""

from __future__ import annotations

import contextlib
import io
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_DIR = _REPO_ROOT / "skills" / "skill-eval-runner" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

import assign_ab  # noqa: E402


def _run_assign(iteration_dir: Path) -> int:
    """Invoke assign_ab silencing its stdout manifest / stderr summary so CI
    logs stay readable. Returns the exit code."""
    with contextlib.redirect_stdout(io.StringIO()), \
            contextlib.redirect_stderr(io.StringIO()):
        return assign_ab.assign_ab(iteration_dir)


class FindEvalDirTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_matches_by_numeric_id(self) -> None:
        (self.root / "eval-1-alpha").mkdir()
        (self.root / "eval-2-beta").mkdir()
        got = assign_ab.find_eval_dir(self.root, 2)
        self.assertEqual(got.name, "eval-2-beta")

    def test_no_partial_id_match(self) -> None:
        # eval-12 must not be returned when looking for eval-1.
        (self.root / "eval-12-gamma").mkdir()
        self.assertIsNone(assign_ab.find_eval_dir(self.root, 1))

    def test_missing_returns_none(self) -> None:
        self.assertIsNone(assign_ab.find_eval_dir(self.root, 99))

    def test_nonexistent_dir_returns_none(self) -> None:
        self.assertIsNone(assign_ab.find_eval_dir(self.root / "nope", 1))


class _Workspace:
    """Helper to construct an iteration directory for assign_ab."""

    def __init__(self, root: Path):
        self.root = root

    def write_config(self, **cfg) -> None:
        (self.root / "iteration_config.json").write_text(
            json.dumps(cfg), encoding="utf-8"
        )

    def add_eval(self, eval_id: int, name: str, *, current=True, without=False) -> Path:
        d = self.root / f"eval-{eval_id}-{name}"
        if current:
            self._response(d / "current_skill")
        if without:
            self._response(d / "without_skill")
        return d

    @staticmethod
    def _response(variant_dir: Path) -> None:
        out = variant_dir / "outputs"
        out.mkdir(parents=True, exist_ok=True)
        (out / "response.md").write_text("# response\n", encoding="utf-8")


class BaselineAssignmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.iter_dir = Path(self._tmp.name) / "iteration-1"
        self.iter_dir.mkdir(parents=True)
        self.ws = _Workspace(self.iter_dir)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_baseline_pairs_current_vs_without(self) -> None:
        self.ws.write_config(
            ab_seed=1000,
            eval_classification={"existing": [], "new": [1]},
        )
        eval_dir = self.ws.add_eval(1, "alpha", current=True, without=True)
        rc = _run_assign(self.iter_dir)
        self.assertEqual(rc, 0)
        data = json.loads((eval_dir / "ab_assignment.json").read_text())
        self.assertEqual(data["comparison_mode"], "baseline")
        variants = {data["variant_A"], data["variant_B"]}
        self.assertEqual(variants, {"current_skill", "without_skill"})

    def test_deterministic_orientation(self) -> None:
        # The script uses random.Random(ab_seed + eval_id). Verify the written
        # assignment matches an independent computation with the same seed.
        seed = 424242
        self.ws.write_config(
            ab_seed=seed, eval_classification={"existing": [], "new": [1]}
        )
        eval_dir = self.ws.add_eval(1, "alpha", current=True, without=True)
        _run_assign(self.iter_dir)
        data = json.loads((eval_dir / "ab_assignment.json").read_text())

        rng = random.Random(seed + 1)
        flip = rng.random() < 0.5
        expected_A = "current_skill" if flip else "without_skill"
        self.assertEqual(data["variant_A"], expected_A)

    def test_rerun_is_byte_identical(self) -> None:
        self.ws.write_config(
            ab_seed=777, eval_classification={"existing": [], "new": [1, 2]}
        )
        self.ws.add_eval(1, "alpha", current=True, without=True)
        self.ws.add_eval(2, "beta", current=True, without=True)

        _run_assign(self.iter_dir)
        first = {
            p.parent.name: p.read_text()
            for p in self.iter_dir.glob("eval-*/ab_assignment.json")
        }
        _run_assign(self.iter_dir)
        second = {
            p.parent.name: p.read_text()
            for p in self.iter_dir.glob("eval-*/ab_assignment.json")
        }
        self.assertEqual(first, second)

    def test_missing_config_returns_error(self) -> None:
        # No iteration_config.json written.
        rc = _run_assign(self.iter_dir)
        self.assertEqual(rc, 1)

    def test_missing_ab_seed_returns_error(self) -> None:
        self.ws.write_config(eval_classification={"existing": [], "new": [1]})
        self.ws.add_eval(1, "alpha", current=True, without=True)
        rc = _run_assign(self.iter_dir)
        self.assertEqual(rc, 1)

    def test_eval_missing_current_response_skipped(self) -> None:
        self.ws.write_config(
            ab_seed=1, eval_classification={"existing": [], "new": [1]}
        )
        # current=False → no current_skill/outputs/response.md
        eval_dir = self.ws.add_eval(1, "alpha", current=False, without=True)
        rc = _run_assign(self.iter_dir)
        self.assertEqual(rc, 0)
        self.assertFalse((eval_dir / "ab_assignment.json").exists())


class RegressionAssignmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self._tmp.name)
        self.prev_dir = self.workspace / "iteration-1"
        self.iter_dir = self.workspace / "iteration-2"
        self.prev_dir.mkdir(parents=True)
        self.iter_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_regression_pairs_current_vs_previous(self) -> None:
        # Previous iteration holds the prior current_skill response.
        prev_ws = _Workspace(self.prev_dir)
        prev_ws.add_eval(1, "alpha", current=True, without=True)

        ws = _Workspace(self.iter_dir)
        ws.write_config(
            ab_seed=5,
            eval_classification={"existing": [1], "new": []},
            previous_iteration=1,
            previous_path="../iteration-1",
            baseline_iteration=1,
            baseline_path="../iteration-1",
        )
        eval_dir = ws.add_eval(1, "alpha", current=True, without=False)

        rc = _run_assign(self.iter_dir)
        self.assertEqual(rc, 0)
        data = json.loads((eval_dir / "ab_assignment.json").read_text())
        self.assertEqual(data["comparison_mode"], "regression")
        self.assertEqual(
            {data["variant_A"], data["variant_B"]},
            {"current_skill", "previous_skill"},
        )

    def test_regression_without_previous_path_errors(self) -> None:
        ws = _Workspace(self.iter_dir)
        ws.write_config(
            ab_seed=5,
            eval_classification={"existing": [1], "new": []},
            # previous_path intentionally omitted
        )
        ws.add_eval(1, "alpha", current=True)
        rc = _run_assign(self.iter_dir)
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
