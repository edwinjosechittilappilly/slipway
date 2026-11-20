# 4. omp-first, multi-harness routing

- **Status:** Accepted
- **Date:** 2026-11-20

## Context

Exploration, implementation, review and writing need different trade-offs. A single provider is not required for every role, and parallel execution should not require a new task model immediately.

## Decision

Use [omp](https://github.com/can1357/oh-my-pi) as the primary harness. Its model roles, task agents, `task.agentModelOverrides` and model presets route work inside omp. Its native Jev-backed judge supports judge-assisted features; it is distinct from an experimental router plugin. The base manifest is provider-neutral, while `profiles/edwin.toml` supplies model IDs and presets. See the [role matrix](../harnesses.md).

Use `slipway run <role>` to launch a role's configured harness, or `slipway run --bead <id>` to select from a `role:<name>` label and claim the work. This is a handoff, not a parallel scheduler. Add [Agent Deck](https://github.com/asheshgoplani/agent-deck) for parallel sessions; consider [Gas City](https://github.com/gastownhall/gascity) for formula-driven teams on Beads once its additional operations are warranted.

The `jev-router` pack is opt-in. [oh-my-jev](https://github.com/apetcu/oh-my-jev) is early; its prompt router requires `OMJ_ROUTER=1` and its tool gate is a separate feature. Native roles and the judge do not require installing that plugin.

## Consequences

- Routing can use different model vendors for implementation and review, but availability, model IDs, credentials and pricing can change.
- omp configuration changes preserve independently edited entries unless forced. Base model aliases resolve against the user's omp config; the base manifest does not set providers.
- Bead handoff claims work and passes a prompt; it does not automatically close a bead on process exit. A harness override uses a configured alternative where available, otherwise its default for unresolved aliases.
- Gas City adds a supervisor, Dolt server and tmux; installation alone does not configure orchestration.

## Alternatives considered

- [Claude Code](https://code.claude.com/docs/en/sub-agents) or [Codex](https://developers.openai.com/codex/concepts/customization) alone: useful second and third vendors, but the selected default needs multi-provider role routing.
- [opencode](https://opencode.ai/docs/agents/): open multi-provider fallback with per-agent models; another viable primary if omp is unsuitable.
- An automatic Jev router everywhere: more moving parts and early projects before measured need. Native role mapping is explicit and easier to inspect.
