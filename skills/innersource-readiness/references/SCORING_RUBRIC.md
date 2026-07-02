# Scoring Rubric for Repository Readiness Assessment

This rubric provides consistent scoring criteria for both Open Source and InnerSource readiness assessments. It defines how to evaluate each category and calculate overall readiness scores.

---

## Scoring Principles

### 1. Evidence-Based Scoring
- **Every score must be justified with evidence** from the repository
- Reference specific files, lines, commits, or URLs
- If evidence cannot be found, the item scores 0
- Never assume or infer without documentation

### 2. Partial Credit
- Items can receive partial credit when partially implemented
- Use the following scale:
  - **0%**: Not implemented or not found
  - **25%**: Minimal/placeholder implementation
  - **50%**: Partial implementation with gaps
  - **75%**: Mostly complete with minor issues
  - **100%**: Fully implemented and documented

### 3. Blocking Issues
- Some items are **blockers** that prevent readiness regardless of score
- Blocking issues must be resolved before any readiness level above "Not Ready"
- See "Critical Blockers" sections in checklists

---

## Open Source Scoring Categories

### Category 1: Documentation (25 points)

| Score Range | Criteria |
|-------------|----------|
| 0-6 | Missing critical files (README, LICENSE) |
| 7-12 | Basic files present but incomplete |
| 13-18 | Good documentation with minor gaps |
| 19-25 | Comprehensive documentation |

**Key Indicators:**
- README completeness (8 points max)
- LICENSE validity (5 points max)
- CONTRIBUTING quality (5 points max)
- CODE_OF_CONDUCT presence (4 points max)
- SECURITY.md completeness (3 points max)

### Category 2: Community Health (20 points)

| Score Range | Criteria |
|-------------|----------|
| 0-5 | No activity, no community infrastructure |
| 6-10 | Some activity, basic templates |
| 11-15 | Active project, good contributor experience |
| 16-20 | Thriving community, excellent onboarding |

**Key Indicators:**
- Activity metrics (8 points max)
- Contributor experience (8 points max)
- Communication channels (4 points max)

### Category 3: Security (20 points)

| Score Range | Criteria |
|-------------|----------|
| 0-5 | No security policy, critical vulnerabilities |
| 6-10 | Basic security policy, some protections |
| 11-15 | Good security posture, dependency scanning |
| 16-20 | Comprehensive security program |

**Key Indicators:**
- Security policy (6 points max)
- Repository security settings (8 points max)
- Dependency security (6 points max)

### Category 4: Governance (15 points)

| Score Range | Criteria |
|-------------|----------|
| 0-4 | No clear ownership or process |
| 5-8 | Maintainers identified, basic process |
| 9-12 | Clear governance, documented processes |
| 13-15 | Mature governance model |

**Key Indicators:**
- Ownership clarity (6 points max)
- Decision-making process (5 points max)
- Release management (4 points max)

### Category 5: License Compliance (20 points)

| Score Range | Criteria |
|-------------|----------|
| 0-5 | No license or non-OSI license |
| 6-10 | Valid license, unknown dependencies |
| 11-15 | Good compliance, minor issues |
| 16-20 | Full compliance, all dependencies verified |

**Key Indicators:**
- License clarity (8 points max)
- Dependency compliance (8 points max)
- Legal clarity (4 points max)

---

## InnerSource Scoring Categories

### Category 1: Base Documentation (20 points)

| Score Range | Criteria |
|-------------|----------|
| 0-5 | Missing critical files |
| 6-10 | Basic files present, lacks InnerSource context |
| 11-15 | Good documentation with team context |
| 16-20 | Comprehensive InnerSource documentation |

**Key Indicators:**
- README with team context (7 points max)
- CONTRIBUTING with cross-team process (6 points max)
- CODE_OF_CONDUCT (3 points max)
- SECURITY.md with internal process (4 points max)

### Category 2: Communication (15 points)

| Score Range | Criteria |
|-------------|----------|
| 0-4 | No COMMUNICATION.md |
| 5-8 | Basic communication channels listed |
| 9-12 | Good incoming and outgoing communication |
| 13-15 | Comprehensive communication strategy |

**Key Indicators:**
- Incoming communication (8 points max)
- Outgoing communication (7 points max)

### Category 3: InnerSource Roles (15 points)

| Score Range | Criteria |
|-------------|----------|
| 0-4 | No roles defined |
| 5-8 | TCs identified but limited documentation |
| 9-12 | Clear TC role, contributor process |
| 13-15 | Mature role definitions, path to TC |

**Key Indicators:**
- Trusted Committers (8 points max)
- Contributors (7 points max)

### Category 4: Maturity Dimensions (25 points)

| Score Range | Criteria |
|-------------|----------|
| 0-6 | Level 0-1 across dimensions |
| 7-12 | Mix of Level 1-2 |
| 13-18 | Mostly Level 2 |
| 19-25 | Level 2-3 across dimensions |

**Dimension Breakdown:**
- Transparency (7 points max)
- Collaboration (6 points max)
- Community (6 points max)
- Governance (6 points max)

### Category 5: Cross-Team Readiness (15 points)

| Score Range | Criteria |
|-------------|----------|
| 0-4 | Not ready for external contributors |
| 5-8 | Basic readiness, some gaps |
| 9-12 | Good readiness, clear process |
| 13-15 | Excellent cross-team support |

**Key Indicators:**
- Organizational readiness (7 points max)
- Technical readiness (8 points max)

### Category 6: Discoverability (10 points)

| Score Range | Criteria |
|-------------|----------|
| 0-3 | Not discoverable |
| 4-6 | Basic listing, minimal metadata |
| 7-8 | Good discoverability |
| 9-10 | Excellent discoverability and clarity |

**Key Indicators:**
- Portal presence (5 points max)
- Project clarity (5 points max)

---

## Readiness Level Definitions

### 🔴 Not Ready (0-40 points)

**Definition:** Critical gaps exist that prevent successful Open Source or InnerSource adoption.

**Characteristics:**
- Missing critical documentation (README, LICENSE, CONTRIBUTING)
- No clear ownership or maintainers
- No contribution process defined
- Security vulnerabilities or policy gaps
- For InnerSource: No COMMUNICATION.md, no TCs identified

**Required Actions:**
- Address all critical blockers
- Create minimum required documentation
- Identify and empower maintainers/TCs
- Establish basic security practices

### 🟡 Emerging (41-60 points)

**Definition:** Basic structure in place but significant improvements needed before adoption.

**Characteristics:**
- Core files present but incomplete
- Maintainers identified but process unclear
- Some community infrastructure
- Basic security measures
- For InnerSource: TCs exist but not fully empowered

**Required Actions:**
- Complete documentation gaps
- Establish clear contribution workflow
- Improve community health indicators
- Document governance and decision-making

### 🟠 Maturing (61-80 points)

**Definition:** Good foundation with refinements recommended.

**Characteristics:**
- Comprehensive documentation
- Active maintainership
- Good contributor experience
- Solid security posture
- For InnerSource: Cross-team contributions happening

**Required Actions:**
- Refine edge cases and gaps
- Improve metrics and monitoring
- Enhance contributor recognition
- Document advanced scenarios

### 🟢 Ready (81-100 points)

**Definition:** Meets standards for successful adoption.

**Characteristics:**
- Excellent documentation across all areas
- Thriving community/cross-team collaboration
- Mature governance model
- Comprehensive security program
- For InnerSource: Multiple cross-team success stories

**Ongoing Focus:**
- Continuous improvement
- Mentoring other projects
- Sharing best practices
- Measuring and reporting success

---

## Score Calculation

### Step 1: Score Each Category

For each checklist item:
1. Find evidence in the repository
2. Apply partial credit rules
3. Sum points within category

### Step 2: Calculate Total

```
Total Score = Sum of all category scores
```

### Step 3: Determine Readiness Level

| Total Score | Level |
|-------------|-------|
| 0-40 | 🔴 Not Ready |
| 41-60 | 🟡 Emerging |
| 61-80 | 🟠 Maturing |
| 81-100 | 🟢 Ready |

### Step 4: Check for Blockers

Even with a high score, the following blockers force a "Not Ready" rating:

**Open Source Blockers:**
- No LICENSE file
- Non-OSI license
- No README
- Known critical security vulnerabilities
- No maintainers identified
- Proprietary code included

**InnerSource Blockers:**
- No README
- No CONTRIBUTING.md
- No COMMUNICATION.md
- No Trusted Committers identified
- No dev environment docs
- Cross-team contributions actively rejected

---

## Reporting Template

### Executive Summary
```markdown
## Repository Readiness Assessment: [REPO NAME]

**Assessment Type:** [Open Source / InnerSource]
**Date:** [DATE]
**Assessor:** [NAME/TOOL]

### Overall Score: [XX]/100 - [LEVEL]

| Category | Score | Max |
|----------|-------|-----|
| [Category 1] | XX | XX |
| [Category 2] | XX | XX |
| ... | ... | ... |
| **Total** | **XX** | **100** |

### Critical Blockers
- [ ] [Blocker 1 - if any]
- [ ] [Blocker 2 - if any]

### Top Strengths
1. [Strength 1]
2. [Strength 2]
3. [Strength 3]

### Priority Improvements
1. [Improvement 1] - [Estimated Effort]
2. [Improvement 2] - [Estimated Effort]
3. [Improvement 3] - [Estimated Effort]
```

### Detailed Assessment
```markdown
## Detailed Findings

### [Category Name] - [Score]/[Max]

| Item | Status | Evidence | Score |
|------|--------|----------|-------|
| [Item 1] | ✅/⚠️/❌ | [Link/Description] | X/X |
| [Item 2] | ✅/⚠️/❌ | [Link/Description] | X/X |
| ... | ... | ... | ... |

**Recommendations:**
- [Recommendation 1]
- [Recommendation 2]

[Repeat for each category]
```

---

## Effort Estimation Guide

| Effort Level | Description | Typical Duration |
|--------------|-------------|------------------|
| 🟢 Low | Single file creation, minor edits | < 1 hour |
| 🟡 Medium | Multiple files, process documentation | 1-4 hours |
| 🟠 High | Significant documentation, tooling setup | 1-2 days |
| 🔴 Very High | Organizational changes, major refactoring | 1+ weeks |
