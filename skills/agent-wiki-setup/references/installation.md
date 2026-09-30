# Installation details

## Requirements

Use Python 3.10 or later on macOS, Linux or Windows.
On Windows, use `py -3` or the appropriate `python` executable instead of `python3`.
No Obsidian plugin, API token, model subscription or network connection is required by the Python tools.
Semantic compilation still requires an agent with filesystem access.

## Choose a layout

| Mode | Meaning of `--vault` | Actual wiki root |
| --- | --- | --- |
| `new-vault` (default) | Exact path of a new standalone vault, usually `<chosen-parent>/Agent Wiki` | The supplied path |
| `existing-vault` | An existing vault or folder explicitly selected as the vault | The supplied path |
| `subfolder` | An existing vault that should contain the wiki | `<vault>/Agent Wiki`, or `--wiki-name` |

In `new-vault` mode, the parent must exist; the target must be absent, empty or an identical previous installation.
The installer creates a minimal `.obsidian/app.json` along with the wiki, preserving changed Obsidian settings on repeat installation.
Open the resulting folder using Obsidian's “Open folder as vault”; this tool does not register vaults in the application.
The default name recommended by the skill is `Agent Wiki`; the exact path controls the name.

In `existing-vault` mode, `--vault .` means the current directory itself is the root.
Use that only after the user selects it as the vault, not because it happens to be the working directory.
Unrelated notes and Obsidian settings are preserved.
Existing `wiki/`, `sources/` or `_system/` namespaces are not silently adopted, and a differing `Home.md` stops installation before writes.
The existing `.gitignore` is retained and extended only with the workflow's private paths.
No Obsidian settings are created or changed in this mode, including when the vault uses a custom configuration folder.

Subfolder mode is opt-in and does not create another `.obsidian` directory.
For direct-root modes, the installer rejects paths nested under a detected `.obsidian` ancestor.
Obsidian supports custom configuration folders, so still confirm the actual vault boundary when that detection is inconclusive.
Generated links use vault-relative paths for the selected layout.

## Agent connections

`--agents codex` reuses a single existing runtime skill at `~/.codex/skills/agent-wiki` or `~/.agents/skills/agent-wiki`; new connections use the latter and appends a small managed block to `~/.codex/AGENTS.md`.
`--agents claude` writes the runtime skill to `~/.claude/skills/agent-wiki` and appends the same block to `~/.claude/CLAUDE.md`.
Existing unrelated instruction text is preserved, including when both instruction files resolve to the same symlink target.

If the host uses `CODEX_HOME`, `CLAUDE_CONFIG_DIR` or another custom configuration location, pass the corresponding explicit `--codex-home`, `--claude-home` or `--codex-skills-dir` value.
The script does not infer these environment variables, which also keeps isolated tests away from real agent configuration.
`--home` changes the base home for all defaults and is useful for testing.
Other agents can use the generated ENTRYPOINT without a skill loader.

## Discover and update existing installations

Run `setup_wiki.py --discover --agents codex claude` before choosing a new destination.
Discovery reads current entrypoints and skills without writing.
Reuse the reported wiki root; recorded layout and timezone are inferred when omitted.
An exact existing subfolder wiki path is accepted and resolved to its recorded vault boundary.
Multiple skill locations or connections to a different wiki stop installation before writes.
The installer never creates a second vault or skill to work around those conflicts.

Version 2 stores package version, settings and managed file hashes in `_system/installation.json`.
Rerunning the current installer upgrades unchanged managed files in place and backs up replaced files under `_system/setup-backups/`.
Known public version 1 files are recognized using bundled fingerprints.
A newer installed release is never downgraded.
An identical rerun is a no-op, preserving knowledge, sources, catalog, ledger, review state, history intake checkpoints, Home and Obsidian settings.
Global instruction symlinks are retained and their shared target is updated once.

For modified managed files, preview reports conflicts containing exact before/after hashes and makes no changes.
Save that JSON outside the wiki, inspect the current files and proposed templates, and merge meaningful local policy before proceeding.
Pass `--reviewed-plan <conflicts.json> --apply` only after reviewing those exact replacements within the user's update authorization.
If a file or the proposed replacement changes after review, acknowledgement no longer matches and the installer refuses it.
There is no blanket force-overwrite flag.

An existing unversioned wiki requires `--adopt-existing` after verifying its policy, runtime and knowledge layout.
Its differing files still require the same reviewed plan; adoption does not reset knowledge or processing state.
Unknown occupied namespaces are never silently adopted.
If a customization must stay, preserve it in the proposed managed template or keep that file unchanged before accepting the plan; do not approve a replacement that discards user policy.

## History and scheduling

The installer does not enable history access or create jobs implicitly.
The setup skill configures authorized local adapters using `_system/sessions.md`, with an explicit start timestamp.
Fresh installs start at installation time; past conversations require a selected backfill window.
Existing history config and checkpoints are reused, not reset by reinstalling.
Find and update the existing matching scheduler task before considering creation of another; see automation.md.

The private wiki's `.gitignore` excludes its contents from accidental Git staging; existing-vault mode scopes the added ignores to workflow files.
Keep the vault and private setup backups outside this public checkout.

References: [Obsidian vaults](https://help.obsidian.md/manage-vaults), [Obsidian configuration folders](https://help.obsidian.md/Files+and+folders/Configuration+folder), [Codex skills](https://learn.chatgpt.com/docs/build-skills), [Claude skills](https://code.claude.com/docs/en/skills).
