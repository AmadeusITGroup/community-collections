# Contributing to Skill Eval Runner

The skill-eval-runner executes skill evaluation suites and grades responses via LLM-as-judge. Contributions typically involve improving grading logic, adding expectation patterns, enhancing the viewer, or refining benchmark analysis.

## Areas of Contribution

### Grading Logic

- Improve the skill-eval-grader agent prompt (`agents/skill-eval-grader.agent.md`) for more accurate pass/fail verdicts
- Add support for new expectation types (e.g., numeric thresholds, regex matching, structural checks)
- Reduce false positives and false negatives in grading

### Expectation Patterns

- Document reusable expectation patterns for common eval scenarios
- Add helpers for confidence-level expectations, output format validation, and evidence checks
- Improve expectation wording guidelines in the skill-eval-generator's design principles (`skills/skill-eval-generator/SKILL.md`, Phase 2)

### Viewer UX

- The eval-viewer lives in `skills/skill-eval-runner/eval-viewer/`
- Improve the feedback workflow for flagging incorrect grades
- Enhance the benchmark tab with trend visualizations

### Benchmark Analysis

- Improve the skill-eval-analyzer agent (`agents/skill-eval-analyzer.agent.md`) for pattern detection
- Add regression detection heuristics to `skills/skill-eval-runner/scripts/aggregate_benchmark.py`
- Improve comparison output

## Testing

After changes, run the skill-eval-runner on a skill that has evals:
```
/skill-eval-runner skill-optimiser
```

Check that:
- All test cases execute without errors
- Grading produces reasonable pass/fail verdicts
- The viewer renders outputs and benchmark correctly
- `benchmark.json` is well-formed

## Extending

### Adding a New Agent Role

1. Create the agent file in `agents/` following the `skill-eval-*.agent.md` convention
2. Register it in `collections/skills-creator-toolbox.collection.yml`
3. Update the skill-eval-runner SKILL.md to reference the new agent
4. Update this documentation

### Modifying the Viewer

The viewer is a standalone HTML/JS application. Changes should preserve:
- Offline functionality (no external dependencies)
- Three-view layout: Review (per-eval), Benchmark (per-iteration), Progression (across iterations)
- Feedback capture workflow

## Questions?

Open an issue if you need help with skill-eval-runner improvements.
