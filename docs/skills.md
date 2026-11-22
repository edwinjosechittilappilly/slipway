# Skills catalogue

`slipway.toml` selects skills by pack. Default packs are core, harnesses, engineering, quality, tasks, spec, docs and routing; Edwin's profile also enables shipshape and jev. Other packs are opt-in. A pack selection installs its components, subject to prerequisites. `slipway packs` shows the current selection.

**Invoked by** describes upstream's intended use, not an access restriction: user means an explicit request, model means the agent can select it from its description. For sources without verified invocation metadata, the table says “not verified”; users can still request a skill by name. Local skills have description-based triggers. See [upstream invocation conventions](https://github.com/mattpocock/skills).

## Engineering

Source for every row: [mattpocock/skills](https://github.com/mattpocock/skills).

| Skill | Invoked by | When to use it |
|---|---|---|
| `ask-matt` | User | Choose a suitable skill or workflow. |
| `code-review` | Model | Review changes for defects and regressions. |
| `codebase-design` | Model | Design module boundaries and interfaces. |
| `diagnosing-bugs` | Model | Investigate broken behavior before fixing it. |
| `domain-modeling` | Model | Establish domain language and decisions. |
| `grill-with-docs` | User | Challenge a design and record glossary terms and decisions. |
| `implement` | User | Implement a specified piece of work. |
| `implement-spec` | User | Implement an approved specification. |
| `improve-codebase-architecture` | User | Identify and improve architectural friction. |
| `pr` | Model | Prepare a pull request. |
| `prototype` | Model | Explore an approach with a prototype. |
| `research` | Model | Investigate a question using evidence. |
| `retro` | User | Reflect on completed work and lessons. |
| `setup-matt-pocock-skills` | User | Configure a repository's tracker and documentation conventions. |
| `tdd` | Model | Develop through test-first iterations. |
| `to-spec` | User | Turn an idea into a specification. |
| `to-tickets` | User | Slice a plan into actionable tickets. |
| `triage` | User | Sort and assess incoming work. |
| `wayfinder` | User | Navigate choices and their consequences. |
| `wizard` | Model | Guide an interactive setup or decision. |
| `grill-me` | User | Stress-test an idea through questions. |
| `grilling` | Model | Challenge assumptions and sharpen a plan. |
| `handoff` | User | Prepare context for another session or agent. |
| `teach` | User | Explain a topic or implementation. |
| `wait-what` | User | Pause and clarify a surprising claim or decision. |
| `writing-for-agents` | Model | Write instructions intended for agents. |

## Quality

| Skill | Source | Invoked by | When to use it |
|---|---|---|---|
| `humanizer` | [blader/humanizer](https://github.com/blader/humanizer) | Model | Remove AI-writing tells from prose without changing claims: one-pagers, PR bodies, docs. |
| `deslop` | [cursor/plugins](https://github.com/cursor/plugins) | Model | Strip AI code slop from a branch diff: needless comments, defensive try/catch, `any` casts. |
| `impeccable` | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | User / model | Shape and critique UI; its own installer supplies its skill and commands, including the `detect` tool. |

Impeccable uses its own global installer, not the `skills` source pin mechanism. Its live mode and hooks have separate approval implications; consult [upstream](https://github.com/pbakaus/impeccable).

## Docs

| Skill | Source | Invoked by | When to use it |
|---|---|---|---|
| `drawio-skill` | [Agents365-ai/drawio-skill](https://github.com/Agents365-ai/drawio-skill) | User (`disable-model-invocation: true`) | Edit, import or export draw.io diagrams by hand-off; `arch-diagram` generates new ones. |

## Routing

These six are maintained in this repository (`skills/<name>/SKILL.md`) and linked from the checkout, not downloaded from an `owner/repo` skills source. The model may select them from their descriptions; users may request them directly.

| Skill | Source | Invoked by | When to use it |
|---|---|---|---|
| `ship-flow` | Slipway local | User / model | Navigate idea, spec, implementation, review and closeout. |
| `parallel-pr-delivery` | Slipway local | User / model | Coordinate worktrees, independent PR review, merge gates and cleanup. |
| `exec-one-pager` | Slipway local | User / model | Prepare a decision brief for a stakeholder. |
| `design-doc` | Slipway local | User / model | Write a technical design with alternatives and cross-cutting concerns. |
| `arch-diagram` | Slipway local | User / model | Generate an editable architecture diagram and SVG. |
| `spec-to-beads` | Slipway local | User / model | Convert an approved spec into an epic, dependency graph and role-labeled tasks after approval. |

## Shipshape

Source for every row: [edwinjosechittilappilly/shipshape-stack](https://github.com/edwinjosechittilappilly/shipshape-stack). All four are model-invoked ("Use when …" descriptions).

| Skill | Invoked by | When to use it |
|---|---|---|
| `repo-audit` | Model | Score a repository on ShipShape's 96 checks and plan the PRs that raise it. |
| `ci-triage` | Model | Find the first real failure in a red CI check and fix it. |
| `integration-tests` | Model | Write or debug tests against a real database or service. |
| `playwright-tests` | Model | Write or debug browser end-to-end tests. |

## Jev

| Skill | Source | Invoked by | When to use it |
|---|---|---|---|
| `typesafe-ai` | [typesafe-ai/skills](https://github.com/typesafe-ai/skills) | User / model | Design typed TypeSafe System One judgments; Claude gets the TypeSafe plugin instead of a second skills install. |

## Office

Source: [anthropics/skills](https://github.com/anthropics/skills). Invocation metadata is not verified; check the upstream document-skills license before redistribution.

| Skill | Invoked by | When to use it |
|---|---|---|
| `docx` | Not verified | Create or edit Word documents. |
| `pptx` | Not verified | Create or edit presentations. |
| `pdf` | Not verified | Read, create or manipulate PDFs. |

## Security

Source: [trailofbits/skills](https://github.com/trailofbits/skills). Invocation metadata is not verified; the pack is CC-BY-SA-4.0.

| Skill | Invoked by | When to use it |
|---|---|---|
| `differential-review` | Not verified | Review a change for security impact. |
| `supply-chain-risk-auditor` | Not verified | Assess dependency and supply-chain risk. |
| `sharp-edges` | Not verified | Find interfaces and defaults prone to security mistakes. |
| `agentic-actions-auditor` | Not verified | Audit agentic GitHub Actions workflows. |
| `second-opinion` | Not verified | Get an independent security-oriented assessment. |

## Skills generated by OpenSpec

The `spec` pack installs the [OpenSpec CLI](https://github.com/Fission-AI/OpenSpec), not a `skills` component. During `slipway init`, OpenSpec installs skills for detected or selected harnesses; its configured profile controls the set. Its documented core profile includes explore, propose, apply, update, sync and archive; the precise names and installed profile are controlled by OpenSpec, not the Slipway lock. Project scope can be selected instead of the default global scope. [OpenSpec profiles](https://openspec.dev/docs/profiles).

## Skills deliberately left out

| Option | Reason |
|---|---|
| [Superpowers](https://github.com/obra/superpowers) | Its brainstorm-to-TDD methodology overlaps the selected Matt Pocock workflow; choose one rather than load both by default. |
| ShipShape `pull-request` and `code-review` | Matt's `pr` and `code-review` cover these jobs; do not install a competing `code-review` name or two PR workflows. |
| [stop-slop](https://github.com/hardikpandya/stop-slop), [avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing) | `humanizer` already covers prose; avoid-ai-writing also warns that some installers can omit its references. |
| [openai/skills](https://github.com/openai/skills) | Deprecated upstream in favor of [openai/plugins](https://github.com/openai/plugins). |

## Renamed or removed upstream

[Matt Pocock's changelog](https://github.com/mattpocock/skills/blob/main/CHANGELOG.md) records these changes. `slipway doctor` lists same-source skills your manifest no longer names. `slipway update --prune` removes the ones Slipway installed; for older copies (installed before Slipway, like the renamed ones below) doctor prints the exact `npx skills remove … -g -y` command and leaves the decision to you.

| Old | New |
|---|---|
| `to-prd` | `to-spec` |
| `to-plan`, `to-issues` | `to-tickets` |
| `review` | `code-review` |
| `decision-mapping` | `wayfinder` |
| `diagnose` | `diagnosing-bugs` |
| `writing-great-skills` | `writing-for-agents` |
| `caveman`, `zoom-out`, `resolving-merge-conflicts` | Removed; no direct replacement stated |
