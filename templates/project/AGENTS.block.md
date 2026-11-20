## Delivery workflow (Slipway)

- **Tasks** live in Beads (`bd`). Start a session with `bd prime`. `bd ready` lists unblocked work; claim with
  `bd update <id> --claim`; finish with `bd close <id> --reason "…"`. Humans see the board with `slipway ui`.
- **Behaviour changes** start as an OpenSpec change in `openspec/changes/` (`openspec-propose`, then
  `openspec-apply-change`, then `openspec-archive-change`). Turn an approved change into beads with the
  `spec-to-beads` skill.
- **Documents**: executive one-pagers in `docs/one-pagers/`, design docs in `docs/design/`, decisions in
  `docs/adr/`, diagrams in `docs/diagrams/` (edit the `.json` spec and regenerate; never hand-edit the SVG).
- **Issue tracker for the engineering skills**: `docs/agents/issue-tracker.md` (Beads); labels in
  `docs/agents/triage-labels.md`; domain docs layout in `docs/agents/domain.md`.
- **Roles**: label beads `role:explore|plan|implement|review|issues|pr|docs|design`; `slipway run --bead <id>` hands
  one to the harness and model mapped to that role (`slipway roles` shows the map).
