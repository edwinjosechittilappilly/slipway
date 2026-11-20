---
name: exec-one-pager
description: Write a one-page executive brief that gets a decision - the ask, the problem with evidence, the proposal, impact, cost, options and risks. Use when a feature, initiative or architecture change needs buy-in from leadership, a customer or a budget owner, or when asked for an exec summary, one-pager, brief, decision memo or PR/FAQ.
---

# Executive one-pager

One page, one decision. A reader with two minutes should know what you want, why now, and what it costs.

## Process

1. **Evidence first.** Collect the problem's numbers: incidents, hours lost, cost, users affected, deadlines. Ask
   the user for numbers you cannot find. Label every estimate `estimate:` with its basis.
2. **Name the ask.** Who decides, what they decide, by when. If you cannot write that sentence, run `grill-me`
   until you can.
3. **Fill [template.md](template.md).** About 450 words of body; it must fit one printed page.
4. **Diagram (optional).** At most one C4 context diagram from `arch-diagram`. No container or deployment detail.
5. **Edit.** Apply the `humanizer` skill, then the rules and checklist below.
6. **Save** to `docs/one-pagers/<slug>.md`. Export when asked:
   `pandoc docs/one-pagers/<slug>.md -o docs/one-pagers/<slug>.docx` (PDF: add `--pdf-engine=<engine>` if one is
   installed; otherwise export the .docx to PDF).
7. **Link** it from the design doc and the OpenSpec proposal's "Why".

## Rules

- The ask, its owner and its deadline are in the first three lines.
- Every impact claim has a number, a baseline, and a source or an `estimate:` basis.
- "Do nothing" is always an option, with its cost.
- Top three risks only, each with a mitigation and an owner.
- Use the reader's words. No architecture detail beyond the one diagram.
- Cut on sight: leverage, seamless, robust, cutting-edge, game-changer, synergy, unlock, delve, "in today's fast-paced".

## Checklist

- [ ] Ask, owner and deadline in the first three lines
- [ ] Problem quantified, with a source
- [ ] Do-nothing option costed
- [ ] Cost as people × weeks, spend, and what stops
- [ ] One success metric with a baseline, a target and a date
- [ ] Fits one page
