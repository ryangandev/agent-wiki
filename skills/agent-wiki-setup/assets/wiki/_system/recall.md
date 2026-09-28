# Selective recall

Use when a task needs a prior reason, constraint or lesson that the current context does not provide.
Skip trivial requests and questions answered by current code.

## Search

Tool: `__WIKI_ROOT__/_system/tools/wiki.py`.
Run `python3 "<tool>" search "one to three terms" --scope <project-slug> --limit 4`.
Omit scope for cross-project methods; scopes are user-defined, not a fixed registry.
The tool searches title, aliases, keywords, summary and headings locally; it does not send the entire index to the model.
Results default to 2,800 characters and at most four pages.
Try a relevant synonym once if needed; do not scan every source after an empty result.

## Read

Use `python3 "<tool>" read "wiki/decisions/example.md" --section "Conclusion"` for a returned heading.
Read one to three relevant sections first, typically 1,500 to 3,000 tokens or less.
Use next_offset with `--offset` only when the remaining text is needed.
Read a page's source references only to check original wording, confidence or a disputed claim.

## Apply

Check scope, as_of, status and conditions for reevaluation.
Current user instructions take priority over historical summaries.
Use prior reasoning without treating old implementation or service details as proof of current behavior.
Say when evidence is absent; do not invent remembered decisions.
