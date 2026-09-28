# Current status

The distribution includes a self-contained setup skill, an empty private wiki template, optional Codex and Claude Code entrypoints, a portable Python runtime and installation documentation in English and Chinese.
Other agents can use the generated Markdown entrypoint with their supported instruction mechanism.

The runtime supports selective catalog search and section reads, content-addressed capture, source dispositions, checked publication, revision history, recovery, incremental review and no-op maintenance.
The installer supports read-only preview, conflict detection, instruction preservation and repeat installation without resetting knowledge.

The standard-library test suite exercises these mechanics in temporary vaults and fake home directories.
The repository's CI tests Python 3.10 and 3.13 on macOS, Linux and Windows; use the actual workflow result as evidence for a specific commit.

Scheduling remains a host integration step.
No background service, automatic chat-history import, embedding search, automatic upgrade or cross-device write coordination is included.
Model judgment, host skill availability and real unattended write access must be checked during each user's setup.
