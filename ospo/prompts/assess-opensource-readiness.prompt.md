---
name: assess-opensource-readiness
description: Assess a repository's readiness for Open Source adoption using the open-source-readiness skill.
---

# Assess Open Source Readiness for a repository.

## What you should do

1. Ask for (or confirm) the repository to assess. This can be:
   - The current workspace repository
   - A GitHub repository in `OWNER/REPO` format
   - A local path to a repository

2. Use the `open-source-readiness` skill to perform a comprehensive assessment:
   - Research the repository thoroughly (README, CONTRIBUTING, LICENSE, etc.)
   - Evaluate documentation completeness
   - Assess community health indicators
   - Evaluate security posture
   - Check governance and maintainer clarity
   - Verify license compliance

3. Generate a detailed report with:
   - Executive summary with overall readiness score
   - Detailed assessment by category
   - Remediation plan with prioritized improvements
   - Any clarifying questions for items that couldn't be reliably assessed

## Inputs

- Repository: current workspace, `OWNER/REPO`, or local path

## Output

A comprehensive Open Source readiness assessment report including:
- Overall readiness score (0-100) and level (Not Ready/Emerging/Maturing/Ready)
- Category scores (Documentation, Community Health, Security, Governance, License Compliance)
- Key strengths and critical gaps
- Prioritized remediation recommendations
- Template suggestions for missing documentation
