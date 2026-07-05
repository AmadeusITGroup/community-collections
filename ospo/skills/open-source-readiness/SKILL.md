---
name: open-source-readiness
description: Assesses repository readiness for Open Source adoption. Use when evaluating documentation completeness, community health, governance, security posture, and license compliance. This skill performs thorough repository research before assessment and never hallucinates - it will pause and ask for clarification when information cannot be reliably inferred.
---

# Open Source Readiness Assessment

## Purpose

This skill evaluates whether a repository meets the standards required for successful Open Source adoption, based on best practices from opensource.guide, GitHub's open source resources, and industry standards.

## When to Use This Skill

- Before making a private repository public
- When evaluating a project for open source contribution
- During open source program office (OSPO) reviews
- When onboarding new maintainers to understand project health
- For periodic health checks of existing open source projects

## Critical Principles

### Research-First Approach
**ALWAYS thoroughly research the repository before making any assessments.** This includes:
1. Reading the full README.md
2. Checking all documentation files
3. Reviewing recent commit history and activity
4. Examining issue and PR patterns
5. Understanding the project's purpose and architecture

### No Hallucination Policy
**NEVER assume or fabricate information.** When you cannot reliably determine:
- Project ownership or maintainers → **PAUSE and ask**
- License type or compatibility → **PAUSE and ask**
- Security policies or practices → **PAUSE and ask**
- Governance model → **PAUSE and ask**
- Contribution requirements → **PAUSE and ask**

Use this phrase when uncertain: *"I cannot reliably determine [X] from the repository contents. Could you please clarify [specific question]?"*

---

## Organization-Level `.github` Repository

When assessing a repository hosted on GitHub, you must consider the organization's `.github` repository, which can provide **default community health files** that are inherited by all repositories in the organization.

### Understanding Inheritance

GitHub allows organizations to create a special public repository named `.github` that contains default community health files. These files are automatically used by repositories that don't have their own version. See: [GitHub Documentation on Default Community Health Files](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)

**Inheritable Files:**
| File | Can Be Inherited | Notes |
|------|------------------|-------|
| CODE_OF_CONDUCT.md | ✅ Yes | From `.github/`, root, or `docs/` in org's `.github` repo |
| CONTRIBUTING.md | ✅ Yes | From `.github/`, root, or `docs/` in org's `.github` repo |
| SECURITY.md | ✅ Yes | From `.github/`, root, or `docs/` in org's `.github` repo |
| SUPPORT.md | ✅ Yes | From `.github/`, root, or `docs/` in org's `.github` repo |
| FUNDING.yml | ✅ Yes | From `.github/` folder |
| Issue Templates | ✅ Yes | From `.github/ISSUE_TEMPLATE/` |
| PR Templates | ✅ Yes | From `.github/` folder |
| LICENSE | ❌ No | **Must be in each repository** |
| README.md | ❌ No | Must be in each repository |
| CODEOWNERS | ❌ No | Must be in each repository |

**Workflow Templates:**
Organizations can also provide workflow templates in `.github/workflow-templates/` that appear when users create new workflows. See: [GitHub Documentation on Workflow Templates](https://docs.github.com/en/actions/how-tos/reuse-automations/create-workflow-templates)

### Assessment Strategy for Remote Repositories

When the target is a **remote GitHub repository URL** (not a local folder):

1. **Extract the organization name** from the repository URL (e.g., `github.com/org-name/repo-name` → `org-name`)
2. **Clone both repositories:**
   - The target repository
   - The organization's `.github` repository (if it exists): `github.com/org-name/.github`
3. **Apply inheritance rules** when checking for files:
   - If file exists in target repo → Use target repo's version only
   - If file is missing in target repo but exists in org's `.github` → Count as present (inherited)
   - If inherited file content is generic/unclear for the specific repo → Flag for override recommendation

### Inheritance Evaluation Criteria

When a file is inherited from the organization's `.github` repository:

| Scenario | Assessment | Recommendation |
|----------|------------|----------------|
| Inherited file is specific and applicable | ✅ Count as present | None needed |
| Inherited file is generic but acceptable | ⚠️ Count as present | Consider repo-specific override |
| Inherited file causes confusion for this repo | ⚠️ Count as present with warning | **Must override** in target repo |
| No file in repo AND no org-level file | ❌ Missing | Create file |

**Confusion indicators for inherited files:**
- Security contact doesn't apply to this project type
- Contributing guidelines reference technologies not used in this repo
- Code of conduct enforcement contacts are outdated or irrelevant
- Issue templates don't match the project's issue types

---

## Assessment Workflow

### Phase 0: Organization Context Discovery (Remote Repos Only)

When assessing a remote GitHub repository URL:

```
1. Parse the repository URL to extract: organization/owner name, repository name
2. Attempt to clone the organization's .github repository: github.com/<org>/.github
3. If .github repo exists and is public:
   a. Catalog all community health files present
   b. Note workflow templates in workflow-templates/ directory
   c. Document which files will be inherited by target repo
4. If .github repo doesn't exist or is private: Proceed with target repo only
```

### Phase 1: Repository Discovery

Gather comprehensive context about the target repository:

```
1. Identify and read: README.md, CONTRIBUTING.md, LICENSE, CODE_OF_CONDUCT.md, SECURITY.md
2. Check for: .github/ directory contents (templates, workflows, CODEOWNERS)
3. For each inheritable file missing in target repo:
   a. Check if it exists in org's .github repository
   b. If inherited: Read and evaluate relevance to target repo
   c. Flag any inherited files that may cause confusion
4. Review: Recent commits (last 30 days), open issues, open PRs
5. Understand: Project purpose, technology stack, target audience
6. Note: Any ambiguities or missing information for clarification
```

### Phase 2: Documentation Assessment

Evaluate each required file against the checklist in `references/OPEN_SOURCE_CHECKLIST.md`.

**Required Files:**
| File | Status | Source | Notes |
|------|--------|--------|-------|
| README.md | ⬜ | Repo only | Must include: purpose, installation, usage, contributing link |
| LICENSE | ⬜ | Repo only | Must be OSI-approved license (cannot be inherited) |
| CONTRIBUTING.md | ⬜ | Repo / Org | Must include: how to contribute, code standards |
| CODE_OF_CONDUCT.md | ⬜ | Repo / Org | Must include: expected behavior, enforcement |
| SECURITY.md | ⬜ | Repo / Org | Must include: vulnerability reporting process |

**Source Legend:**
- **Repo only**: File must exist in the target repository
- **Repo / Org**: File can be inherited from organization's `.github` repo if not present in target repo

**When file is inherited from org's `.github` repo:**
- Mark status with 🔗 to indicate inheritance (e.g., 🔗✅)
- Evaluate if content is appropriate for this specific repository
- If content causes confusion or is not applicable, recommend override

### Phase 3: Community Health Assessment

Evaluate indicators of project health and sustainability:

**Activity Metrics:**
- Recent commits (within 30 days): ⬜
- Issues being triaged/responded to: ⬜
- PRs being reviewed: ⬜
- Multiple contributors: ⬜

**Contributor Experience:**
- Issue templates configured: ⬜ (can be inherited from org's `.github`)
- PR templates configured: ⬜ (can be inherited from org's `.github`)
- "good first issue" labels present: ⬜
- "help wanted" labels present: ⬜
- Clear path from user → contributor → maintainer: ⬜

### Phase 4: Security Assessment

Evaluate security posture and practices:

- Security policy documented: ⬜
- Vulnerability reporting process defined: ⬜
- Branch protection on main/master: ⬜
- Dependency scanning enabled: ⬜
- Secret scanning enabled: ⬜
- No exposed credentials in commit history: ⬜

### Phase 5: Governance Assessment

Evaluate project governance and sustainability:

- Maintainers/owners clearly identified: ⬜
- Decision-making process documented: ⬜
- Commit access policy defined: ⬜
- Release process documented: ⬜
- Semantic versioning followed: ⬜

### Phase 6: License Compliance

Evaluate license clarity and compatibility:

- LICENSE file present: ⬜
- License is OSI-approved: ⬜
- License type clearly identified: ⬜
- Dependencies have compatible licenses: ⬜
- No proprietary code without proper licensing: ⬜

---

## Scoring Model

See `references/SCORING_RUBRIC.md` for detailed scoring criteria.

| Category | Weight | Max Points |
|----------|--------|------------|
| Documentation | 25% | 25 |
| Community Health | 20% | 20 |
| Security | 20% | 20 |
| Governance | 15% | 15 |
| License Compliance | 20% | 20 |
| **Total** | 100% | 100 |

**Readiness Levels:**
- 🔴 **0-40: Not Ready** - Critical gaps exist, significant work required
- 🟡 **41-60: Emerging** - Basic structure in place, improvements needed
- 🟠 **61-80: Maturing** - Good foundation, refinements recommended
- 🟢 **81-100: Ready** - Meets standards for Open Source adoption

---

## Output Format

After completing the assessment, provide:

### 1. Executive Summary
- Overall readiness score and level
- Key strengths (top 3)
- Critical gaps (blocking issues)
- High-priority recommendations

### 2. Detailed Assessment
- Category-by-category breakdown
- Specific checklist item results
- Evidence/links for each finding
- **Inheritance Report** (if org's `.github` repo was analyzed):
  - Files inherited from organization level
  - Inherited files that are appropriate for this repo
  - Inherited files that need repo-specific overrides

### 3. Remediation Plan
- Prioritized list of improvements
- Template suggestions from `assets/` directory
- Estimated effort for each item

### 4. Inheritance Recommendations (if applicable)
- List inherited files that should be overridden in the target repo
- Explain why the inherited content may cause confusion
- Provide templates or guidance for creating repo-specific versions

### 5. Questions (if any)
- List any items that could not be reliably assessed
- Specific clarifying questions for the repository owner

---

## Pause Points

**STOP and ask for clarification when:**

1. **LICENSE is missing or unclear**
   - "I found [X] but cannot confirm the license type. What license should this project use?"

2. **Ownership is ambiguous**
   - "I cannot identify the project maintainers. Who are the primary maintainers of this repository?"

3. **Security practices are unclear**
   - "I don't see a security policy. Does this project have a vulnerability disclosure process I should know about?"

4. **Purpose is not documented**
   - "The README doesn't clearly explain the project's purpose. Could you describe what this project does?"

5. **Contribution process is undefined**
   - "I cannot find contribution guidelines. What is the expected process for external contributions?"

6. **Inherited file causes confusion**
   - "The [file] is inherited from the organization's .github repository, but its content [specific issue]. Should this be overridden with a repo-specific version?"

---

## References

- See `references/OPEN_SOURCE_CHECKLIST.md` for complete checklist
- See `references/SCORING_RUBRIC.md` for scoring details
- See `assets/` for remediation templates
