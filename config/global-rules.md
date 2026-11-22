## Working rules (managed by Slipway: edit `config/global-rules.md` in your Slipway checkout, then `slipway update`)

**Flow.** Non-trivial work goes idea → grill → spec → tickets → implement → review → PR. The `ship-flow` skill has
the map and says which skill, tool and model role fits each stage. Use it when unsure what comes next.

**Before code**
- Restate the goal and the acceptance check in one line each. Ask only what the repo and tools cannot answer.
- Read `GLOSSARY.md` / `CONTEXT.md` and `docs/adr/` when present, and use their terms.
- If `.beads/` exists: `bd prime`; track each plan item, spec task, review and finding as a bead with description,
  acceptance and dependencies. Split large beads into dependent children; claim only `bd ready` work before starting.
- Propose OpenSpec before behaviour changes when `openspec/` exists; fold audits into the change before implementation.

**While coding**
- Make the smallest change that meets the acceptance check. Prefer boring code. Delete what your change makes dead.
- Write tests that would catch a real regression; use TDD at agreed seams (`tdd` skill).
- Never commit secrets, push to `main`, force-push a shared branch, or skip hooks.
- Run independent beads in parallel worktrees and branches with explicit file ownership; assign one integration owner
  per shared file. Plan merge order, sequence only dependencies, and remove worktrees after merge.
- Back up user data before migrations or edits; test destructive operations on copies first.
- For UI work, run a restart-resilient live preview from source, not stale `dist/`, and give the owner its link.
- New repos are licensed Apache-2.0: full `LICENSE` text, `license` field in package metadata, README badge and
  footer, and the docs-site copyright line.

**Before saying done**
- Run the narrowest check that proves the change. Report the command and what it printed; claim nothing you did not
  observe.
- Run `deslop` on your diff and `humanizer` on prose you wrote (PR bodies, docs). For UI changes run
  `npx impeccable detect` on the changed files.
- Per PR, get an independent review from a different model vendor; record every finding as a child bead, fix and
  re-check it, or track the remainder as follow-up beads. Reply to and resolve all review threads, citing fix commits.
- Never push to main. Merge only with required CI passing and the branch up to date; use
  `gh pr update-branch --rebase` when needed. Non-UI PRs may auto-merge after findings are addressed; UI PRs require
  actual visual review of desktop light/dark and 375px screenshots. Data migrations require full review and re-check.
- Close beads only after their PR merges, citing the PR or commit; close parents only after all children close.

**Writing.** Lead with the answer. Numbers over adjectives. No filler, hype or hedging. Diagrams come from
`arch-diagram` (C4 level stated, legend present, left-to-right flow).
