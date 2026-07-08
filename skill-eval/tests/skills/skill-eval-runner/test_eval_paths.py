"""Unit tests for eval_paths.resolve_eval_dir / iter_eval_dirs.

Covers the two supported eval layouts and their precedence:
- canonical ``evals/skills/<name>/`` wins over colocated ``skills/<name>/evals/``
- presence is decided by ``evals.json`` existence, not the directory alone
- a skill present in both layouts triggers a stderr warning
- ``iter_eval_dirs`` (the lister) and ``resolve_eval_dir`` (the runner) agree
  on the same directory for a skill present in both layouts

Lives under ``/tests/skills/<name>/`` (a typed test lane parallel to
``/docs/skills/`` and ``/evals/skills/``) so it stays out of the skill's
progressive-disclosure surface. Stdlib ``unittest`` only — no third-party
runtime dependency.
"""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

# Reach the module under test: <repo>/skills/skill-eval-runner/scripts/
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_DIR = _REPO_ROOT / "skills" / "skill-eval-runner" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

import eval_paths  # noqa: E402


def _make_eval(dir_path: Path) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / "evals.json").write_text("{}", encoding="utf-8")
    return dir_path


class ResolveEvalDirTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_canonical_only(self) -> None:
        can = _make_eval(self.root / "evals" / "skills" / "foo")
        self.assertEqual(eval_paths.resolve_eval_dir(self.root, "foo"), can)

    def test_colocated_only(self) -> None:
        col = _make_eval(self.root / "skills" / "bar" / "evals")
        self.assertEqual(eval_paths.resolve_eval_dir(self.root, "bar"), col)

    def test_both_canonical_wins_and_warns(self) -> None:
        can = _make_eval(self.root / "evals" / "skills" / "baz")
        _make_eval(self.root / "skills" / "baz" / "evals")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            got = eval_paths.resolve_eval_dir(self.root, "baz")
        self.assertEqual(got, can)
        self.assertIn("warning", err.getvalue())
        self.assertIn("both", err.getvalue())

    def test_both_no_warn_when_suppressed(self) -> None:
        _make_eval(self.root / "evals" / "skills" / "baz")
        _make_eval(self.root / "skills" / "baz" / "evals")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            eval_paths.resolve_eval_dir(self.root, "baz", warn=False)
        self.assertEqual(err.getvalue(), "")

    def test_empty_canonical_dir_does_not_shadow_colocated(self) -> None:
        # canonical directory exists but has no evals.json
        (self.root / "evals" / "skills" / "qux").mkdir(parents=True)
        col = _make_eval(self.root / "skills" / "qux" / "evals")
        self.assertEqual(eval_paths.resolve_eval_dir(self.root, "qux"), col)

    def test_missing_returns_none(self) -> None:
        self.assertIsNone(eval_paths.resolve_eval_dir(self.root, "nope"))


class IterEvalDirsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_discovers_both_layouts(self) -> None:
        _make_eval(self.root / "evals" / "skills" / "foo")
        _make_eval(self.root / "skills" / "bar" / "evals")
        results = dict(eval_paths.iter_eval_dirs(self.root))
        self.assertEqual(set(results), {"foo", "bar"})

    def test_same_skill_in_both_layouts_agrees_with_resolver(self) -> None:
        # The lister must report a skill once, at the same directory the
        # runner would resolve — otherwise list_evals and prepare_workspace
        # would disagree on which evals a skill has.
        can = _make_eval(self.root / "evals" / "skills" / "baz")
        _make_eval(self.root / "skills" / "baz" / "evals")
        results = dict(eval_paths.iter_eval_dirs(self.root))
        self.assertEqual(list(results).count("baz"), 1)
        self.assertEqual(results["baz"], can)
        self.assertEqual(
            results["baz"],
            eval_paths.resolve_eval_dir(self.root, "baz", warn=False),
        )

    def test_empty_repo_yields_nothing(self) -> None:
        self.assertEqual(list(eval_paths.iter_eval_dirs(self.root)), [])


if __name__ == "__main__":
    unittest.main()
