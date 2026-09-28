# Agent Wiki

[中文说明](README.zh-CN.md) · [Workflow](docs/workflow.md) · [Setup skill](skills/agent-wiki-setup/SKILL.md)

A private, shared memory for agents, stored as ordinary Markdown in an Obsidian vault.
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
Ask for my vault path, participating agents and timezone if you cannot determine them.
Install the workflow, run its isolated verification, and configure maintenance
through my agent host's supported scheduler if available.
Report installation, agent access and scheduling separately.
```

In Codex, you can also ask its skill installer to install that GitHub skill URL and then invoke `$agent-wiki-setup`.
For Claude Code or another skill-compatible host, install the complete `skills/agent-wiki-setup` directory in its supported skill location, or clone this repository and point the agent to its `SKILL.md`.
Installing the setup skill alone does not create the wiki: run it once to choose your private destination and connections.

## Set up from the command line

Requires Python 3.10 or later.
The tools use the standard library and do not need an Obsidian plugin, API key or model connection.
An agent with filesystem access performs the actual interpretation and compilation.

Clone this repository, then run from its root:

```sh
git clone https://github.com/ryangandev/agent-wiki.git
cd agent-wiki

# Preview. Select an existing vault outside this checkout.
python3 skills/agent-wiki-setup/scripts/setup_wiki.py \
  --vault "/path/to/your/vault" \
  --agents codex claude \
  --timezone "Europe/London"

# Run the same command with --apply to write the reviewed installation.
```

Include only the agents you use, or omit `--agents` for a generic Markdown installation.
On Windows, use your Python executable, such as `py -3`, and put the command on one line.
Existing instructions are preserved; conflicting installations are reported before writing.
An identical rerun leaves existing knowledge and processing state intact.

The installer creates:

```text
Your private vault/
└── Agent Wiki/
    ├── Home.md                 # Human-readable entrypoint
    ├── wiki/                  # Canonical project, decision, topic and method pages
    ├── sources/               # Minimal evidence, read only when needed
    └── _system/               # Routing, policies, tools, ledger and revision history
```

For Codex and Claude Code, it also installs a small runtime `agent-wiki` skill and appends a routing block to the chosen agents' global instructions.
Other agents use the generated `_system/ENTRYPOINT.md` with their own instruction mechanism.
See [installation details](skills/agent-wiki-setup/references/installation.md) for custom locations and conflicts.

## Verify and schedule

```sh
python3 "/path/to/your/vault/Agent Wiki/_system/tools/wiki.py" check
python3 skills/agent-wiki-setup/scripts/smoke_test.py \
  --wiki "/path/to/your/vault/Agent Wiki"
```

The smoke test uses a disposable wiki and does not add synthetic knowledge to your real vault.
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
- Keep private backups. The generated wiki ignores its contents in Git by default; do not publish it with this distribution.
- Setup initializes new wikis and refuses conflicting customizations; it is not an automatic upgrade or migration tool.

## Develop

```sh
python3 -m unittest discover -s tests -v
```

Tests use temporary vaults and fake home directories.
CI runs on macOS, Linux and Windows with Python 3.10 and 3.13.
Start at [docs/README.md](docs/README.md) for the code map, design and current limitations.

MIT licensed.
