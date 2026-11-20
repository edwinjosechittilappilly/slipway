# Security

## Reporting

Report vulnerabilities privately through GitHub's **Security → Report a vulnerability**. Do not open a public issue.
Include the affected file or command, the commit, reproduction steps and the impact you expect.

## What Slipway does and does not do

- It runs the installers named in `slipway.toml` (Homebrew, npm, `npx skills`, `npx impeccable`, and the documented
  `curl … | sh` installers for omp, Claude Code and Cursor). Review the manifest before running `install`.
- Upstream skills are pinned to commits in `slipway.lock.json`. Skills are prompts that run with your agent's
  permissions; treat a lock bump like a dependency update and read the changed `SKILL.md` files.
- It never reads, stores or transmits credentials. `doctor` checks only whether a login or key exists.
- It writes only: symlinks into harness folders, managed blocks marked `<!-- slipway:begin … -->`, omp settings via
  `omp config set`, and its state file. `slipway uninstall` removes them.
- It sets `DISABLE_TELEMETRY=1` and `DO_NOT_TRACK=1` for every `npx` call.
