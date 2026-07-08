# Contributing to Skill Eval Generator

The skill-eval-generator produces evaluation test cases by browsing a skill's structure. Contributions typically involve improving eval design heuristics, adding testable surface area patterns, or refining the `[auto]` convention.

## Areas of Contribution

### Testable Surface Area Patterns

The generator identifies testable patterns in skills (Phase 1). To add a new pattern:

1. Add the pattern to the "Identify testable surface area" table in `skills/skill-eval-generator/SKILL.md`
2. Add corresponding design guidance in Phase 2
3. Test by running the generator against a skill that exhibits the pattern

### Eval Design Heuristics

Phase 2 contains design principles for writing good expectations. Improve these by:

- Adding new eval type templates (e.g., performance-focused, security-focused)
- Refining the difficulty gradient guidance
- Adding domain-specific expectation patterns

### Incremental Merge Logic

The generator's merge rules (Phase 3) protect human-refined content. Enhance by:

- Adding edge case handling for merge conflicts
- Improving ID assignment for mixed manual/auto eval sets

### Mock Data Guidance

The generator suggests which evals would benefit from input files (Phase 4). Improve by:

- Adding file type suggestions based on skill domain
- Providing mock data templates for common patterns (metrics/log responses, API outputs)

## Testing

After changes, run the generator on a skill that has existing evals to verify:

1. Incremental merge preserves non-`[auto]` expectations
2. New evals have unique IDs and names
3. The report correctly identifies mock data candidates

```
/skill-eval-generator skill-optimiser
```

## Questions?

Open an issue if you need help with skill-eval-generator improvements.
