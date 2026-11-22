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
| 4 | Spec | `openspec-propose` (or `to-spec` without OpenSpec) | plan | `openspec/changes/<slug>/`, including audit findings | `openspec validate <slug>` passes; human approved before behaviour changes |
| 5 | Tickets | `spec-to-beads` (or `to-tickets`) | issues | One bead per spec task, plus review beads, with descriptions, acceptance and deps | `bd dep cycles` clean; every plan item is tracked |
| 6 | Build | `bd ready` → claim → `parallel-pr-delivery` + `tdd` | implement | Independent slices in owned worktrees and branches | Each bead's acceptance check passes |
| 7 | Review | `code-review`, `deslop`; UI: `impeccable` | review (other vendor) | Child finding beads, fixes and independent re-check | All findings addressed or tracked as follow-ups |
| 8 | Ship | `pr`, `parallel-pr-delivery` | pr | PR per slice; threads answered and resolved | Required CI green, branch current; UI visually reviewed; migrations fully reviewed and re-checked |
| 9 | Close | `openspec-archive-change`, `bd close`, `retro` | docs | Beads closed after their PR merges; parents after children | PR or commit cited; specs match what shipped |

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
- **In parallel**: use `parallel-pr-delivery`: one claimed bead, worktree and branch per agent; explicit file ownership,
  one integration owner per shared file, and a merge order that minimises conflicts.
- **Review with a different vendor** than the one that implemented. Same-model review misses the same mistakes.
- Non-UI PRs may auto-merge after findings are addressed. UI PRs require actual desktop light/dark and 375px screenshot
  review; migrations require full review and re-check. Update stale branches with `gh pr update-branch --rebase`.

## 5. Gates that always apply

- Prose (one-pagers, design docs, PR bodies): `humanizer`.
- Code diffs: `deslop`. UI: `npx impeccable detect <changed files>`.
- "Done" means: the command you ran and what it printed. No unobserved claims.
- New work found mid-task becomes a bead (`--deps discovered-from:<id>`), not a TODO comment or scope creep.
