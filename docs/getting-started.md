# Getting started

## 1. Preview

```bash
curl -fsSL https://raw.githubusercontent.com/edwinjosechittilappilly/slipway/main/install.sh | bash -s -- --dry-run
```

This changes nothing. It says what the bootstrap would install, clones Slipway to a temporary folder, and lists every
component and command `slipway install` would run.

## 2. Install

```bash
curl -fsSL https://raw.githubusercontent.com/edwinjosechittilappilly/slipway/main/install.sh | bash
```

Pick a profile if omp is not your main agent:

```bash
... | bash -s -- --profile claude-code     # Claude Code only
... | bash -s -- --profile codex           # Codex, with Claude Code for reviews
```

The script:

1. installs Homebrew if it is missing (asks for your password once) and adds it to your shell profile;
2. installs git, gh, Node and uv if they are missing;
3. clones Slipway to `~/.slipway` and installs the `slipway` command;
4. runs `slipway install`, which backs up your agent config and installs every component in the default packs.

Each component installs on its own. If one fails, the summary prints the exact command to retry and the rest still
install.

## 3. Open a new terminal and check

```bash
slipway doctor
```

`doctor` shows each component as installed (✔), missing (✘), outdated (↑) or changed by you (!), then a **fix** list
with the commands to run. Expect it to list logins:

| Agent | Log in with |
|---|---|
| omp | start `omp`, then `/login` |
| Claude Code | start `claude` once |
| Codex | `codex login` |
| GitHub | `gh auth login` |

## 4. Make the setup yours

```bash
slipway profile new me          # captures the omp model roles and presets you already use
slipway install --dry-run       # shows what would change; nothing should surprise you
```

Your profile lives in `~/.config/slipway/profiles/me.toml`. See [configuration](configuration.md).

## 5. Set up a repository

```bash
cd ~/code/my-app
slipway init
```

This adds:

| Path | What |
|---|---|
| `.beads/` | The task graph (`bd`); `--stealth` keeps it out of git |
| `openspec/` | Specs and change proposals |
| `docs/agents/*.md` | How the engineering skills use Beads, labels and domain docs |
| `AGENTS.md` block | The delivery workflow, in a marked block Slipway keeps current |
| `CLAUDE.md` | Imports `AGENTS.md` so Claude Code reads the same rules |

Then start your agent and ask "what's next?". [Daily use](using.md) walks through a session.

## Remove it

```bash
slipway uninstall               # removes links, rules blocks and omp settings Slipway wrote
uv tool uninstall slipway       # removes the command
```

Tools Slipway installed with Homebrew or npm stay; `uninstall` prints the command for each.
