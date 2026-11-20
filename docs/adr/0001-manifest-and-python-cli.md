# 1. Manifest and Python CLI

- **Status:** Accepted
- **Date:** 2026-11-20

## Context

A machine setup spans package managers, upstream installers, skills, links and settings. Repeating shell commands does not describe which values Slipway owns or whether a user changed them.

## Decision

Declare packs, components, project defaults and harness roles in `slipway.toml`, with optional profile and machine overlays. Implement the CLI in Python using the standard library; bootstrap it as an editable [uv tool](https://docs.astral.sh/uv/concepts/tools/), so the checkout remains the source. Component kinds in `src/slipway/kinds.py` handle their own checks and operations.

Use a three-way comparison of desired, last-written and live values for managed links, blocks and omp config. For omp record entries, a missing new entry is written; an unchanged managed entry can be updated or removed; a user-modified or user-deleted entry is preserved and reported as drift. `--force` permits replacement. Managed text blocks use embedded hashes; links and config have ownership state. This is not a blanket guarantee for files written by external installers.

## Consequences

- The manifest explains why components exist, and profiles can replace personal model choices.
- The checkout must remain available for the editable tool and symlinked skills.
- Python and uv are bootstrap dependencies; upstream installers still have their own side effects. Package uninstall is not automatic.
- Skills have separate source, commit and content-hash checks; see [0003](0003-pinned-skills-via-npx-skills.md). `--force` can overwrite local work.

## Alternatives considered

- Bash alone: less setup, but parsing TOML, structured state and three-way merges is harder to maintain.
- [chezmoi](https://www.chezmoi.io/) or [Home Manager](https://github.com/nix-community/home-manager): useful for machine files, but do not by themselves express this skill lock, omp record merge and project setup. They can coexist with Slipway.
- `pakage/install.py`: hash-tracked file installation inspired the ownership rule, but its copies are Codex-directory-centric and do not update upstream sources.
