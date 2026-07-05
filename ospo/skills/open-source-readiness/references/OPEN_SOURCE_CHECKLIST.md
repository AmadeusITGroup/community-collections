# Open Source Readiness Checklist

This comprehensive checklist covers all requirements for Open Source readiness assessment. Each item includes the requirement, how to verify it, and its scoring weight.

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

### Inheritance Rules

| File Type | Can Inherit? | Precedence |
|-----------|--------------|------------|
| CODE_OF_CONDUCT.md | ✅ Yes | Repo > Org |
| CONTRIBUTING.md | ✅ Yes | Repo > Org |
| SECURITY.md | ✅ Yes | Repo > Org |
| SUPPORT.md | ✅ Yes | Repo > Org |
| Issue Templates | ✅ Yes | Repo > Org (entire folder) |
| PR Templates | ✅ Yes | Repo > Org |
| LICENSE | ❌ No | Repo only |
| README.md | ❌ No | Repo only |
| CODEOWNERS | ❌ No | Repo only |

### Inherited File Evaluation

When a file is inherited from org's `.github` repo:

| # | Requirement | Verification | Status |
|---|-------------|--------------|--------|
| 0.5 | Inherited file content is relevant | Content applies to this specific repo | ⬜ |
| 0.6 | No confusion from inherited content | Security contacts, tech stack, etc. match | ⬜ |
| 0.7 | Override recommended if generic | Flag files that should be repo-specific | ⬜ |

**Scoring for inherited files:**
- Inherited + relevant = Full points
- Inherited + generic but acceptable = Full points (with recommendation)
- Inherited + causes confusion = Partial points + **must override**
- Missing everywhere = 0 points

---

## 1. Required Documentation (25 points total)

### 1.1 README.md (8 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 1.1.1 | README.md file exists | File present in repository root | 1 |
| 1.1.2 | Project name clearly stated | First heading or title element | 0.5 |
| 1.1.3 | Project description/purpose | Clear explanation of what the project does | 1 |
| 1.1.4 | Installation instructions | Step-by-step setup guide | 1 |
| 1.1.5 | Usage examples with code | At least one code example | 1 |
| 1.1.6 | API/feature documentation or link | Documentation or link to docs | 0.5 |
| 1.1.7 | Contributing section or link | Link to CONTRIBUTING.md | 0.5 |
| 1.1.8 | License mentioned or badge | License name or badge visible | 0.5 |
| 1.1.9 | Contact/communication info | How to reach maintainers | 0.5 |
| 1.1.10 | Maintainers listed | Names or @handles of maintainers | 0.5 |
| 1.1.11 | Status badges (CI, coverage) | At least one status badge | 0.5 |
| 1.1.12 | Table of contents (if long) | TOC for README > 200 lines | 0.5 |

### 1.2 LICENSE (5 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 1.2.1 | LICENSE file exists | File present in repository root | 2 |
| 1.2.2 | License is OSI-approved | Check against OSI license list | 2 |
| 1.2.3 | License matches declared license | LICENSE content matches README/package.json | 1 |

**Common OSI-approved licenses:**
- MIT, Apache 2.0, GPL v2/v3, BSD 2-Clause, BSD 3-Clause, MPL 2.0, ISC, LGPL

### 1.3 CONTRIBUTING.md (5 points)

**Note:** This file can be inherited from organization's `.github` repository.

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 1.3.1 | CONTRIBUTING.md file exists | File present in repo OR inherited from org | 1 |
| 1.3.2 | How to report bugs | Bug reporting process documented | 0.5 |
| 1.3.3 | How to suggest features | Feature request process documented | 0.5 |
| 1.3.4 | Development environment setup | How to set up dev environment | 0.5 |
| 1.3.5 | How to run tests | Testing instructions provided | 0.5 |
| 1.3.6 | Code style guidelines | Formatting/linting rules documented | 0.5 |
| 1.3.7 | Pull request process | How to submit PRs | 0.5 |
| 1.3.8 | Review expectations | Expected review time, who reviews | 0.5 |
| 1.3.9 | Types of contributions accepted | What contributions are welcome | 0.5 |

### 1.4 CODE_OF_CONDUCT.md (4 points)

**Note:** This file can be inherited from organization's `.github` repository.

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 1.4.1 | CODE_OF_CONDUCT.md file exists | File present in repo OR inherited from org | 1 |
| 1.4.2 | Expected behavior defined | Clear behavioral expectations | 1 |
| 1.4.3 | Unacceptable behavior defined | What is not tolerated | 1 |
| 1.4.4 | Enforcement process | How violations are handled | 1 |

**Recommended:** Use Contributor Covenant (https://www.contributor-covenant.org/)

### 1.5 SECURITY.md (3 points)

**Note:** This file can be inherited from organization's `.github` repository.

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 1.5.1 | SECURITY.md file exists | File present in repo OR inherited from org | 1 |
| 1.5.2 | Vulnerability reporting process | How to report vulnerabilities | 1 |
| 1.5.3 | Security contact information | Email or form for security issues | 0.5 |
| 1.5.4 | Response expectations | Expected response timeline | 0.5 |

---

## 2. Community Health (20 points total)

### 2.1 Activity Metrics (8 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 2.1.1 | Recent commits | Commits within last 30 days | 2 |
| 2.1.2 | Issues being triaged | Issues have responses within 7 days | 2 |
| 2.1.3 | PRs being reviewed | PRs have reviews within 7 days | 2 |
| 2.1.4 | Multiple contributors | More than 1 contributor | 1 |
| 2.1.5 | Release activity | Releases within last 6 months | 1 |

### 2.2 Contributor Experience (8 points)

**Note:** Issue and PR templates can be inherited from organization's `.github` repository.

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 2.2.1 | Issue templates configured | .github/ISSUE_TEMPLATE exists in repo OR org | 1 |
| 2.2.2 | Bug report template | Template for bug reports (repo or org) | 0.5 |
| 2.2.3 | Feature request template | Template for feature requests (repo or org) | 0.5 |
| 2.2.4 | PR template configured | PULL_REQUEST_TEMPLATE.md exists in repo OR org | 1 |
| 2.2.5 | "good first issue" labels | Labels exist and are used | 1 |
| 2.2.6 | "help wanted" labels | Labels exist and are used | 1 |
| 2.2.7 | Contributor recognition | CONTRIBUTORS file or acknowledgments | 1 |
| 2.2.8 | Path to maintainer documented | How to become a maintainer | 1 |
| 2.2.9 | Discussion forums enabled | GitHub Discussions or external forum | 1 |

### 2.3 Communication (4 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 2.3.1 | Communication channels listed | Slack, Discord, mailing list, etc. | 1 |
| 2.3.2 | Response time expectations | SLAs or expected response times | 1 |
| 2.3.3 | Active communication | Recent activity in channels | 1 |
| 2.3.4 | Multiple contact methods | More than one way to reach maintainers | 1 |

---

## 3. Security (20 points total)

### 3.1 Security Policy (6 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 3.1.1 | SECURITY.md present | Security policy documented | 2 |
| 3.1.2 | Private vulnerability reporting | GitHub security advisories or email | 2 |
| 3.1.3 | Incident response plan | How security incidents are handled | 1 |
| 3.1.4 | Security update process | How security updates are communicated | 1 |

### 3.2 Repository Security (8 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 3.2.1 | Branch protection on main | Settings → Branches → Rules | 2 |
| 3.2.2 | Required reviews for PRs | PR reviews required before merge | 1 |
| 3.2.3 | Status checks required | CI must pass before merge | 1 |
| 3.2.4 | Signed commits encouraged | Commit signing mentioned/enforced | 1 |
| 3.2.5 | CODEOWNERS file | Code ownership defined | 1 |
| 3.2.6 | Force push disabled | No force push to main | 1 |
| 3.2.7 | Delete branch on merge | Auto-delete stale branches | 1 |

### 3.3 Dependency Security (6 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 3.3.1 | Dependency scanning enabled | Dependabot, Renovate, or similar | 2 |
| 3.3.2 | No critical vulnerabilities | No known critical CVEs | 2 |
| 3.3.3 | Lock file present | package-lock.json, Cargo.lock, etc. | 1 |
| 3.3.4 | SBOM available | Software Bill of Materials | 1 |

---

## 4. Governance (15 points total)

### 4.1 Ownership (6 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 4.1.1 | Maintainers clearly identified | Listed in README or MAINTAINERS file | 2 |
| 4.1.2 | CODEOWNERS file present | .github/CODEOWNERS exists | 2 |
| 4.1.3 | Contact information available | How to reach maintainers | 1 |
| 4.1.4 | Succession plan | What happens if maintainer leaves | 1 |

### 4.2 Decision Making (5 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 4.2.1 | Decision process documented | How decisions are made | 2 |
| 4.2.2 | Commit access policy | Who can commit directly | 1.5 |
| 4.2.3 | Governance model specified | BDFL, Meritocracy, etc. | 1.5 |

### 4.3 Release Management (4 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 4.3.1 | Release process documented | How releases are made | 1 |
| 4.3.2 | Semantic versioning | MAJOR.MINOR.PATCH followed | 1 |
| 4.3.3 | CHANGELOG maintained | Changelog file or release notes | 1 |
| 4.3.4 | Release schedule | Regular or documented release cadence | 1 |

---

## 5. License Compliance (20 points total)

### 5.1 License Clarity (8 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 5.1.1 | LICENSE file present | In repository root | 3 |
| 5.1.2 | OSI-approved license | Check OSI list | 3 |
| 5.1.3 | License in package metadata | package.json, Cargo.toml, etc. | 1 |
| 5.1.4 | License headers in source | Optional but recommended | 1 |

### 5.2 Dependency Compliance (8 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 5.2.1 | No copyleft conflicts | Permissive dependencies for permissive project | 3 |
| 5.2.2 | All dependencies licensed | No unlicensed dependencies | 2 |
| 5.2.3 | License compatibility verified | Dependencies compatible with project license | 2 |
| 5.2.4 | Third-party notices | Attribution for dependencies requiring it | 1 |

### 5.3 Legal Clarity (4 points)

| # | Requirement | Verification | Points |
|---|-------------|--------------|--------|
| 5.3.1 | No proprietary code | All code is properly licensed | 2 |
| 5.3.2 | DCO or CLA (if required) | Contribution agreement if needed | 1 |
| 5.3.3 | Export control considered | ECCN classification if applicable | 1 |

---

## Quick Reference: Critical Blockers

These items are **blocking** for Open Source readiness (must be resolved):

| # | Critical Blocker | Why |
|---|------------------|-----|
| ❌ | No LICENSE file | Cannot be legally used/contributed to |
| ❌ | Non-OSI license | Not recognized as open source |
| ❌ | No README | Project is not understandable |
| ❌ | Known critical security vulnerabilities | Unsafe for adoption |
| ❌ | No maintainers identified | No one to manage contributions |
| ❌ | Proprietary/confidential code included | Legal liability |

---

## Checklist Summary

| Category | Items | Max Points |
|----------|-------|------------|
| Required Documentation | 32 items | 25 |
| Community Health | 17 items | 20 |
| Security | 15 items | 20 |
| Governance | 11 items | 15 |
| License Compliance | 11 items | 20 |
| **Total** | **86 items** | **100** |
