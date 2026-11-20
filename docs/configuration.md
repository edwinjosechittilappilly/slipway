# Configuration

Slipway reads three TOML files, each an overlay on the one before:

| Layer | File | Committed | Use it for |
|---|---|---|---|
| Base | `slipway.toml` | yes | Packs, components, provider-neutral roles. Shared by everyone who forks. |
| Profile | `~/.config/slipway/profiles/<name>.toml`, else `profiles/<name>.toml` in the checkout | yours: no; shipped: yes | One person's choices: model ids, extra packs, role overrides. |
| Local | `~/.config/slipway/config.toml` | no | This machine: which profile, packs on or off, one-off overrides. |

Create your profile with `slipway profile new <name>`: it captures the omp model roles, agent overrides, presets and
fallback chains you already use, or `--copy edwin|claude-code|codex` starts from a shipped one. It lives outside the
checkout, so `slipway update` can always `git pull`. Choose a profile with `slipway install --profile <name>`
(remembered in the local file), `SLIPWAY_PROFILE=<name>`, or `profile = "<name>"` in the local file.

## Merge rules

- Tables merge key by key, so an overlay can change one field of a role without repeating the rest.
- `[[component]]` entries merge by `id`: same id updates fields, a new id adds a component.
- `enable_packs = [...]` and `disable_packs = [...]` adjust `settings.default_packs`. They accumulate across layers.
- Lists and scalars replace.
- `enabled = false` on a `[[component]]` (matched by `id`) skips that one component everywhere: install, update,
  doctor. The shipped `claude-code` and `codex` profiles use it to switch off omp.

Example local file:

```toml
profile = "edwin"
enable_packs = ["security", "parallel"]
disable_packs = ["harnesses-extra"]

[roles.implement]
harness = "codex"          # try Codex as the implementer on this machine

[[component]]
id = "impeccable"
args = ["--no-hooks"]      # install impeccable without its editor hooks
```

## `[settings]`

| Key | Default | Meaning |
|---|---|---|
| `skill_agents` | `["pi", "claude-code"]` | `npx skills -a` targets. `pi` writes to `~/.agents/skills` (omp, Codex, Pi read it); `claude-code` links into `~/.claude/skills`. |
| `skills_cli` | `"skills"` | npm package for the skills CLI; its version comes from the lock. |
| `default_packs` | core … routing | Packs `install`, `update` and `doctor` use when no `--packs` is given. |

## `[project]` (used by `slipway init`)

| Key | Default | Meaning |
|---|---|---|
| `openspec_scope` | `"global"` | `global` installs OpenSpec skills once per machine; `project` commits them into the repo (better for teams). |
| `beads_stealth` | `false` | `true` keeps `.beads/` out of git (`bd init --stealth`), for personal tracking in shared repos. |
| `beads_metrics` | `false` | `false` runs `bd metrics off` after `bd init`; Beads shares anonymous command counts by default. |

`slipway init` records each repo it sets up. `slipway update` then refreshes the managed `AGENTS.md` block and the
`CLAUDE.md` import in every recorded repo (edited blocks are kept), and `slipway doctor` lists repos whose block is
older than the template. Files under `docs/agents/` are yours after `init` creates them.

## Components

Every component has `id`, `pack`, `kind` and `why`. Kind-specific fields:

| Kind | Required | Optional |
|---|---|---|
| `brew`, `cask` | `name` | `bin`, `check`, `platforms` |
| `npm` | `name` | `bin` |
| `script` | `install` | `bin`, `upgrade`, `check` |
| `skills` | `source` (`owner/repo`), `skills` | `agents` (overrides `skill_agents`), `args` |
| `impeccable` | `providers` | `args` (e.g. `--no-hooks`) |
| `claude-plugin` | `marketplace`, `plugin` | |
| `omp-plugin` | `plugin` | `marketplace`, `name` (as listed by `omp plugin list`) |
| `link` | `dir`, `targets` | `pattern` (default `*`: skill folders) |
| `block` | `file`, `targets` (`omp`, `claude`, `codex`, `gemini`) | |
| `omp-config` | | values come from the `[omp]` table |

`check` is a shell command whose exit status 0 means "installed", for tools found by other means (for example
`test -d /Applications/draw.io.app`). `requires = ["bin", ...]` adds prerequisites; a missing prerequisite skips the
component instead of failing the run.

Link targets: `agents-skills` (`~/.agents/skills`), `claude-skills`, `claude-agents`, `omp-agents`, `omp-skills`.
Targets for a harness are written only when that harness's CLI or config folder exists.

## `[roles.<name>]`

| Key | Meaning |
|---|---|
| `harness` | `omp`, `claude`, `codex`, `gemini`, `cursor-agent`, `opencode` |
| `model` | Harness model id, an omp role alias such as `@plan` (resolved from your omp config), or `default` |
| `alt` | `{ harness = "model" }` used by `slipway run <role> --harness <harness>` |
| `why` | Shown by `slipway roles`; keep it honest |

## `[omp]`

Any omp setting key. Records (`modelRoles`, `task.agentModelOverrides`, `modelPresets`, `retry.fallbackChains`) merge
entry by entry with the 3-way rule; scalars (`defaultThinkingLevel`) are compared as a single value. Slipway compares
against what your global `~/.omp/agent/config.yml` sets, never omp's built-in defaults.

## Lock

`slipway.lock.json` is written by `slipway lock --refresh` (and the weekly workflow), not by hand:

```json
{
  "skills": { "mattpocock/skills": { "commit": "abeeaf9…" } },
  "npm":    { "skills": "1.9.0", "@fission-ai/openspec": "2.1.1" },
  "brew":   { "beads": "1.3.4" }
}
```

Skill commits and npm versions are installed exactly. Homebrew cannot pin versions, so `brew` entries record what CI
tested; `doctor` shows yours.

## State

`~/.local/state/slipway/state.json` (or `$XDG_STATE_HOME/slipway/`) holds what Slipway last wrote: symlinks and their
component, omp values, a content hash per installed skill, and which tools Slipway installed (so `uninstall` can tell
you what it added). Deleting it is safe; the next run re-adopts matching values and treats differing ones as yours.
