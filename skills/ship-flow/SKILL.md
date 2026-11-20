---
name: ship-flow
description: The end-to-end delivery map (idea → one-pager → design → spec → beads → implement → review → PR → close) with the skill, tool, harness role and gate for each stage. Use when starting a feature, when unsure what comes next, when asked "how do we ship X", or to hand work to another harness.
---

# Ship flow

Find the current stage from evidence in the repo, run that stage's skill, and check its gate before moving on.
Skip stages the work is too small to need; never skip a gate.

## 1. Size the work

| Size | Signal | Stages to run |
|---|---|---|
| Tiny | Under an hour, one area, no public behaviour change | 6 → 7 → 8 |
| Small | One session, behaviour is clear | `grill-me` (5 min) → one bead → 6 → 7 → 8 |
| Feature | Several sessions or areas, or a behaviour change others depend on | 1 → 9 |
| Initiative | Needs budget or buy-in, or spans several features | 2 first, then `wayfinder` for the map, then 1 → 9 per feature |

## 2. Stages

| # | Stage | Skill / tool | Role | Output | Gate |
|---|---|---|---|---|---|
| 1 | Clarify | `grill-with-docs` (`grill-me` outside a repo) | plan | Terms in `GLOSSARY.md`, ADRs in `docs/adr/` | Goal and acceptance check fit in one line each |
| 2 | Decide | `exec-one-pager` | docs | `docs/one-pagers/<slug>.md` | The decision owner said yes |
| 3 | Design | `design-doc` + `arch-diagram` | plan | `docs/design/<slug>.md`, `docs/diagrams/<slug>-*.{json,svg,drawio}` | Alternatives and risks reviewed by another model |
| 4 | Spec | `openspec-propose` (or `to-spec` without OpenSpec) | plan | `openspec/changes/<slug>/` | `openspec validate <slug>` passes; human approved |
| 5 | Tickets | `spec-to-beads` (or `to-tickets`) | issues | Epic + child beads with deps, acceptance, `role:` labels | `bd dep cycles` clean; every ticket has an acceptance check |
| 6 | Build | `bd ready` → `implement` + `tdd` | implement | Commits on a feature branch | The ticket's acceptance check passes |
| 7 | Review | `code-review`, `deslop`; UI: `impeccable` audit | review (other vendor) | Findings fixed | No blockers left |
| 8 | Ship | `pr` skill, `gh pr create` | pr | PR naming its beads and OpenSpec change | CI green |
| 9 | Close | tick `tasks.md`, `openspec-archive-change`, `bd close`, `retro` | docs | Archived change, closed epic, retro notes | Specs in `openspec/specs/` match what shipped |

## 3. Detect the stage

- Needs buy-in and no `docs/one-pagers/<slug>.md` → stage 2.
- One-pager approved, no `docs/design/<slug>.md` → stage 3.
- Design approved, no `openspec/changes/<slug>/` → stage 4.
- Change exists, no beads labelled `change:<slug>` (`bd list -l change:<slug>`) → stage 5.
- `bd ready` returns work → stage 6. Claim before starting: `bd update <id> --claim`.
- Branch ahead of `main` without a PR → stage 7, then 8.
- Epic's children all closed → stage 9.

## 4. Who does the work

Roles map to harnesses and models in Slipway's manifest; `slipway roles` prints the current map.

- **Inside omp** the task agents route by role on their own: `scout` (explore), `planner`, `task` (implement),
  `reviewer`, `issue-writer`, `pr-author`, `drafter` (docs).
- **Inside Claude Code**: subagents `explorer`, `planner`, `cross-reviewer`, `issue-writer`.
- **Across harnesses**: label beads `role:<name>` and run `slipway run --bead <id>`; for ad-hoc work,
  `slipway run <role> "<prompt>"`.
- **In parallel**: one worktree per bead (`bd worktree create <name>`), one agent per bead. `--claim` is atomic, so two
  agents cannot take the same bead.
- **Review with a different vendor** than the one that implemented. Same-model review misses the same mistakes.

## 5. Gates that always apply

- Prose (one-pagers, design docs, PR bodies): `humanizer`.
- Code diffs: `deslop`. UI: `npx impeccable detect <changed files>`.
- "Done" means: the command you ran and what it printed. No unobserved claims.
- New work found mid-task becomes a bead (`--deps discovered-from:<id>`), not a TODO comment or scope creep.
