#!/usr/bin/env python3
"""Small local Agent Wiki tools. Python standard library only; no model calls."""
import argparse
import base64
import contextlib
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

if os.name == 'nt':
    import msvcrt
else:
    import fcntl


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')


class Wiki:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.system = self.root / '_system'
        if not (self.system / 'installation.json').is_file():
            raise ValueError('Not an initialized Agent Wiki; run the setup skill first')
        installation = json.loads((self.system / 'installation.json').read_text(encoding='utf-8'))
        self.link_prefix = installation.get('link_prefix', self.root.name + '/')

    def path(self, rel, prefix=None):
        p = Path(rel)
        if p.is_absolute() or '..' in p.parts or not p.parts or '\\' in rel or ':' in rel:
            raise ValueError('Expected a relative path without traversal')
        if prefix and p.parts[0] != prefix:
            raise ValueError('Path must start with ' + prefix)
        result = self.root / p
        if any(part.is_symlink() for part in [result, *result.parents] if part != self.root.parent):
            raise ValueError('Symlinks are not writable wiki paths')
        if not result.resolve().is_relative_to(self.root):
            raise ValueError('Path escapes wiki')
        return result

    def atomic(self, rel, data):
        p = self.path(rel)
        if p.exists() and p.read_bytes() == data:
            return False
        p.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix='.wiki-', dir=p.parent)
        try:
            with os.fdopen(fd, 'wb') as out:
                out.write(data)
                out.flush()
                os.fsync(out.fileno())
            os.replace(tmp, p)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        return True

    @contextlib.contextmanager
    def lock(self):
        self.system.mkdir(parents=True, exist_ok=True)
        with self.path('_system/write.lock').open('a+b') as f:
            if os.name == 'nt':
                if f.tell() == 0:
                    f.write(b'\0')
                    f.flush()
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
            else:
                fcntl.flock(f, fcntl.LOCK_EX)
            try:
                yield
            finally:
                if os.name == 'nt':
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(f, fcntl.LOCK_UN)

    def ledger(self):
        p = self.path('_system/ledger.jsonl')
        return [json.loads(line) for line in p.read_text(encoding='utf-8').splitlines() if line] if p.exists() else []

    def documents(self, changes=None):
        documents = {}
        for p in sorted((self.root / 'wiki').rglob('*.md')):
            rel = p.relative_to(self.root).as_posix()
            documents[rel] = self.path(rel).read_text(encoding='utf-8')
        documents.update(changes or {})
        return documents

    def catalog(self, documents=None):
        records, ids = [], set()
        for rel, text in sorted((documents if documents is not None else self.documents()).items()):
            if not text.startswith('---\n') or '\n---\n' not in text[4:]:
                raise ValueError(rel + ': missing frontmatter')
            raw, body = text[4:].split('\n---\n', 1)
            meta = {}
            for line in raw.splitlines():
                if not line.strip():
                    continue
                key, val = line.split(':', 1)
                meta[key] = json.loads(val.strip())
            for key in ('id', 'title', 'kind', 'scope', 'summary', 'as_of', 'status'):
                if not isinstance(meta.get(key), str) or not meta[key]:
                    raise ValueError(rel + ': invalid ' + key)
            for key in ('aliases', 'keywords', 'sources'):
                if not isinstance(meta.get(key), list) or not all(isinstance(x, str) for x in meta[key]):
                    raise ValueError(rel + ': invalid ' + key)
            if not meta['sources']:
                raise ValueError(rel + ': at least one evidence source required')
            if meta['id'] in ids:
                raise ValueError('Duplicate id: ' + meta['id'])
            ids.add(meta['id'])
            if meta['kind'] not in ('project', 'topic', 'decision', 'method'):
                raise ValueError('Unknown kind')
            if meta['status'] not in ('active', 'historical', 'needs-review', 'superseded'):
                raise ValueError('Unknown status')
            for source in meta['sources']:
                if not self.path(source, 'sources').is_file():
                    raise ValueError(rel + ': missing source ' + source)
            for link in re.findall(r'\[\[([^\]|#]+)(?:[^\]]*)\]\]', body):
                target = link.removeprefix(self.link_prefix) if self.link_prefix else link
                if not target.endswith('.md'):
                    target += '.md'
                if target not in (documents or {}) and not self.path(target).is_file():
                    raise ValueError(rel + ': broken link ' + link)
            meta.update(path=rel, sha256=sha(text.encode()), headings=re.findall(r'^## (.+)$', body, re.M))
            records.append(meta)
        return records

    def index_bytes(self, records):
        return ''.join(encode(r) + '\n' for r in records).encode()

    def rebuild(self):
        with self.lock():
            self.require_clean_publication()
            records = self.catalog()
            return {'changed': self.atomic('_system/catalog.jsonl', self.index_bytes(records)), 'pages': len(records)}

    def search(self, query, scope, limit):
        p = self.path('_system/catalog.jsonl')
        if not p.exists():
            raise ValueError('Catalog missing; run rebuild')
        terms = re.findall(r'[\w\-]+', query.casefold())
        found = []
        for line in p.read_text(encoding='utf-8').splitlines():
            r = json.loads(line)
            if r['status'] == 'superseded' or (scope and r['scope'].casefold() != scope.casefold()):
                continue
            title = ' '.join([r['title'], r['id'], *r['aliases']]).casefold()
            hay = ' '.join([title, r['scope'], r['summary'], *r['keywords'], *r['headings']]).casefold()
            score = sum(4 if t in title else 1 if t in hay else 0 for t in terms)
            if score or (scope and not terms):
                found.append((score, r))
        found.sort(key=lambda pair: (-pair[0], pair[1]['id']))
        return [{k:r[k] for k in ('id', 'title', 'scope', 'summary', 'as_of', 'status', 'path', 'headings', 'sha256')} for _, r in found[:limit]]

    def pending(self, limit=20):
        limit = max(1, min(limit, 100))
        seen = {(r['source'], r['sha256']) for r in self.ledger() if r.get('type') == 'source'}
        pending = []
        for p in sorted((self.root / 'sources').rglob('*.md')):
            rel = p.relative_to(self.root).as_posix()
            digest = sha(self.path(rel).read_bytes())
            if (rel, digest) not in seen:
                pending.append({'source': rel, 'sha256': digest, 'bytes': p.stat().st_size})
        return {'count': len(pending), 'items': pending[:limit], 'remaining': max(0, len(pending)-limit)}

    def capture(self, file, category):
        if category not in ('conversations', 'research'):
            raise ValueError('Unknown source category')
        data = Path(file).read_bytes()
        if not data.strip():
            raise ValueError('Empty capture')
        rel = 'sources/' + category + '/' + sha(data)[:24] + '.md'
        with self.lock():
            p = self.path(rel)
            if p.exists() and p.read_bytes() != data:
                raise ValueError('Hash collision; existing source preserved')
            changed = self.atomic(rel, data)
        return {'source': rel, 'sha256': sha(data), 'created': changed}

    def apply(self, payload):
        """Validate the whole batch, compare versions, then publish under one lock."""
        with self.lock():
            self.require_clean_publication()
            edits, old, paths = {}, {}, set()
            for item in payload.get('notes', []):
                rel, text = item['path'], item['content']
                p = self.path(rel, 'wiki')
                if not rel.endswith('.md') or rel in paths:
                    raise ValueError('Duplicate or non-Markdown note path')
                paths.add(rel)
                before = p.read_bytes() if p.exists() else None
                if item.get('expected_sha256') != (sha(before) if before is not None else None):
                    raise ValueError('Stale note; reread before merging: ' + rel)
                if before != text.encode():
                    edits[rel], old[rel] = text, before
            records = self.catalog(self.documents(edits))
            ids = {r['id'] for r in records}
            ledger = self.ledger()
            known = {(r.get('source'), r.get('sha256')): r for r in ledger if r.get('type') == 'source'}
            additions = []
            for item in payload.get('resolved', []):
                rel = item['source']
                data = self.path(rel, 'sources').read_bytes()
                if sha(data) != item['sha256']:
                    raise ValueError('Source changed; reread: ' + rel)
                if item['status'] not in ('compiled', 'duplicate', 'rejected', 'needs-review'):
                    raise ValueError('Invalid source disposition')
                if not item.get('reason') or not set(item.get('targets', [])).issubset(ids):
                    raise ValueError('Missing reason or invalid target')
                if item['status'] in ('compiled','duplicate') and not item.get('targets'):
                    raise ValueError('Compiled source must link to knowledge')
                key = (rel, item['sha256'])
                disposition = {k: item.get(k, []) if k == 'targets' else item[k]
                               for k in ('source', 'sha256', 'status', 'targets', 'reason')}
                previous = known.get(key, {})
                if any(previous.get(k) != value for k, value in disposition.items()):
                    additions.append(dict(disposition, type='source', recorded_at=now()))
                    known[key] = disposition
            if not edits and not additions:
                return {'changed': False, 'notes': 0, 'sources': 0}
            stamp = now()
            events = [{'type':'note','path':rel,'sha256':sha(text.encode()),'recorded_at':stamp} for rel,text in edits.items()]
            writes = {rel:text.encode() for rel,text in edits.items()}
            writes['_system/catalog.jsonl'] = self.index_bytes(records)
            writes['_system/ledger.jsonl'] = ''.join(encode(r)+'\n' for r in ledger+additions+events).encode()
            # Backups contain only changed compiled notes, never credentials or chat logs.
            backup = {}
            for rel in writes:
                p = self.path(rel)
                backup[rel] = p.read_bytes() if p.exists() else None
            for rel, data in old.items():
                if data is not None:
                    self.atomic('_system/history/' + sha(data) + '.md', data)
            journal = [{'path':rel, 'before':base64.b64encode(backup[rel]).decode() if backup[rel] is not None else None,
                        'after_sha256':sha(data)} for rel,data in writes.items()]
            self.atomic('_system/publish-in-progress.json', (encode(journal)+'\n').encode())
            try:
                for rel,data in writes.items():
                    self.atomic(rel,data)
            except Exception:
                for rel,data in backup.items():
                    if data is None:
                        self.path(rel).unlink(missing_ok=True)
                    else:
                        self.atomic(rel,data)
                self.path('_system/publish-in-progress.json').unlink()
                raise
            self.path('_system/publish-in-progress.json').unlink()
        return {'changed': True, 'notes': len(edits), 'sources': len(additions)}

    def require_clean_publication(self):
        if self.path('_system/publish-in-progress.json').exists():
            raise ValueError('Interrupted publication; run check and recover before publishing again')

    def recover(self):
        with self.lock():
            marker = self.path('_system/publish-in-progress.json')
            if not marker.exists():
                return {'recovered': False}
            journal = json.loads(marker.read_text(encoding='utf-8'))
            backups = {}
            for item in journal:
                rel = item['path']
                if not (rel.startswith('wiki/') and rel.endswith('.md')) and rel not in ('_system/catalog.jsonl', '_system/ledger.jsonl'):
                    raise ValueError('Invalid transaction path')
                p = self.path(rel)
                before = base64.b64decode(item['before'], validate=True) if item['before'] is not None else None
                current = p.read_bytes() if p.exists() else None
                if current != before and (current is None or sha(current) != item['after_sha256']):
                    raise ValueError('File changed after interruption; reconcile manually: '+rel)
                backups[rel] = before
            for rel,before in backups.items():
                if before is None:
                    self.path(rel).unlink(missing_ok=True)
                else:
                    self.atomic(rel,before)
            marker.unlink()
            return {'recovered': True, 'restored_files': len(backups)}

    def check(self):
        records = self.catalog()
        p = self.path('_system/catalog.jsonl')
        issues = []
        if not p.exists() or p.read_bytes() != self.index_bytes(records):
            issues.append('catalog-stale: run rebuild')
        if self.path('_system/publish-in-progress.json').exists():
            issues.append('interrupted-publication: inspect the saved transaction before writing')
        latest = {}
        for r in self.ledger():
            if r.get('type') == 'source':
                latest[r['source']] = r
        for rel,r in latest.items():
            if not self.path(rel,'sources').exists():
                issues.append('missing-processed-source: '+rel)
        waiting = [rel for rel,r in latest.items() if r.get('status') == 'needs-review']
        return {'pages':len(records), 'issues':issues, 'pending':self.pending()['count'], 'awaiting_review':waiting}

    def review(self):
        records = self.catalog()
        checkpoint = self.path('_system/review.json')
        previous = json.loads(checkpoint.read_text(encoding='utf-8')) if checkpoint.exists() else {}
        previous_hashes = previous.get('pages',{})
        changed = {r['path'] for r in records if previous_hashes.get(r['path']) != r['sha256']}
        scopes = {r['scope'] for r in records if r['path'] in changed}
        candidates = [{'id':r['id'],'path':r['path'],'scope':r['scope'],'summary':r['summary'],'sha256':r['sha256']} for r in records if r['scope'] in scopes]
        if not candidates:
            return {'count':0,'items':[]}
        return {'count':len(candidates),'items':candidates}

    def acknowledge(self, snapshot):
        with self.lock():
            self.require_clean_publication()
            current = self.review()
            if snapshot != current:
                raise ValueError('Review scope changed; inspect the new candidates before acknowledging')
            if current['count'] == 0:
                return {'acknowledged': 0}
            records = self.catalog()
            self.atomic('_system/review.json', (encode({'pages':{r['path']:r['sha256'] for r in records},'reviewed_at':now()})+'\n').encode())
            return {'acknowledged':current['count']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(Path(__file__).resolve().parents[2]))
    sub = parser.add_subparsers(dest='command', required=True)
    s = sub.add_parser('search'); s.add_argument('query', nargs='?', default=''); s.add_argument('--scope'); s.add_argument('--limit',type=int,default=4); s.add_argument('--max-chars',type=int,default=2800)
    r = sub.add_parser('read'); r.add_argument('path'); r.add_argument('--section'); r.add_argument('--max-chars',type=int,default=7000); r.add_argument('--offset',type=int,default=0)
    sub.add_parser('pending').add_argument('--limit',type=int,default=20)
    c = sub.add_parser('capture'); c.add_argument('--file',required=True); c.add_argument('--category',choices=['conversations','research'],default='conversations')
    sub.add_parser('apply').add_argument('--file',required=True)
    sub.add_parser('rebuild'); sub.add_parser('check'); sub.add_parser('recover'); rv=sub.add_parser('review'); rv.add_argument('--ack',action='store_true'); rv.add_argument('--file')
    a = parser.parse_args(); w = Wiki(a.root)
    if a.command == 'search':
        result = w.search(a.query,a.scope,max(1,min(a.limit,10)))
        budget = max(200,min(a.max_chars,12000))
        while len(encode(result)) > budget and result:
            result.pop()
        print(encode(result)); return
    if a.command == 'read':
        data = w.path(a.path).read_bytes()
        text = data.decode('utf-8')
        if a.section:
            parts = re.split(r'(?m)(?=^## )',text)
            text = next((p for p in parts if p.splitlines()[0] == '## '+a.section), '')
            if not text: raise ValueError('Section not found')
        offset=max(0,a.offset); end=offset+max(100,min(a.max_chars,30000))
        print(encode({'path':a.path,'section':a.section,'text':text[offset:end],'next_offset':end if end<len(text) else None,'sha256':sha(data)})); return
    if a.command == 'capture': result=w.capture(a.file,a.category)
    elif a.command == 'apply': result=w.apply(json.loads(Path(a.file).read_text(encoding='utf-8')))
    elif a.command == 'pending': result=w.pending(a.limit)
    elif a.command == 'review':
        if a.ack and not a.file:
            raise ValueError('Use review --ack --file with the exact reviewed JSON snapshot')
        result = w.acknowledge(json.loads(Path(a.file).read_text(encoding='utf-8'))) if a.ack else w.review()
    else: result=getattr(w,a.command)()
    print(encode(result))
    if a.command=='check' and result['issues']: sys.exit(1)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    try:
        main()
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as error:
        print(encode({'error':str(error)}),file=sys.stderr)
        sys.exit(2)
