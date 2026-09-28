# Agent Wiki

[中文说明](README.zh-CN.md) · [Workflow](docs/workflow.md) · [Setup skill](skills/agent-wiki-setup/SKILL.md)

A private, shared memory for agents, stored as ordinary Markdown in a standalone Obsidian vault named `Agent Wiki` by default.
Keep decisions, their reasons, project constraints and reusable lessons that would otherwise need to be explained again.
Agents search a compact local index only when that history matters, then read the relevant sections.

This repository contains the workflow, an installable setup skill and Python tools.
It contains no personal knowledge or sample conversations.
Inspired by [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f); this is an independent implementation.

## How it works

1. **Recall when needed.** Search the index for missing historical context; read a few selected sections and open evidence only when necessary.
2. **Capture selectively.** Save a short, supported record when a conversation produces authorized durable knowledge.
3. **Compile daily.** An agent processes pending sources into canonical knowledge pages, merging duplicates and retaining decision history.
4. **Review weekly.** Review changed themes, resolve conflicts and compress repetition without erasing useful evidence.
5. **Do nothing when nothing changed.** No empty daily notes, timestamp refreshes or routine reports.

Code, live deployment status and other easily queried facts stay in their original systems.
The wiki stores the reasoning those systems often omit.

## Set up with an agent

Give your agent this request:

```text
Use https://github.com/ryangandev/agent-wiki/tree/main/skills/agent-wiki-setup
to set up a private Agent Wiki on my computer.
Read SKILL.md and obtain the complete skill directory, including its scripts and assets.
Recommend a new standalone vault named Agent Wiki and ask where to create it.
If I choose an existing vault or say this folder is already my vault, use that root directly.
Ask for any missing agent choices and timezone.
Install the workflow, run its isolated verification, and configure maintenance
through my agent host's supported scheduler if available.
Report installation, agent access and scheduling separately.
```

In Codex, you can also ask its skill installer to install that GitHub skill URL and then invoke `$agent-wiki-setup`.
For Claude Code or another skill-compatible host, install the complete `skills/agent-wiki-setup` directory in its supported skill location, or clone this repository and point the agent to its `SKILL.md`.
Installing the setup skill alone does not create the wiki: run it once to choose your private destination and connections.

The skill resolves the layout before installing:

| Choice | Result |
| --- | --- |
| **New vault (recommended)** | Creates `<chosen-parent>/Agent Wiki` as its own vault |
| **Use an existing vault, including the current folder** | Installs directly at that vault's root and preserves unrelated notes and settings |
| **Subfolder inside an existing vault** | Creates `<vault>/Agent Wiki` only when explicitly selected |

The current working directory is never assumed to be your vault.
If the requested root already contains conflicting workflow paths, the installer stops for review.

## Set up from the command line

Requires Python 3.10 or later.
The tools use the standard library and do not need an Obsidian plugin, API key or model connection.
An agent with filesystem access performs the actual interpretation and compilation.

Clone this repository, then run from its root:

```sh
git clone https://github.com/ryangandev/agent-wiki.git
cd agent-wiki

# Preview a new standalone vault. Its parent must already exist outside this checkout.
python3 skills/agent-wiki-setup/scripts/setup_wiki.py \
  --vault "/path/to/parent/Agent Wiki" \
  --mode new-vault \
  --agents codex claude \
  --timezone "Europe/London"

# Run the same command with --apply to write the reviewed installation.
```

Include only the agents you use, or omit `--agents` for a generic Markdown installation.
On Windows, use your Python executable, such as `py -3`, and put the command on one line.
Existing instructions are preserved; conflicting installations are reported before writing.
An identical rerun leaves existing knowledge and processing state intact.

For an existing vault, pass its exact path with `--mode existing-vault`; `--vault .` uses the current folder itself when that is your intended vault.
For an explicitly requested child folder, use `--mode subfolder` and optionally `--wiki-name "Agent Wiki"`.
`--vault` is always the vault path, while the reported `wiki_root` identifies where the workflow is installed.

The default layout is:

```text
Agent Wiki/                    # This folder IS the vault
├── .obsidian/                 # Minimal Obsidian configuration
├── Home.md                    # Human-readable entrypoint
├── wiki/                      # Canonical project, decision, topic and method pages
├── sources/                   # Minimal evidence, read only when needed
└── _system/                   # Routing, policies, tools, ledger and revision history
```

Use Obsidian's **Open folder as vault** to open this exact folder.
The installer prepares the files; it does not register or launch a vault in the app.

For Codex and Claude Code, it also installs a small runtime `agent-wiki` skill and appends a routing block to the chosen agents' global instructions.
Other agents use the generated `_system/ENTRYPOINT.md` with their own instruction mechanism.
See [installation details](skills/agent-wiki-setup/references/installation.md) for custom locations and conflicts.

## Verify and schedule

```sh
python3 "/path/to/parent/Agent Wiki/_system/tools/wiki.py" check
python3 skills/agent-wiki-setup/scripts/smoke_test.py \
  --wiki "/path/to/parent/Agent Wiki"
```

The smoke test uses a disposable wiki and does not add synthetic knowledge to your real vault.
For other layouts, replace the example path with the installer's reported `wiki_root`.
It verifies capture, publication, duplicate handling, recall, stale-write rejection and no-op behavior.

**Scheduling is a separate setup step.**
The installer produces a maintenance prompt, not a background service.
Recommended cadence is daily at 00:00 in your timezone, with a weekly review on Sunday.
Use a supported agent scheduler and verify its actual access before relying on unattended maintenance.
Without one, the same prompt works for manual maintenance.
See [scheduling and acceptance](skills/agent-wiki-setup/references/automation.md).

## Boundaries

- Only captured sources enter maintenance; it does not scan every chat or access another agent's session history.
- Exact repeated captures are deduplicated by Python; semantic merging and judgment belong to the agent.
- Retrieval has output limits, but this is not a promise of fixed token use or perfect recall.
- Local writers use a lock, revision checks and a recovery journal; synced devices still need one writer machine at a time.
- Keep private backups. Generated workflow files are ignored by Git by default; do not publish private knowledge with this distribution.
- Setup initializes new wikis and refuses conflicting customizations; it is not an automatic upgrade or migration tool.

## Develop

```sh
python3 -m unittest discover -s tests -v
```

Tests use temporary vaults and fake home directories.
CI runs on macOS, Linux and Windows with Python 3.10 and 3.13.
Start at [docs/README.md](docs/README.md) for the code map, design and current limitations.

MIT licensed.
