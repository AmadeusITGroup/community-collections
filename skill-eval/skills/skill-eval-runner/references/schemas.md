# JSON Schemas

Authoritative schema definitions for all JSON files produced and consumed by the eval framework. The eval-viewer, aggregate_benchmark.py, and agent definitions all depend on these exact field names.

**Important:** Using incorrect field names (e.g., `config` instead of `configuration`, or `assertions` instead of `expectations`) will cause silent failures in the viewer and benchmark aggregation. Always reference this document when producing JSON output.

---

## evals.json

Defines the test cases for a skill. Located at `evals/{skill-name}/evals.json`.

```json
{
  "schema_version": "1.0.0",
  "skill_name": "example-skill",
  "skill_version": "1.0.0",
  "description": "Evaluation test cases for the example skill.",
  "evals": [
    {
      "id": 1,
      "name": "import-validation-failure",
      "prompt": "The nightly import job failed with a record validation error...",
      "expected_output": "Skill identifies FM-1 with HIGH confidence...",
      "files": ["files/mock-metrics-import-duration-spike.json"],
      "expectations": [
        "Response identifies record validation failure as root cause",
        "Confidence is HIGH or >= 80"
      ]
    }
  ]
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | No | Version of the evals.json schema (e.g., `"1.0.0"`). Allows the eval-runner to detect format changes across generator versions. Omitted in legacy files — treated as `"1.0.0"`. |
| `skill_name` | string | Yes | Matches the skill's frontmatter `name` |
| `skill_version` | string | Yes | Version of the skill these evals target — compared with skill's `metadata.version` for staleness detection |
| `description` | string | No | Human-readable description of the eval set |
| `evals` | array | Yes | Array of test case objects |
| `evals[].id` | integer | Yes | Unique numeric identifier |
| `evals[].name` | string | Yes | Descriptive kebab-case name (used for workspace directory names) |
| `evals[].prompt` | string | Yes | Realistic user message or parent-agent message |
| `evals[].expected_output` | string | Yes | Human-readable description of what a correct response looks like |
| `evals[].files` | array of strings | No | Paths to input files, relative to `evals/{skill-name}/` (e.g., `files/sample.json`) |
| `evals[].expectations` | array of strings | Yes | Verifiable pass/fail checks (evaluated by eval-grader) |

**Notes:**
- Auto-generated expectations are prefixed with `[auto]` to distinguish them from human-refined ones
- The `files` paths are relative to `evals/{skill-name}/` (e.g., `files/mock-metrics-xyz.json`)
- Staleness detection: the eval-runner compares `skill_version` with the skill's `metadata.version` from its SKILL.md frontmatter. A mismatch means evals may be outdated.

---

## eval_metadata.json

Per-eval metadata written by eval-runner during PHASE 1. Located at `evals/{skill-name}/workspace/iteration-{N}/eval-{id}-{name}/eval_metadata.json`.

```json
{
  "id": 1,
  "name": "import-validation-failure",
  "prompt": "The nightly import job failed with a record validation error...",
  "expectations": [
    "Response identifies record validation failure as root cause",
    "Confidence is HIGH or >= 80"
  ],
  "files": ["files/mock-metrics-import-duration-spike.json"],
  "iteration": 2,
  "prepared_at": "2026-04-16T10:30:00Z",
  "eval_mode": "regression",
  "baseline_iteration": 1,
  "baseline_path": "../../iteration-1/eval-1-import-validation-failure",
  "previous_iteration": 1,
  "previous_path": "../../iteration-1/eval-1-import-validation-failure"
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | integer | Yes | Eval ID from evals.json |
| `name` | string | Yes | Eval name from evals.json |
| `prompt` | string | Yes | The test prompt |
| `expectations` | array of strings | Yes | Expectations to grade |
| `files` | array of strings | No | This variant's staged input copies inside its sandbox, relative to the **variant dir** (e.g. `sandbox/files/sample.log`; resolve against `eval-{id}-{name}/current_skill/`). Staged by `prepare_workspace.py` from the eval's declared `files`; the executor reads them and may edit them in place, and the grader reads their post-run state as evidence. Never the shared `evals/{skill}/files/`. Empty when the eval declares no inputs. |
| `sandbox_dir` | string | Yes | Relative path to the current_skill variant's writable sandbox root (`current_skill/sandbox`) — the skill's repository root for the run. Always present: every variant gets a sandbox even when the eval declares no input files, so a skill that only produces output still has somewhere to write. |
| `iteration` | integer | Yes | Iteration number |
| `prepared_at` | string | Yes | ISO 8601 UTC timestamp when `prepare_workspace.py` created the eval directory. Used by `finalize_metrics.py` as a fallback start time when log-based timing is unavailable. (Replaces the legacy `started_at` field.) |
| `eval_mode` | string | Yes | `"baseline"` or `"regression"`. Baseline evals run both `current_skill` and `without_skill`. Regression evals reuse `without_skill` data from the baseline iteration and compare against the previous iteration's `current_skill` (exposed as `previous_skill`). |
| `baseline_iteration` | integer | No | Latest iteration that holds a usable `without_skill/grading.json` for this eval (reused to save executors). Present only when `eval_mode` is `"regression"`. |
| `baseline_path` | string | No | Relative path from this eval directory to the baseline eval directory. Present only when `eval_mode` is `"regression"`. |
| `previous_iteration` | integer | No | Previous iteration number (N-1) whose `current_skill` response is exposed as `previous_skill` for regression comparison. Present only when `eval_mode` is `"regression"`. |
| `previous_path` | string | No | Relative path from this eval directory to the previous iteration's eval directory. Present only when `eval_mode` is `"regression"`. |

---

## metrics.json

Consolidated per-variant telemetry file, located at `evals/{skill-name}/workspace/iteration-{N}/eval-{id}-{name}/{variant}/outputs/metrics.json`. This is the **single** place where every post-execution signal for a variant lives — there is no longer a separate `execution.json`.

Three writers contribute, in order, and each owns a disjoint set of top-level keys:

1. **Executor** (`agents/skill-eval-executor.agent.md`) writes `self_report` + `user_notes` once, immediately after `response.md`. It never touches timing or tokens.
2. **Parent orchestrator** optionally drops an `outputs/notification.json` sidecar next to `metrics.json` capturing host Task-return telemetry. `finalize_metrics.py` merges it into the `notification` block and deletes the sidecar.
3. **`finalize_metrics.py`** adds `host_telemetry` (timing + tokens + log-derived tool counts + model) and the top-level `metrics_source` tag. It runs exactly once at the end of PHASE 2.

```json
{
  "self_report": {
    "tool_calls": {"read_file": 5, "create_file": 2, "run_in_terminal": 8},
    "total_tool_calls": 15,
    "total_steps": 6,
    "files_created": ["response.md"],
    "output_chars": 12450
  },
  "user_notes": {
    "skill_feedback": {
      "missing_from_skill": [
        {"topic": "No guidance on the validation-failure path when input data is partial",
         "impact": "major",
         "reference": "references/failure-modes.md#FM-1"}
      ],
      "ambiguous_instructions": [],
      "broken_references": [],
      "outdated_or_wrong": []
    },
    "response_risks": [
      {"assumption": "Spike 10:15–10:40 maps to the import window",
       "if_wrong": "Root cause points at wrong batch",
       "grounded_in": "metrics_mock_query.json timestamp range"}
    ],
    "missing_inputs": []
  },
  "notification": {
    "spawned_at": "2026-04-16T10:32:22Z",
    "returned_at": "2026-04-16T10:32:45Z",
    "total_tokens": 84852,
    "duration_ms": 23332,
    "status": "ok"
  },
  "host_telemetry": {
    "started_at": "2026-04-16T10:32:22Z",
    "completed_at": "2026-04-16T10:32:45Z",
    "duration_ms": 23332,
    "total_duration_seconds": 23.3,
    "total_tokens": 84852,
    "input_tokens": 62100,
    "output_tokens": 22752,
    "turn_count": 6,
    "ttft_ms_first_turn": 1820,
    "model": "claude-opus-4.7",
    "tool_calls": {"read_file": 5, "create_file": 2, "run_in_terminal": 8},
    "total_tool_calls": 15,
    "tool_errors": 0,
    "source": "debug_log"
  },
  "metrics_source": "debug_log"
}
```

### Top-level keys

| Key | Required | Writer | Description |
|-----|----------|--------|-------------|
| `self_report` | Yes | executor | Everything the executor can measure itself. Never overwritten; stays as the self-assessment of record even when log-derived numbers are available. |
| `user_notes` | Yes | executor | Typed, actionable skill-quality feedback. The executor is the ONLY stage that reads the skill + KB; this is how it critiques them. Never touched by the grader. |
| `notification` | No | finalize_metrics.py (merged from parent sidecar) | Present only when the parent wrote `outputs/notification.json` before the finalizer ran. Captures host-reported Task-return telemetry verbatim. |
| `host_telemetry` | Yes | finalize_metrics.py | Authoritative timing + tokens + log-derived tool metrics. Always present; the `source` sub-field indicates which backing data was available. |
| `metrics_source` | Yes | finalize_metrics.py | Single downstream tag. `"debug_log"` when `host_telemetry.tool_calls` was populated from a session log; `"self_report"` otherwise. Consumers wanting "best available" tool counts prefer `host_telemetry.total_tool_calls` when this is `"debug_log"`, else fall back to `self_report.total_tool_calls`. |

### `self_report` fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tool_calls` | object | Yes | Count per tool type using platform-specific tool names (Claude: `Read`/`Write`/`Bash`, Copilot: `read_file`/`create_file`/`run_in_terminal`). |
| `total_tool_calls` | integer | Yes | Sum of tool calls. |
| `total_steps` | integer | Yes | Number of major execution steps / turns, as observed by the executor. |
| `files_created` | array of strings | Yes | Filenames (not paths) present in `outputs/` at the moment the executor finished. Always includes `response.md`. |
| `output_chars` | integer | Yes | Byte length of `response.md` as written by the executor. |

### `user_notes` fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `skill_feedback` | object | Yes | Issues with the skill itself. Populated ONLY in with-skill mode; all four sub-lists must be empty in baseline/without-skill mode. Each sub-list is capped at 5 entries (highest impact first). |
| `skill_feedback.missing_from_skill` | array | Yes | Knowledge/guidance needed but absent from the skill or its KB. Each entry: `{topic, impact, reference}` where `impact ∈ {blocking, major, minor}`. |
| `skill_feedback.ambiguous_instructions` | array | Yes | Skill instructions that admitted multiple interpretations. Same entry shape. |
| `skill_feedback.broken_references` | array | Yes | References (links, file paths, reference-table rows) that did not resolve or were empty. Same entry shape. |
| `skill_feedback.outdated_or_wrong` | array | Yes | Statements in the skill that contradicted the actual data/tools encountered. Same entry shape. |
| `response_risks` | array | Yes | Assumptions in the response that would change the conclusion if wrong. Each entry: `{assumption, if_wrong, grounded_in}`. Populated in both modes. |
| `missing_inputs` | array of strings | Yes | File paths or data pieces referenced by the prompt but absent or empty. Populated in both modes. |

### `notification` fields

Shape is whatever the host surfaced. `finalize_metrics.py` stores the sidecar content verbatim. Common fields the harvester reads when building `host_telemetry`:

| Field | Type | Description |
|-------|------|-------------|
| `spawned_at` / `returned_at` | string | ISO 8601 UTC parent wall-clock timestamps. |
| `total_tokens` | integer | Host-reported token total, when available. |
| `duration_ms` | integer | Host-reported duration. |
| `status` | string | Free-form status string (`ok`, `error`, etc.). |

### `host_telemetry` fields

Sources, in precedence order: `debug_log` (VS Code `runSubagent-*.jsonl`) > `notification` > `wall_clock` (derived from `eval_metadata.prepared_at` + `response.md` mtime).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `started_at` | string | Yes | ISO 8601 UTC. |
| `completed_at` | string | Yes | ISO 8601 UTC. |
| `duration_ms` | integer | No | Wall-clock duration in milliseconds. |
| `total_duration_seconds` | float | No | `duration_ms / 1000`, convenience field. |
| `total_tokens` | integer | No | Populated from `notification` or `debug_log`; absent under `wall_clock`. |
| `input_tokens` / `output_tokens` | integer | No | Populated only when `source` is `debug_log`. |
| `turn_count` | integer | No | LLM turn count from `debug_log`. |
| `ttft_ms_first_turn` | integer | No | Time-to-first-token for the first turn (ms), from `debug_log`. |
| `model` | string | No | Model name(s) from `debug_log`. Comma-joined when several appear. |
| `tool_calls` | object | No | Per-tool counts from `debug_log`. When present, downstream consumers prefer this over `self_report.tool_calls`. |
| `total_tool_calls` | integer | No | Sum of log-derived tool calls. |
| `tool_errors` | integer | No | Count of tool calls that returned an error, from `debug_log`. |
| `source` | string | Yes | `"debug_log"`, `"notification"`, or `"wall_clock"`. |

**Consumed by:** `aggregate_benchmark.py` reads `host_telemetry.total_duration_seconds` / `total_tokens` / `model` / `tool_errors` and joins `self_report.total_tool_calls` / `total_steps` / `output_chars` into each per-run row. The eval-viewer reads the same layers via `run.metrics.*` (see `generate_review.py`). **The grader does NOT read this file.**

**Removed in this schema version:** `execution.json` (merged into `host_telemetry`), top-level `tool_calls` / `total_tool_calls` / `total_steps` / `output_chars` / `files_created` / `tool_errors` (moved under `self_report` or `host_telemetry`), `started_at` / `completed_at` at top level (now in `host_telemetry`), `.notification.json` hidden sidecar (replaced by visible `outputs/notification.json` consumed and deleted by the finalizer).

---

## grading.json

Output from the eval-grader agent. Located at `evals/{skill-name}/workspace/iteration-{N}/eval-{id}-{name}/{variant}/grading.json`.

> **Path is load-bearing.** `grading.json` sits at the **variant root**, as a sibling of `outputs/` — **never inside** `outputs/`. `aggregate_benchmark.py` reads it from the variant root; a misplaced file (e.g. `{variant}/outputs/grading.json`) causes a silent 0% pass rate. The grader self-derives this path from `response_path.parent.parent / "grading.json"`; `aggregate_benchmark.py` additionally hard-fails with a clear error when it detects the misplacement (see its `--fix-grading-paths` flag for auto-repair).

```json
{
  "expectations": [
    {
      "text": "Response identifies record validation failure as root cause",
      "passed": true,
      "evidence": [
        "Response states: 'The import failed due to the record validation threshold being exceeded'",
        "Conclusion section: 'Root cause: validation failure on FM-1 import batch'"
      ]
    },
    {
      "text": "Confidence is HIGH or >= 80",
      "passed": true,
      "evidence": ["Output contains 'confidence: 85'"]
    }
  ],
  "summary": {
    "passed": 5,
    "failed": 1,
    "total": 6,
    "pass_rate": 0.833
  },
  "claims": [
    {
      "claim": "The failure started at 14:02 UTC",
      "type": "factual",
      "verified": true,
      "evidence": ["Supported by mock data timestamp range"]
    }
  ],
  "eval_feedback": {
    "suggestions": [
      {
        "expectation": "Response mentions record validation",
        "reason": "Non-discriminating — any response about import processing would mention this term"
      }
    ],
    "missing": [
      {
        "expectation": "Response identifies FM-1 as the specific failure mode ID",
        "reason": "The response correctly identifies the module but no expectation tests this"
      }
    ],
    "overall": "Brief assessment of expectation coverage and quality"
  }
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `expectations` | array | Yes | Graded expectations |
| `expectations[].text` | string | Yes | The original expectation text |
| `expectations[].passed` | boolean | Yes | `true` if expectation passes, `false` if fails |
| `expectations[].evidence` | array of strings | Yes | List of quoted passages from the response supporting the verdict. One element per passage; do not concatenate quotes into a single string. Use `[]` when no relevant evidence exists (only valid when `passed` is `false`). |
| `summary` | object | Yes | Aggregate counts |
| `summary.passed` | integer | Yes | Count of passed expectations |
| `summary.failed` | integer | Yes | Count of failed expectations |
| `summary.total` | integer | Yes | Total expectations evaluated |
| `summary.pass_rate` | float | Yes | Fraction passed (0.0 to 1.0) |
| `claims` | array | No | Extracted implicit claims from the response |
| `claims[].claim` | string | Yes | The statement being verified |
| `claims[].type` | string | Yes | `"factual"`, `"process"`, or `"quality"` |
| `claims[].verified` | boolean | Yes | Whether the claim holds |
| `claims[].evidence` | array of strings | Yes | List of supporting or contradicting passages. One element per passage; do not concatenate quotes into a single string. Use `[]` when no evidence exists. |
| `eval_feedback` | object | No | Improvement suggestions for the eval expectations |
| `eval_feedback.suggestions` | array | No | Expectations that could be improved |
| `eval_feedback.missing` | array | No | Important outcomes not covered by any expectation |
| `eval_feedback.overall` | string | No | Brief assessment of eval quality |

**Only these four top-level keys.** Execution telemetry (`self_report`, `host_telemetry`, `notification`, `metrics_source`) and skill-quality feedback (`user_notes`) live in the variant's `outputs/metrics.json`; `aggregate_benchmark.py` and the eval-viewer join the two files at read time. The grader never reads or duplicates them.

---

## ab_assignment.json

Produced by `scripts/assign_ab.py` before any comparator spawns. Located at `evals/{skill-name}/workspace/iteration-{N}/eval-{id}-{name}/ab_assignment.json`.

This file records the deterministic A/B variant mapping. Comparator agents MUST NOT read it — it is consumed only by `scripts/resolve_comparisons.py` during PHASE 3b post-processing.

```json
{
  "eval_id": 1,
  "comparison_mode": "regression",
  "A": "current_skill/outputs/response.md",
  "B": "previous_skill/outputs/response.md",
  "variant_A": "current_skill",
  "variant_B": "previous_skill",
  "baseline_iteration": 1,
  "previous_iteration": 2,
  "seed": 2873142191
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `eval_id` | integer | Yes | Eval ID from `eval_metadata.json` |
| `comparison_mode` | string | Yes | `"baseline"` (pair `current_skill` vs `without_skill`) or `"regression"` (pair `current_skill` vs `previous_skill`) |
| `A` | string | Yes | Path to the response file assigned to label A (relative to the eval directory) |
| `B` | string | Yes | Path to the response file assigned to label B |
| `variant_A` | string | Yes | Resolved variant name for A: `current_skill`, `without_skill`, or `previous_skill` |
| `variant_B` | string | Yes | Resolved variant name for B |
| `baseline_iteration` | integer | No | Iteration number providing the `without_skill` response in baseline mode |
| `previous_iteration` | integer | No | Iteration number providing the `previous_skill` response in regression mode |
| `seed` | integer | Yes | Per-eval seed (`ab_seed + eval_id`) used to randomize A/B. Recorded for audit/reproduction. |

---

## comparison.json

Output from the eval-comparator agent (blind A/B comparison), located at `evals/{skill-name}/workspace/iteration-{N}/eval-{id}-{name}/comparison.json`.

The comparator writes only the blind fields (`winner`, `rubric`, `reasoning`, `notable_differences`, `output_quality`, `expectation_results`). `scripts/resolve_comparisons.py` then merges `ab_assignment.json` into this file, adding `assignment`, `winner_variant`, `comparison_mode`, `baseline_iteration`, and `previous_iteration`.

```json
{
  "assignment": {"A": "current_skill", "B": "without_skill"},
  "winner": "A",
  "winner_variant": "current_skill",
  "comparison_mode": "baseline",
  "baseline_iteration": 1,
  "reasoning": "A provides a specific root cause with supporting evidence while B gives a generic diagnosis",
  "rubric": {
    "A": {
      "content": {
        "correctness": 5,
        "completeness": 4,
        "accuracy": 5
      },
      "structure": {
        "organization": 4,
        "formatting": 5,
        "usability": 4
      },
      "content_score": 4.7,
      "structure_score": 4.3,
      "overall_score": 9.0
    },
    "B": {
      "content": {
        "correctness": 2,
        "completeness": 3,
        "accuracy": 2
      },
      "structure": {
        "organization": 3,
        "formatting": 4,
        "usability": 3
      },
      "content_score": 2.7,
      "structure_score": 2.7,
      "overall_score": 5.0
    }
  },
  "output_quality": {
    "A": {
      "score": 9,
      "strengths": ["Identifies specific module FM-1", "Cites exact error timestamps"],
      "weaknesses": ["Does not suggest preventive measures"]
    },
    "B": {
      "score": 5,
      "strengths": ["Correct general area identified"],
      "weaknesses": ["No specific root cause", "Missing confidence level"]
    }
  },
  "expectation_results": {
    "A": {
      "passed": 4,
      "total": 5,
      "pass_rate": 0.80,
      "details": [
        {"text": "expectation text", "passed": true, "evidence": ["first quoted passage", "second quoted passage"]}
      ]
    },
    "B": {
      "passed": 2,
      "total": 5,
      "pass_rate": 0.40,
      "details": [
        {"text": "expectation text", "passed": false, "evidence": []}
      ]
    }
  }
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `assignment` | object | Yes | Maps blind labels to variant names. Keys are `"A"` and `"B"`; values are `"current_skill"`, `"without_skill"`, or `"previous_skill"`. Written by `resolve_comparisons.py`. |
| `winner` | string | Yes | `"A"`, `"B"`, or `"TIE"` — blind verdict from the comparator |
| `winner_variant` | string | Yes | Resolved variant: `"current_skill"`, `"without_skill"`, `"previous_skill"`, or `"tie"`. Written by `resolve_comparisons.py`. |
| `comparison_mode` | string | Yes | `"baseline"` (pair current_skill vs without_skill) or `"regression"` (pair current_skill vs previous_skill). Written by `resolve_comparisons.py`. |
| `baseline_iteration` | integer | No | Iteration number providing `without_skill`. Present when `comparison_mode` is `"baseline"`. |
| `previous_iteration` | integer | No | Iteration number providing `previous_skill`. Present when `comparison_mode` is `"regression"`. |
| `reasoning` | string | Yes | Explanation of why the winner was chosen |
| `rubric` | object | Yes | Structured scores for each output |
| `rubric.{A\|B}.content` | object | Yes | Content scores: `correctness`, `completeness`, `accuracy` (each 1-5) |
| `rubric.{A\|B}.structure` | object | Yes | Structure scores: `organization`, `formatting`, `usability` (each 1-5) |
| `rubric.{A\|B}.content_score` | float | Yes | Average of content sub-scores |
| `rubric.{A\|B}.structure_score` | float | Yes | Average of structure sub-scores |
| `rubric.{A\|B}.overall_score` | float | Yes | Combined score (1-10), weighted: content 70% + structure 30% |
| `output_quality` | object | Yes | Qualitative assessment per output |
| `output_quality.{A\|B}.score` | integer | Yes | 1-10 rating (should match rubric `overall_score`) |
| `output_quality.{A\|B}.strengths` | array of strings | Yes | Positive aspects |
| `output_quality.{A\|B}.weaknesses` | array of strings | Yes | Issues or shortcomings |
| `expectation_results` | object | No | Only present if expectations were provided |
| `expectation_results.{A\|B}.passed` | integer | Yes | Count of expectations that passed |
| `expectation_results.{A\|B}.total` | integer | Yes | Total expectations |
| `expectation_results.{A\|B}.pass_rate` | float | Yes | Fraction passed (0.0 to 1.0) |
| `expectation_results.{A\|B}.details` | array | Yes | Per-expectation results: `text` (string), `passed` (boolean), `evidence` (array of strings — one quoted passage per element; `[]` when none) |

---

## benchmark.json

Aggregated benchmark produced by `aggregate_benchmark.py`. Located at `evals/{skill-name}/workspace/iteration-{N}/benchmark.json`.

```json
{
  "metadata": {
    "skill_name": "example-skill",
    "skill_version": "1.5.0",
    "timestamp": "2026-04-16T10:45:30Z",
    "evals_run": [1, 2, 3, 4, 5, 6, 7, 8]
  },
  "runs": [
    {
      "eval_id": 1,
      "eval_name": "import-validation-failure",
      "configuration": "current_skill",
      "result": {
        "pass_rate": 0.833,
        "passed": 5,
        "failed": 1,
        "total": 6,
        "time_seconds": 42.5,
        "tokens": 3800,
        "total_tool_calls": 15,
        "total_steps": 6,
        "tool_errors": 0,
        "output_chars": 12450,
        "metrics_source": "debug_log",
        "source": "debug_log"
      },
      "expectations": [
        {"text": "...", "passed": true, "evidence": ["first passage", "second passage"]}
      ]
    }
  ],
  "run_summary": {
    "current_skill": {
      "pass_rate": {"mean": 0.85, "stddev": 0.05, "min": 0.80, "max": 0.90},
      "time_seconds": {"mean": 45.0, "stddev": 12.0, "min": 32.0, "max": 58.0},
      "tokens": {"mean": 3800.0, "stddev": 400.0, "min": 3200.0, "max": 4100.0}
    },
    "without_skill": {
      "pass_rate": {"mean": 0.35, "stddev": 0.08, "min": 0.28, "max": 0.45},
      "time_seconds": {"mean": 32.0, "stddev": 8.0, "min": 24.0, "max": 42.0},
      "tokens": {"mean": 2100.0, "stddev": 300.0, "min": 1800.0, "max": 2500.0}
    },
    "delta": {
      "pass_rate": "+0.50",
      "time_seconds": "+13.0",
      "tokens": "+1700.0"
    }
  },
  "comparisons": {
    "current_skill_wins": 5,
    "without_skill_wins": 1,
    "ties": 2
  },
  "per_eval_comparisons": [
    {
      "eval_id": 1,
      "eval_name": "import-validation-failure",
      "comparison_mode": "baseline",
      "winner_variant": "current_skill",
      "winner": "A",
      "reasoning": "A provides a specific root cause with evidence; B is generic.",
      "assignment": {"A": "current_skill", "B": "without_skill"},
      "rubric_scores": {"A": 9.0, "B": 5.0},
      "baseline_iteration": 1,
      "previous_iteration": null,
      "per_expectation": [
        {
          "text": "Response identifies record validation failure as root cause",
          "current_skill": {"passed": true, "evidence": ["first passage", "second passage"]},
          "without_skill": {"passed": false, "evidence": []}
        }
      ]
    }
  ],
  "notes": [
    {
      "category": "non_discriminating",
      "text": "Expectation 'Response identifies root cause' is non-discriminating: passes 8/8 in both configurations.",
      "eval_refs": [],
      "metrics": { "current_skill_rate": "8/8", "without_skill_rate": "8/8" }
    },
    {
      "category": "skill_value",
      "text": "Eval #3 shows the largest skill benefit: current_skill passes 5/5 vs 1/5 without.",
      "eval_refs": [3],
      "metrics": { "current_skill": "5/5", "without_skill": "1/5" }
    }
  ],
  "skill_feedback_rollup": {
    "totals": {
      "missing_from_skill": 3,
      "ambiguous_instructions": 1,
      "broken_references": 0,
      "outdated_or_wrong": 0
    },
    "by_impact": {"blocking": 1, "major": 2, "minor": 1},
    "top_references": [
      {"reference": "references/failure-modes.md#FM-1", "count": 2, "eval_ids": [1, 4]}
    ],
    "items": [
      {"category": "missing_from_skill",
       "topic": "No guidance on ratio-failure path when AF data is partial",
       "impact": "major",
       "reference": "references/failure-modes.md#FM-1",
       "eval_id": 1,
       "eval_name": "import-validation-failure"}
    ],
    "response_risks": [
      {"assumption": "…", "if_wrong": "…", "grounded_in": "…",
       "eval_id": 1, "eval_name": "…", "variant": "current_skill"}
    ],
    "missing_inputs": [
      {"input": "metrics_mock_query.json", "eval_id": 2, "eval_name": "…", "variant": "current_skill"}
    ],
    "delta_vs_previous": {
      "missing_from_skill": -2,
      "ambiguous_instructions": 0,
      "broken_references": 0,
      "outdated_or_wrong": 0
    }
  }
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `metadata` | object | Yes | Run metadata |
| `metadata.skill_name` | string | Yes | Skill being evaluated |
| `metadata.skill_version` | string | No | Version of the skill that was actually evaluated, captured from its `metadata.version` at PREPARE time. Frozen for the lifetime of the iteration so re-rendering an old report shows the version that produced the responses, not whatever the skill says today. Absent when the evaluated skill has no `metadata.version`. |
| `metadata.timestamp` | string | Yes | ISO 8601 timestamp |
| `metadata.evals_run` | array of integers | Yes | Eval IDs included in this benchmark |
| `metadata.iteration` | integer | No | Current iteration number. Absent in legacy benchmarks. |
| `metadata.comparison_mode` | string | No | `"baseline"`, `"regression"`, or `"mixed"`. Absent in legacy benchmarks (treat as `"baseline"`). |
| `metadata.baseline_iteration` | integer | No | Latest iteration used to source `without_skill` data. Present only when `comparison_mode` is `"regression"` or `"mixed"`. |
| `metadata.previous_iteration` | integer | No | Previous iteration (N-1) used for regression deltas. Present only when `comparison_mode` is `"regression"` or `"mixed"`. |
| `metadata.new_evals` | array of integers | No | Eval IDs that are new in this iteration (run full baseline). Present only in `"mixed"` mode. |
| `runs` | array | Yes | Individual run results |
| `runs[].eval_id` | integer | Yes | Eval ID |
| `runs[].eval_name` | string | Yes | Eval name (used as section header in viewer) |
| `runs[].configuration` | string | Yes | One of `"current_skill"`, `"without_skill"`, or `"previous_skill"` (viewer uses these exact strings). `previous_skill` rows appear only in regression iterations and carry N-1's `current_skill` metrics. |
| `runs[].source_iteration` | integer | No | Present when the run's data was sourced from a different iteration: baseline iteration for reused `without_skill`; N-1 for `previous_skill`. |
| `runs[].result` | object | Yes | Nested result metrics |
| `runs[].result.pass_rate` | float | Yes | 0.0 to 1.0 |
| `runs[].result.passed` | integer | Yes | Count of passed expectations |
| `runs[].result.failed` | integer | Yes | Count of failed expectations |
| `runs[].result.total` | integer | Yes | Total expectations |
| `runs[].result.time_seconds` | float | Yes | Execution time |
| `runs[].result.tokens` | integer | Yes | Token usage |
| `runs[].result.total_tool_calls` | integer | No | Sum of tool calls (surfaced for analyzer) |
| `runs[].result.total_steps` | integer | No | Turn count (surfaced for analyzer) |
| `runs[].result.tool_errors` | integer | No | Tool-call error count (surfaced for analyzer) |
| `runs[].result.output_chars` | integer | No | Response byte count (surfaced for analyzer) |
| `runs[].result.metrics_source` | string | No | Top-level `metrics.json.metrics_source` tag: `"debug_log"` or `"self_report"` |
| `runs[].result.source` | string | No | Provenance of `host_telemetry`: `debug_log`, `notification`, or `wall_clock` |
| `runs[].result.model` | string | No | Model name from `host_telemetry` when available (debug_log source only) |
| `runs[].source_iteration` | integer | No | The iteration this run's data was sourced from. Absent or equal to current iteration for fresh runs. Different when `without_skill` is reused from a baseline iteration. |
| `runs[].expectations` | array | Yes | Copied from grading.json: `text` (string), `passed` (boolean), `evidence` (array of strings — one quoted passage per element) |
| `run_summary` | object | Yes | Aggregate stats per configuration |
| `run_summary.{config}` | object | Yes | Contains `pass_rate`, `time_seconds`, `tokens` objects. `config` is `current_skill`, `without_skill`, or `previous_skill`. The `previous_skill` bucket is present only when regression evals contributed runs in this iteration. |
| `run_summary.{config}.{metric}` | object | Yes | Contains `mean`, `stddev`, `min`, `max` |
| `run_summary.delta` | object | Yes | Differences (current_skill minus without_skill) as formatted strings |
| `run_summary.regression_delta` | object | No | Differences between current iteration's `current_skill` and previous iteration's `current_skill`. Present only when `comparison_mode` is `"regression"` or `"mixed"`. Contains `pass_rate`, `time_seconds`, `tokens` as formatted strings (e.g., `"+0.05"`). |
| `comparisons` | object | Yes | Blind comparison tallies |
| `comparisons.current_skill_wins` | integer | Yes | Number of baseline evals where comparator preferred `current_skill` |
| `comparisons.without_skill_wins` | integer | Yes | Number of baseline evals where comparator preferred `without_skill` |
| `comparisons.ties` | integer | Yes | Number of baseline ties |
| `comparisons.current_wins` | integer | No | Number of regression evals where current `current_skill` was preferred over `previous_skill`. Present only when regression comparisons exist. |
| `comparisons.previous_wins` | integer | No | Number of regression evals where `previous_skill` was preferred. Present only when regression comparisons exist. |
| `comparisons.regression_ties` | integer | No | Number of regression comparison ties. Present only when regression comparisons exist. |
| `per_eval_comparisons` | array | Yes | Per-eval comparator verdicts surfaced for the analyzer. Each entry contains `eval_id`, `eval_name`, `comparison_mode`, `winner_variant`, `winner`, `reasoning`, `assignment`, `rubric_scores` (A/B), `baseline_iteration`, `previous_iteration`, and `per_expectation` (per-expectation cross-variant pass/evidence breakdown). |
| `contradictions` | array | Yes | Evals where the grader `pass_rate` and the blind comparator disagree by at least 0.20 in favor of the opposite side. Each entry has `eval_id`, `eval_name`, `comparison_mode`, `current_skill_pass_rate`, `alternate_pass_rate`, `alternate_variant`, `grader_preferred`, `comparator_winner`, `rubric_scores` (keyed by variant), `reasoning`, and `severity` (`blocking`/`major`/`minor`). Sorted by severity then absolute gap. |
| `skill_regressions` | object | Yes | Evals where the blind comparator preferred the alternate variant over `current_skill`. Two buckets: `vs_baseline` (baseline-mode evals where `without_skill` won) and `vs_previous` (regression-mode evals where `previous_skill` won). Each entry has `eval_id`, `eval_name`, `current_pass_rate`, `alternate_pass_rate`, `alternate_variant`, `pass_rate_delta`, `severity`, `comparator_reasoning`. Both buckets sorted by `pass_rate_delta` ascending (worst regressions first). |
| `notes` | array of objects | Yes | Structured analyzer observations (may be empty before analyzer runs). Each object has `category`, `text`, and optional `eval_refs` and `metrics`. Legacy string entries are normalized to `{ "category": "observation", "text": "..." }` by `aggregate_benchmark.py`. |
| `notes[].category` | string | Yes | One of: `regression`, `improvement`, `skill_hurts`, `new_eval`, `cost_saving`, `non_discriminating`, `skill_value`, `contradiction`, `skill_feedback`, `observation` |
| `notes[].text` | string | Yes | Human-readable observation grounded in data |
| `notes[].eval_refs` | array of integers | No | Eval IDs referenced by this observation |
| `notes[].metrics` | object | No | Freeform key-value data supporting the observation |
| `skill_feedback_rollup` | object | No | Aggregated executor-produced skill feedback across all evals in this iteration. Empty category totals when no executor flagged issues. |
| `skill_feedback_rollup.totals` | object | No | Integer counts per skill-feedback category: `missing_from_skill`, `ambiguous_instructions`, `broken_references`, `outdated_or_wrong`. |
| `skill_feedback_rollup.by_impact` | object | No | Integer counts keyed by impact level: `blocking`, `major`, `minor`. |
| `skill_feedback_rollup.by_impact_items` | object | No | Items grouped by impact level (`blocking`/`major`/`minor`), deduped on `(category, topic)`. Each entry has `category`, `topic`, `reference`, `eval_ids`, `eval_names`. Sorted by eval-fan-out desc. Consumed by the HTML report and the analyzer as a scan-friendly view. |
| `skill_feedback_rollup.top_references` | array | No | Top 10 most-flagged `reference` strings with `{reference, count, eval_ids}`. Sort: count desc. |
| `skill_feedback_rollup.items` | array | No | Flat list of every skill_feedback entry with `{category, topic, impact, reference, eval_id, eval_name}`. Sourced from `current_skill/outputs/metrics.json.user_notes.skill_feedback` only. |
| `skill_feedback_rollup.response_risks` | array | No | Flat list of executor-declared response risks from all variants with `{assumption, if_wrong, grounded_in, eval_id, eval_name, variant}`. |
| `skill_feedback_rollup.missing_inputs` | array | No | Flat list of missing-input reports with `{input, eval_id, eval_name, variant}`. |
| `skill_feedback_rollup.delta_vs_previous` | object | No | Signed integer deltas per category (current totals minus previous iteration's totals). Absent when no `--previous-iteration` was supplied. |

**Critical:** The `configuration` field must use the exact strings `"current_skill"` or `"without_skill"`. The viewer uses these for grouping and color coding. Regression data lives in `per_eval_comparisons` (keyed by `winner_variant`), not in `runs`.

---

## files/*

Input files for reproducible testing. Located at `evals/{skill-name}/files/`.

These can be any format — mock API responses, sample documents, configuration snippets. For mock observability data, a common structure is:

```json
{
  "description": "Mock metrics response showing import duration spike",
  "query": "service=import-pipeline | stats avg(import_duration) as avg_duration by _time span=5m",
  "time_range": {
    "earliest": "2026-04-03T10:00:00Z",
    "latest": "2026-04-03T11:00:00Z"
  },
  "results": [
    {"_time": "2026-04-03T10:00:00Z", "avg_duration": 45.2},
    {"_time": "2026-04-03T10:15:00Z", "avg_duration": 189.4}
  ]
}
```

**Not auto-generated:** Input files require domain expertise and are created by humans during eval refinement.

**Naming convention:** Descriptive kebab-case filenames (e.g., `mock-metrics-import-duration-spike.json`, `sample-config.yaml`).

---

## iteration_config.json

Written by the eval-runner during PHASE 1 at the iteration root. Single source of truth for the iteration's mode. Located at `evals/{skill-name}/workspace/iteration-{N}/iteration_config.json`.

Always written for every iteration. For iteration 1, `mode` is `"baseline"` and all evals are classified as `new`. Legacy workspaces without this file are treated as baseline mode for backward compatibility.

```json
{
  "iteration": 3,
  "mode": "mixed",
  "ab_seed": 2873142190,
  "skill_version": "1.5.0",
  "baseline_iteration": 1,
  "baseline_path": "../iteration-1",
  "previous_iteration": 2,
  "previous_path": "../iteration-2",
  "eval_classification": {
    "existing": [1, 2, 3],
    "new": [9, 10]
  },
  "total_executors": 7,
  "skipped_without_skill": 3
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `iteration` | integer | Yes | Current iteration number |
| `mode` | string | Yes | `"baseline"` (iteration 1 or all evals are new), `"regression"` (all evals have existing baselines), or `"mixed"` (some new, some existing) |
| `ab_seed` | integer | Yes | 32-bit unsigned seed used by `assign_ab.py` to deterministically randomize A/B assignment. The per-eval RNG is `random.Random(ab_seed + eval_id)`. Re-running `assign_ab.py` with the same `iteration_config.json` produces identical assignments. |
| `git_status_baseline` | array of strings | No | Sorted repo-root-relative paths that `git status --porcelain` reported as already changed/untracked at PREPARE (before executors ran). `finalize_metrics.py` re-runs `git status` post-run and warns loudly about any path that became dirty *outside* the gitignored per-variant `sandbox/` — catching a skill that escaped isolation and wrote into the real repo tree. Empty list when the repo was clean (or not a git work tree). Absent in legacy iterations (check skipped). |
| `skill_version` | string | No | Snapshot of the evaluated skill's `metadata.version` at PREPARE time. Forwarded into `benchmark.json` so the report shows the version that was actually evaluated. Absent when the skill has no `metadata.version`. |
| `baseline_iteration` | integer | No | **Latest** iteration that holds usable `without_skill/grading.json` data to reuse. May be any prior iteration — not necessarily N-1. Absent when `mode` is `"baseline"`. |
| `baseline_path` | string | No | Relative path from this iteration directory to the baseline iteration directory. Absent when `mode` is `"baseline"`. |
| `previous_iteration` | integer | No | Previous iteration number (N-1). Used by `assign_ab.py` to pair `current_skill` vs `previous_skill` for regression comparisons, and by `aggregate_benchmark.py` (`--previous-iteration`) for regression deltas. Absent when `mode` is `"baseline"`. |
| `previous_path` | string | No | Relative path from this iteration directory to the previous iteration directory. Absent when `mode` is `"baseline"`. |
| `eval_classification` | object | Yes | Classification of eval IDs |
| `eval_classification.existing` | array of integers | Yes | Eval IDs that have valid baselines (usable `without_skill/grading.json`) in the baseline iteration |
| `eval_classification.new` | array of integers | Yes | Eval IDs without baselines (need full `current_skill` + `without_skill` runs) |
| `total_executors` | integer | Yes | Total executor sub-agents to spawn: `2 × count(new) + 1 × count(existing)` |
| `skipped_without_skill` | integer | Yes | Count of without_skill runs skipped (equals `count(existing)`) |

**Note on baseline vs previous:** `baseline_iteration` answers *"where can I reuse `without_skill` data?"* — it points at the most recent iteration that ran the without-skill arm for these eval IDs. `previous_iteration` answers *"what should I regress against?"* — it is always N−1 and anchors `previous_skill` for A/B comparison. They are almost always different once iteration 3+ rolls around: baseline stays pinned at 1, while previous advances.

**Mode determination logic:**
- Iteration 1 → `"baseline"`
- Iteration 2+ with all evals having baselines → `"regression"`
- Iteration 2+ with some new evals → `"mixed"`

---

## Variant vocabulary (normative)

All variant names used across `iteration_config.json`, `eval_metadata.json`, `ab_assignment.json`, `comparison.json`, and `benchmark.json` come from this fixed set:

| Variant | Meaning | Lives in |
|---------|---------|----------|
| `current_skill` | Agent runs the skill under test at its current version. | `eval-*/current_skill/` of the current iteration |
| `without_skill` | Agent runs with no skill loaded (no-skill baseline). | `eval-*/without_skill/` of the current iteration **or** of `baseline_iteration` (reused) |
| `previous_skill` | The previous iteration's `current_skill` response, exposed as a comparison variant. | `eval-*/current_skill/` of `previous_iteration` (N-1) |

`baseline_iteration` and `previous_iteration` are orthogonal:

- `baseline_iteration` = **where `without_skill` data can be reused.** Typically sticky at 1 for many iterations; only advances when the grading schema changes or expectations drift.
- `previous_iteration` = **what the regression comparator regresses against.** Always N−1.

`comparison_mode` selects which variant pair the comparator sees:

- `baseline` → `current_skill` vs `without_skill`
- `regression` → `current_skill` vs `previous_skill`
