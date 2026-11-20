# Commands

Every command that changes something accepts `--dry-run` (show, change nothing) and `--force` (replace values you
changed, after backing them up). `--profile <name>` selects a profile for one run.

## Machine

| Command | What it does |
|---|---|
| `slipway install [--packs a,b] [--all] [--prune]` | Install every component in the selected packs. Safe to re-run: present tools are left alone. |
| `slipway update [--latest] [--prune] [--no-pull]` | `git pull` the Slipway checkout, move components to the lock, refresh rules blocks in repos you set up. `--latest` ignores the lock. `--prune` removes skills Slipway installed that the manifest no longer lists. |
| `slipway doctor [--json \| --markdown]` | Status of every component, environment checks (Node, gh login, Jev key, omp roles), and a fix list. `--markdown` prints a shareable summary without paths. |
| `slipway packs` | Packs, whether each is on by default, and what it installs. |
| `slipway profile new <name> [--copy p] [--dry-run]` | Write `~/.config/slipway/profiles/<name>.toml` from your current omp setup (or a copy of a shipped profile) and select it. |
| `slipway uninstall` | Remove the links, rules blocks and omp settings Slipway wrote. Tools stay installed. |

## Repository

| Command | What it does |
|---|---|
| `slipway init [path] [--stealth] [--tools ids] [--no-beads] [--no-openspec]` | Set up Beads, OpenSpec, `docs/agents/*` and the AGENTS.md block. `--stealth` keeps `.beads/` out of git. |
| `slipway ui [path]` | Open the Beads board (beads-ui) in your browser. |

## Routing

| Command | What it does |
|---|---|
| `slipway roles` | The job → agent → model table, with what each omp alias resolves to. |
| `slipway run <role> ["prompt"] [--harness h] [--print]` | Open the agent and model mapped to a role. `--harness` sends it to another agent; `--print` runs non-interactively. |
| `slipway run --bead <id> [--no-claim]` | Claim a bead and hand it, with its description and acceptance check, to the agent its `role:` label selects. |

## Lock

| Command | What it does |
|---|---|
| `slipway lock` | Show the pinned skill commits and tool versions. |
| `slipway lock --refresh [--only skills\|npm\|brew] [--markdown file]` | Check upstream, rewrite the lock, print what changed with diff links. The weekly workflow runs this. |

## Exit codes

`0` success · `1` a component failed (the summary prints the retry command) · `2` the manifest or a profile is invalid.
