---
name: FourSight Code Review
description: "Orchestrates a multi-agents PR review by dispatching four specialized subagents — QA, Technical Debt, Functional, and Architecture — each acting as a distinct expert persona, then consolidates their findings into a single prioritized report. Use when reviewing pull requests, checking test quality, detecting tech debt, validating functional completeness, or verifying architectural consistency."
argument-hint: "Provide a PR URL, PR number, or branch name to review"
agents: ["Code Review - QA", "Code Review - Technical Debt", "Code Review - Functional", "Code Review - Architecture"]
model: Claude Opus 4.6 (copilot)
user-invocable: true
---

Read and follow the foursight-code-review Skill instructions.
