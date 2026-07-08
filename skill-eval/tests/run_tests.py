#!/usr/bin/env python3
"""Zero-dependency test runner for the repo's Python unit tests.

Why this exists instead of ``python -m unittest discover``:
``unittest`` discovery imports each test file as a dotted module, which
requires every parent directory to be a valid Python package name. Our
typed test lanes live under ``tests/skills/<skill-name>/`` and skill names
contain dashes (e.g. ``skill-eval-runner``), so dotted import fails and
discovery silently finds **zero** tests.

This runner sidesteps that by loading every ``test_*.py`` file directly from
its path via ``importlib`` (a synthetic, dash-free module name), collecting
its ``TestCase`` classes, and running them with the stdlib ``unittest``
runner. No third-party dependency — consistent with the existing test's
"stdlib only" convention.

Usage::

    python tests/run_tests.py                      # run everything under tests/
    python tests/run_tests.py -v                   # verbose (per-test names)
    python tests/run_tests.py --md-summary out.md  # also write a markdown summary

The optional markdown summary lists per-file pass counts and every failure /
error, so CI can fold it into the PR validation comment.
"""

from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent


def _module_name_for(path: Path) -> str:
    """Stable, dash-free, collision-free module name derived from the path."""
    rel = path.relative_to(TESTS_ROOT).with_suffix("")
    slug = re.sub(r"[^0-9a-zA-Z]+", "_", str(rel))
    return f"reflex_tests.{slug}"


def _load_module_from_path(path: Path, mod_name: str):
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load test module from {path}")
    module = importlib.util.module_from_spec(spec)
    # Register so dataclasses / pickling / unittest internals can find it.
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


def discover_test_files() -> list[Path]:
    files = sorted(TESTS_ROOT.rglob("test_*.py"))
    if not files:
        print("No test files (test_*.py) found under", TESTS_ROOT, file=sys.stderr)
    return files


def build_suite(test_files: list[Path]) -> unittest.TestSuite:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for path in test_files:
        module = _load_module_from_path(path, _module_name_for(path))
        suite.addTests(loader.loadTestsFromModule(module))
    return suite


def _write_md_summary(path: Path, result: unittest.TestResult, n_files: int) -> None:
    passed = result.testsRun - len(result.failures) - len(result.errors)
    ok = result.wasSuccessful()
    lines = ["## Python unit tests", ""]
    status = "✅ all passing" if ok else "❌ failures"
    lines.append(
        f"**{status}** — {passed}/{result.testsRun} passed "
        f"across {n_files} file(s)."
    )
    if result.failures or result.errors:
        lines.append("")
        lines.append("<details><summary>Failures & errors</summary>")
        lines.append("")
        for kind, bucket in (("FAIL", result.failures), ("ERROR", result.errors)):
            for test, _ in bucket:
                lines.append(f"- **[{kind}]** `{test.id()}`")
        lines.append("")
        lines.append("</details>")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str]) -> int:
    verbosity = 2 if {"-v", "--verbose"} & set(argv) else 1

    md_summary: Path | None = None
    if "--md-summary" in argv:
        i = argv.index("--md-summary")
        if i + 1 < len(argv):
            md_summary = Path(argv[i + 1])

    test_files = discover_test_files()
    suite = build_suite(test_files)
    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)

    if md_summary is not None:
        _write_md_summary(md_summary, result, len(test_files))

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
