---
name: spec-to-beads
description: Turn an approved OpenSpec change (or an approved design doc plan) into a Beads epic with child tickets, blocking dependencies, acceptance criteria and role labels, after showing the graph for approval. Use after openspec-propose is approved, or when asked to turn a spec, change or plan into tickets or beads.
---

# Spec to Beads

OpenSpec decides *what*; Beads tracks *who does what next*. This skill is the bridge.

## Process

1. **Load the change.** Read `openspec/changes/<slug>/` (`proposal.md`, `specs/`, `design.md`, `tasks.md`). Run
   `openspec validate <slug>` and stop if it fails.
2. **Draft the graph. Do not create anything yet.**
   - **Epic:** title from the proposal; description = the proposal's Why and What Changes, plus a link to the design
     doc. Labels `change:<slug>`.
   - **Tickets:** one per task group in `tasks.md`. If the tasks are horizontal layers (all schema, then all API),
     re-slice them into tracer bullets: each ticket a thin path through every layer, demoable on its own.
     Prefactoring comes first.
   - **Acceptance:** from the matching spec scenarios (GIVEN / WHEN / THEN), written as a check someone can run.
   - **Labels:** `role:<name>` (`implement` by default; `docs`, `design`, `review` where they fit), `phase:<n>`,
     `change:<slug>`, and `ready-for-agent` when the ticket needs no human context.
   - **Dependencies:** real ones only (data, API, migration order). Work that can run in parallel stays unblocked.
   - **Open questions** from the proposal or design become `-t decision` beads that block the tickets they affect.
3. **Show** the graph as a table (title, blocked by, role, acceptance) and get the user's approval.
4. **Create**, epic first, capturing ids with `--silent`:

   ```bash
   EPIC=$(bd create "<title>" -t epic -l change:<slug> --spec-id openspec/changes/<slug> \
     --body-file - --silent <<'EOF'
   <why + what changes + link to design doc>
   EOF
   )
   T1=$(bd create "<ticket>" -t task --parent "$EPIC" -l role:implement,phase:1,change:<slug> \
     --acceptance "<check>" -d "<scope>" --silent)
   T2=$(bd create "<ticket>" -t task --parent "$EPIC" -l role:implement,phase:2,change:<slug> \
     --deps blocked-by:"$T1" --acceptance "<check>" -d "<scope>" --silent)
   ```

5. **Verify:** `bd graph "$EPIC"`, `bd dep cycles` (must be empty), `bd ready` (shows the first slice).
6. **Point `tasks.md` at Beads.** Add one line under its title: `Tracked in Beads: epic <id>. Close beads, not
   checkboxes; tick these when the epic closes.` Keep the file: `openspec archive` reads it.
7. **Report** the epic id, the ready list, and how to watch it: `slipway ui`.

## Without OpenSpec

Use the same steps with the design doc's plan or the `planner` agent's output as the source. Set `--spec-id` to the
design doc path.
