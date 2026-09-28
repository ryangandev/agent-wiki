# Daily maintenance and weekly review

Recommended cadence: daily 00:00 in `__TIMEZONE__`, plus a Sunday review.
The host scheduler owns execution; this file does not schedule itself.

## Daily

1. Run pending and check with `_system/tools/wiki.py`.
2. If the only issue is a stale catalog, rebuild and check again; other errors require inspection.
3. With no work and no weekly review due, finish without changing notes, timestamps or reports.
4. Read ingest.md and only the pending sources when compilation is needed.
5. Search related knowledge; compile supported claims, merge duplicates, reject noise or register unresolved conflicts using apply.
6. Repeat pending/check until the accessible backlog is handled or a concrete problem prevents completion.

Process all pending sources, not only yesterday's files, so missed runs do not lose accumulated input.
The input is what connected agents captured; do not scan all historical chats.
Existing awaiting_review entries are already-known conflicts, not a reason for repeated notifications.
Permission failure is a failure, not a successful no-op.
Maintain only the wiki; do not change agent configuration, project code, external services or schedules.

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
