# Capture and compile

## Capture threshold

Preserve supported decisions and reasons, lasting constraints, useful research with unresolved questions, and verified reusable lessons.
Skip routine progress, transcript dumps, test counts, branch cleanup, deployment announcements and implementation facts easily queried from code.
An empty capture queue is normal.

## Capture evidence

Search for an existing conclusion before creating another source.
Prepare a short UTF-8 Markdown file outside the wiki containing title, scope, event_date (or unknown), captured_at, and a source reference or conversation ID with message locator.
Keep minimum sufficient quotations or clearly labeled agent synthesis, the decision's conditions, and unresolved points.
Use `python3 "<tool>" capture --file "<evidence.md>" --category conversations`; external research uses `research`.
`<tool>` is `__WIKI_ROOT__/_system/tools/wiki.py`.
Identical bytes produce one source; semantic duplicates are resolved by the agent during compilation.
The agent may compile now when the user needs the knowledge immediately, or leave the source for maintenance.

## Knowledge format

Use Markdown frontmatter whose values are JSON: one `key: JSON-value` per line, between `---` lines.
String fields: id, title, kind, scope, summary, as_of, status.
String-array fields: aliases, keywords, sources.
kind is project, topic, decision or method; status is active, historical, needs-review or superseded.
Use a stable project slug for scope; `cross-project` is useful for general methods.
sources contains existing wiki-relative paths beginning with `sources/`.
as_of is the date the evidence supports, not merely today's maintenance date.
Headings and body may use the user's language.
Use full vault-relative Obsidian links, for example `[[__WIKI_NAME__/wiki/decisions/example|Example]]`.
Aim for short project summaries and focused pages, not a page per conversation.

## Publish

Get pending sources and hashes with `pending`.
Search the existing topic, then update its authoritative page rather than copying a conclusion.
Write the complete proposed note and source disposition to an external JSON file:

```json
{
  "notes": [{"path": "wiki/decisions/example.md", "expected_sha256": null, "content": "complete Markdown with frontmatter"}],
  "resolved": [{"source": "sources/conversations/example.md", "sha256": "hash from pending", "status": "compiled", "targets": ["example"], "reason": "New supported decision"}]
}
```

Use the hash from a fresh `read` for expected_sha256 when updating; use null only for a new file.
Run `python3 "<tool>" apply --file "<changes.json>"`, then pending/check.
Concurrent edits cause rejection; reread and merge rather than force-overwriting.
Disposition status may be compiled, duplicate, rejected or needs-review.
compiled/duplicate must point to existing knowledge IDs; rejected/needs-review may use an empty targets array.
Duplicates update only the ledger unless the authoritative conclusion actually changes.
Preserve conflicting claims and the user's decision history rather than silently choosing a version.

Use apply for publication, not direct writes to knowledge, catalog or ledger.
If interrupted-publication is reported, inspect its saved transaction; `recover` rolls it back only if no later edits would be overwritten.
Do not delete an interruption marker to bypass validation.
