# Skill Eval

Use this collection when you want to measure whether an Agent Skill actually improves outcomes — author an evaluation suite for a skill, then run it with LLM-as-judge grading, blind A/B comparison, and regression tracking across iterations.

## Why use it

This collection helps you:
- generate evaluation test cases for any skill by browsing its `SKILL.md` and references
- run those evals with and without the skill to quantify the skill's value
- grade responses against expectations using an LLM-as-judge protocol
- compare variants blindly (A/B), with deterministic, seedable, auditable assignment
- sandbox each variant's inputs so file-mutating skills are graded on their real artifacts without contaminating shared fixtures
- track pass-rate and quality regressions across skill iterations
- review results visually in a self-contained HTML report (progression, benchmark, per-eval)

## Contents

| Item | Type | Purpose |
|------|------|---------|
| `skill-eval-generator` | Skill | Generate `evals.json` test cases for a skill from its documented surface area |
| `skill-eval-runner` | Skill | Run a skill's evals through PREPARE → EXECUTE → GRADE → REPORT, orchestrating the sub-agents below |
| `skill-eval-runner` (agent) | Agent | Entry-point agent that drives the four-phase run workflow |
| `skill-eval-executor` | Agent | Executes a test prompt with or without the skill and reports metrics |
| `skill-eval-grader` | Agent | Grades a response against expectations and post-run artifact files |
| `skill-eval-comparator` | Agent | Blind A/B comparison of two variant responses against a rubric |
| `skill-eval-analyzer` | Agent | Cross-eval pattern detection and benchmark insights |

## Prerequisites

- Python 3.9+ (standard library only — no third-party packages required)
- A subagent-capable host (the runner spawns executor, grader, comparator, and analyzer sub-agents)
- A skill with an eval suite at `evals/skills/<skill_name>/evals.json` (the generator produces one; the colocated `skills/<skill_name>/evals/evals.json` layout is also resolved)

## How to use it

In GitHub Copilot Chat or another compatible environment:

Generate evals for a skill that has none yet:

```text
/skill-eval-generator
```

Then run them:

```text
/skill-eval-runner
```

Provide the skill name when prompted. The runner prepares an iteration workspace, executes each test case with and without the skill, grades and compares the outputs, and opens an HTML report.

To list the skills that currently have evals:

```text
python skills/skill-eval-runner/scripts/list_evals.py
```

Run commands from this `skill-eval/` directory; the scripts resolve their own paths relative to it.

## Expected output

You will receive:
- per-expectation pass/fail grading for the with-skill and without-skill variants
- the skill's measured value (pass-rate delta) and blind A/B win counts
- for iteration 2+, regression deltas versus the previous iteration
- a `benchmark.json` / `benchmark.md` summary plus a unified HTML report with Progression, Benchmark, and Review pages

## Development

The framework ships with a standard-library unit-test suite. From this `skill-eval/` directory:

```bash
python tests/run_tests.py        # run everything
python tests/run_tests.py -v     # verbose
```

Per-skill documentation lives under [`docs/skills/`](docs/skills/).
