"""Unit tests for _sandbox: per-variant sandbox staging + git-escape detection."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_DIR = _REPO_ROOT / "skills" / "skill-eval-runner" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

import _sandbox  # noqa: E402


class StageSandboxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.evals_dir = Path(self.tmp.name) / "evals" / "demo-skill"
        (self.evals_dir / "files").mkdir(parents=True)
        (self.evals_dir / "files" / "sample.log").write_text("LINE\n")
        (self.evals_dir / "files" / "codebase").mkdir()
        (self.evals_dir / "files" / "codebase" / "a.py").write_text("x = 1\n")
        self.variant_dir = (
            self.evals_dir / "workspace" / "iteration-1" / "eval-1-x" / "current_skill"
        )
        self.variant_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_copies_declared_files_into_variant_sandbox(self) -> None:
        resolved = _sandbox.stage_sandbox(
            evals_dir=self.evals_dir,
            variant_dir=self.variant_dir,
            declared_files=["files/sample.log", "files/codebase"],
        )
        self.assertTrue((self.variant_dir / "sandbox" / "files" / "sample.log").is_file())
        self.assertTrue(
            (self.variant_dir / "sandbox" / "files" / "codebase" / "a.py").is_file()
        )
        self.assertEqual(
            resolved, ["sandbox/files/sample.log", "sandbox/files/codebase"]
        )

    def test_editing_the_copy_does_not_touch_the_shared_fixture(self) -> None:
        _sandbox.stage_sandbox(
            evals_dir=self.evals_dir,
            variant_dir=self.variant_dir,
            declared_files=["files/sample.log"],
        )
        copy = self.variant_dir / "sandbox" / "files" / "sample.log"
        copy.write_text("MUTATED\n")
        self.assertEqual((self.evals_dir / "files" / "sample.log").read_text(), "LINE\n")

    def test_missing_declared_file_raises_clear_error(self) -> None:
        with self.assertRaises(FileNotFoundError) as ctx:
            _sandbox.stage_sandbox(
                evals_dir=self.evals_dir,
                variant_dir=self.variant_dir,
                declared_files=["files/does-not-exist.json"],
            )
        self.assertIn("does-not-exist.json", str(ctx.exception))

    def test_empty_declared_files_still_creates_the_sandbox_dir(self) -> None:
        # A skill with no declared inputs still needs a writable root to PRODUCE
        # files into, so the sandbox is created even though nothing is staged.
        resolved = _sandbox.stage_sandbox(
            evals_dir=self.evals_dir,
            variant_dir=self.variant_dir,
            declared_files=[],
        )
        self.assertEqual(resolved, [])
        sandbox = self.variant_dir / "sandbox"
        self.assertTrue(sandbox.is_dir())
        self.assertEqual(list(sandbox.iterdir()), [])


def _run_git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


class GitDirtyPathsTests(unittest.TestCase):
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

    def test_clean_repo_has_no_dirty_paths(self) -> None:
        self.assertEqual(_sandbox.git_dirty_paths(self.repo), set())

    def test_untracked_file_appears(self) -> None:
        (self.repo / "escape.json").write_text("{}\n")
        self.assertIn("escape.json", _sandbox.git_dirty_paths(self.repo))

    def test_modified_tracked_file_appears(self) -> None:
        (self.repo / "tracked.txt").write_text("v2-MUTATED\n")
        self.assertIn("tracked.txt", _sandbox.git_dirty_paths(self.repo))

    def test_renamed_file_reports_uncorrupted_paths(self) -> None:
        _run_git(self.repo, "mv", "tracked.txt", "renamed.txt")
        dirty = _sandbox.git_dirty_paths(self.repo)
        # Both the new name and the original name must appear intact — no token
        # sliced into a garbage string.
        self.assertIn("renamed.txt", dirty)
        self.assertIn("tracked.txt", dirty)
        for p in dirty:
            self.assertNotIn("\0", p)

    def test_non_git_dir_returns_empty_set_without_crashing(self) -> None:
        not_a_repo = Path(self.tmp.name) / "plain"
        not_a_repo.mkdir()
        result = _sandbox.git_dirty_paths(not_a_repo)
        self.assertEqual(result, set())

    def test_paths_are_repo_root_relative_regardless_of_anchor(self) -> None:
        # Load-bearing invariant for the escape guard: prepare_workspace snapshots
        # the baseline anchored at evals_dir, but finalize checks anchored at the
        # deeper iteration_dir. Their subtraction is only sound because
        # `git status --porcelain` yields repo-root-relative paths regardless of the
        # -C anchor depth. Pin it: an escape at the repo root must appear identically
        # whether git_dirty_paths is anchored at the root or at a deep subdirectory.
        deep = self.repo / "evals" / "skills" / "demo" / "workspace" / "iteration-1"
        deep.mkdir(parents=True)
        (self.repo / "escape-at-root.json").write_text("{}\n")
        from_root = _sandbox.git_dirty_paths(self.repo)
        from_deep = _sandbox.git_dirty_paths(deep)
        self.assertIn("escape-at-root.json", from_root)
        self.assertEqual(from_root, from_deep)


if __name__ == "__main__":
    unittest.main()
