# Connect another agent

Add this block to the agent's supported global instructions and grant scoped access to `__WIKI_ROOT__`:

```text
Shared long-term context lives at __WIKI_ROOT__.
Recall only when missing historical decisions or lessons are relevant; use _system/recall.md and the compact index.
After a user-confirmed decision or corrected lasting requirement, and before substantive task completion, assess the current conversation for reusable knowledge.
Capture qualifying minimal evidence using _system/ingest.md without waiting for a separate "remember this" request, within the user's authorized scope.
This checkpoint uses current context; never preload the wiki or all project summaries.
Skip routine progress, duplicates and facts adequately documented in the repository; no qualifying knowledge means no capture or report.
```

An agent needs actual filesystem access and Python, not merely this path string.
Codex and Claude can additionally use opt-in local session adapters described in `_system/sessions.md`.
Other agents retain the same capture protocol; their session history is not covered until an adapter is connected and verified.
