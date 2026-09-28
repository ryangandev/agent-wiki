---
name: agent-wiki
description: Recall prior decisions, project intent, constraints and reusable lessons when current context is insufficient; capture confirmed durable knowledge or maintain the shared Agent Wiki. Skip routine progress and facts answered by current code alone.
---

# Agent Wiki

Shared root: `__WIKI_ROOT__`.

Choose one mode and read only its file inside that directory:

- Recall: `_system/recall.md`, when historical context is needed and missing.
- Capture or compile: `_system/ingest.md`, for new durable knowledge with evidence.
- Maintenance: `_system/maintain.md`, for an authorized maintenance run.

Use `_system/tools/wiki.py` to filter the index before reading matched sections.
Do not preload Home, the full index, project summaries or source archives.
No substantive new knowledge means no capture and no status report.
Consult `_system/GUIDE.md` only when policy is unclear.
