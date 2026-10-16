---
name: renovate-config
description: 'Build or improve a best-practice renovate.json through guided, group-by-group elicitation. Use when a user wants to set up Renovate, create or review renovate.json, configure grouping, automerge, scheduling, rate limits, security/vulnerability alerts, or manager-specific options. Triggers on "set up renovate", "configure renovate.json", "renovate best practices".'
argument-hint: "Point to the repo (and existing renovate.json if any)"
metadata:
  author: "Mahesh GADAGI"
  version: "1.0.0"
compatibility: "Works with GitHub Copilot and other Agent Skills-compatible tools. Targets any Renovate-managed repository."
---

# Renovate Config Builder

Produce a schema-valid `renovate.json` by walking the user through option groups, grounded in the bundled catalog and best-practices references.

## Bundled and shared resources

This skill uses two sets of resources:

- **Bundled assets** alongside this SKILL.md: `assets/renovate.base.json` (baseline) and `assets/examples/` (sample configs). These omit the `$schema` header by design — add `"$schema": "https://docs.renovatebot.com/renovate-schema.json"` as the first key during assembly (Step 4).
- **Bundled references** alongside this SKILL.md: `references/config-options-catalog.md` and `references/renovate-best-practices.md`. Derive their absolute path from where this SKILL.md was loaded.
- If `assets/renovate.base.json` cannot be read, halt and notify the user: "Baseline file not found. Please ensure the skill assets are installed correctly." Do not proceed to assembly. If `references/config-options-catalog.md` cannot be read, treat all catalog lookups in Steps 2 and 3 as affected and source every option from public Renovate documentation, noting this prominently in the final output. If `references/renovate-best-practices.md` cannot be read, proceed without best-practice annotations and note the gap in the recap.

## When to Use

- Set up Renovate for a repository that has no `renovate.json`
- Review or improve an existing Renovate configuration
- Configure grouping, automerge, scheduling, rate limits, security alerts, or manager-specific behavior

## Procedure

### 1. Detect current state

- Search for an existing `renovate.json`, `.github/renovate.json`, `.renovaterc`, or `renovate.json5`. If found, read and summarize the current config.
- If the existing file is not well-formed JSON or contains unrecognized presets, report each issue to the user, ask whether to repair or start fresh, and do not proceed to Step 2 until the user confirms.
- If the existing file is valid, summarize what is already enabled (presets, grouping, automerge, schedule, security, manager options) before eliciting anything. In Step 2, offer choices only for gaps, risky settings, or groups the user explicitly wants to change — preserve existing behavior unless the user selects a replacement.
- Build an evidence-backed repository inventory before proposing configuration, using actual searches rather than assumptions:
  - Use file search for manifest/lock patterns per ecosystem (for example `package.json`/`pnpm-lock.yaml`/`yarn.lock`/`package-lock.json`, `requirements*.txt`/`poetry.lock`/`pyproject.toml`, `Gemfile.lock`, `pom.xml`/`build.gradle*`, `go.mod`, `Cargo.lock`, `composer.lock`, and .NET project or lock files), plus `Dockerfile*`, `docker-compose*.yml`, `.tool-versions`, and CI config across providers (`.github/workflows/**`, `.gitlab-ci.yml`, `azure-pipelines.yml`, `Jenkinsfile`, `.circleci/config.yml`) — exclude vendored/build output directories (`node_modules`, `vendor`, `dist`, `build`) from results.
  - Use content search for signals that a filename alone can't reveal: monorepo tooling (`"workspaces"` in `package.json`, `pnpm-workspace.yaml`, `lerna.json`, `nx.json`, `turbo.json`, `go.work`, a `[workspace]` table in `Cargo.toml`); Red Hat/RHEL base images (`FROM` lines referencing `registry.access.redhat.com`, `registry.redhat.io`, `ubi8`/`ubi9`, or `rhel`); and private registries (custom URLs in `.npmrc`, `pip.conf`/`pip.ini`, `settings.xml`, `nuget.config`, or `.dockerconfigjson`-style registry mirrors).
  - Flag conflicting evidence explicitly instead of picking one silently — for example two lock files for the same ecosystem (`package-lock.json` and `yarn.lock` both present), or a runtime version declared differently in two sources. Surface each conflict as its own selectable question before proposing grouping or lock-file maintenance for that ecosystem.
- Record detected ecosystems and package managers; runtime versions and every source that declares them; lock-file behavior; service or ownership boundaries; and private registry, vendor, or platform constraints. Use the inventory to omit irrelevant choices rather than assuming npm, Docker, Python, Gradle, or GitHub Actions are present. Distinguish confirmed evidence (a file or line you actually read) from inferred/low-confidence signals, and turn anything low-confidence into a selectable question rather than guessing.

### 2. Elicit by group (interactive)

Use the `vscode_askQuestions` tool to present the configuration wizard. For every user decision, the tool call MUST be the next action; do not send ordinary chat text before the selection result arrives. Do not simulate selectable choices with Markdown checkboxes, numbered lists, or reply-with-a-number instructions. If the tool is unavailable, say only that interactive selections are unavailable and ask the user to retry with a tool-enabled agent; never create a text-based substitute. Do not add unrelated repository advice while a selection is pending.

For each tool question: set a concise `header` naming the current category and a focused `question` stating the decision; put each option's practical effect, benefit, and trade-off in its `description`; mark exactly one `recommended: true` option when choices are mutually exclusive; set `multiSelect: true` only when options can safely be combined, otherwise use a single-select question and explain precedence in the question `message`; and include a `Custom` option with free-form input where a supported choice cannot capture the user's policy.

Use these fixed batching rules. In the default flow, ask each topic in its own call. In the full-review flow, batch `Lock-file maintenance`, `Registry and source management`, and `Vendor-specific versioning` in one call when applicable; ask `Repository strategy`, `Dependency grouping`, `Update-type grouping`, `Runtime and platform versions`, `Presets and extends`, and the final policy group in separate calls. `Update-type grouping` always follows `Dependency grouping`; do not batch them. Do not send progress notes before tool calls.

If a question is dismissed or returns no selection, apply its recommended option automatically, continue the flow without blocking, and list it as an auto-applied default in the final recap.

#### 2a. Filter groups

Using the inventory from Step 1, list only applicable groups and state why each was included or excluded.

#### 2b. Select group options

Execute exactly one of the following flows. Never mix steps between them. Complete the selected flow before proceeding to 2c.

**DEFAULT FLOW — for a plain "configure Renovate" request**

Do not start with a profile choice or the full topic list. Drive this flow entirely from the Step 1 inventory:

1. D1. `Grouping` (one consolidated `multiSelect` question): offer checkbox items built only from detected evidence, such as grouping non-major updates per detected package manager (recommended), grouping across monorepo workspace packages (only if a monorepo was found), grouping minor and patch updates together (recommended), keeping major updates separate (recommended), grouping related dependency families with manifest evidence, and grouping by service or ownership where directories/CODEOWNERS support it.
2. D2. `Lock-file maintenance` (single-select, only when a supported lock file is present): scheduled dedicated maintenance PRs (recommended), refresh only when a dependency changes, or disable dedicated maintenance.
3. D3. `Runtime and platform versions` (only if a runtime version is declared somewhere): one PR per detected runtime across all its declaration sources, or separate PRs by source.
4. D4. `Registry and source management` (if applicable): propose the recommended default and record the user's choice.
5. D5. `Vendor-specific versioning` (if applicable): propose the recommended default and record the user's choice.
6. D6. `PR optimisation`: propose the recommended default and record the user's choice.
7. D7. `Automerge, scheduling, rate limits, security, dashboard`: propose the recommended default and record the user's choice. Stop after D7.

If the user named a specific topic, begin at the Dn step matching that topic and continue sequentially through D7.

**END DEFAULT FLOW**

**FULL REVIEW FLOW — only when the user explicitly asks for a full review**

First call `vscode_askQuestions` with a single-select `Choose a starting policy` question offering these profiles plus `Custom`, customized to detected ecosystems:

- `Best Practice Configuration` (recommended): moderate grouping of non-major updates, separate major upgrades, stability window, scheduled lock-file maintenance, and no unapproved automerge.
- `Enterprise Configuration`: ownership or service-aware grouping where detected, internal-registry and vendor-aware rules, labels/dashboard, scheduled maintenance, and approval boundaries.

Do not claim a profile is enabled until the user selects it, and flag any part that cannot be represented by Renovate.

Then walk the full, more granular topic list — this expands the same decisions the default flow's `Grouping` question already covers, plus the remaining topics — in this dependency-driven order:

1. Repository strategy: only when monorepo, multi-service, or ownership evidence exists; independent repository, monorepo-aware, service/domain grouping, or ownership-team grouping
2. Dependency grouping: individual updates, one group per detected ecosystem, related dependency-family groups supported by manifest evidence, and service or ownership-based groups
3. Update-type grouping: after dependency grouping, choose the handling for major, minor, patch, and digest updates. Recommend grouped patch/minor updates and separate major PRs. Explain that an update-type rule overrides a broad dependency group when both match.
4. Runtime and platform versions: group each detected runtime across manifests, lock files, containers, workflows, and build files; or split it by source
5. Lock-file maintenance: only when a supported lock file is present; scheduled dedicated maintenance (recommended), refresh with dependency changes, or disable dedicated maintenance
6. Registry and source management: public registry inclusion, internal registry priority, or separate internal/external rules
7. Vendor-specific versioning: only when Red Hat or RHEL-derived images, repositories, or packages are detected; apply Red Hat versioning only to those dependencies (recommended), retain default versioning, or specify a custom policy
8. Presets and extends: recommended base preset (for example `config:recommended`) versus a conservative or aggressive starting preset, plus any manager-specific presets the detected ecosystems support
9. Automerge, scheduling, rate limits, security, manager-specific options, dashboard, labels, reviewers, and semantic commits

For each group: state the best-practice default from `references/config-options-catalog.md` when available, let the user accept, multi-select, or override, and record the choice. Keep momentum — do not ask everything at once. Do not fabricate a Renovate setting for a requested policy; explain the gap and offer the closest supported alternative.

**END FULL REVIEW FLOW**

#### 2c. Recap and confirm

Before assembling the config, post a compact bulleted recap of every accepted selection (including any auto-applied defaults from skipped questions), grouped by topic. Then call `vscode_askQuestions` once more with a single-select confirmation: `Generate renovate.json with these choices` (recommended) or `Change a selection` (loop back to the relevant topic if chosen). Do not proceed to Step 3 until the user confirms.

### 3. Sourcing (hybrid)

- Use the bundled catalog as the primary source.
- Only consult `https://docs.renovatebot.com/` for options absent from the catalog. Do not fetch the URL solely to validate catalog entries — treat catalog values as authoritative unless the user explicitly questions them.
- Fall back to the catalog if a fetch fails, and note any value you could not verify.

### 4. Assemble & validate

- Start from `assets/renovate.base.json`, then layer in the chosen options.
- Ensure the `$schema` header is present.
- Validate JSON well-formedness and that presets/fields exist. Flag anything unverified.

### 5. Present

- Show the final `renovate.json` and a short rationale for each non-default choice.
- Offer to write it to the repo root (only when the user confirms).
