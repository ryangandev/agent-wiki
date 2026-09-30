# Architecture

## Code map

| Path | Responsibility |
| --- | --- |
| `skills/agent-wiki-setup/SKILL.md` | Installation routing, verification and handoff |
| `scripts/setup_wiki.py` within that skill | Preview, conflict checks, template rendering and optional agent integrations |
| `scripts/smoke_test.py` within that skill | Installed-tool CLI integration against a disposable wiki |
| `assets/runtime/` within that skill | Small runtime skill rendered with the user's local wiki path |
| `assets/wiki/` within that skill | Empty vault templates and the canonical runtime tool |
| `assets/wiki/_system/tools/wiki.py` within that skill | Local capture, index, publication, ledger, review and recovery |
| `assets/wiki/_system/tools/sessions.py` within that skill | Incremental local message selection, checkpoints, bounded batches and acknowledgement |
| `tests/test_intake_upgrade.py` | Intake recovery, coverage and safe upgrade regression tests |
| `tests/test_workflow.py` | Installer and runtime behavior, including filesystem failure cases |

The public setup skill is self-contained so a skill installer can fetch only that directory.
Its bundled runtime skill is the lightweight entry used after setup.
User knowledge and generated paths never belong in this repository.

## Installation

Three layouts share the same runtime: a new standalone vault by default, an explicitly selected existing vault root, or an opt-in subfolder.
The CLI takes the exact vault path and reports the actual wiki root; it never infers that the current working directory is the vault.
The setup skill recommends the name `Agent Wiki` and asks for unresolved layout and location choices.
New-vault mode prepares minimal Obsidian configuration; existing-vault mode preserves configuration and unrelated notes, while refusing occupied workflow namespaces.
Opening or registering the vault in Obsidian is separate from creating the files.

The installer first builds a complete write plan and refuses conflicting content before executing it.
Preview mode writes nothing, including directories.
Execution verifies that each target still matches the planned previous bytes and uses atomic file replacement.
Ordinary execution errors roll back completed writes; empty directories may remain after a failed setup.
This is not a general multi-process transaction manager.
Versioned managed-file fingerprints enable in-place upgrades, and known v1 templates have normalized migration fingerprints.
Modified or unversioned files require a reviewed before/after hash plan; changed files are backed up before replacement.
Discovery reuses existing agent skill locations, entrypoints, root layout and timezone instead of creating duplicates.

Only the marked instruction block is appended; unrelated global instructions are retained.
When global files intentionally share a symlink target, the target is updated once and the symlink remains.
Changed instruction files are backed up inside the private wiki, where they must remain private.
Repeat installation does not reset sources, compiled knowledge, ledger or review state.

`assets/wiki/private.gitignore` is installed as `.gitignore` in the private wiki.
The template has a different filename so its ignore policy does not hide distribution assets from Git.
In existing-vault mode, only workflow-specific ignore paths are appended, preserving the user's existing rules and unrelated notes.
The installation marker records the vault root, layout and vault-relative link prefix, so direct-root links do not incorrectly include the vault name.

## Publication and integrity

Capture hashes the source bytes and creates a content-addressed file under `sources/`.
An exact repeat leaves the source unchanged.
An agent supplies structured publication data containing complete note content, each note's expected previous hash and source dispositions.
Frontmatter uses one key per line with JSON values, a deliberately small YAML subset that requires no YAML dependency.

Publication checks paths, source existence and hashes, unique IDs, wiki links and expected note versions under a local exclusive lock.
It writes note revisions, then a journal of before-images and expected new hashes before publishing notes, the index and the ledger.
Ordinary I/O exceptions roll the publication back.
A process interruption leaves a journal; subsequent publication is blocked until `recover` restores the recorded previous state.
Recovery refuses to overwrite files whose content differs from both the previous state and the attempted publication.
Separate backups are still necessary for disk failure, accidental deletion or damaged evidence.

Locks use `fcntl` on macOS/Linux and `msvcrt` on Windows.
They coordinate cooperating local writers only, not Obsidian edits or different computers connected by a sync service.
Use one writer machine at a time and reread files after a reported conflict.

## Retrieval and maintenance

The compact catalog stores note metadata and section headings.
Search returns ranked keyword matches with bounded output; read supports sections, offsets and a hash of the exact file snapshot.
The tool performs filesystem work locally without loading every note into the model context.
There are no network calls, embedding dependencies or model invocations.

Index rebuild and publication validate all knowledge pages; pending scans source hashes.
This simple design prioritizes auditability for personal knowledge bases and is not optimized for millions of documents.
The agent handles multilingual query expansion, semantic deduplication, evidence evaluation and meaningful compression.
Bounded retrieval reduces context growth but does not guarantee complete recall or a constant token budget.

The review checkpoint is acknowledged only against an unchanged candidate snapshot.
No-op publication and repeated setup avoid rewriting identical files.
Read-only wiki checks leave note and state timestamps unchanged; session review may update system coverage metadata without touching knowledge notes.
A first write operation can create the local lock file.

## Session intake

The separate sessions.py adapter reads only explicitly configured local history roots since a selected timestamp.
It selects human messages and visible assistant responses, excluding thinking, tool output, injected context, approval-review messages and maintenance conversations.
Offsets and consumed-prefix hashes detect truncation or rewrites; partial final JSON records are retried.
Session IDs survive moves into Codex archived_sessions, and original message identities deduplicate forked Claude messages.
Long messages are chunked without dropping their suffix, with original locators for bounded context lookup.

One private pending batch is retained until the agent supplies a disposition for every item.
Acknowledgement verifies captured source hashes or existing duplicate targets before committing checkpoints and removing batch text.
A retry after checkpoint persistence but before batch removal recognizes the completed batch.
The latest disposition receipt and message fingerprints are metadata, not retrieved knowledge.
Neither selection nor receipt validation proves the model correctly classified every claim.

## Validation boundaries

Automated tests use isolated filesystem roots and synthetic evidence.
They cover install preservation, exact deduplication, version conflicts, evidence links, publication rollback, interrupted-run recovery, bounded recall and no-op behavior.
They cannot prove a model's judgment, a host's actual skill discovery, permissions in a different session, or successful unattended scheduling.
The setup skill must report those acceptance steps separately on the target computer.
