---
name: innersource-readiness
description: Assesses repository readiness for InnerSource adoption within an organization. Use when evaluating cross-team contribution readiness, internal documentation, communication channels, governance, and maturity across Transparency, Collaboration, Community, and Governance dimensions. This skill performs thorough repository research before assessment and never hallucinates - it will pause and ask for clarification when information cannot be reliably inferred.
---

# InnerSource Readiness Assessment

## Purpose

This skill evaluates whether a repository meets the standards required for successful InnerSource adoption, based on best practices from InnerSource Commons patterns (https://patterns.innersourcecommons.org/), the Common Requirements pattern, and industry standards.

InnerSource applies open source collaboration practices within an organization, enabling cross-team contributions while respecting internal constraints like security, compliance, and organizational structure.

## When to Use This Skill

- Before opening a team's codebase for cross-team contributions
- When evaluating a project for InnerSource program inclusion
- During InnerSource program office reviews
- When onboarding Trusted Committers
- For periodic health checks of existing InnerSource projects
- When transitioning from siloed to collaborative development

## Critical Principles

### Research-First Approach
**ALWAYS thoroughly research the repository before making any assessments.** This includes:
1. Reading the full README.md and understanding the project context
2. Checking all documentation files including COMMUNICATION.md
3. Reviewing recent commit history and cross-team contribution patterns
4. Examining issue and PR patterns for external contributor participation
5. Understanding the project's organizational context and stakeholders

### No Hallucination Policy
**NEVER assume or fabricate information.** When you cannot reliably determine:
- Project ownership or Trusted Committers → **PAUSE and ask**
- Cross-team contribution policies → **PAUSE and ask**
- Internal communication channels → **PAUSE and ask**
- Organizational constraints or approvals → **PAUSE and ask**
- Roadmap or planning visibility → **PAUSE and ask**

Use this phrase when uncertain: *"I cannot reliably determine [X] from the repository contents. Could you please clarify [specific question]?"*

---

## InnerSource vs Open Source: Key Differences

| Aspect | Open Source | InnerSource |
|--------|-------------|-------------|
| **Audience** | Global public | Organization employees |
| **Discovery** | GitHub/package registries | Internal portal, wiki, catalog |
| **Communication** | Public channels | Internal Slack/Teams (archived) |
| **Legal** | OSI licenses | InnerSource license (optional) |
| **Security** | Public vulnerability disclosure | Private reporting channels |
| **Governance** | Community-driven | May require management approval |
| **Contribution Time** | Personal/sponsored | Requires manager approval |
| **Metrics** | Public (stars, forks) | Internal tracking, gamification |

---

## Organization-Level `.github` Repository

When assessing a repository hosted on GitHub (including GitHub Enterprise), you must consider the organization's `.github` repository, which can provide **default community health files** that are inherited by all repositories in the organization.

### Understanding Inheritance

GitHub allows organizations to create a special public repository named `.github` that contains default community health files. These files are automatically used by repositories that don't have their own version. See: [GitHub Documentation on Default Community Health Files](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)

**Inheritable Files:**
| File | Can Be Inherited | Notes |
|------|------------------|-------|
| CODE_OF_CONDUCT.md | ✅ Yes | From `.github/`, root, or `docs/` in org's `.github` repo |
| CONTRIBUTING.md | ✅ Yes | From `.github/`, root, or `docs/` in org's `.github` repo |
| SECURITY.md | ✅ Yes | From `.github/`, root, or `docs/` in org's `.github` repo |
| SUPPORT.md | ✅ Yes | From `.github/`, root, or `docs/` in org's `.github` repo |
| Issue Templates | ✅ Yes | From `.github/ISSUE_TEMPLATE/` |
| PR Templates | ✅ Yes | From `.github/` folder |
| COMMUNICATION.md | ❌ No | **InnerSource-specific, must be in each repository** |
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

**Confusion indicators for inherited files (InnerSource context):**
- Contributing guidelines don't mention cross-team contribution process
- Security contact doesn't apply to this project's compliance requirements
- Code of conduct enforcement contacts are not relevant for internal teams
- Issue templates don't support InnerSource contribution patterns
- No mention of Trusted Committer roles or 30-day warranty

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
   d. Check if org-level files support InnerSource patterns
4. If .github repo doesn't exist or is private: Proceed with target repo only
```

### Phase 1: Repository Discovery

Gather comprehensive context about the target repository:

```
1. Identify and read: README.md, CONTRIBUTING.md, COMMUNICATION.md, CODE_OF_CONDUCT.md
2. Check for: .github/ directory contents, CODEOWNERS, internal documentation links
3. For each inheritable file missing in target repo:
   a. Check if it exists in org's .github repository
   b. If inherited: Read and evaluate relevance to target repo
   c. Evaluate if inherited content supports InnerSource practices
   d. Flag any inherited files that may cause confusion
4. Review: Recent commits, cross-team contributions, issue/PR patterns
5. Understand: Project purpose, owning team, consuming teams, stakeholders
6. Identify: Trusted Committers, contribution approval process
7. Note: Any ambiguities or missing information for clarification
```

### Phase 2: Base Documentation Assessment

InnerSource requires the same base documentation as Open Source, with additional internal context.

**Required Files:**
| File | Status | Source | InnerSource-Specific Requirements |
|------|--------|--------|-----------------------------------|
| README.md | ⬜ | Repo only | Include owning team, internal contacts, business context |
| CONTRIBUTING.md | ⬜ | Repo / Org | Cross-team contribution process, approval requirements |
| COMMUNICATION.md | ⬜ | Repo only | **InnerSource-specific** - internal channels, escalation |
| CODE_OF_CONDUCT.md | ⬜ | Repo / Org | May reference organizational policies |
| SECURITY.md | ⬜ | Repo / Org | Internal vulnerability reporting process |

**Source Legend:**
- **Repo only**: File must exist in the target repository (cannot be inherited)
- **Repo / Org**: File can be inherited from organization's `.github` repo if not present in target repo

**When file is inherited from org's `.github` repo:**
- Mark status with 🔗 to indicate inheritance (e.g., 🔗✅)
- Evaluate if content supports InnerSource practices (cross-team contribution, TC roles, etc.)
- If content doesn't address InnerSource needs, recommend override

**Note:** COMMUNICATION.md is InnerSource-specific and should always be in the target repository, as it contains project-specific internal communication channels and escalation paths.

### Phase 3: COMMUNICATION.md Assessment (InnerSource-Specific)

This file is critical for InnerSource success. Evaluate:

**Incoming Communication (how others reach you):**
- How to report bugs: ⬜
- How to follow up on PRs: ⬜
- Feature request process: ⬜
- Documentation questions: ⬜
- Escalation paths: ⬜

**Outgoing Communication (how you inform others):**
- Planned outage notifications: ⬜
- Feature release announcements: ⬜
- Code freeze notifications: ⬜
- Breaking change alerts: ⬜
- Roadmap updates: ⬜

### Phase 4: InnerSource Roles Assessment

Evaluate the presence and clarity of InnerSource roles:

**Trusted Committers:**
- Trusted Committers identified and listed: ⬜
- TC responsibilities documented: ⬜
- Path to becoming a TC defined: ⬜
- TC availability/response expectations: ⬜

**Contributors:**
- Contributor expectations documented: ⬜
- Cross-team contribution examples exist: ⬜
- 30-day warranty pattern considered: ⬜
- Contribution recognition process: ⬜

### Phase 5: InnerSource Maturity Assessment

Evaluate the project across the four InnerSource maturity dimensions (Levels 0-3):

#### Transparency Dimension

**Plans & Products:**
| Level | Criteria | Status |
|-------|----------|--------|
| 0 | No disclosure of plans | ⬜ |
| 1 | Visible roadmap to stakeholders | ⬜ |
| 2 | Shared roadmaps with contribution rules (not standardized) | ⬜ |
| 3 | Standardized roadmap sharing with clear contribution guidelines | ⬜ |

**Development Process & Tools:**
| Level | Criteria | Status |
|-------|----------|--------|
| 0 | Siloed development team | ⬜ |
| 1 | Shared repository internally, no standardized CI | ⬜ |
| 2 | Shared repository with corporate CI, code review defined | ⬜ |
| 3 | Consistent CI/CD, code review by internal and external teams | ⬜ |

**Decisions:**
| Level | Criteria | Status |
|-------|----------|--------|
| 0 | Decisions withheld | ⬜ |
| 1 | Materials available after decisions finalized | ⬜ |
| 2 | Involvement in most decisions as they unfold | ⬜ |
| 3 | Standard collective decision-making process | ⬜ |

#### Collaboration Dimension

**Communication Channels:**
| Level | Criteria | Status |
|-------|----------|--------|
| 0 | No established channels | ⬜ |
| 1 | Channels being established | ⬜ |
| 2 | Established guidelines and training | ⬜ |
| 3 | Official platforms with leader participation | ⬜ |

**Contribution Culture:**
| Level | Criteria | Status |
|-------|----------|--------|
| 0 | Completely siloed | ⬜ |
| 1 | Occasional collaboration, perceived as "too difficult" | ⬜ |
| 2 | Active collaboration seeking | ⬜ |
| 3 | Internal and external collaboration as standard practice | ⬜ |

#### Community Dimension

**Sharing Policies:**
| Level | Criteria | Status |
|-------|----------|--------|
| 0 | No sharing culture | ⬜ |
| 1 | Some define values (unsupported) | ⬜ |
| 2 | Documented shared visions, codes of conduct | ⬜ |
| 3 | Shared values inform all decisions | ⬜ |

**Engagement:**
| Level | Criteria | Status |
|-------|----------|--------|
| 0 | Low engagement | ⬜ |
| 1 | Comfortable in familiar domains | ⬜ |
| 2 | Comfortable sharing without fear | ⬜ |
| 3 | Proactive, shared consciousness | ⬜ |

#### Governance Dimension

**Rewards & Recognition:**
| Level | Criteria | Status |
|-------|----------|--------|
| 0 | No rewards for collaboration | ⬜ |
| 1 | Leaders encouraged to reward (no process) | ⬜ |
| 2 | Standard processes for rewarding collaboration | ⬜ |
| 3 | Community-defined rewards | ⬜ |

**InnerSource Roles:**
| Level | Criteria | Status |
|-------|----------|--------|
| 0 | No specific roles | ⬜ |
| 1 | Technical reference members, contributor role | ⬜ |
| 2 | InnerSource Officer, Trusted Committer role defined | ⬜ |
| 3 | Evangelists, Community Managers, non-technical contributors | ⬜ |

### Phase 6: Cross-Team Contribution Readiness

Evaluate readiness for contributions from other teams:

- Manager approval process documented: ⬜
- Time allocation for contributions acknowledged: ⬜
- Cross-team onboarding process exists: ⬜
- Development environment setup documented: ⬜
- Testing requirements clear: ⬜
- Review SLAs defined: ⬜

### Phase 7: Discoverability Assessment

Evaluate how easily other teams can find and understand this project:

- Listed in InnerSource portal/catalog: ⬜
- Searchable by technology/domain tags: ⬜
- Clear "what this project does" summary: ⬜
- Business value/use cases documented: ⬜
- Dependency information available: ⬜

---

## Scoring Model

See `references/SCORING_RUBRIC.md` for detailed scoring criteria.

| Category | Weight | Max Points |
|----------|--------|------------|
| Base Documentation | 20% | 20 |
| Communication (COMMUNICATION.md) | 15% | 15 |
| InnerSource Roles | 15% | 15 |
| Maturity Dimensions | 25% | 25 |
| Cross-Team Readiness | 15% | 15 |
| Discoverability | 10% | 10 |
| **Total** | 100% | 100 |

**Readiness Levels:**
- 🔴 **0-40: Not Ready** - Critical gaps exist, significant work required
- 🟡 **41-60: Emerging** - Basic structure in place, improvements needed
- 🟠 **61-80: Maturing** - Good foundation, refinements recommended
- 🟢 **81-100: Ready** - Meets standards for InnerSource adoption

---

## Output Format

After completing the assessment, provide:

### 1. Executive Summary
- Overall readiness score and level
- Maturity level summary (per dimension)
- Key strengths (top 3)
- Critical gaps (blocking issues)
- High-priority recommendations

### 2. Detailed Assessment
- Category-by-category breakdown
- Maturity dimension scores (0-3 per dimension)
- Specific checklist item results
- Evidence/links for each finding
- **Inheritance Report** (if org's `.github` repo was analyzed):
  - Files inherited from organization level
  - Inherited files that are appropriate for this repo
  - Inherited files that need repo-specific overrides
  - InnerSource-specific gaps in inherited files

### 3. Remediation Plan
- Prioritized list of improvements
- Template suggestions from `assets/` directory
- InnerSource patterns to adopt (from patterns.innersourcecommons.org)
- Estimated effort for each item

### 4. Inheritance Recommendations (if applicable)
- List inherited files that should be overridden in the target repo
- Explain why the inherited content may cause confusion or doesn't support InnerSource
- Provide templates or guidance for creating repo-specific versions
- Highlight missing InnerSource-specific content (TC roles, cross-team process, etc.)

### 5. Questions (if any)
- List any items that could not be reliably assessed
- Specific clarifying questions for the repository owner

---

## Pause Points

**STOP and ask for clarification when:**

1. **Trusted Committers are not identified**
   - "I cannot identify the Trusted Committers for this project. Who has commit access and mentoring responsibilities?"

2. **Cross-team contribution policy is unclear**
   - "I don't see a policy for contributions from other teams. What approval process should external contributors follow?"

3. **Communication channels are not documented**
   - "I cannot find internal communication channels. What Slack/Teams channels or mailing lists should contributors use?"

4. **Organizational context is missing**
   - "I cannot determine which team owns this project. Who is the owning team and who are the primary stakeholders?"

5. **Manager approval process is undefined**
   - "I don't see documentation about time allocation for contributors. How should contributors from other teams get approval to contribute?"

6. **Roadmap visibility is unclear**
   - "I cannot find a roadmap or planned features. Is there a roadmap that potential contributors can see?"

7. **Inherited file causes confusion or lacks InnerSource support**
   - "The [file] is inherited from the organization's .github repository, but its content [specific issue - e.g., doesn't mention cross-team contribution process / TC roles / 30-day warranty]. Should this be overridden with a repo-specific version that addresses InnerSource practices?"

---

## Relevant InnerSource Patterns

Consider recommending these patterns from patterns.innersourcecommons.org:

| Pattern | When to Recommend |
|---------|-------------------|
| **Trusted Committer** | No TC role defined |
| **30 Day Warranty** | Contribution ownership unclear |
| **Common Requirements** | Requirements not aligned across teams |
| **InnerSource Portal** | Discoverability is poor |
| **Gig Marketplace** | Want task-based contributions |
| **Service vs Library** | Ownership model unclear |
| **Standard Base Documentation** | Missing core documentation |
| **Communication Tooling** | Channels not established |

---

## References

- See `references/INNERSOURCE_CHECKLIST.md` for complete checklist
- See `references/SCORING_RUBRIC.md` for scoring details
- See `assets/` for remediation templates
- See https://patterns.innersourcecommons.org/ for full pattern catalog
