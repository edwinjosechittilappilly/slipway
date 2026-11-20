# 2. Beads for agent work

- **Status:** Accepted
- **Date:** 2026-11-20

## Context

Agents need dependency-aware work that survives sessions and can be claimed when several workers are active. People still need an accessible public history of issues and pull requests.

## Decision

Use [Beads](https://github.com/gastownhall/beads) (`bd`) as agent working memory and [beads-ui](https://github.com/mantoni/beads-ui) for a local board. GitHub Issues and PRs remain the public record; link bead IDs in PRs and synchronize deliberately, not by assuming every local item is public. Beads supports [GitHub synchronization](https://beads.gascity.com/cli-reference/github).

`slipway init` initializes a project; stealth is optional, via project configuration or the init option. Stealth excludes local Beads artifacts from ordinary repository tracking, but **does not itself stop Dolt network sync**. Set `dolt.local-only` or configure a private remote when privacy requires it; check [Beads sync documentation](https://beads.gascity.com/core-concepts/sync-concepts).

## Consequences

- Beads offers dependency graphs and atomic claims, useful for parallel agents. beads-ui invokes `bd` and provides a board; its minimum supported `bd` version is unverified.
- Beads uses Dolt. Embedded mode has a single writer; migrations, schema skew and release churn add operational risk. Before upgrades, push where appropriate and export, then follow the [upgrade guide](https://beads.gascity.com/getting-started/upgrading); an export alone is not a Dolt backup. Coordinate schema migration across clones and use stable releases. The lock records observed brew versions; Homebrew is not guaranteed to enforce them.
- [Gas City](https://github.com/gastownhall/gascity) offers a later path to formulas on Beads, at the cost of a supervisor, Dolt server and tmux. Installing it does not automatically configure a city or migrate a project graph.

## Alternatives considered

| Alternative | Trade-off |
|---|---|
| [Backlog.md](https://github.com/MrLesk/Backlog.md) | Readable Markdown and a board; a simpler solo choice, but not the chosen Beads/Gas City coordination path. |
| [tk](https://github.com/wedow/ticket) | Small, grep-friendly Markdown tracker; no atomic claim. |
| [kata](https://github.com/kenn-io/kata) | Local SQLite and terminal/web UI; young, with breaking renames. |
| GitHub Issues alone | Public and familiar, but network-dependent for agent loops; local Beads ready/claim workflow is not provided by this choice. |
