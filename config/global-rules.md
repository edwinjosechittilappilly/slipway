## Working rules (managed by Slipway: edit `config/global-rules.md` in your Slipway checkout, then `slipway update`)

**Flow.** Non-trivial work goes idea → grill → spec → tickets → implement → PR → review → merge. The `ship-flow` skill has
the map and says which skill, tool and model role fits each stage. Use it when unsure what comes next.

**Before code**
- Restate the goal and the acceptance check in one line each. Ask only what the repo and tools cannot answer.
- Read `GLOSSARY.md` / `CONTEXT.md` and `docs/adr/` when present, and use their terms.
- If `.beads/` exists: `bd prime`; track each plan item, spec task, review and finding with description, acceptance
  and dependencies. Split large beads into dependent children. Claim `bd ready` work with `bd update <id> --claim`.
  Discovered work becomes a bead (`--deps discovered-from:<id>`), not a TODO.
- Propose OpenSpec before behaviour changes when `openspec/` exists; include applicable audit findings in the change.

**While coding**
- Make the smallest change that meets the acceptance check. Prefer boring code. Delete what your change makes dead.
- Write tests that would catch a real regression; use TDD at agreed seams (`tdd` skill).
- Never commit secrets, push to `main`, force-push a shared branch, or skip hooks.
- Run parallel beads through `parallel-pr-delivery`, with worktrees, branches and explicit file ownership.
- Back up user data before migration or destructive operations; rehearse them on a copy.
- For UI work, keep a dev server running from source across restarts and share its URL.
- New repos are licensed Apache-2.0: full `LICENSE` text, `license` field in package metadata, README badge and
  footer, and the docs-site copyright line.

**Before saying done**
- Run the narrowest check that proves the change. Report the command and what it printed; claim nothing you did not
  observe.
- Run `deslop` on your diff and `humanizer` on prose you wrote (PR bodies, docs). For UI changes run
  `npx impeccable detect` on the changed files.
- Ship PRs through `parallel-pr-delivery` for independent review, finding beads, threads, CI and UI/migration gates.
  Write the PR with the `pr` skill.
- Close code-changing beads after their PR merges, citing the PR or merge commit; close decision, spike and research
  beads when acceptance is met. Close parents after all children close.

**Writing.** Lead with the answer. Numbers over adjectives. No filler, hype or hedging. Diagrams come from
`arch-diagram` (C4 level stated, legend present, left-to-right flow).
