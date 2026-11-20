# How Slipway compares

Slipway sets up and maintains a machine's agent environment and wires repositories for one delivery flow. It is not
an application template (that is ShipShape) and not a parallel-agent supervisor (that is Agent Deck or Gas City).

## Against the approaches it replaces

Each earlier approach solved one slice well. Slipway keeps those pieces and fills the gaps between them.

| | ShipShape stack | patentkit | research-agent-harness `pakage/` | Ad-hoc machine setup (before Slipway) |
|---|---|---|---|---|
| Scope | One repo: full-stack template, CI gate, agent hooks, 8 skills, `repo-audit` score | One domain: patent workspaces | One toolkit: paper and slide builders copied into a project | Whatever was installed by hand |
| Install | "Use this template", or `npx skills add …/shipshape-stack` for the skills | `make install` → `uv tool install --editable`; `make new` per workspace | `python3 pakage/install.py install <dir> --profile all` | `npx skills add …`, `claude plugin install …`, editing `~/.omp/agent/config.yml` |
| Update path | Per repo, by hand | `make upgrade` pushes kit updates into every workspace, with `upgrade-dry` | `install.py update` (only files still matching their recorded hash) | None; renamed upstream skills kept loading |
| Pinning and review | Skills tracked at whatever `npx skills` fetched | Kit version only | SHA-256 of installed files; no upstream source | None |
| Multi-harness | Hooks for Claude Code, Codex, Cursor | Claude Code, omp, AGENTS.md | One agent dir at a time (`--agent-dir`) | Three separate setups (omp, Claude plugins, Codex) |
| Safety for your edits | n/a (template) | Never overwrites workspace files | Refuses to overwrite edited files without `--force` | No rule |

What Slipway kept and fixed:

| From | Kept | Fixed |
|---|---|---|
| ShipShape | Skills distributed through `npx skills`; "one command proves it" (`make check`) | Machine-wide, not per repo; ShipShape's unique skills (`repo-audit`, `ci-triage`, test skills) installed as a pack, overlapping ones left out |
| patentkit | `uv tool install --editable`, `doctor`, dry-run upgrades, never overwrite | Generic packs instead of one domain |
| `pakage/install.py` | Manifest + recorded hashes + refuse-to-overwrite | Applied to config keys (3-way rule) and managed blocks, not only files; upstream sources pinned by commit and bumped by PR |
| Ad-hoc setup | The shared `~/.agents/skills` folder, the omp model roles | Pins, stale-skill pruning (`to-prd`, `to-issues`, `diagnose`, `caveman`, `zoom-out`), one manifest for every channel, Beads and OpenSpec, role routing |

## Against other tools

| Option | What it does well | Why Slipway is still needed |
|---|---|---|
| [chezmoi](https://www.chezmoi.io/), [Nix Home Manager](https://github.com/nix-community/home-manager) | Any dotfile or package, reproducibly | No notion of skill sources, omp records or project wiring. Slipway can run inside a chezmoi-managed home. |
| [rulesync](https://github.com/dyoshikawa/rulesync), [agentsync](https://github.com/x0c/agentsync) | Translate one rules/skills source into each harness's format | Slipway avoids translation: one skill copy in `~/.agents/skills`, managed blocks for rules. It also installs tools and routes roles. |
| [Superpowers](https://github.com/obra/superpowers) | A complete brainstorm → plan → TDD methodology | A methodology, not an environment manager. It overlaps Matt Pocock's skills, so Slipway ships one of the two. |
| [Gas City](https://github.com/gastownhall/gascity) | Formula-driven agent teams over Beads, with an omp provider | The layer after Slipway; installable as the `factory` pack. Needs a Dolt server, a supervisor and tmux. |
| [Vibe Kanban](https://github.com/BloopAI/vibe-kanban), Conductor | Visual boards for parallel agents | Neither lists omp; Vibe Kanban is community-maintained since Bloop shut down, and Conductor joined Meta in November 2026. beads-ui plus `slipway run --bead` covers the board for an omp-first setup. |

## Usability scorecard

| Criterion | Before | With Slipway | Remaining gap |
|---|---|---|---|
| Time to a working setup on a new Mac | Hours of copy-paste from READMEs | One command; prompts only for the Homebrew password; logins listed at the end | Harness logins stay manual (they are OAuth flows) |
| Commands to learn | A dozen tool-specific ones | `install`, `doctor`, `update`, `init`; `roles`/`run` when routing | Beads and OpenSpec have their own CLIs; the skills drive them |
| Seeing state | None | `doctor` shows installed, outdated, drifted, stale and missing-login items | No GUI; `doctor --markdown` for sharing |
| Recovering from a failure | Re-run and hope | Each component installs independently; the summary prints the exact retry command | A half-finished upstream installer is that installer's to clean up |
| Updating safely | Silent `npx skills update` | Weekly PR with changed `SKILL.md` files; `update` moves to the reviewed lock | Homebrew versions are observed, not pinned |
| Forking for someone else | Rewrite everything | Copy `profiles/edwin.toml`, change model ids, `install --profile you` | Forkers still choose their own model ids |
