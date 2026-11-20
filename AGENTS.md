# AGENTS.md

Instructions for coding agents working on the Slipway repository itself. (Slipway writes a different, managed block
into your user-level AGENTS.md; that content lives in `config/global-rules.md`.)

## Map

| Path | What |
|---|---|
| `slipway.toml` | Base manifest: packs, components, roles. Provider-neutral. |
| `profiles/*.toml` | Personal overlays (model ids, extra packs). |
| `slipway.lock.json` | Pins. Written by `slipway lock --refresh`, never by hand. |
| `src/slipway/` | CLI (stdlib only, Python 3.11+). `kinds.py` = one handler per component kind. |
| `skills/` | Slipway's own skills, symlinked into harness folders by `slipway install`. |
| `agents/omp`, `agents/claude` | Role agents. |
| `config/global-rules.md` | The managed block written into every harness's user-level instructions. |
| `templates/project/` | Files `slipway init` adds to a repo. |
| `docs/` | One-pager, design doc, ADRs, catalogues. Diagrams are generated from `docs/diagrams/*.json`. |
| `tests/` | `unittest`, temporary HOME, fake runner. No network. |

## Commands

```bash
make test       # unit tests (PYTHONPATH=src:tests python3 -m unittest discover -s tests -t tests)
make lint       # ruff check + ruff format --check + shellcheck
make check      # lint + test + dry-run install in a scratch HOME
make diagrams   # regenerate docs/diagrams/*.svg|.drawio from their .json specs
```

## Rules

- Stdlib only in `src/` and skill scripts. No new runtime dependencies.
- Every external command goes through `shell.Runner` so tests can fake it and `--dry-run` can show it.
- Never write user config without the 3-way rule (`merge.py`), block hashes (`blocks.py`) or link records
  (`links.py`). A change that could overwrite a user's edit needs a test proving it does not.
- Adding a tool or skill pack is a manifest edit plus a `why`. Adding a kind needs a handler and a test.
- Upstream skill names must stay unique across packs; `tests/test_manifest.py` enforces it.
- Verify CLI flags of upstream tools against their `--help` before encoding them; cite the version in the PR.
- Keep docs in step with behaviour. Prose: lead with the answer, numbers over adjectives, no hype words.

## Definition of done

`make check` passes; behaviour changes have a test that fails without them; README or docs updated when a command,
flag or default changes; CHANGELOG entry under Unreleased.
