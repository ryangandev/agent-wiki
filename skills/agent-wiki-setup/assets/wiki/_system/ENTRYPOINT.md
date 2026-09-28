# Connect another agent

Give the agent scoped access to `__WIKI_ROOT__` and add this small block to its supported global instructions:

```text
Shared long-term context lives at __WIKI_ROOT__.
When prior decisions, intent, constraints or lessons are needed and the current context is insufficient, read _system/recall.md there and retrieve only relevant indexed sections.
When new confirmed durable knowledge emerges within the user's authorization, read _system/ingest.md and capture minimal evidence for compilation.
Do not preload the wiki, read every project summary, or capture routine progress.
No new durable knowledge means no capture or report.
```

An agent still needs permission to access the directory and a compatible tool to run Python.
Remote agents need an explicitly arranged storage connection; sharing a path string does not connect machines.
