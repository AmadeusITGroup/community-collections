# Worked Commit-Message Examples

Before/after examples for the commit-message-writer skill.

## Example 1 — a bug fix with a scope

Change: the date parser crashed on empty input.

```
fix(parser): handle empty input without crashing

Return an empty result instead of throwing when the input string is
blank. Adds a guard clause at the top of parseDate().
```

## Example 2 — a new feature, no body needed

Change: add a `--json` output flag to the CLI.

```
feat(cli): add --json output flag
```

## Example 3 — a breaking change

Change: the `format()` function now returns an object instead of a string.

```
refactor!: return a result object from format()

BREAKING CHANGE: format() now returns { text, warnings } instead of a
bare string. Callers must read the .text property.
```

## Example 4 — docs only

```
docs: clarify installation steps in README
```
