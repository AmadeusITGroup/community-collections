"""Integration tests: prepare_workspace creates per-variant sandboxes."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_DIR = _REPO_ROOT / "skills" / "skill-eval-runner" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

import prepare_workspace  # noqa: E402


class PrepareSandboxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.evals_dir = self.repo / "evals" / "skills" / "demo-skill"
        (self.evals_dir / "files").mkdir(parents=True)
        (self.evals_dir / "files" / "sample.log").write_text("ORIGINAL\n")
        evals = {
            "schema_version": "1.0.0",
            "skill_name": "demo-skill",
            "skill_version": "1.0.0",
            "evals": [
                {"id": 1, "name": "uses-file", "prompt": "p", "expected_output": "o",
                 "files": ["files/sample.log"], "expectations": ["e"]},
                {"id": 2, "name": "no-file", "prompt": "p", "expected_output": "o",
                 "files": [], "expectations": ["e"]},
            ],
        }
        (self.evals_dir / "evals.json").write_text(json.dumps(evals))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _iter1(self) -> Path:
        return self.evals_dir / "workspace" / "iteration-1"

    def _prepare(self) -> None:
        """Run prepare_workspace with its console banner suppressed, so the test
        suite's output stays pristine (prepare_workspace prints a summary tree)."""
        with contextlib.redirect_stdout(io.StringIO()):
            prepare_workspace.prepare_workspace(self.repo, "demo-skill", None)

    def test_iteration1_baseline_stages_inputs_for_both_variants(self) -> None:
        self._prepare()
        for variant in ("current_skill", "without_skill"):
            copy = self._iter1() / "eval-1-uses-file" / variant / "sandbox" / "files" / "sample.log"
            self.assertTrue(copy.is_file(), f"missing staged copy for {variant}")
            self.assertEqual(copy.read_text(), "ORIGINAL\n")

    def test_eval_metadata_files_point_at_the_variant_copy(self) -> None:
        self._prepare()
        meta = json.loads(
            (self._iter1() / "eval-1-uses-file" / "eval_metadata.json").read_text()
        )
        self.assertEqual(meta["files"], ["sandbox/files/sample.log"])
        self.assertEqual(meta["sandbox_dir"], "current_skill/sandbox")

    def test_eval_with_no_files_still_gets_a_sandbox_root(self) -> None:
        self._prepare()
        eval2 = self._iter1() / "eval-2-no-file"
        meta = json.loads((eval2 / "eval_metadata.json").read_text())
        # No declared inputs -> empty files list, but a sandbox root is still
        # created and advertised so a skill that only PRODUCES files has a home.
        self.assertEqual(meta["files"], [])
        self.assertEqual(meta["sandbox_dir"], "current_skill/sandbox")
        self.assertTrue((eval2 / "current_skill" / "sandbox").is_dir())
        self.assertEqual(list((eval2 / "current_skill" / "sandbox").iterdir()), [])

    def test_shared_fixture_is_untouched_after_prepare(self) -> None:
        self._prepare()
        self.assertEqual((self.evals_dir / "files" / "sample.log").read_text(), "ORIGINAL\n")

    def test_iteration_config_records_git_status_baseline(self) -> None:
        self._prepare()
        cfg = json.loads((self._iter1() / "iteration_config.json").read_text())
        self.assertIn("git_status_baseline", cfg)
        # The tmp repo is not a git work tree, so git_dirty_paths returns an
        # empty set and the recorded baseline is []. (git_dirty_paths' behavior
        # against a real repo is covered by test_sandbox.GitDirtyPathsTests.)
        self.assertEqual(cfg["git_status_baseline"], [])


if __name__ == "__main__":
    unittest.main()
