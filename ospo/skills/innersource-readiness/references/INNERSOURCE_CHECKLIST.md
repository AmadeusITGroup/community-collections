# InnerSource Readiness Checklist

This comprehensive checklist covers all requirements for InnerSource readiness assessment. It extends Open Source requirements with InnerSource-specific considerations for cross-team collaboration within an organization.

---

## Organization-Level `.github` Repository Inheritance

Before assessing individual files, check if the target repository belongs to a GitHub organization with a `.github` repository. Some community health files can be **inherited** from the organization level.

### Pre-Assessment: Organization Context

| # | Step | Action |
|---|------|--------|
| 0.1 | Extract org name from repo URL | Parse `github.com/<org>/<repo>` |
| 0.2 | Check for org's `.github` repo | Try to access `github.com/<org>/.github` |
| 0.3 | If exists, clone and catalog files | List all community health files present |
| 0.4 | Document inheritance context | Note which files will be inherited |
| 0.5 | Evaluate InnerSource support | Check if org files mention cross-team practices |

### Inheritance Rules

| File Type | Can Inherit? | Precedence | InnerSource Notes |
|-----------|--------------|------------|-------------------|
| CODE_OF_CONDUCT.md | ✅ Yes | Repo > Org | Usually acceptable from org level |
| CONTRIBUTING.md | ✅ Yes | Repo > Org | **Often needs override** for TC roles, cross-team process |
| SECURITY.md | ✅ Yes | Repo > Org | May need project-specific compliance info |
| SUPPORT.md | ✅ Yes | Repo > Org | Usually acceptable from org level |
| Issue Templates | ✅ Yes | Repo > Org | May need InnerSource-specific templates |
| PR Templates | ✅ Yes | Repo > Org | Should mention 30-day warranty if applicable |
| COMMUNICATION.md | ❌ No | Repo only | **InnerSource-critical, must be repo-specific** |
| README.md | ❌ No | Repo only | Must include owning team, TCs |
| CODEOWNERS | ❌ No | Repo only | Must be repo-specific |

### Inherited File Evaluation (InnerSource Focus)

When a file is inherited from org's `.github` repo, evaluate for InnerSource readiness:

| # | Requirement | Verification | Status |
|---|-------------|--------------|--------|
| 0.6 | Inherited file content is relevant | Content applies to this specific repo | ⬜ |
| 0.7 | No confusion from inherited content | Security contacts, tech stack, etc. match | ⬜ |
| 0.8 | InnerSource practices supported | Cross-team contribution, TC roles mentioned | ⬜ |
| 0.9 | Override recommended if generic | Flag files that should be repo-specific | ⬜ |

**Scoring for inherited files:**
- Inherited + relevant + InnerSource-ready = Full points
- Inherited + generic but acceptable = Full points (with recommendation)
- Inherited + causes confusion or lacks InnerSource support = Partial points + **must override**
- Missing everywhere = 0 points

**InnerSource-specific gaps to check in inherited files:**
- [ ] Does CONTRIBUTING.md mention Trusted Committer roles?
- [ ] Does CONTRIBUTING.md explain cross-team contribution process?
- [ ] Does CONTRIBUTING.md mention 30-day warranty expectations?
- [ ] Do issue templates support feature requests from other teams?
- [ ] Does PR template mention cross-team review process?

---

## 1. Base Documentation (20 points total)

### 1.1 README.md (7 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 1.1.1 | README.md file exists | File present in repository root | 1 |
| 1.1.2 | Project name and description | Clear explanation of purpose | 1 |
| 1.1.3 | Owning team identified | Team name and business unit | 1 |
| 1.1.4 | Business context explained | Why this project exists, who uses it | 1 |
| 1.1.5 | Installation/setup instructions | How to run locally | 1 |
| 1.1.6 | Usage examples | At least one code example | 0.5 |
| 1.1.7 | Internal contacts listed | Slack handles, email aliases | 0.5 |
| 1.1.8 | Trusted Committers identified | TCs listed with availability | 1 |

### 1.2 CONTRIBUTING.md (6 points)

**Note:** This file can be inherited from organization's `.github` repository, but often needs a repo-specific override for InnerSource practices.

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 1.2.1 | CONTRIBUTING.md file exists | File present in repo OR inherited from org | 1 |
| 1.2.2 | Cross-team contribution process | How other teams can contribute | 1 |
| 1.2.3 | Manager approval requirements | Time allocation expectations | 0.5 |
| 1.2.4 | Development environment setup | Complete dev setup guide | 1 |
| 1.2.5 | Testing requirements | How to run tests, coverage expectations | 0.5 |
| 1.2.6 | Code review process | Who reviews, expected turnaround | 1 |
| 1.2.7 | 30-day warranty expectations | Bug fix responsibilities post-contribution | 1 |

### 1.3 CODE_OF_CONDUCT.md (3 points)

**Note:** This file can be inherited from organization's `.github` repository.

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 1.3.1 | CODE_OF_CONDUCT.md exists | File present in repo OR inherited from org | 1 |
| 1.3.2 | References org policies | Links to HR/organizational policies | 1 |
| 1.3.3 | Enforcement contacts | Who to contact for violations | 1 |

### 1.4 SECURITY.md (4 points)

**Note:** This file can be inherited from organization's `.github` repository.

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 1.4.1 | SECURITY.md exists | File present in repo OR inherited from org | 1 |
| 1.4.2 | Internal reporting process | Security team contact, Jira project | 1 |
| 1.4.3 | Sensitive data handling | What data this project handles | 1 |
| 1.4.4 | Compliance requirements | Regulatory constraints (GDPR, SOX, etc.) | 1 |

---

## 2. Communication - COMMUNICATION.md (15 points total)

This is the **most critical InnerSource-specific document**.

### 2.1 Incoming Communication (8 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 2.1.1 | COMMUNICATION.md exists | File present | 2 |
| 2.1.2 | Bug reporting process | How to report bugs | 1 |
| 2.1.3 | Feature request process | How to request features | 1 |
| 2.1.4 | PR follow-up process | How to follow up on stale PRs | 1 |
| 2.1.5 | Documentation questions | Where to ask questions | 1 |
| 2.1.6 | Escalation paths | Who to contact if blocked | 1 |
| 2.1.7 | Office hours / sync meetings | Regular touchpoints documented | 1 |

### 2.2 Outgoing Communication (7 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 2.2.1 | Release announcements | How releases are communicated | 1 |
| 2.2.2 | Breaking change alerts | How breaking changes are announced | 1.5 |
| 2.2.3 | Planned outage notifications | How maintenance is communicated | 1 |
| 2.2.4 | Code freeze notifications | How freezes are announced | 0.5 |
| 2.2.5 | Roadmap updates | How roadmap changes are shared | 1 |
| 2.2.6 | Newsletter or changelog | Regular project updates | 1 |
| 2.2.7 | Communication channels listed | Slack, Teams, email lists | 1 |

---

## 3. InnerSource Roles (15 points total)

### 3.1 Trusted Committers (8 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 3.1.1 | TCs identified and listed | Names/handles in README or docs | 2 |
| 3.1.2 | TC responsibilities documented | What TCs do | 1 |
| 3.1.3 | TC availability stated | When TCs are available | 1 |
| 3.1.4 | Path to becoming TC | How contributors can become TCs | 1 |
| 3.1.5 | TC rotation/succession | How TCs change over time | 1 |
| 3.1.6 | Backup TCs identified | Coverage when primary TCs unavailable | 1 |
| 3.1.7 | TC time allocation | % of time dedicated to TC duties | 1 |

### 3.2 Contributors (7 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 3.2.1 | Contributor expectations documented | What's expected of contributors | 1 |
| 3.2.2 | Cross-team contribution examples | Evidence of external contributions | 2 |
| 3.2.3 | Contributor onboarding process | First-time contributor guide | 1 |
| 3.2.4 | Contribution recognition | How contributions are acknowledged | 1 |
| 3.2.5 | CONTRIBUTORS file | List of contributors | 1 |
| 3.2.6 | Contribution metrics tracked | PRs, issues from external teams | 1 |

---

## 4. Maturity Dimensions (25 points total)

### 4.1 Transparency (7 points)

#### Plans & Products
| Level | Criteria | Points |
|-------|----------|--------|
| 0 | No disclosure of plans | 0 |
| 1 | Visible roadmap to stakeholders | 0.5 |
| 2 | Shared roadmaps with contribution rules | 1 |
| 3 | Standardized roadmap sharing with clear guidelines | 2 |

#### Development Process & Tools
| Level | Criteria | Points |
|-------|----------|--------|
| 0 | Siloed development team | 0 |
| 1 | Shared repository internally | 0.5 |
| 2 | Shared repo with corporate CI, code review defined | 1 |
| 3 | Consistent CI/CD, cross-team code review | 2 |

#### Decisions
| Level | Criteria | Points |
|-------|----------|--------|
| 0 | Decisions withheld | 0 |
| 1 | Materials available after decisions | 0.5 |
| 2 | Involvement in decisions as they unfold | 1 |
| 3 | Standard collective decision-making | 1.5 |

#### Helpful Resources
| Level | Criteria | Points |
|-------|----------|--------|
| 0 | No shared knowledge repository | 0 |
| 1 | Materials in fragmented systems | 0.5 |
| 2 | Materials accessible with defined protocols | 1 |
| 3 | Broadly accessible with clear criteria | 1.5 |

### 4.2 Collaboration (6 points)

#### Communication Channels
| Level | Criteria | Points |
|-------|----------|--------|
| 0 | No established channels | 0 |
| 1 | Channels being established | 0.5 |
| 2 | Established guidelines and training | 1 |
| 3 | Official platforms with leader participation | 1.5 |

#### Leadership Openness
| Level | Criteria | Points |
|-------|----------|--------|
| 0 | Command & control culture | 0 |
| 1 | Some leaders open to feedback | 0.5 |
| 2 | Most leaders open, encourage sharing | 1 |
| 3 | Empowered members, mentor culture | 1.5 |

#### Contribution Culture
| Level | Criteria | Points |
|-------|----------|--------|
| 0 | Completely siloed | 0 |
| 1 | Occasional collaboration, "too difficult" | 0.5 |
| 2 | Active collaboration seeking | 1.5 |
| 3 | Cross-team collaboration as standard | 3 |

### 4.3 Community (6 points)

#### Sharing Policies
| Level | Criteria | Points |
|-------|----------|--------|
| 0 | No sharing culture | 0 |
| 1 | Some define values (unsupported) | 0.5 |
| 2 | Documented shared visions, codes of conduct | 1.5 |
| 3 | Shared values inform all decisions | 3 |

#### Engagement
| Level | Criteria | Points |
|-------|----------|--------|
| 0 | Low engagement | 0 |
| 1 | Comfortable in familiar domains | 0.5 |
| 2 | Comfortable sharing without fear | 1.5 |
| 3 | Proactive, shared consciousness | 3 |

### 4.4 Governance (6 points)

#### Rewards & Recognition
| Level | Criteria | Points |
|-------|----------|--------|
| 0 | No rewards for collaboration | 0 |
| 1 | Leaders encouraged to reward | 0.5 |
| 2 | Standard reward processes | 1 |
| 3 | Community-defined rewards | 1.5 |

#### Monitoring & Metrics
| Level | Criteria | Points |
|-------|----------|--------|
| 0 | No monitoring policies | 0 |
| 1 | Isolated metrics use | 0.5 |
| 2 | Organizational metrics strategy | 1 |
| 3 | Clear guidelines, training, infrastructure | 1.5 |

#### InnerSource Roles
| Level | Criteria | Points |
|-------|----------|--------|
| 0 | No specific roles | 0 |
| 1 | Technical reference, contributor role | 0.5 |
| 2 | InnerSource Officer, TC role defined | 1.5 |
| 3 | Evangelists, Community Managers | 3 |

---

## 5. Cross-Team Contribution Readiness (15 points total)

### 5.1 Organizational Readiness (7 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 5.1.1 | Manager approval process documented | How contributors get time | 2 |
| 5.1.2 | Time allocation acknowledged | InnerSource work is recognized | 1 |
| 5.1.3 | Cross-team examples exist | Evidence of external PRs merged | 2 |
| 5.1.4 | SLAs for external contributors | Review time commitments | 1 |
| 5.1.5 | Escalation path for blockers | How to unblock external contributors | 1 |

### 5.2 Technical Readiness (8 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 5.2.1 | Complete dev environment docs | Can set up in < 1 hour | 2 |
| 5.2.2 | Automated testing | CI runs on PRs | 1.5 |
| 5.2.3 | Clear testing requirements | What tests must pass | 1 |
| 5.2.4 | Coding standards documented | Style guides, linting | 1 |
| 5.2.5 | Architecture documentation | How the system works | 1 |
| 5.2.6 | Local development works | Can run and test locally | 1.5 |

---

## 6. Discoverability (10 points total)

### 6.1 Portal Presence (5 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 6.1.1 | Listed in InnerSource portal | Searchable in catalog | 2 |
| 6.1.2 | Tagged by technology | Language, framework tags | 1 |
| 6.1.3 | Tagged by domain | Business domain tags | 1 |
| 6.1.4 | Search keywords defined | Topics, keywords configured | 1 |

### 6.2 Project Clarity (5 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 6.2.1 | Clear "what this does" summary | One-paragraph description | 1 |
| 6.2.2 | Business value documented | Why this project matters | 1 |
| 6.2.3 | Use cases listed | Who uses this and how | 1 |
| 6.2.4 | Dependency information | What depends on this | 1 |
| 6.2.5 | Related projects linked | Ecosystem context | 1 |

---

## Quick Reference: Critical Blockers

These items are **blocking** for InnerSource readiness (must be resolved):

| # | Critical Blocker | Why |
|---|------------------|-----|
| ❌ | No README | Project is not understandable |
| ❌ | No CONTRIBUTING.md | Contributors don't know how to help |
| ❌ | No COMMUNICATION.md | No way to reach the team |
| ❌ | No Trusted Committers identified | No one to review external contributions |
| ❌ | No dev environment docs | Contributors can't get started |
| ❌ | Cross-team contributions rejected | Not actually practicing InnerSource |
| ❌ | No manager approval path | Contributors can't get time allocated |

---

## InnerSource Patterns to Recommend

When gaps are found, recommend these patterns from https://patterns.innersourcecommons.org/:

| Gap | Pattern to Recommend |
|-----|---------------------|
| No TCs defined | **Trusted Committer** |
| Contribution ownership unclear | **30 Day Warranty** |
| Requirements not aligned | **Common Requirements** |
| Hard to find project | **InnerSource Portal** |
| No small tasks for new contributors | **Gig Marketplace** |
| Service vs library confusion | **Service vs Library** |
| Missing documentation | **Standard Base Documentation** |
| No communication channels | **Communication Tooling** |
| No metrics | **Cross-Team Project Valuation** |
| External reviewers not empowered | **Review Committee** |
| Contributors can't get time | **Dedicated Community Leader** |
| No recognition | **Praise Participants** |

---

## Checklist Summary

| Category | Items | Max Points |
|----------|-------|------------|
| Base Documentation | 22 items | 20 |
| Communication (COMMUNICATION.md) | 14 items | 15 |
| InnerSource Roles | 13 items | 15 |
| Maturity Dimensions | 12 dimensions | 25 |
| Cross-Team Readiness | 11 items | 15 |
| Discoverability | 9 items | 10 |
| **Total** | **81+ items** | **100** |
