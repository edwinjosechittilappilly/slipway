---
name: design-doc
description: Write a developer design doc (Google-style structure, arc42 cross-cutting checks, C4 diagrams, ADR links) after the one-pager is approved and before the OpenSpec change. Use when asked for a design doc, technical design, RFC, architecture proposal, or "how should we build X".
---

# Design doc

The design doc explains how and why, for engineers. The one-pager already settled whether.

## Process

1. **Read** the one-pager (`docs/one-pagers/<slug>.md`), `GLOSSARY.md`, `docs/adr/`, the current specs in
   `openspec/specs/`, and the code involved. Use an explorer/scout agent for wide searches.
2. **Diagram** with `arch-diagram`: a C4 context view and a container view. Add a deployment or sequence view only
   when it changes a decision. IBM theme for enterprise audiences; the team's brand theme otherwise.
3. **Write** from [template.md](template.md) into `docs/design/<slug>.md`. Two to six pages. For a small feature write
   the mini version: Context, Design, Alternatives, Risks.
4. **Record decisions.** Each choice that is hard to reverse gets an ADR in `docs/adr/NNNN-<slug>.md`
   (`domain-modeling` skill format). Link it from the doc.
5. **Review.** Run a `grilling` pass on the doc, then a review by a different vendor's model:
   `slipway run review --print "Review docs/design/<slug>.md: correctness, missing alternatives, risks"`, or the
   `cross-reviewer` subagent in Claude Code. Open questions become `decision` beads.
6. **Hand off.** When approved, create the OpenSpec change (`openspec-propose`). Its `design.md` links to this doc
   instead of copying it.

## Rules

- Goals are measurable. Non-goals are explicit and as specific as goals.
- At least two real alternatives plus "do nothing", each with why not.
- Walk the cross-cutting checklist; write "n/a" with a reason rather than dropping an item.
- Code only for contracts: API shapes, schemas, events, config.
- Diagrams are generated from committed JSON specs; never paste screenshots.
- Use the glossary's terms. New terms go to `GLOSSARY.md` first.

## Cross-cutting checklist (arc42 §8 and §10)

Security and privacy · data migration and backfill · failure modes and recovery · observability (logs, metrics,
traces, alerts) · performance budget · cost · backwards compatibility · accessibility (UI) · rollout, feature flags
and rollback · operational ownership.
