# Skill Eval Generator

> **Skill:** [`skills/skill-eval-generator/`](../../../skills/skill-eval-generator/) — see [SKILL.md](../../../skills/skill-eval-generator/SKILL.md) for the agent-facing definition.

The skill-eval-generator browses a skill's structure and references to produce evaluation test cases. It outputs `evals/skills/{skill-name}/evals.json` with prompts, expected outputs, and `[auto]`-prefixed expectations ready for human refinement.

## Pipeline

The skill-eval-generator follows a 4-phase pipeline:

| Phase | What happens | Output |
|-------|-------------|--------|
| **BROWSE** | Reads the target skill's SKILL.md and references, identifies testable surface area | Understanding of skill capabilities |
| **DESIGN** | Designs eval scenarios per testable pattern (symptoms, routing, triggering, overview) | List of eval scenarios with rationale |
| **GENERATE** | Writes `evals/skills/{skill-name}/evals.json`, respecting incremental merge rules | evals.json with `[auto]`-prefixed content |
| **REPORT** | Presents summary with mock data candidates and next steps | User guidance for refinement |

## When To Use

- A skill exists but has no evals yet
- A skill was updated and evals need refreshing
- You want to scaffold baseline evals before running `/skill-eval-runner`

## When NOT To Use

- You want to run existing evals — use `/skill-eval-runner` instead
- You want to manually write evals — edit `evals/skills/{skill-name}/evals.json` directly
- The skill doesn't exist yet — generate the skill first

## Usage

```
/skill-eval-generator skill-optimiser
```

The generator accepts any skill name that has a corresponding `skills/{skill-name}/SKILL.md`.

## Next Step

The generated `evals.json` is a **starting point, not a finished suite**. Every prompt and expectation is `[auto]`-prefixed and needs human review:

- Refine prompts so they look like real user messages, not paraphrased SKILL.md snippets
- Drop expectations that aren't actually verifiable, sharpen vague ones, add the ones the generator missed
- Add `files/` inputs (logs, payloads) where the prompt would naturally come with attached data
- Remove the `[auto]` prefix once you've vouched for an expectation

Once the suite is human-reviewed, use [`/skill-eval-runner`](../skill-eval-runner/README.md) to execute the test cases, grade the responses, and produce a report you can re-open after every skill update.

## Further Reading

- [SKILL.md](../../../skills/skill-eval-generator/SKILL.md) — full skill definition with phase details
- [schemas.md](../../../skills/skill-eval-runner/references/schemas.md) — authoritative JSON schema for evals.json

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to improve the skill-eval-generator.
