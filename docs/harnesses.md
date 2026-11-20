# Harnesses and routing

omp is the primary harness; Claude Code and Codex provide additional vendors. The base manifest does not prescribe provider model IDs. Select Edwin's profile to apply its model-role choices, or define your own profile. `slipway roles` shows the effective matrix and availability.

## Role matrix

The Edwin column shows the profile overlay on the base; all other roles are inherited. `default` means the harness's configured default. An omp alias resolves against the live omp config, not directly against this table.

| Slipway role | Base harness → model | Edwin harness → model | Edwin model behind alias |
|---|---|---|---|
| explore | omp → `@smol` | omp → `@scout` | `google-antigravity/gemini-3.8-flash:low` |
| plan | omp → `@plan` | omp → `@plan` | `openai-codex/gpt-6.1-sol:high` |
| implement | omp → `@task` | omp → `@task` | `openai-codex/gpt-6.1-terra:auto` |
| review | omp → `@slow` | omp → `@review` | `anthropic/claude-opus-5-5:high` |
| issues | omp → `@smol` | omp → `@smol` | `openai-codex/gpt-6-luna:low` |
| pr | omp → `@commit` | omp → `@commit` | `openai-codex/gpt-6-luna:medium` |
| docs | omp → `default` | omp → `@draft` | `anthropic/claude-sonnet-5-5:medium` |
| design | Claude Code → `opus` | Claude Code → `opus` | Claude alias `opus` |

Edwin's remaining omp roles are `slow` = `gpt-6.1-sol:high`, `tiny` and `memory` = `gpt-6-luna:low`, and `advisor` = `claude-opus-5-5:high` (with the provider prefixes shown above). Model availability depends on credentials and the provider. Alternatives declared in the manifest include Codex `default` and Claude `sonnet` for implementation, Codex `default` and Claude `opus` for review, and omp `default` for design.

## Inside omp

[omp model roles](https://github.com/can1357/oh-my-pi/blob/main/docs/models.md) map aliases such as `@plan` to selectors and optional thinking levels. `review`, `draft` and `scout` in Edwin's profile are custom aliases, not claims that omp has those built-in model roles. Base `[omp]` is empty; it does not create provider mappings.

[Task agents](https://github.com/can1357/oh-my-pi/blob/main/docs/task-agent-discovery.md) have frontmatter models. `task.agentModelOverrides` takes precedence over agent frontmatter, which takes precedence over the parent model. Edwin maps `task` → `@task`, `reviewer` and `security-reviewer` → `@review`, `scout` → `@scout`, `sonic` and `issue-writer` → `@smol`, `drafter` → `@draft`, `planner` → `@plan`, and `pr-author` → `@commit`. The routing pack links its own omp agent files; some override targets are bundled agents rather than files in this repo.

Edwin ships `daily`, `frugal`, and `deep` presets. Switch inside omp with `/modelpreset switch daily` (or `frugal` / `deep`); see the profile for every selector. [Fallback chains](https://github.com/can1357/oh-my-pi/blob/main/docs/settings.md) are configured under `retry.fallbackChains`, keyed by role, model, or provider wildcard; an empty list disables that chain. Slipway's shipped base and Edwin profile do **not** define chains. Configure them explicitly if needed.

Slipway merges managed omp record entries using live, desired and last-written values. A local change wins unless forced. `slipway run` passes omp aliases through unchanged (`omp --model @review`), so omp applies the role's thinking level and fallback chain itself; built-in roles you have not assigned fall back to omp's default model.

## Claude Code subagents

The routing pack links the repository's Claude subagents: `explorer` and `issue-writer` use `haiku`; `planner` and `cross-reviewer` use `opus`. Claude subagent frontmatter controls the model, independently of omp's aliases and overrides. See [Claude Code subagents](https://code.claude.com/docs/en/sub-agents). The Slipway `design` role launching Claude `opus` is a separate role-to-harness mapping.

## From one launch to parallel work

1. **Today:** `slipway run implement` launches the mapped harness; `slipway run --bead <id>` reads the bead, picks the first `role:<name>` label or defaults to `implement`, claims it, and passes its description and available acceptance/design/spec fields. The prompt asks the agent to close or note the bead; Slipway does not itself do that after exit. Use `--no-claim` when a claim is inappropriate. A role or harness override can change the launch; an unmapped alternative uses that harness's default.
2. **Parallel sessions:** `slipway install --packs parallel` installs [Agent Deck](https://github.com/asheshgoplani/agent-deck), a terminal session manager with worktree support. Configure and launch sessions yourself; installing the pack does not start them.
3. **Formula-driven teams:** `slipway install --packs factory` installs [Gas City](https://github.com/gastownhall/gascity). It uses Beads graphs and has a [built-in omp provider](https://raw.githubusercontent.com/gastownhall/gascity/main/internal/worker/builtin/profiles.go). Set up a city and its rigs separately; using the same Beads substrate does not automatically connect an existing project. Expect a Dolt server, supervisor and tmux. Review provider permission defaults before use.

## Alternatives to omp

Recommendation: keep omp primary; use Claude Code and Codex as second and third vendors, and opencode as the open multi-provider fallback. Model routing and skills capabilities of Amp, Droid, Gemini and Cursor beyond the cited integration are not verified here.

| Harness | Strength | Limit or reason not primary |
|---|---|---|
| [Claude Code](https://code.claude.com/docs/en/sub-agents) | Native Claude features and model-selectable subagents. | Anthropic-centered; not the chosen multi-provider router. |
| [Codex CLI](https://developers.openai.com/codex/concepts/customization) | OpenAI-native workflow, profiles and skills. | Different vendor for cross-checks; not the selected cross-provider router. |
| [opencode](https://opencode.ai/docs/agents/) | Open, multi-provider and per-agent model selection. | Good fallback; switching would require migrating omp-specific configuration. |
| [pi](https://github.com/earendil-works/pi) | Minimal multi-provider core with extensions. | No built-in subagents or permission system in the researched version. |
| [Amp](https://raw.githubusercontent.com/gastownhall/gascity/main/internal/worker/builtin/profiles.go) | Available as a Gas City provider. | Routing and skill details not verified. |
| [Factory Droid](https://vibekanban.com/docs/supported-coding-agents) | Supported by Vibe Kanban. | Routing and skill details not verified. |
| [Gemini CLI](https://raw.githubusercontent.com/gastownhall/gascity/main/internal/worker/builtin/profiles.go) | Google model access; optional Slipway harness. | Routing details not verified. |
| [Cursor CLI](https://vibekanban.com/docs/supported-coding-agents) | Terminal access to Cursor's agent; optional Slipway harness. | Routing details not verified. |

## Jev and experimental routers

[Jev](https://github.com/typesafe-ai/skills) is TypeSafe's System One judge: it makes typed judgments for classification and similar decisions, rather than being the coding agent itself. omp's [judge model role](https://github.com/can1357/oh-my-pi/blob/main/docs/settings.md) supports native judge-dependent features including find-tool selection, judged rules, auto-thinking and task prewalk. The exact feature configuration and provider credentials matter; the shipped profile does not set a custom judge. `task.agentPrewalkAuto` can use the judge to decide whether a task merits a cheaper handoff ([agent docs](https://github.com/can1357/oh-my-pi/blob/main/docs/task-agent-discovery.md)).

The opt-in `jev` pack installs the `typesafe-ai` skill into the shared skills location and the TypeSafe Claude plugin. These teach use of TypeSafe's API; they are separate from omp's native judge and from the `jev-router` pack. Authentication may require `TYPESAFE_API_KEY` or omp's TypeSafe token; check `slipway doctor` and provider documentation.

| Router | Maturity and behavior |
|---|---|
| [oh-my-jev](https://github.com/apetcu/oh-my-jev) | `jev-router` installs this early plugin. Tool-call gate on by default; per-prompt routing off unless `OMJ_ROUTER=1`. Upstream has evals but reported no speedup on Anthropic. |
| [model-router](https://github.com/Akurganow/model-router) | Separate early project routing subagent spawns, not the main prompt; not installed by Slipway. |
| [omp-plugin-jev-router](https://github.com/atulify/omp-plugin-jev-router) | Small interactive-prompt router written for an older omp version; not installed. |
| [omp-jev](https://github.com/thejorgg/omp-jev) | Archived; not installed. |

Do not assume a router saves cost or latency without measuring the workload. Native roles and judge features work independently of these plugins.
