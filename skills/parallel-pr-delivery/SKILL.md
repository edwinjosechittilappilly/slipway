---
name: parallel-pr-delivery
description: Deliver independent Beads slices in parallel worktrees through PR review and merge. Use when coordinating parallel agents, PR review findings, protected-branch gates, or post-merge cleanup.
---

# Parallel PR delivery

1. **Slice.** Record each plan item, spec task and PR review as a bead with description, acceptance and real dependencies. Split large beads into small dependent children. Map OpenSpec tasks 1:1 to beads; fold audit findings into the change before implementation. Plan the merge order to minimise conflicts. Sequence only true dependencies.
2. **Claim and isolate.** Run `bd prime` and `bd ready`; claim each ready bead before starting. Give each independent bead an agent, branch and worktree, explicit file ownership and acceptance criteria. Assign one integration owner for each shared file; other agents hand changes to that owner.

   ```bash
   bd ready
   bd update "$BEAD" --claim
   git worktree add -b "feat/$BEAD" "../worktrees/$BEAD" origin/main
   ```

3. **Implement and open.** Each agent works in its assigned worktree, verifies its acceptance criteria and pushes its branch, never `main`. Open one PR per slice naming its bead and spec; record a review bead with a description, acceptance and dependencies.

   ```bash
   git push -u origin "feat/$BEAD"
   gh pr create --base main --head "feat/$BEAD" --title "$TITLE" --body "$BODY"
   REVIEW=$(bd create "Review PR #$PR" -t task --parent "$BEAD" -l role:review \
     -d "Independently review PR #$PR and re-check fixes" \
     --acceptance "Review and re-check complete; findings tracked" --silent)
   ```

4. **Review and re-check.** An independent reviewer from a different model vendor reviews each PR. Record every finding as a child of the review bead, including severity, file:line, required fix, acceptance and any real dependencies. The author fixes findings and the reviewer re-checks the final diff. Track any accepted remainder as a follow-up bead, never silently drop it. Reply to every review thread, including CodeRabbit, citing the fix commit or the follow-up bead and rationale; resolve each thread after the reply. Inspect all pages of review threads via GitHub's GraphQL API, including resolved status.

   ```bash
   FINDING=$(bd create "P1: <finding>" -t bug --parent "$REVIEW" \
     -d "<file:line> — <fix>" --acceptance "<observable check>" --silent)
   ```

5. **Gate and merge.** Required CI must pass and the PR branch must be current. Update a stale branch and repeat affected checks and review. UI PRs require actually inspecting screenshots at desktop light, desktop dark and 375px before merge; CI is not a visual review. Data migrations require full review and a re-check before merge. Back up user data before migration and test destructive operations on copies. Once findings and threads are addressed, non-UI PRs may use auto-merge; UI PRs merge only after the visual gate. Respect all branch protections.

   ```bash
   gh pr checks "$PR" --watch
   gh pr update-branch "$PR" --rebase  # only if behind
   gh pr merge "$PR" --squash --auto  # non-UI, after findings are addressed
   ```

6. **Close and clean up.** After GitHub confirms the PR merged, close its findings, review and slice beads with the PR URL or merge commit. Close a parent only after all its children close; keep follow-up beads open. Remove the merged worktree to recover disk space.

   ```bash
   bd close "$FINDING" --reason "Merged in $PR_URL ($MERGE_COMMIT)"
   bd close "$REVIEW" "$BEAD" --reason "Merged in $PR_URL ($MERGE_COMMIT)"
   git worktree remove "../worktrees/$BEAD"
   ```
