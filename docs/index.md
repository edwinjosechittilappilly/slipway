---
title: Slipway
hide:
  - navigation
---

![Slipway: your AI coding setup, launched in one command](assets/banner.svg)

# Slipway { .visually-hidden }

**Dotfiles for AI coding agents.** Slipway sets up your machine for working with coding agents (omp, Claude Code,
Codex) and keeps that setup current. One command installs the agents, the skills they use, the model each kind of job
runs on, a task board agents claim work from, and a spec tool. Every agent then works the same way:
idea → one-pager → design → spec → tickets → code → review → pull request.

```bash
curl -fsSL https://raw.githubusercontent.com/edwinjosechittilappilly/slipway/main/install.sh | bash -s -- --dry-run
```

The `--dry-run` preview changes nothing. Drop it to install. [Getting started](getting-started.md) has the details.

## Where to start

<div class="grid cards" markdown>

- **[Getting started](getting-started.md)**

    Install, check with `slipway doctor`, log in to your agents, set up your first repo.

- **[Daily use](using.md)**

    What you type in the terminal and what you ask inside your agent.

- **[Ship flow](ship-flow.md)**

    The nine stages from idea to merged PR, and how the agent knows which one you are in.

- **[Configuration](configuration.md)**

    Profiles, packs, switching components off, the lock file.

</div>

## What changes on your machine

| Before | After `slipway install` |
|---|---|
| Skills copied by hand; renamed ones keep loading | 30+ skills pinned to a commit, one copy shared by every agent |
| Each agent has its own rules, or none | One set of working rules in omp, Claude Code, Codex and Gemini |
| Every job runs on whatever model is active | Exploring, planning, coding and reviewing each go to a chosen model |
| Tasks live in chat history and TODO comments | A Beads task graph agents claim work from, and a board you can watch |
| Updates happen whenever a tool updates itself | A weekly pull request shows which skill files changed |

![Architecture](diagrams/architecture.svg)

## What it is not

- Not an application template. [ShipShape](https://github.com/edwinjosechittilappilly/shipshape-stack) makes a
  repository agent-ready; Slipway makes your machine agent-ready.
- Not an agent runner. You still drive the agent; Slipway gives it the right tools, rules and models.
- Not a lock-in. Every file it writes is recorded, your edits win, and `slipway uninstall` removes its changes.
