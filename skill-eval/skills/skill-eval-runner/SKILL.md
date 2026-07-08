---
name: skill-eval-runner
description: "Run skill evaluations by spawning sub-agents for test execution and LLM-as-judge grading. Includes blind A/B comparison and eval-viewer for visual review. Triggers: user says 'run evals', 'evaluate skill', 'test skill'; or after generating/updating a skill with evals."
argument-hint: "Provide a skill name"
compatibility: Requires Python 3.9+ and subagent support.
disable-model-invocation: false
user-invocable: true
license: SEE LICENSE IN LICENSE
metadata:
  author: Cyril Colombel
  version: "1.0.0"
---

# Skill Eval Runner

## When To Use This Skill

- User wants to run evaluations for a skill (e.g., "run evals for example-skill")
- After generating or regenerating a skill with evals
- During PR review when a skill with evals was modified

## When NOT To Use This Skill

- No `evals/skills/{skill_name}/evals.json` (or the colocated fallback `skills/{skill_name}/evals/evals.json`) exists for the skill (tell user: "No evals found for this skill.")
- User wants to generate evals, not run them (for REFLEX skills: use reflex-skill-generator Phase 3b; for other skills: create evals.json manually)
- User just wants to list available evals (use `python skills/skill-eval-runner/scripts/list_evals.py`)

---

## Workflow Overview

Execute **4 phases in order**:

```
PREPARE -> EXECUTE -> GRADE -> REPORT
```

| Phase | Actor | Output |
|-------|-------|--------|
| 1. Prepare | You | Workspace directory, eval metadata files |
| 2. Execute | Sub-agents (eval-executor) | `response.md` + consolidated `outputs/metrics.json` (executor writes `self_report` + `user_notes`; `finalize_metrics.py` adds `host_telemetry` + optional `notification`) per variant |
| 3. Grade | Sub-agents (eval-grader, eval-comparator, eval-analyzer) | `grading.json`, `comparison.json`, `benchmark.json` |
| 4. Report | You + script | `benchmark.md`, eval-viewer HTML, summary |

---

## PHASE 1: PREPARE

> **Goal**: Validate inputs, determine iteration, create workspace structure.

1. **Accept skill name** from user.
2. **Check `evals.json` exists — before running any script.** Look in both `evals/skills/{skill_name}/evals.json` (canonical) and `skills/{skill_name}/evals/evals.json` (colocated fallback). If neither exists, **STOP here**: tell the user "No evals found for this skill."
3. **Run the preparation script**:

```bash
python skills/skill-eval-runner/scripts/prepare_workspace.py {skill_name}
```

For a single eval case: add `--eval-id N`.

4. **Read the script output** to get the iteration number, mode (baseline/regression/mixed), and executor count needed for PHASE 2.

> **Workspace path is resolved for you.** `prepare_workspace.py` finds the skill's evals in either the canonical `evals/skills/{skill_name}/` or the colocated `skills/{skill_name}/evals/` layout, and prints the actual `iteration-{N}` directory it created. **Use that printed path** as `{workspace}` / `{iteration_dir}` in every later command. The example paths below assume the canonical layout; substitute the printed path if your skill uses the colocated one.

### GATE 1: Preparation Complete

- [ ] `prepare_workspace.py` completed successfully
- [ ] Workspace directory created with `iteration_config.json` and `eval_metadata.json` per eval

---

## PHASE 2: EXECUTE

> **Goal**: Run each test case with and without the skill, capturing outputs and tool metrics.

**Spawn ALL executor sub-agents in parallel.** The number of sub-agents depends on eval classification:

- **Baseline evals** (iteration 1, or new evals in mixed mode): spawn 2 executors per eval (`current_skill` + `without_skill`)
- **Regression evals** (existing evals in iteration 2+): spawn 1 executor per eval (`current_skill` only; its `without_skill` is reused from the baseline iteration, and its `previous_skill` is the previous iteration's `current_skill`)
- **Total** = `2 × count(baseline_evals) + 1 × count(regression_evals)`

Issue all Agent tool calls in a single message. Do NOT loop eval cases sequentially.

### current_skill prompt

```
Execute this evaluation task:

**Skill to load**: Read `skills/{skill_name}/SKILL.md` and follow its workflow.
Read reference files as the skill directs.

**Test prompt**: {prompt from evals.json}

**Sandbox (your private writable working root)**: `{workspace}/eval-{id}-{name}/current_skill/sandbox/`. Treat this directory as the repository root for this task. {if files: "Your staged input files are inside it at: {eval_metadata.files paths, each resolved as {workspace}/eval-{id}-{name}/current_skill/{path}}. Read them for context."} If the task creates, edits, or merges ANY file — including a path the skill computes for itself or a brand-new file — resolve that path INSIDE this sandbox and write there. NEVER write anywhere else in the repository, and never to the shared evals/{skill_name}/files/.

Save your response to: `{workspace}/eval-{id}-{name}/current_skill/outputs/response.md`
Save your metrics to: `{workspace}/eval-{id}-{name}/current_skill/outputs/metrics.json`
```

### without_skill prompt

```
Execute this evaluation task:

**No skill**: Do NOT read any files from skills/ or knowledge-bases/.
Use only your general knowledge.

**Test prompt**: {prompt from evals.json}

**Sandbox (your private writable working root)**: `{workspace}/eval-{id}-{name}/without_skill/sandbox/`. Treat this directory as the repository root for this task. {if files: "Your staged input files are inside it at: {eval_metadata.files paths, each resolved as {workspace}/eval-{id}-{name}/without_skill/{path}}. Read them for context."} If the task calls for creating, editing, or merging any file — including a path you compute for yourself or a brand-new file — resolve that path INSIDE this sandbox and write there. NEVER write anywhere else in the repository, and never to the shared evals/{skill_name}/files/.

Save your response to: `{workspace}/eval-{id}-{name}/without_skill/outputs/response.md`
Save your metrics to: `{workspace}/eval-{id}-{name}/without_skill/outputs/metrics.json`
```

### Finalizing metrics (canonical)

**You (the parent) do NOT assemble `metrics.json` by hand.** The executor writes its `self_report` + `user_notes` portion; after all executors finish, run the deterministic finalizer exactly once:

```bash
python skills/skill-eval-runner/scripts/finalize_metrics.py \
  evals/skills/{skill_name}/workspace/iteration-{N} \
  --session-log "{{VSCODE_TARGET_SESSION_LOG}}"
```

**CRITICAL — session log path:** `{{VSCODE_TARGET_SESSION_LOG}}` is a **prompt-template variable**, not a shell environment variable. You MUST substitute its literal value (visible at the top of your system prompt) directly into the command before execution. Do **not** write `$VSCODE_TARGET_SESSION_LOG` — the shell will expand that to an empty string and the finalizer will find zero debug logs, silently degrading every variant to `wall_clock` source with no token/turn/tool counts. If your system prompt does not expose this variable, omit `--session-log` entirely and accept the degraded result.

The finalizer:

- Walks every `eval-*/current_skill` and `eval-*/without_skill` directory in the iteration
- Reads the executor's `outputs/metrics.json` (containing `self_report` + `user_notes`) and leaves those layers untouched
- Merges `outputs/notification.json` (parent-written sidecar, if present) into a `notification` block and deletes the sidecar on success
- Adds a `host_telemetry` block with timing + tokens + turn count + log-derived tool calls/errors + model. Its `source` is one of `debug_log` (VS Code `runSubagent-*.jsonl`), `notification` (sidecar only), or `wall_clock` (last-resort fallback from `eval_metadata.json.prepared_at` + `response.md` mtime)
- Stamps a top-level `metrics_source` = `debug_log` when `host_telemetry` has log-derived tool counts, else `self_report`
- Deletes any legacy `execution.json` / `.notification.json` it finds from prior iteration layouts

If the parent process is VS Code, the finalizer looks at `$VSCODE_TARGET_SESSION_LOG` as a real shell env var if set; otherwise pass `--session-log PATH` explicitly (see the template-variable note above).

**Parent responsibility — `outputs/notification.json` (mandatory attempt).** Immediately after each executor subagent returns, you (the parent) MUST inspect the Task return value. If it exposes timing or usage fields, write `{variant_dir}/outputs/notification.json` capturing them verbatim: `spawned_at` and `returned_at` (ISO 8601 UTC, parent wall-clock) at minimum, plus `total_tokens`, `duration_ms`, and `status` when the host surfaces them. If the Task return exposes nothing beyond the response text, skip the file — the finalizer will fall back to `debug_log` or `wall_clock`. What you MUST NOT do is silently skip the inspection step: the whole point of the notification source is to capture host telemetry the debug log may lack. One-line write per subagent, no computation. The sidecar is visible (no dot prefix) so you can inspect it during debugging; the finalizer consumes then deletes it.

The executor's `self_report` covers what it can measure itself (`tool_calls`, `total_tool_calls`, `total_steps`, `files_created`, `output_chars`). The finalizer's `host_telemetry` layers authoritative log-derived counts on top when a debug log is available; `self_report` stays intact as the self-assessment. Downstream consumers prefer `host_telemetry` numbers when present and fall back to `self_report` otherwise.

### user_notes — the skill-quality feedback channel

The executor is the ONLY pipeline stage that reads the skill and its KB. `user_notes` is the channel through which it critiques them so a skill author can act between iterations. Shape:

- `skill_feedback` (four buckets): `missing_from_skill`, `ambiguous_instructions`, `broken_references`, `outdated_or_wrong`. Each entry is `{topic, impact, reference}` where `impact ∈ {blocking, major, minor}`. Populated in with-skill mode only.
- `response_risks`: `{assumption, if_wrong, grounded_in}` — assumptions that would change the conclusion if wrong. Both modes.
- `missing_inputs`: plain strings — absent files/data referenced by the prompt. Both modes.

Executor caps each skill_feedback bucket at 5 entries (highest impact first). The grader does NOT touch `user_notes` — it stays in `outputs/metrics.json.user_notes`, untouched from writer to reader. `aggregate_benchmark.py` reads it directly and rolls it up across evals into `benchmark.json.skill_feedback_rollup` (totals, by_impact, top_references, delta vs previous iteration); the HTML report renders it on the Benchmark tab (aggregated), the Review tab (per-eval, via `run.metrics.user_notes`), and the Progression tab (cross-iteration trend).

### GATE 2: Execution Complete

- [ ] `response.md` exists for all required variants (both for baseline evals, `current_skill` only for regression evals)
- [ ] `outputs/metrics.json` written by every executor (contains `self_report` + `user_notes`)
- [ ] `finalize_metrics.py` ran successfully — every variant's `outputs/metrics.json` now also has `host_telemetry` and a top-level `metrics_source` tag
- [ ] No `outputs/notification.json` sidecars remain (consumed and deleted by the finalizer)
- [ ] No `execution.json` or `.notification.json` files remain anywhere in the iteration (legacy artifacts)
- [ ] No variant still has `host_telemetry.source: "wall_clock"` as its only signal unless you know the subagent host exposes no usage telemetry

---

## PHASE 3: GRADE

> **Goal**: Grade expectations, run blind comparisons, aggregate benchmark.

### 3a. Grade expectations (parallel)

**Spawn ALL grader sub-agents in a single parallel batch.** Do NOT run them sequentially.

- **Baseline evals**: 2 graders per eval (`current_skill` + `without_skill`)
- **Regression evals**: 1 grader per eval (`current_skill` only; `without_skill` grading is reused from the baseline iteration)
- Input: `response.md` + expectations from `evals.json` + `expected_output` (grader does NOT read `metrics.json`)
- Output: `grading.json` with fields `expectations`, `summary`, `claims`, `eval_feedback` (execution telemetry and user-notes live in `outputs/metrics.json` and are joined by the aggregator at read time). `evidence` fields under `expectations[]` and `claims[]` are **arrays of strings** — one quoted passage per element; never concatenated into a single string (see [references/schemas.md](references/schemas.md))

#### Grader prompt template (mandatory wording for paths)

```
Grade this evaluation response.

**Response file**: {workspace}/eval-{id}-{name}/{variant}/outputs/response.md
**Expectations**: {inlined from evals.json}
**Expected output**: {inlined from evals.json, if any}
{if eval_metadata.sandbox_dir: "**Sandbox artifacts** (post-run): this variant's writable working tree is at {workspace}/eval-{id}-{name}/{variant}/sandbox/. Read any files under it — staged inputs AND anything this variant created, edited, or merged (e.g. a merged evals.json) — as first-class evidence."}

Save your grading to: {workspace}/eval-{id}-{name}/{variant}/grading.json
```

**CRITICAL — `grading.json` path:** `grading.json` is a **sibling** of the `outputs/` directory, **not a child**. If it is written under `outputs/` (e.g. `{variant}/outputs/grading.json`), `aggregate_benchmark.py` hard-fails with an explicit ERROR and exit code 2 (`detect_misplaced_grading`); re-run it with `--fix-grading-paths` to move the misplaced files automatically. The grader agent self-derives the path from `response_path.parent.parent / "grading.json"` and will log a warning if the prompt names a non-canonical location, but the prompt template above must always use the correct path to avoid confusion.

### 3b. Blind comparison (script-bracketed parallel)

The comparator step is wrapped by two scripts so A/B assignment is deterministic, seedable, and auditable — and so the comparator stays strictly blind.

**Step 3b-i (pre, deterministic):**

```bash
python skills/skill-eval-runner/scripts/assign_ab.py \
  evals/skills/{skill_name}/workspace/iteration-{N}
```

`assign_ab.py` reads `iteration_config.json` (specifically `ab_seed`, `baseline_path`, `previous_path`, and `eval_classification`). For each eval it decides:

- `comparison_mode` = `baseline` (pair `current_skill` vs `without_skill`) or `regression` (pair `current_skill` vs `previous_skill`, using `previous_path`)
- A/B randomization, seeded by `random.Random(ab_seed + eval_id)` so the assignment is reproducible

It writes `ab_assignment.json` in each eval directory. The comparator agent MUST NOT read this file.

**Step 3b-ii (parallel comparators):**

Spawn one `skill-eval-comparator` per eval. Each comparator only sees `variant_A_response.md` and `variant_B_response.md` (by path, not by variant name). It writes `comparison.json` with a blind `winner` (`A`, `B`, or `TIE`), `rubric`, `reasoning`, and `notable_differences`. It does NOT write `assignment`, `winner_variant`, `comparison_mode`, `baseline_iteration`, or `previous_iteration`.

**Step 3b-iii (post, deterministic):**

```bash
python skills/skill-eval-runner/scripts/resolve_comparisons.py \
  evals/skills/{skill_name}/workspace/iteration-{N}
```

`resolve_comparisons.py` merges each `ab_assignment.json` into the matching `comparison.json`, adding `assignment`, `winner_variant`, `comparison_mode`, `baseline_iteration`, and `previous_iteration`. The merge is idempotent: re-running it overwrites the same fields without touching the comparator's verdict.

### 3c. Aggregate and analyze

Run the aggregation script. For iteration 2+, pass both `--baseline-iteration` (latest iteration with usable `without_skill` data to reuse) and `--previous-iteration` (N-1, used to compute regression deltas):

```bash
python skills/skill-eval-runner/scripts/aggregate_benchmark.py \
  evals/skills/{skill_name}/workspace/iteration-{N} \
  --skill-name {skill_name} \
  --baseline-iteration evals/skills/{skill_name}/workspace/iteration-{B} \
  --previous-iteration evals/skills/{skill_name}/workspace/iteration-{N-1}
```

For iteration 1, omit both flags.

This produces `benchmark.json` (including `per_eval_comparisons` — every comparator's resolved verdict, reasoning, rubric scores, and per-expectation cross-variant breakdown) and `benchmark.md`.

Then spawn `skill-eval-analyzer` to read `benchmark.json`. Tell the analyzer to write its observations to `evals/skills/{skill_name}/workspace/iteration-{N}/analyzer_notes.json`. After it finishes, re-run `aggregate_benchmark.py` with the same flags so notes are folded into the final `benchmark.md`.

### GATE 3: Grading Complete

- [ ] `grading.json` exists for every required (eval, variant) pair
- [ ] `ab_assignment.json` written for every eval by `assign_ab.py` (before comparators spawn)
- [ ] `comparison.json` has a blind `winner` for every eval
- [ ] `resolve_comparisons.py` ran and added `winner_variant` + `comparison_mode` to every `comparison.json`
- [ ] `benchmark.json` + `benchmark.md` produced by `aggregate_benchmark.py`
- [ ] Analyzer notes appended and `aggregate_benchmark.py` re-run

---

## PHASE 4: REPORT

> **Goal**: Launch eval-viewer and present summary to user.

### Launch eval report

```bash
python skills/skill-eval-runner/eval-viewer/generate_review.py \
  evals/skills/{skill_name}/workspace \
  --skill-name {skill_name} \
  --iteration {N}
```

This opens a single unified report with 3 pages:
- **Progression** — pass rate trend chart, per-eval heatmap, token/time table across iterations
- **Benchmark** — summary metrics, blind comparison stats, per-eval breakdown, structured analyzer insights
- **Review** — eval-by-eval output viewer with prompt, grading, comparison, and feedback

An iteration timeline in the top bar lets users navigate between iterations. Selecting an older iteration truncates the Progression view to that point in time and shows that iteration's Benchmark and Review data.

### Present summary

Read `benchmark.json` and present the summary below. For the pass-rate figures, **quote the mean pass rate from `run_summary`** — `run_summary.current_skill.pass_rate.mean` and `run_summary.without_skill.pass_rate.mean` (each a 0–1 fraction; render as a percentage), and `run_summary.delta.pass_rate` for the improvement. Do NOT compute your own figure from the raw summed `passed`/`total` across `runs[]`: it weights larger evals more heavily than the per-eval mean and disagrees with `run_summary`, so mixing the two produces a misleading headline.

```
Evaluation complete: {skill_name} (iteration {N})

With skill:    {current_skill.pass_rate.mean}% mean pass rate
Without skill: {without_skill.pass_rate.mean}% mean pass rate
Skill value:   {delta.pass_rate} pass rate improvement

Blind comparison: current_skill preferred in {N}/{total} test cases

I've opened the results in your browser. The "Outputs" tab shows each test case
with the agent's response. The "Benchmark" tab shows quantitative comparison.
```

For iteration 2+, append regression delta:

```
vs previous:   {delta_from_prev} pass rate change (iteration {N-1} -> {N})
Regression:    current preferred in {N}/{total} comparisons vs previous iteration
Skipped:       {skipped} without_skill runs reused from baseline (iteration 1)
```

### GATE 4: Report Complete

- [ ] Eval-viewer launched successfully
- [ ] Summary presented to user with pass rates and blind comparison results

---

## Common Mistakes to Avoid

| Mistake | Consequence | Correct Approach |
|---------|-------------|------------------|
| Running evals when `evals.json` is missing | Confusing errors | Check file exists in PHASE 1, stop early with guidance |
| Spawning executor sub-agents sequentially | Multiplied execution time | Launch all 2×N executors in a single parallel batch |
| Letting without_skill variant read skill files | Contaminated baseline | Prompt explicitly says "Do NOT read any files from skills/ or knowledge-bases/" |
| Assembling `metrics.json`'s `host_telemetry` block manually from wall-clock | Silent data loss vs real token/turn counts | Always run `finalize_metrics.py` after PHASE 2 |
| Writing `grading.json` under `{variant}/outputs/` | `aggregate_benchmark.py` hard-fails (ERROR, exit code 2) | `grading.json` is a sibling of `outputs/`. Use the Phase 3a template. Re-run with `--fix-grading-paths` to auto-repair |
| Letting the comparator randomize A/B itself | Assignment non-reproducible, blindness weaker | Always run `assign_ab.py` before comparators and `resolve_comparisons.py` after |
| Skipping `resolve_comparisons.py` | `comparison.json` stays blind, aggregator can't count wins | Always run it post-comparator |
| Skipping the aggregation script | No benchmark.json for viewer | Always run `aggregate_benchmark.py` before eval-viewer |
| Hardcoding iteration number to 1 | Overwrites previous results | Let `prepare_workspace.py` scan the workspace |
| Not passing `--previous-iteration` on iteration 2+ | No regression delta vs N-1 | Always pass both `--baseline-iteration` and `--previous-iteration` on iteration 2+ |
| Executor writing timing or token fields into `metrics.json` | Pollutes `self_report` with host-side numbers it can't measure | Executor writes only `self_report` (tool counts, steps, files_created, output_chars) + `user_notes`; `finalize_metrics.py` owns `host_telemetry` |
| Not writing `outputs/notification.json` when the Task return has timing/usage fields | Loses host-level token and duration telemetry | Parent MUST inspect every Task return and write `outputs/notification.json` when any useful field is present (finalizer consumes and deletes it) |
| Re-running without_skill for existing evals in iteration 2+ | Wasted execution time and tokens | `prepare_workspace.py` only creates `current_skill/` for regression evals |
| Comparing current vs without_skill for regression evals | Wrong signal — doesn't measure improvement | `assign_ab.py` pairs `current_skill` vs `previous_skill` in regression mode |

---

## Reference Documentation

| Reference | When to Read |
|-----------|-------------|
| `agents/skill-eval-executor.agent.md` | Before PHASE 2 — defines how sub-agents execute test prompts and produce metrics |
| `agents/skill-eval-grader.agent.md` | Before PHASE 3a — defines expectation grading protocol and output format |
| `agents/skill-eval-comparator.agent.md` | Before PHASE 3b — defines blind A/B comparison rubric |
| `agents/skill-eval-analyzer.agent.md` | Before PHASE 3c — defines cross-eval pattern detection |
| `skills/skill-eval-runner/scripts/prepare_workspace.py` | PHASE 1 — creates iteration workspace, classifies evals, writes `iteration_config.json` and per-eval `eval_metadata.json` |
| `skills/skill-eval-runner/scripts/finalize_metrics.py` | End of PHASE 2 — canonical assembler for `outputs/metrics.json`: merges notification sidecar + debug-log telemetry into `host_telemetry`, stamps `metrics_source` |
| `skills/skill-eval-runner/scripts/assign_ab.py` | Before PHASE 3b comparators — deterministic seeded A/B assignment |
| `skills/skill-eval-runner/scripts/resolve_comparisons.py` | After PHASE 3b comparators — merges blind `ab_assignment.json` into `comparison.json` |
| `skills/skill-eval-runner/scripts/aggregate_benchmark.py` | PHASE 3c — aggregates grading + comparison files into benchmark |
| `skills/skill-eval-runner/scripts/list_evals.py` | When user asks to list available evals |
| `skills/skill-eval-runner/eval-viewer/generate_review.py` | PHASE 4 — generates HTML review report page |
| `skills/skill-eval-runner/eval-viewer/generate_progression.py` | PHASE 4 (iteration 2+) — generates cross-iteration progression report |
| [references/schemas.md](references/schemas.md) | When producing or consuming JSON files — authoritative field names for all schemas |
