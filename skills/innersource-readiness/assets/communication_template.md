# Communication

This document describes how to communicate with the [Project Name] team. We want to make it easy for you to reach us and to stay informed about project updates.

## Table of Contents

- [Getting Help](#getting-help)
- [Reporting Issues](#reporting-issues)
- [Following Up](#following-up)
- [Project Updates](#project-updates)
- [Communication Channels](#communication-channels)
- [Response Expectations](#response-expectations)

---

## Getting Help

### Quick Questions

For quick questions about using [Project Name]:

| Channel | Best For | Response Time |
|---------|----------|---------------|
| [#project-help on Slack](link) | Quick questions, troubleshooting | < 4 hours during business hours |
| [GitHub Discussions](link) | Longer discussions, Q&A | < 24 hours |
| [Stack Overflow [tag]](link) | Public Q&A, searchable answers | Community-driven |

### Contacting the Team

| Need | Contact |
|------|---------|
| **General questions** | [#project-name on Slack](link) |
| **Security issues** | [security@example.com](mailto:security@example.com) - see [SECURITY.md](SECURITY.md) |
| **Partnership inquiries** | [partnerships@example.com](mailto:partnerships@example.com) |
| **Press inquiries** | [press@example.com](mailto:press@example.com) |

---

## Reporting Issues

### Bugs

1. **Search existing issues** first: [GitHub Issues](link)
2. If not found, [open a bug report](link-to-template)
3. Include:
   - Steps to reproduce
   - Expected vs. actual behavior
   - Environment details
   - Logs or screenshots

### Feature Requests

1. **Check the roadmap**: [Project Roadmap](link)
2. **Search existing requests**: [Feature Requests](link)
3. If new, [open a feature request](link-to-template)
4. Include:
   - Problem you're trying to solve
   - Proposed solution
   - Alternatives considered

### Documentation Issues

- For typos or small fixes: Open a PR directly
- For larger changes: [Open a docs issue](link)

---

## Following Up

### On Your Pull Request

| Timeframe | Status | Action |
|-----------|--------|--------|
| 3 days | No response | Comment with a gentle ping |
| 7 days | Still no response | Ping a specific [Trusted Committer](#trusted-committers) |
| 14 days | Still blocked | Escalate via [#project-escalations](link) |

### On Your Issue

| Timeframe | Status | Action |
|-----------|--------|--------|
| 7 days | No response | Add "needs-triage" label + comment |
| 14 days | Still no response | Ping in [#project-help](link) |

### Escalation Path

1. **First**: Comment on the issue/PR
2. **Second**: Reach out on [Slack #project-name](link)
3. **Third**: Contact a [Trusted Committer](#trusted-committers) directly
4. **Finally**: Email [project-lead@example.com](mailto:project-lead@example.com)

---

## Project Updates

### How We Communicate Changes

| Update Type | Channel | Frequency |
|-------------|---------|-----------|
| **Releases** | [GitHub Releases](link), [#project-announcements](link) | Per release |
| **Breaking changes** | [CHANGELOG](link), email list, Slack | 2 weeks notice minimum |
| **Planned maintenance** | [#project-announcements](link), status page | 48 hours notice |
| **Unplanned outages** | [#project-announcements](link), status page | ASAP |
| **Roadmap updates** | [Roadmap](link), monthly update | Monthly |
| **Newsletter** | [Subscribe](link) | Monthly |

### Subscribe to Updates

- **Release notifications**: Watch the repository on GitHub (Releases only)
- **All announcements**: Join [#project-announcements](link) on Slack
- **Newsletter**: [Subscribe here](link)
- **RSS feed**: [releases.atom](link)

### Breaking Changes

We follow semantic versioning and announce breaking changes:

1. **Deprecation warning** in minor version (with migration guide)
2. **Announcement** in [#project-announcements](link)
3. **Email** to affected users (when possible)
4. **Removal** in next major version

---

## Communication Channels

### Official Channels

| Channel | Purpose | Join |
|---------|---------|------|
| **Slack: #project-name** | General discussion, quick help | [Join](link) |
| **Slack: #project-announcements** | Official updates (read-only) | [Join](link) |
| **Slack: #project-contributors** | Contributor discussion | [Join](link) |
| **GitHub Discussions** | Long-form discussion, RFCs | [View](link) |
| **Mailing List** | Announcements, monthly digest | [Subscribe](link) |

### Meeting Schedule

| Meeting | Purpose | Frequency | Calendar |
|---------|---------|-----------|----------|
| **Community Call** | Updates, demos, Q&A | Monthly, 1st Tuesday | [Add to calendar](link) |
| **Office Hours** | Live help, pair programming | Weekly, Thursdays 2pm UTC | [Add to calendar](link) |
| **Contributor Sync** | Contributor coordination | Bi-weekly | [Add to calendar](link) |

### Archived Communication

All Slack channels are archived and searchable. Historical discussions are available in:
- [GitHub Discussions Archive](link)
- [Mailing List Archive](link)

---

## Response Expectations

### Service Level Agreements

| Request Type | Initial Response | Resolution Target |
|--------------|------------------|-------------------|
| **Security vulnerability** | 24 hours | ASAP (based on severity) |
| **Critical bug** (production down) | 4 hours | 24 hours |
| **Bug report** | 48 hours | 2 weeks |
| **Feature request** | 1 week | Roadmap consideration |
| **Pull request** | 3 business days | 2 weeks |
| **General question** | 24 hours | N/A |

### Business Hours

The core team operates primarily in these timezones:
- **Primary**: [UTC-5 to UTC-8] (Americas)
- **Secondary**: [UTC+0 to UTC+2] (Europe)

Expect faster responses during business hours in these regions.

---

## Trusted Committers

These team members can help with contributions and escalations:

| Name | Focus Area | Slack | GitHub | Availability |
|------|------------|-------|--------|--------------|
| [Name 1] | Core, API | @handle | @ghhandle | Mon-Fri, UTC-5 |
| [Name 2] | Docs, Onboarding | @handle | @ghhandle | Mon-Thu, UTC+1 |
| [Name 3] | Frontend, UX | @handle | @ghhandle | Tue-Sat, UTC+8 |

---

## Code Freeze & Maintenance Windows

### Scheduled Freezes

| Period | Dates | Restrictions |
|--------|-------|--------------|
| **Release prep** | 1 week before major release | No new features |
| **Holiday freeze** | Dec 20 - Jan 5 | Emergency fixes only |

### Maintenance Windows

Regular maintenance may occur:
- **Time**: Sundays, 02:00-06:00 UTC
- **Notice**: 48 hours minimum
- **Status**: Check [status.example.com](link)

---

## Feedback

This communication process is always evolving. Suggestions welcome:
- Open an issue with label "process-improvement"
- Discuss in [#project-meta](link)
