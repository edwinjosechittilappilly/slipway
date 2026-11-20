# Contributing

Agents: read [AGENTS.md](AGENTS.md). Humans: the same rules apply; this page is the short version.

## Set up

```bash
git clone https://github.com/edwinjosechittilappilly/slipway && cd slipway
make check        # lint + tests + dry-run install into a scratch HOME
```

Python 3.11+ and `uv` are the only requirements; the CLI uses the standard library only.

## Common changes

| You want to | Change |
|---|---|
| Add a tool or skill pack | A `[[component]]` in `slipway.toml` with a `why`, then `make lock` |
| Change your models | `profiles/<you>.toml`, never the base manifest |
| Add a component kind | Handler in `src/slipway/kinds.py` + a test in `tests/test_kinds.py` |
| Add or edit a Slipway skill | `skills/<name>/SKILL.md`; the contract test checks frontmatter and links |
| Change a diagram | Edit `docs/diagrams/<name>.json`, run `make diagrams`, commit all three files |

## Pull requests

- Conventional Commit titles (`feat:`, `fix:`, `docs:`, `chore(lock):`).
- Say what you verified and paste the command output that proves it.
- Upstream bumps arrive from the `upstream-watch` workflow; review the changed `SKILL.md` files before merging,
  because skills are prompts that run with your agent's permissions.
