---
name: assess-innersource-readiness
description: Assess a repository's readiness for InnerSource adoption using the innersource-readiness skill.
---

# Assess InnerSource Readiness for a repository.

## What you should do

1. Ask for (or confirm) the repository to assess. This can be:
   - The current workspace repository
   - A GitHub repository in `OWNER/REPO` format
   - A local path to a repository

2. Use the `innersource-readiness` skill to perform a comprehensive assessment:
   - Research the repository thoroughly (README, CONTRIBUTING, COMMUNICATION, etc.)
   - Evaluate base documentation completeness
   - Assess COMMUNICATION.md for InnerSource-specific requirements
   - Evaluate InnerSource roles (Trusted Committers, Contributors)
   - Score maturity across Transparency, Collaboration, Community, and Governance dimensions
   - Check cross-team contribution readiness
   - Evaluate discoverability

3. Generate a detailed report with:
   - Executive summary with overall readiness score
   - Detailed assessment by category
   - Remediation plan with prioritized improvements
   - Any clarifying questions for items that couldn't be reliably assessed

## Inputs

- Repository: current workspace, `OWNER/REPO`, or local path

## Output

A comprehensive InnerSource readiness assessment report including:
- Overall readiness score (0-100) and level (Not Ready/Emerging/Maturing/Ready)
- Maturity dimension scores (Transparency, Collaboration, Community, Governance)
- Key strengths and critical gaps
- Prioritized remediation recommendations
- Suggested InnerSource patterns to adopt
