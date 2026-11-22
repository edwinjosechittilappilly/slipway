## Working rules (managed by Slipway: edit `config/global-rules.md` in your Slipway checkout, then `slipway update`)

**Flow.** Non-trivial work goes idea → grill → spec → tickets → implement → review → PR. The `ship-flow` skill has
the map and says which skill, tool and model role fits each stage. Use it when unsure what comes next.

**Before code**
- Restate the goal and the acceptance check in one line each. Ask only what the repo and tools cannot answer.
- Read `GLOSSARY.md` / `CONTEXT.md` and `docs/adr/` when present, and use their terms.
- If `.beads/` exists: run `bd prime`, take work from `bd ready`, claim it with `bd update <id> --claim`. Work you
  discover becomes a bead (`bd create "…" --deps discovered-from:<id>`), not a TODO comment.
- If `openspec/` exists and the change alters behaviour, propose an OpenSpec change before writing code.

**While coding**
- Make the smallest change that meets the acceptance check. Prefer boring code. Delete what your change makes dead.
- Write tests that would catch a real regression; use TDD at agreed seams (`tdd` skill).
- Never commit secrets, push to `main`, force-push a shared branch, or skip hooks.
- New repos are licensed Apache-2.0: full `LICENSE` text, `license` field in package metadata, README badge and
  footer, and the docs-site copyright line.

**Before saying done**
- Run the narrowest check that proves the change. Report the command and what it printed; claim nothing you did not
  observe.
- Run `deslop` on your diff and `humanizer` on prose you wrote (PR bodies, docs). For UI changes run
  `npx impeccable detect` on the changed files.
- Close the bead with a one-line reason. Write the PR with the `pr` skill.

**Writing.** Lead with the answer. Numbers over adjectives. No filler, hype or hedging. Diagrams come from
`arch-diagram` (C4 level stated, legend present, left-to-right flow).
