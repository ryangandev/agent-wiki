#!/usr/bin/env python3
"""Create an empty, private Agent Wiki and optional agent entrypoints. No network."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

PACKAGE = Path(__file__).resolve().parents[1]
ASSETS = PACKAGE / 'assets'
START = '<!-- agent-wiki:start -->'
END = '<!-- agent-wiki:end -->'
VERSION = 1


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
        'Use `agent-wiki` only when prior decisions, intent, constraints or lessons are needed and current context is insufficient, or when new confirmed durable knowledge merits capture.',
        'If the skill is unavailable, read `_system/recall.md` or `_system/ingest.md` inside that directory for the relevant mode.',
        'Search the compact index first, then read only relevant sections; never preload the whole wiki or all project summaries.',
        'Capture minimal evidence, not routine progress, transcripts or easily queried implementation facts.',
        'No new durable knowledge means no capture or report.',
        END,
    ])


def add_hook(text, block):
    if START not in text and END not in text:
        return text + ('\n\n' if text and not text.endswith('\n\n') else '') + block + '\n'
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError('Ambiguous Agent Wiki instruction markers; review the file manually')
    begin, end = text.index(START), text.index(END) + len(END)
    if end <= begin:
        raise ValueError('Reversed Agent Wiki instruction markers')
    if text[begin:end] != block:
        raise ValueError('An existing Agent Wiki entrypoint differs; review it before changing roots')
    return text


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
    home = Path(args.home).expanduser().resolve()
    codex_home = Path(args.codex_home).expanduser().resolve() if args.codex_home else home / '.codex'
    claude_home = Path(args.claude_home).expanduser().resolve() if args.claude_home else home / '.claude'
    skills_dir = Path(args.codex_skills_dir).expanduser().resolve() if args.codex_skills_dir else home / '.agents/skills'
    marker_path = root / '_system/installation.json'
    marker = {'format': VERSION, 'wiki_root': root.as_posix(), 'timezone': args.timezone,
              'vault_root': vault.as_posix(), 'layout': args.mode, 'link_prefix': link_prefix}
    existing_marker = content(marker_path)
    if args.mode == 'existing-vault' and existing_marker is None:
        if any((root / name).exists() for name in ('wiki', 'sources', '_system')):
            raise ValueError('An Agent Wiki namespace already exists; review it or choose subfolder mode')
    elif root.exists() and any(root.iterdir()) and existing_marker is None:
        raise ValueError('The destination is not empty and was not created by this installer')
    if existing_marker is not None and json.loads(existing_marker) != marker:
        raise ValueError('Existing installation settings differ; no automatic migration is performed')

    writes = {}
    def propose(path, data, allow_append=False):
        # Instruction-file symlinks may intentionally share one global file.
        destination = path.resolve()
        before = content(destination)
        if before is not None and before != data and not allow_append:
            raise ValueError(f'Existing file differs; refusing to overwrite: {destination}')
        if destination in writes and writes[destination][1] != data:
            raise ValueError(f'Conflicting output paths: {destination}')
        if before != data:
            writes[destination] = (before, data)

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
        else:
            propose(destination, data)
    propose(marker_path, encode(marker).encode('utf-8'))

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
        if agent == 'codex':
            destination, instructions = skills_dir / 'agent-wiki', codex_home / 'AGENTS.md'
            previous = codex_home / 'skills/agent-wiki'
            if previous.exists() and previous.resolve() != destination.resolve():
                raise ValueError(f'Another agent-wiki skill exists at {previous}; reconcile it before installing')
        else:
            destination, instructions = claude_home / 'skills/agent-wiki', claude_home / 'CLAUDE.md'
        if destination.is_symlink():
            raise ValueError(f'Skill destination is a symlink: {destination}')
        for source in sorted((ASSETS / 'runtime').rglob('*')):
            if source.is_file():
                propose(destination / source.relative_to(ASSETS / 'runtime'),
                        render(source.read_text(encoding='utf-8'), root, args.timezone, link_prefix).encode('utf-8'))
        current = content(instructions.resolve()) or b''
        new = add_hook(current.decode('utf-8'), block).encode('utf-8')
        if current != new and instructions.exists():
            digest = hashlib.sha256(current).hexdigest()[:16]
            propose(root / '_system/setup-backups' / (instructions.name + '.' + digest + '.bak'), current)
        propose(instructions, new, allow_append=True)
    return root, writes


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
    parser.add_argument('--vault', required=True, help='Exact new or existing vault path; use . only when that directory is the intended vault')
    parser.add_argument('--mode', choices=['new-vault', 'existing-vault', 'subfolder'], default='new-vault',
                        help='Default: create a standalone vault at --vault; existing-vault uses its root, subfolder creates a wiki within it')
    parser.add_argument('--wiki-name', help='Folder name within the vault, only for subfolder mode (default: Agent Wiki)')
    parser.add_argument('--agents', nargs='*', choices=['codex', 'claude'], default=[])
    parser.add_argument('--home', default=str(Path.home()), help='User home; override for isolated testing')
    parser.add_argument('--codex-home', help='Override the Codex global-instructions directory')
    parser.add_argument('--claude-home', help='Override the Claude global configuration directory')
    parser.add_argument('--codex-skills-dir', help='Override ~/.agents/skills for another supported host location')
    parser.add_argument('--timezone', default='local', help='Scheduler timezone, for example Europe/London')
    parser.add_argument('--apply', action='store_true', help='Write the previewed setup; default is read-only')
    args = parser.parse_args()
    root, writes = plan(args)
    if args.apply:
        execute(writes)
        for folder in ('wiki/projects', 'wiki/decisions', 'wiki/topics', 'wiki/methods', 'sources/conversations', 'sources/research'):
            (root / folder).mkdir(parents=True, exist_ok=True)
    print(encode({'mode': 'applied' if args.apply else 'preview', 'wiki_root': str(root),
                  'layout': args.mode, 'vault_root': str(Path(args.vault).expanduser().resolve()),
                  'changed_files': [str(p) for p in writes], 'scheduled': False,
                  'obsidian': 'Use Open folder as vault to open vault_root; application registration is not automatic.',
                  'next': 'Run the setup skill verification, then configure an authorized agent scheduler.'}))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    try:
        main()
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(encode({'error': str(error)}), file=sys.stderr)
        sys.exit(2)
