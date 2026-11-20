# 3. Pinned skills via npx skills

- **Status:** Accepted
- **Date:** 2026-11-20

## Context

Skills are instructions executed with agent permissions. Unreviewed updates and old names left on disk can change behavior or cause duplicate discovery.

## Decision

List chosen upstream skills explicitly in `slipway.toml` and pin each source commit in `slipway.lock.json`. Install with [npx skills](https://github.com/vercel-labs/skills) using `owner/repo@sha`, global scope and, by default, `-a pi claude-code`. The shared copy is in `~/.agents/skills`; Claude's directory links to it. The TypeSafe skill is an explicit exception: its skills component targets `pi`, while Claude receives the TypeSafe plugin.

`slipway lock --refresh` resolves upstream heads and writes compare links and the changed `SKILL.md` paths. The `upstream-watch` workflow runs it every Monday and opens (or updates) one PR; review it like a dependency bump before merging. The lock also records npm versions (installed exactly) and Homebrew versions (observed only; Homebrew cannot pin).

Detect stale names from the skills installer's lock, not a hardcoded rename list. `slipway update --prune` removes only skills Slipway itself installed that the manifest no longer lists. Same-source skills installed before Slipway (for example renamed Matt Pocock skills) are reported by `slipway doctor` with the exact `npx skills remove … -g -y` command; Slipway never deletes them on its own. See [the catalogue](../skills.md) for known renames.

## Consequences

- Skill commits are reviewable; a missing pin falls back to an unpinned source. The installer CLI itself is separately versioned.
- Slipway tracks content hashes for installed skills and avoids updating locally edited tracked skills without `--force`; same-name skills attributed to another source are also protected. Pruning uses the upstream installer and is not a general-purpose backup of edited stale skills; review the stale list first.
- Own skills are symlinked from the checkout, not source-pinned by this mechanism. Impeccable uses its own installer. OpenSpec generates its own skills during project initialization.
- Avoid installing the Matt Pocock pack through a plugin marketplace as well as `npx skills`: [upstream warns](https://github.com/mattpocock/skills) that multiple install methods duplicate skills. This does not prohibit the separate TypeSafe Claude plugin.

## Alternatives considered

- Unpinned `npx skills`: convenient, but updates bypass commit review.
- Plugin-marketplace distribution for the same pack: convenient updates for a single harness, but duplicate installations and divergent harness coverage.
- Copy every skill into this repo: direct ownership, but manual upstream synchronization and a larger maintenance burden.
