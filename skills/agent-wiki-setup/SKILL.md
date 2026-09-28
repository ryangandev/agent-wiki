---
name: agent-wiki-setup
description: Set up a private, shared Obsidian knowledge base for coding agents, with selective recall, durable capture and maintenance. Use when someone asks to install this workflow, not for everyday knowledge retrieval.
---

# Agent Wiki Setup

Build a private knowledge base that connected agents consult only when historical context matters.
The bundled tool is standard-library Python 3.10+; it does not call a model or install software.

## Choose the destination

Establish the installation layout, exact path, participating agents, and local timezone.
Recommend a new standalone vault named `Agent Wiki` and ask where to create it if no location was given.
If the user says the current folder is already their vault, use that exact folder as the wiki root; do not create another `Agent Wiki` inside it.
When intent is unclear, offer: create a new vault (recommended), use this or another existing vault at its root, or create a subfolder inside an existing vault.
Ask only for unresolved choices; a working directory or `.obsidian` folder is evidence to inspect, not permission to adopt it.
Keep the private vault outside this public repository and avoid nested vaults.
Read [installation.md](references/installation.md) for mode selection, existing files or custom agent locations.

## Install

Run `scripts/setup_wiki.py` relative to this skill's directory.
Preview the exact changes with `--vault <exact-vault-path> --mode <chosen-mode> --agents codex claude --timezone <timezone>`; include only agents the user requested.
`new-vault` is the default; `existing-vault` installs directly at that root; `subfolder` creates `<vault>/Agent Wiki` only when explicitly chosen.
With setup authorization established, rerun the same command with `--apply`.
The installer preserves unrelated global instructions, backs up changed instruction files inside the private wiki, and refuses differing existing files.
Resolve a reported conflict without deleting the user's existing skill or knowledge.
For another agent, omit `--agents` and add the generated `_system/ENTRYPOINT.md` block to its supported instructions within the user's authorization.
Explain any host-specific read/write permission still needed; do not disable its sandbox.

## Verify

Run the installed `_system/tools/wiki.py pending` and `check`; an empty install should report zero pending sources and no issues.
Run `scripts/smoke_test.py --wiki <installed-path>` to exercise capture, compilation, recall, duplicate handling and no-op behavior in an isolated temporary wiki, without inserting test knowledge in the user's vault.
Verify each chosen agent can discover its generated `agent-wiki` skill; refresh its session if required.
Distinguish filesystem setup from actual agent access and unattended scheduling.

## Connect maintenance

Read [automation.md](references/automation.md) only when configuring an authorized scheduler.
Use the generated `_system/maintenance-prompt.md`, defaulting to midnight local time with weekly review on Sunday, unless the user chooses otherwise.
Use the host's supported automation interface; preserve its permissions and notification preferences.
An available scheduler is not implied by having installed this skill.
Do not claim unattended write access until a real scheduled/manual-triggered agent run has demonstrated it.
If scheduling is unavailable, finish the usable wiki and report that maintenance is manual.

## Handoff

Report the vault path, actual wiki root, agent connections, verification results and schedule status separately.
For a new vault, direct the user to Obsidian's “Open folder as vault” with the generated vault path; creating files does not register or open the vault in the app.
Existing conversations are not automatically migrated; review only user-selected material and preserve minimal evidence for accepted durable claims.
Do not copy transcripts, private configuration or any other person's example knowledge into the new wiki.
