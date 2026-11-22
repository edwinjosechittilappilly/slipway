---
name: parallel-pr-delivery
description: Deliver independent Beads slices in parallel worktrees through PR review and merge. Use when coordinating parallel agents, PR review findings, protected-branch gates, or post-merge cleanup.
---

# Parallel PR delivery

1. **Slice.** Record each plan item and spec task as a bead with description, acceptance and real dependencies.
   Split large beads into small dependent children; map OpenSpec tasks 1:1 to beads. Include applicable audit findings
   in the change before implementation. Plan merge order to minimise conflicts; sequence only true dependencies.
2. **Claim and isolate.** Run `bd prime` and `bd ready`; set `BEAD` to a ready bead and claim it before starting.
   Give each independent bead an agent, branch, worktree, explicit file ownership and acceptance criteria. Assign
   one integration owner for each shared file; other agents hand changes to that owner.

   ```bash
   bd ready
   bd update "$BEAD" --claim
   git fetch origin main
   git worktree add -b "feat/$BEAD" "../worktrees/$BEAD" origin/main
   ```

3. **Implement and open.** Each agent works in its worktree, checks acceptance and pushes its branch, never `main`.
   Set `TITLE` and `BODY` to the PR title and body naming the bead and spec. Open one PR per slice; create its
   review bead with a description, acceptance and dependencies.

   ```bash
   git -C "../worktrees/$BEAD" push -u origin "feat/$BEAD"
   PR_URL=$(gh pr create --base main --head "feat/$BEAD" --title "$TITLE" --body "$BODY")
   PR=${PR_URL##*/}
   REVIEW=$(bd create "Review PR #$PR" -t task --parent "$BEAD" -l role:review \
     -d "Independently review PR #$PR and re-check fixes" \
     --acceptance "Review and re-check complete; findings tracked" --silent)
   ```

4. **Review and re-check.** An independent reviewer from a different model vendor reviews the PR. Create a child
   bead for each finding with severity, file:line, fix, acceptance and real dependencies. The author fixes findings;
   the reviewer re-checks the final diff. For an accepted remainder, create a follow-up outside the slice and epic
   with `--deps discovered-from:$FINDING`, no `--parent`; record its id on the finding for closure after merge.

   ```bash
   FINDING=$(bd create "P1: <finding>" -t bug --parent "$REVIEW" \
     -d "<file:line> — <fix>" --acceptance "<observable check>" --silent)
   FOLLOWUP=$(bd create "<follow-up>" --deps "discovered-from:$FINDING" \
     -d "<scope>" --acceptance "<observable check>" --silent)
   bd update "$FINDING" --append-notes "Deferred to $FOLLOWUP: <rationale>"
   ```

   List every review thread first, including bot reviewers, then reply to each unresolved thread with its fix
   commit or follow-up bead and rationale; resolve after replying. Also address bot summary and nitpick comments
   that are not threads. Set `THREAD` and `SHA` to the thread ID and actual fix commit for each reply.

   ```bash
   gh api graphql --paginate -F owner='{owner}' -F repo='{repo}' -F pr="$PR" -f query='
   query($owner:String!,$repo:String!,$pr:Int!,$endCursor:String) {
     repository(owner:$owner,name:$repo) { pullRequest(number:$pr) {
       reviewThreads(first:100,after:$endCursor) {
         pageInfo { hasNextPage endCursor }
         nodes { id isResolved path line comments(first:1) { nodes { author { login } body } } }
       }
     } }
   }'
   gh api graphql -f id="$THREAD" -f body="Fixed in $SHA" -f query='
   mutation($id:ID!,$body:String!) {
     addPullRequestReviewThreadReply(input:{pullRequestReviewThreadId:$id,body:$body}) { comment { url } }
   }'
   gh api graphql -f id="$THREAD" -f query='
   mutation($id:ID!) { resolveReviewThread(input:{threadId:$id}) { thread { isResolved } } }'
   ```

5. **Gate and merge.** Required CI must pass and the PR branch must be current. If behind, update with a merge
   commit after review starts to preserve cited SHAs, pull it locally, then re-run checks and affected review.
   UI PRs need attached screenshots at desktop and 375px, in light and dark if the app has themes; inspect them
   before merge. Without screenshot tooling, hand the gate to the owner and skip auto-merge. For migration PRs the
   reviewer reads every migration, runs it on a copy and re-checks after fixes. Back up user data before migration
   or destructive operations and rehearse them on a copy.

   Once findings and threads are addressed, non-UI PRs may use auto-merge. If it is disabled, wait for required
   checks, set `SHA` to the reviewed PR head and merge with `--match-head-commit`. UI PRs merge only after the
   visual gate; respect all branch protections.

   ```bash
   gh pr update-branch "$PR"  # only if behind
   git -C "../worktrees/$BEAD" pull --ff-only  # after the server update completes
   gh pr checks "$PR" --watch --required
   gh pr merge "$PR" --squash --auto  # non-UI, after findings are addressed
   # If auto-merge is disabled, after all gates pass:
   SHA=$(gh pr view "$PR" --json headRefOid -q .headRefOid)
   gh pr merge "$PR" --squash --match-head-commit "$SHA"
   ```

   For npm releases, use tag-triggered GitHub Actions trusted publishing with `permissions: id-token: write`;
   skip already-published versions, keep long-lived `NPM_TOKEN` out of the workflow, and obtain owner approval for
   staged publishes. Check the repository's public status when assessing Actions billing.

6. **Close and clean up.** Confirm GitHub reports the PR merged before closing its finding, review and code-changing
   slice beads, citing the PR and merge commit; cite the follow-up id for deferred findings. Close a parent only
   after all children close. Close decision, spike and research beads when acceptance is met. Keep follow-ups open.
   Remove the merged worktree and local branch to recover disk space.

   ```bash
   MERGE_COMMIT=$(gh pr view "$PR" --json state,mergeCommit \
     -q 'select(.state=="MERGED").mergeCommit.oid')
   test -n "$MERGE_COMMIT" || { echo "PR is not merged" >&2; exit 1; }
   for f in $(bd list --parent "$REVIEW" --status open,in_progress,blocked,deferred --json | jq -r '.[].id'); do
     bd close "$f" --reason "Merged in $PR_URL ($MERGE_COMMIT); see notes for any follow-up"
   done
   bd close "$REVIEW" --reason "Merged in $PR_URL ($MERGE_COMMIT)"
   bd close "$BEAD" --reason "Merged in $PR_URL ($MERGE_COMMIT)"
   git worktree remove "../worktrees/$BEAD"
   git branch -D "feat/$BEAD"
   ```
