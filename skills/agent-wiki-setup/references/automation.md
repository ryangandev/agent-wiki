# Maintenance scheduling

The installer creates a prompt, not a background service.
Do not create raw automation database entries, overwrite host configuration, or change system sleep settings to simulate scheduler support.

## Agent scheduler

1. Read `<wiki>/_system/maintenance-prompt.md`.
2. Find the host's supported scheduling interface and an existing matching task before creating another.
3. Use the user's timezone and cadence; defaults are daily 00:00 and a Sunday review.
4. Set the working location and grant write access to the private wiki and read access to explicitly configured local session roots when the host supports scoped permissions.
5. Trigger a real run and inspect its result; report scheduling separately from filesystem installation.

The job must run an agent able to read sources and edit knowledge.
Running Python `pending` from cron does not perform semantic compilation.
For hosts without scheduling, the user can invoke maintenance manually with the generated prompt.
History intake covers only configured, readable local adapters.
Do not promise access to unconfigured agents or cross-machine files.
Reuse an existing matching task ID during upgrades, preserving its cadence, timezone and notification preferences.
Update its prompt to the installed maintenance-prompt.md; an older prompt that checks only pending sources will bypass fallback intake.

## Acceptance

A successful no-work run leaves knowledge note contents and timestamps unchanged; system coverage checkpoints may advance.
Validate that session scan and acknowledgement actually run, not merely that wiki.py pending returns zero.
To validate background writing, use a user-approved real source and verify its recorded disposition, searchable knowledge and final check; do not fill the user's wiki with synthetic facts.
Quietly finish ordinary maintenance and no-op runs; surface new conflicts, failures or required user action.
Use a host's supported archive action if appropriate; do not claim an interrupted run completed just because its chat was archived.
Local jobs may require the computer awake and the agent application running.

Reference: [Codex scheduled tasks](https://learn.chatgpt.com/docs/automations?surface=app).
