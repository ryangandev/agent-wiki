#!/usr/bin/env python3
"""Create an empty, private Agent Wiki and optional agent entrypoints. No network."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import sys
import tempfile

PACKAGE = Path(__file__).resolve().parents[1]
ASSETS = PACKAGE / 'assets'
START = '<!-- agent-wiki:start -->'
END = '<!-- agent-wiki:end -->'
VERSION = 2
PACKAGE_VERSION = "2.0.0"
BASELINE = json.loads(Path(__file__).with_name("baseline-v1.json").read_text(encoding="utf-8"))


def encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def render(data, root, timezone, link_prefix=''):
    return (data.replace('__WIKI_ROOT__', root.as_posix())
            .replace('__WIKI_LINK_PREFIX__', link_prefix)
            .replace('__TIMEZONE__', timezone))


def hook(root):
    return '\n'.join([
        START,
        '## Shared Agent Wiki',
        f'Long-term context lives at `{root.as_posix()}`.',
        'Recall: use `agent-wiki` when prior decisions, intent, constraints or lessons are needed and current context is insufficient; search the compact index and read only relevant sections.',
        'Capture checkpoint: after the user confirms or corrects an important decision or lasting requirement, and before completing substantive work, assess the current conversation for new reusable knowledge.',
        'When it qualifies, use `agent-wiki` to capture minimal evidence now; an extra "remember this" request is not required within authorized capture scope.',
        'This check uses current context and does not require loading the wiki. Skip routine progress, transcripts, duplicates and facts already adequately documented in the repository.',
        'If the skill is unavailable, read `_system/recall.md` or `_system/ingest.md` inside that directory for the relevant mode.',
        'Never preload the whole wiki or all project summaries. No new knowledge means no capture or report.',
        END,
    ])


def instruction_block(text):
    if START in text or END in text:
        if text.count(START) != 1 or text.count(END) != 1 or text.index(END) < text.index(START):
            raise ValueError('Ambiguous Agent Wiki instruction markers')
        return text.index(START), text.index(END) + len(END)
    match = re.search(r'(?m)^## Shared Agent Wiki\s*$', text)
    if match:
        tail = re.search(r'(?m)^## ', text[match.end():])
        end = match.end() + tail.start() if tail else len(text)
        return match.start(), end
    return None


def normalized(data, root, timezone, prefix):
    text = data.decode('utf-8').replace('\r\n', '\n').replace(root.as_posix(), '__WIKI_ROOT__')
    text = text.replace(timezone, '__TIMEZONE__')
    return text.replace(prefix, '') if prefix else text


def locations(args):
    home = Path(args.home).expanduser().resolve()
    codex = Path(args.codex_home).expanduser().resolve() if args.codex_home else home / '.codex'
    claude = Path(args.claude_home).expanduser().resolve() if args.claude_home else home / '.claude'
    candidates = [home / '.agents/skills/agent-wiki', codex / 'skills/agent-wiki']
    if args.codex_skills_dir:
        candidates.insert(0, Path(args.codex_skills_dir).expanduser().resolve() / 'agent-wiki')
    existing = {p.resolve(): p for p in candidates if p.exists()}
    if len(existing) > 1 and 'codex' in args.agents:
        raise ValueError('Multiple Codex agent-wiki skills already exist; reconcile these instead of adding another: ' + ', '.join(map(str, existing)))
    if 'codex' in args.agents and any(not (p / 'SKILL.md').is_file() for p in existing.values()):
        raise ValueError('Existing Codex skill directory is incomplete; inspect it before installation')
    skill = next(iter(existing.values()), candidates[0])
    return {'codex': (skill, codex / 'AGENTS.md'), 'claude': (claude / 'skills/agent-wiki', claude / 'CLAUDE.md')}


def discover(args):
    result = []
    for agent, (skill, instructions) in locations(args).items():
        roots = set()
        for path in (skill / 'SKILL.md', instructions):
            if path.is_file():
                text = path.read_text(encoding='utf-8')
                roots.update(re.findall(r'(?:Shared root:|Long-term context lives at)\s*`([^`]+)`', text))
        result.append({'agent': agent, 'skill': str(skill), 'installed': (skill / 'SKILL.md').is_file(),
                       'instructions': str(instructions), 'wiki_roots': sorted(roots)})
    return result


def content(path):
    if path.exists() and not path.is_file():
        raise ValueError(f'Expected a file: {path}')
    return path.read_bytes() if path.exists() else None


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    fd, temp = tempfile.mkstemp(prefix='.agent-wiki-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def plan(args):
    requested = Path(args.vault).expanduser().absolute()
    if requested.is_symlink():
        raise ValueError('Select the real vault directory, not a symlink')
    vault = requested.resolve()
    if args.mode == 'new-vault':
        if not vault.parent.is_dir():
            raise ValueError('The new vault parent directory must already exist')
    elif not vault.is_dir():
        raise ValueError('Select an existing vault directory for this mode')
    if vault.is_relative_to(PACKAGE):
        raise ValueError('Keep the private vault outside the distributed skill')
    checkout = next((p for p in PACKAGE.parents if (p / '.git').exists()), None)
    if checkout is not None and vault.is_relative_to(checkout):
        raise ValueError('Keep the private vault outside the distribution checkout')
    if args.wiki_name is not None and args.mode != 'subfolder':
        raise ValueError('--wiki-name is only for subfolder mode; --vault is otherwise the exact root')
    folder_name = args.wiki_name or 'Agent Wiki'
    if (not folder_name.strip() or folder_name in ('.', '..')
            or any(c in folder_name for c in '/\\<>:"|?*\n\r\t`[]')
            or folder_name.endswith(('.', ' '))):
        raise ValueError('wiki-name must be a single portable folder name')
    if not args.timezone or any(c in args.timezone for c in '\n\r`'):
        raise ValueError('Provide a timezone name without control characters')
    if args.mode != 'subfolder' and any((p / '.obsidian').exists() for p in vault.parents):
        raise ValueError('This folder is inside another vault; select that vault root or use subfolder mode')
    root = vault / folder_name if args.mode == 'subfolder' else vault
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise ValueError('The wiki root must be a real directory')
    if args.mode == 'new-vault' and (root / '.obsidian').exists() and not (root / '.obsidian').is_dir():
        raise ValueError('The Obsidian configuration path must be a directory')
    link_prefix = root.name + '/' if args.mode == 'subfolder' else ''
    agent_locations = locations(args)
    marker_path = root / '_system/installation.json'
    existing_marker = content(marker_path)
    previous = json.loads(existing_marker) if existing_marker is not None else {}
    installed_release = previous.get('package_version', '1.0.0')
    if not re.fullmatch(r'\d+\.\d+\.\d+', installed_release):
        raise ValueError('Unknown installed release; review before updating')
    if previous.get('format', 1) > VERSION or tuple(map(int, installed_release.split('.'))) > tuple(map(int, PACKAGE_VERSION.split('.'))):
        raise ValueError('Installed workflow is newer than this installer; refusing a downgrade')
    settings = {'wiki_root': root.as_posix(), 'timezone': args.timezone,
                'vault_root': vault.as_posix(), 'layout': args.mode, 'link_prefix': link_prefix}
    if previous and any(previous.get(k, value) != value for k, value in settings.items()):
        raise ValueError('Existing installation settings differ; reuse its recorded path, layout and timezone')
    for connection in discover(args):
        if connection['agent'] in args.agents:
            for found in connection['wiki_roots']:
                if Path(found).expanduser().resolve() != root:
                    raise ValueError('An agent is already connected to ' + found + '; reuse that wiki rather than creating a duplicate')
    recognized = all((root / name).exists() for name in ('_system/tools/wiki.py', '_system/GUIDE.md', 'wiki', 'sources'))
    if existing_marker is None:
        occupied = root.exists() and (any((root / name).exists() for name in ('wiki', 'sources', '_system'))
                                     if args.mode == 'existing-vault' else any(root.iterdir()))
        if occupied and not (args.adopt_existing and recognized):
            raise ValueError('Existing unversioned files detected; inspect them and use --adopt-existing with a reviewed plan, not another installation')
    marker = dict(settings, format=VERSION, package_version=PACKAGE_VERSION,
                  managed=dict(previous.get('managed', {})), agents=sorted(set(previous.get('agents', [])) | set(args.agents)))
    writes, conflicts = {}, []
    approved = json.loads(Path(args.reviewed_plan).read_text(encoding='utf-8')) if args.reviewed_plan else {}
    approvals = {x['path']: x for x in approved.get('conflicts', [])}

    def propose(path, data, allow_append=False, asset=None):
        if path.is_relative_to(root) and any(p.is_symlink() for p in [path, *path.parents] if p.is_relative_to(root)):
            raise ValueError('Symlink inside wiki: ' + str(path))
        destination = path.resolve()
        before = content(destination)
        key = str(destination)
        trusted = before is None or before == data or allow_append
        if not trusted and sha256(before) == previous.get('managed', {}).get(key):
            trusted = True
        if not trusted and previous.get('format') == 1 and asset:
            trusted = sha256(normalized(before, root, args.timezone, link_prefix).encode()) == BASELINE.get(asset)
        if not trusted:
            conflict = {'path': key, 'before_sha256': sha256(before), 'after_sha256': sha256(data)}
            if approvals.get(key) != conflict:
                conflicts.append(conflict)
        if destination in writes and writes[destination][1] != data:
            raise ValueError(f'Conflicting output paths: {destination}')
        if before != data:
            writes[destination] = (before, data)
        if asset:
            marker['managed'][key] = sha256(data)


    for source in sorted((ASSETS / 'wiki').rglob('*')):
        if not source.is_file() or '__pycache__' in source.parts:
            continue
        rel = source.relative_to(ASSETS / 'wiki')
        destination = root / ('.gitignore' if rel.as_posix() == 'private.gitignore' else rel)
        if any(p.is_symlink() for p in [destination, *destination.parents] if p.is_relative_to(root)):
            raise ValueError(f'Symlink inside wiki: {destination}')
        raw = source.read_text(encoding='utf-8')
        data = render(raw, root, args.timezone, link_prefix).encode('utf-8') if source.suffix != '.py' else source.read_bytes()
        if rel.as_posix() == 'private.gitignore' and args.mode == 'existing-vault':
            before = content(destination) or b''
            block = b'# Agent Wiki private paths\n/Home.md\n/wiki/\n/sources/\n/_system/\n'
            data = before if block in before else before + (b'\n' if before and not before.endswith(b'\n') else b'') + block
            propose(destination, data, allow_append=True)
        elif rel.as_posix() in ('Home.md', 'private.gitignore') and destination.exists() and (previous or (args.adopt_existing and recognized)):
            continue  # These belong to the user after initial installation.
        else:
            propose(destination, data, asset='wiki/' + rel.as_posix())

    if args.mode == 'new-vault':
        configuration = root / '.obsidian/app.json'
        if not configuration.exists():
            if configuration.is_symlink() or configuration.parent.is_symlink():
                raise ValueError('Obsidian configuration must not be a symlink')
            propose(configuration, b'{}\n')

    # Never refresh processing state on a repeat install.
    for name, data in [('catalog.jsonl', b''), ('ledger.jsonl', b''), ('review.json', b'{"pages": {}}\n')]:
        p = root / '_system' / name
        if not p.exists():
            propose(p, data)

    block = hook(root)
    for agent in sorted(set(args.agents)):
        destination, instructions = agent_locations[agent]
        if destination.is_symlink():
            raise ValueError(f'Skill destination is a symlink: {destination}')
        for source in sorted((ASSETS / 'runtime').rglob('*')):
            if source.is_file():
                rel = source.relative_to(ASSETS / 'runtime')
                propose(destination / rel, render(source.read_text(encoding='utf-8'), root, args.timezone, link_prefix).encode('utf-8'),
                        asset='runtime/' + rel.as_posix())
        # Reuse the planned value when CLAUDE.md links to the same global file.
        target = instructions.resolve()
        current = writes[target][1] if target in writes else content(target) or b''
        text = current.decode('utf-8')
        span = instruction_block(text)
        if span:
            old = text[span[0]:span[1]].rstrip().replace('\r\n', '\n')
            new = (text[:span[0]] + block + '\n' + text[span[1]:].lstrip('\n')).encode('utf-8')
            digest = sha256(old.encode())
            known = (old == block or digest == previous.get('entrypoint_sha256')
                     or sha256(old.replace(root.as_posix(), '__WIKI_ROOT__').encode()) == BASELINE['entrypoint'])
            # Compare-and-swap approval covers the entire instruction file.
            propose(instructions, new, allow_append=known)
        else:
            new = (text + ('\n\n' if text and not text.endswith('\n\n') else '') + block + '\n').encode('utf-8')
            propose(instructions, new, allow_append=True)
    if args.agents:
        marker['entrypoint_sha256'] = sha256(block.encode())
    # Back up every changed existing file, never knowledge or transcript payloads.
    for path, (before, data) in list(writes.items()):
        if before is not None and before != data:
            backup = root / '_system/setup-backups' / (path.name + '.' + sha256(before)[:16] + '.bak')
            propose(backup, before)
    propose(marker_path, encode(marker).encode('utf-8'), allow_append=True)
    if conflicts:
        raise PlanConflict({'error': 'Local changes require review; no files were written',
                            'wiki_root': str(root), 'conflicts': conflicts,
                            'changed_files': [str(p) for p in writes]})
    # Persist private backups before replacing any managed file.
    writes = dict(sorted(writes.items(), key=lambda item: 0 if item[0].is_relative_to(root / '_system/setup-backups') else 1))
    return root, writes


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class PlanConflict(ValueError):
    def __init__(self, report):
        self.report = report
        super().__init__(report['error'])


def execute(writes):
    applied = []
    try:
        for path, (before, data) in writes.items():
            if content(path) != before:
                raise ValueError(f'File changed after planning: {path}; rerun to review the new state')
            atomic(path, data)
            applied.append(path)
    except Exception:
        for path in reversed(applied):
            before = writes[path][0]
            if before is None:
                path.unlink(missing_ok=True)
            else:
                atomic(path, before)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vault', help='Exact new or existing vault path; use . only when that directory is the intended vault')
    parser.add_argument('--mode', choices=['new-vault', 'existing-vault', 'subfolder'], default=None,
                        help='Default: create a standalone vault at --vault; existing-vault uses its root, subfolder creates a wiki within it')
    parser.add_argument('--wiki-name', help='Folder name within the vault, only for subfolder mode (default: Agent Wiki)')
    parser.add_argument('--agents', nargs='*', choices=['codex', 'claude'], default=None)
    parser.add_argument('--home', default=str(Path.home()), help='User home; override for isolated testing')
    parser.add_argument('--codex-home', help='Override the Codex global-instructions directory')
    parser.add_argument('--claude-home', help='Override the Claude global configuration directory')
    parser.add_argument('--codex-skills-dir', help='Override ~/.agents/skills for another supported host location')
    parser.add_argument('--timezone', default=None, help='Scheduler timezone, for example Europe/London')
    parser.add_argument('--apply', action='store_true', help='Write the previewed setup; default is read-only')
    parser.add_argument('--discover', action='store_true', help='Inspect existing agent connections without writing')
    parser.add_argument('--adopt-existing', action='store_true', help='Review an existing unversioned wiki in place')
    parser.add_argument('--reviewed-plan', help='Previously inspected conflict JSON; accepts only those exact before/after hashes')
    args = parser.parse_args()
    infer_agents = args.agents is None
    args.agents = args.agents or []
    if args.discover:
        print(encode({'connections': discover(args)}))
        return
    if not args.vault:
        parser.error('--vault is required unless using --discover')
    requested = Path(args.vault).expanduser().resolve()
    candidates = [requested / '_system/installation.json', requested / (args.wiki_name or 'Agent Wiki') / '_system/installation.json']
    existing = next((json.loads(p.read_text(encoding='utf-8')) for p in candidates if p.is_file()), {})
    if infer_agents and existing:
        args.agents = existing.get('agents', [])
        if 'agents' not in existing:
            args.agents = [c['agent'] for c in discover(args) if existing.get('wiki_root') in c['wiki_roots']]
    args.mode = args.mode or existing.get('layout', 'new-vault')
    args.timezone = args.timezone or existing.get('timezone', 'local')
    # An exact existing wiki path is accepted even when originally installed as a subfolder.
    if existing and requested.as_posix() == existing.get('wiki_root') and args.mode == 'subfolder':
        args.vault = existing['vault_root']
        args.wiki_name = requested.name
    root, writes = plan(args)
    if args.apply:
        execute(writes)
        for folder in ('wiki/projects', 'wiki/decisions', 'wiki/topics', 'wiki/methods', 'sources/conversations', 'sources/research'):
            (root / folder).mkdir(parents=True, exist_ok=True)
    print(encode({'mode': 'applied' if args.apply else 'preview', 'wiki_root': str(root),
                  'layout': args.mode, 'vault_root': str(Path(args.vault).expanduser().resolve()),
                  'changed_files': [str(p) for p in writes], 'scheduled': False, 'package_version': PACKAGE_VERSION,
                  'obsidian': 'Use Open folder as vault to open vault_root; application registration is not automatic.',
                  'next': 'Run the setup skill verification, then configure an authorized agent scheduler.'}))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    try:
        main()
    except PlanConflict as error:
        print(encode(error.report), file=sys.stderr)
        sys.exit(2)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(encode({'error': str(error)}), file=sys.stderr)
        sys.exit(2)
