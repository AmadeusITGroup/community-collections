# Renovate

Use this collection when you need to set up, configure, or troubleshoot Renovate dependency management for your repositories.

## Why use it

This collection helps you:
- set up Renovate for a new repository with best practices
- create or review `renovate.json` configurations
- configure dependency grouping, automerge, and scheduling
- manage security alerts and vulnerability handling
- set up manager-specific options for different ecosystems
- troubleshoot Renovate logs to understand failed or skipped updates

## Contents

| Item | Type | Purpose |
|------|------|---------|
| `Renovate` | Agent | Orchestrator agent that routes to configuration or log analysis based on your needs |
| `renovate-config` | Skill | Build or improve a best-practice `renovate.json` through guided, group-by-group elicitation |
| `renovate-log-analyzer` | Skill | Analyze Renovate run logs to understand why updates failed or were skipped |

## Prerequisites

- A repository with Git access
- Understanding of your dependency management ecosystem (npm, Python, Docker, etc.)
- Optional: existing `renovate.json` file if configuring an existing setup

## How to use it

### Start with the agent

In GitHub Copilot Chat or other compatible environments, run:

```text
/renovate
```

The agent will determine your intent and route you to the appropriate skill:

#### For configuration

Describe your task:
- "Set up Renovate for a new repository"
- "Create a best-practice renovate.json"
- "Configure grouping and automerge policies"

The agent will launch the **renovate-config** skill, which guides you through:
- Repository discovery and inventory
- Interactive policy elicitation by topic
- Best-practice recommendations
- `renovate.json` assembly and validation

#### For troubleshooting

Describe your task:
- "Why did Renovate skip this update?"
- "Analyze my Renovate run log"
- "What network calls did Renovate make?"

The agent will launch the **renovate-log-analyzer** skill, which:
- Parses Renovate run logs
- Explains why updates failed or were skipped
- Lists all network calls made by Renovate
- Provides actionable debugging insights

## Expected output

**For configuration:**
- a `renovate.json` configuration tailored to your repository
- documentation of enabled presets, grouping, and automerge policies
- best-practice recommendations based on your dependency ecosystem
- step-by-step guidance for implementation

**For troubleshooting:**
- detailed analysis of why updates failed, were skipped, or experienced errors
- list of all network calls and their purposes
- actionable next steps to resolve the issue
