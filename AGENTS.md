# Repository instructions

This repository distributes an empty Agent Wiki workflow and setup skill.
Never add a real vault, personal notes, chat transcripts, credentials or generated setup backups.

Start at `docs/README.md` and read only the route relevant to the change.
The canonical installation assets live under `skills/agent-wiki-setup/assets/`.
Do not maintain a second copy of the runtime tool or operating policy elsewhere.

Use standard-library Python 3.10+ and preserve macOS, Linux and Windows support.
Keep installation preview read-only, preserve existing user instructions, and refuse conflicting files.
Tests must use temporary vaults and explicit fake home directories, never real agent configuration.

Run `python3 -m unittest discover -s tests -v` for runtime or installer changes.
Before publishing, verify the tracked file list contains the complete skill assets and no private data.
Distinguish CLI verification from model judgment, real agent permissions and scheduler acceptance.

Keep complete Markdown sentences on individual lines.
Do not add generated changelogs or auto-add agent co-authors.
