# Changelog

All notable changes are recorded here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `parallel-pr-delivery` skill for isolated parallel slices, independent review and protected-branch merge gates.
- Documentation site (MkDocs Material): home, getting started, daily use, ship flow, commands, plus the existing
  reference pages and ADRs. `make docs` builds it, `make docs-serve` previews it, and the `docs` workflow publishes
  it to <https://edwinjosechittilappilly.github.io/slipway/> on every push to `main`.
- README and docs screenshots of real output: omp answering "what's next?", the Beads board for the same feature,
  and `slipway doctor`.

### Changed

- Global rules and delivery skills track review findings and close beads only after merge.
- README cut from 226 to about 80 lines; detailed tables moved to the docs site.
- Docs site uses the full window width and always shows the copy button on code blocks.

## [0.1.0] - 2026-11-20

### Added

- `slipway` CLI: `install`, `update`, `doctor`, `packs`, `profile new`, `init`, `roles`, `run`, `ui`, `lock`,
  `uninstall`.
- `install.sh` bootstrap for public (`curl … | bash`) and private (`gh api … | bash`) installs; `--dry-run` changes
  nothing; Homebrew is added to the shell profile for new terminals.
- Manifest with 16 packs: harnesses (omp, Claude Code, Codex, Gemini, Cursor, opencode), Matt Pocock's skills,
  anti-slop (humanizer, deslop, impeccable), Beads + beads-ui, OpenSpec, draw.io + pandoc, ShipShape skills,
  TypeSafe Jev, Anthropic document skills, Trail of Bits security skills, Agent Deck, Gas City.
- Lockfile with pinned skill commits and npm versions; weekly `upstream-watch` PRs and a real-install job.
- 3-way ownership rule for omp settings (fails closed if omp's config cannot be read), hash-marked managed blocks,
  recorded symlinks, a config snapshot before every run, and `--force` backups kept outside harness folders.
- Skills: `ship-flow`, `exec-one-pager`, `design-doc`, `arch-diagram` (IBM, C4 and brand themes), `spec-to-beads`.
- Role agents for omp and Claude Code; profiles `edwin` (model roles; `daily`, `frugal`, `deep` presets),
  `claude-code` and `codex`; user profiles in `~/.config/slipway/profiles/`, captured from the live omp setup.
- `slipway init` records repos; `slipway update` refreshes their managed AGENTS.md block.
