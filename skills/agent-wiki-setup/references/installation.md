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

`--agents codex` writes a runtime skill to `~/.agents/skills/agent-wiki` and appends a small managed block to `~/.codex/AGENTS.md`.
`--agents claude` writes the runtime skill to `~/.claude/skills/agent-wiki` and appends the same block to `~/.claude/CLAUDE.md`.
Existing unrelated instruction text is preserved, including when both instruction files resolve to the same symlink target.

If the host uses `CODEX_HOME`, `CLAUDE_CONFIG_DIR` or another custom configuration location, pass the corresponding explicit `--codex-home`, `--claude-home` or `--codex-skills-dir` value.
The script does not infer these environment variables, which also keeps isolated tests away from real agent configuration.
`--home` changes the base home for all defaults and is useful for testing.
Other agents can use the generated ENTRYPOINT without a skill loader.

## Existing installations

Preview mode does not write files or create directories.
An identical rerun is a no-op and does not reset the catalog, ledger, review checkpoint or knowledge.
A nonempty unrecognized new-vault or subfolder destination, reserved-name conflicts in an existing vault, a differing skill, modified managed templates, or another wiki entrypoint causes an explicit conflict before writes.
This version initializes new installations; it is not an automatic upgrader for customized wikis.
Review and merge customizations explicitly instead of using a force-overwrite option.
Keep a private backup of irreplaceable notes and sources; Obsidian is the editor, not a backup guarantee.

The private wiki's `.gitignore` excludes its contents from accidental Git staging; existing-vault mode scopes the added ignores to workflow files.
Users who intentionally version their private vault may adjust that policy themselves.
Do not initialize the wiki inside the public distribution checkout or publish generated setup backups.

References: [Obsidian vaults](https://help.obsidian.md/manage-vaults), [Obsidian configuration folders](https://help.obsidian.md/Files+and+folders/Configuration+folder), [Codex skills](https://learn.chatgpt.com/docs/build-skills), [Claude skills](https://code.claude.com/docs/en/skills).
