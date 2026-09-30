# Current status

Release 2.0.0 supports explicit capture checkpoints, selective recall and opt-in incremental local Codex/Claude session review before daily compilation.
The runtime keeps original evidence separate from canonical knowledge, with deduplication, version checks, recovery and changed-scope weekly review.

Installation discovers existing connections, reuses an existing skill location and wiki, and updates recognized managed files in place.
Known public v1 templates can upgrade automatically; unversioned or locally customized files require review of an exact change plan.
Repeat installation preserves knowledge and processing state, and the setup skill updates existing scheduler jobs instead of creating duplicates.

The standard-library suite covers temporary installations and fake histories, including interruption, malformed records, long messages, fork duplication, archiving, evidence validation and upgrades.
CI runs Python 3.10 and 3.13 on macOS, Linux and Windows; use the actual workflow result for the published commit.
Real-agent acceptance is separate: verify implicit capture, routine work without capture, and a full fallback review/compile cycle on each host.
CLI tests do not establish model quality or unattended scheduler permissions.

No background service or model API is installed by Python.
Scheduling uses the host's supported interface and requires access to configured histories and the private wiki.
Unconfigured agents, deleted/inaccessible logs and other computers remain outside fallback coverage.
Cross-device writer coordination, embedding search and perfect semantic recall are not provided.
