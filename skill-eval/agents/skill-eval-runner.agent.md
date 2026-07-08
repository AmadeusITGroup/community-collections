---
name: Skill Eval Runner
description: "Runs evaluations for a skill — spawns executor sub-agents per test case, grades responses with LLM-as-judge, and produces an eval-viewer report. Optionally compares against a baseline run."
argument-hint: "Provide a skill name"
agents: ["skill-eval-executor", "skill-eval-grader", "skill-eval-analyzer", "skill-eval-comparator"]
user-invocable: true
---

# Skill Eval Runner

Read and follow the skill-eval-runner Skill instructions.
