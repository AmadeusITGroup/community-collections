"""Unit tests for finalize_metrics.verify_no_tree_escape (sandbox-escape guard)."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_DIR = _REPO_ROOT / "skills" / "skill-eval-runner" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

import finalize_metrics as fm  # noqa: E402
import _sandbox  # noqa: E402


def _run_git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


class SandboxEscapeGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir(parents=True)
        _run_git(self.repo, "init", "-q")
        _run_git(self.repo, "config", "user.email", "t@t.test")
        _run_git(self.repo, "config", "user.name", "Test")
        (self.repo / "tracked.txt").write_text("v1\n")
        _run_git(self.repo, "add", "tracked.txt")
        _run_git(self.repo, "commit", "-q", "-m", "seed")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_returns_true_when_no_escape(self) -> None:
        baseline = sorted(_sandbox.git_dirty_paths(self.repo))  # clean -> []
        ok, msg = fm.verify_no_tree_escape(self.repo, baseline)
        self.assertTrue(ok)
        self.assertEqual(msg, "")

    def test_returns_false_and_lists_escaped_path(self) -> None:
        baseline = sorted(_sandbox.git_dirty_paths(self.repo))  # clean -> []
        (self.repo / "escape.json").write_text("{}\n")  # skill wrote to real tree
        ok, msg = fm.verify_no_tree_escape(self.repo, baseline)
        self.assertFalse(ok)
        self.assertIn("outside the per-variant sandbox", msg.lower())
        self.assertIn("escape.json", msg)

    def test_preexisting_dirty_path_not_flagged(self) -> None:
        # A file already dirty at PREPARE (captured in the baseline) is not an escape.
        (self.repo / "preexisting.txt").write_text("local edit\n")
        baseline = sorted(_sandbox.git_dirty_paths(self.repo))
        self.assertIn("preexisting.txt", baseline)
        ok, msg = fm.verify_no_tree_escape(self.repo, baseline)
        self.assertTrue(ok)
        self.assertEqual(msg, "")

    def test_none_baseline_skips_gracefully(self) -> None:
        # Legacy iterations have no recorded baseline -> skip, do not crash.
        ok, msg = fm.verify_no_tree_escape(self.repo, None)
        self.assertTrue(ok)
        self.assertEqual(msg, "")


if __name__ == "__main__":
    unittest.main()
