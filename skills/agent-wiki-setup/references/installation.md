# Installation details

## Requirements

Use Python 3.10 or later on macOS, Linux or Windows.
On Windows, use `py -3` or the appropriate `python` executable instead of `python3`.
No Obsidian plugin, API token, model subscription or network connection is required by the Python tools.
Semantic compilation still requires an agent with filesystem access.

## Locations

The installer creates `<vault>/Agent Wiki` unless `--wiki-name` is supplied.
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
A nonempty unrecognized destination, a differing skill, modified managed templates, or another wiki entrypoint causes an explicit conflict before writes.
This version initializes new installations; it is not an automatic upgrader for customized wikis.
Review and merge customizations explicitly instead of using a force-overwrite option.
Keep a private backup of irreplaceable notes and sources; Obsidian is the editor, not a backup guarantee.

The private wiki's `.gitignore` excludes its contents from accidental Git staging.
Users who intentionally version their private vault may adjust that policy themselves.
Do not initialize the wiki inside the public distribution checkout or publish generated setup backups.

References: [Codex skills](https://learn.chatgpt.com/docs/build-skills), [Claude skills](https://code.claude.com/docs/en/skills).
