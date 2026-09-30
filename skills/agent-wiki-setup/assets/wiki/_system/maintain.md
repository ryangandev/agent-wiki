# Daily maintenance and weekly review

Recommended cadence: daily 00:00 in `__TIMEZONE__`, plus a Sunday review.
The host scheduler owns execution; this file does not schedule itself.

## Daily

1. Run `_system/tools/sessions.py status` and wiki.py pending/check.
2. If session review is configured, read sessions.md and review bounded new batches before deciding there is no work.
   Retry unacknowledged batches; preserve checkpoints on failure; process the backlog or explicitly report remaining coverage.
3. Rebuild only a stale catalog; inspect and recover interrupted publication before publishing.
4. Read ingest.md when sources are pending, search related conclusions and compile, deduplicate or register evidence conflicts with apply.
5. Repeat pending/check after publication.
6. With no pending sessions, sources or issues, finish quietly unless Sunday review has candidates.

Process all unhandled input, not only yesterday, so a missed run can catch up.
An unconfigured adapter is outside coverage, not proof of no new knowledge.
Permission failures and malformed history are failures, not successful no-ops.
Existing awaiting_review conflicts do not require repeated notifications.
Maintain only this wiki and configured read-only history intake; do not alter agent configuration, project code, external services or schedules.

## Weekly

Run review on Sunday to identify changed scopes since the acknowledged checkpoint.
It returns machine-readable candidates; filter/group that output locally before feeding a large list into the model.
Count zero means stop without writes.
Review the affected themes for semantic duplicates, contradictions, overlong summaries and explicitly ended projects.
Merge equivalent conclusions and link to one canonical page; preserve meaningful historical differences and source provenance.
No automatic age-based deletion of sources or project closure is allowed.

Save the full review JSON outside the wiki and inspect every candidate in that snapshot, in small batches when needed.
After edits, get a fresh snapshot and ensure the resulting candidates have all been covered.
Use `review --ack --file <reviewed-snapshot.json>` to acknowledge exactly that scope.
If candidates changed concurrently, the tool refuses acknowledgement; review the new changes and retry.

## Output

Stay quiet for ordinary successful work and no-op runs.
Surface only a new conflict requiring judgment, failure, or action the user must take.
Use the host's supported archive action after successful completion if that is its normal workflow.
