#!/usr/bin/env python3
"""Exercise the installed tool against synthetic data in a disposable wiki."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def snapshot(root):
    return {p.relative_to(root).as_posix(): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
            for p in root.rglob('*') if p.is_file()}


def run_smoke(tool):
    checks = []
    with tempfile.TemporaryDirectory(prefix='agent-wiki-smoke-') as folder:
        temp = Path(folder).resolve()
        root = temp / 'Agent Wiki 知识'
        setup = Path(__file__).with_name('setup_wiki.py')
        subprocess.run([sys.executable, str(setup), '--vault', str(root), '--home', str(temp / 'home'), '--apply'],
                       check=True, capture_output=True, text=True, encoding='utf-8')
        def run(*args, fails=False):
            result = subprocess.run([sys.executable, str(tool), '--root', str(root), *args],
                                    capture_output=True, text=True, encoding='utf-8')
            if fails:
                if result.returncode == 0:
                    raise AssertionError('Expected a rejected operation')
                return json.loads(result.stderr)
            if result.returncode:
                raise AssertionError(result.stderr)
            return json.loads(result.stdout)
        def write(name, value):
            path = temp / name
            path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
            return str(path)
        assert run('check') == {'pages':0, 'pending':0, 'issues':[], 'awaiting_review':[]}
        checks.append('empty installation')
        evidence = temp / 'evidence.md'
        evidence.write_text('# Synthetic decision\n\nThis fixture exists only in a temporary test vault.\n', encoding='utf-8')
        source = run('capture', '--file', str(evidence))
        assert source['created'] and run('pending')['count'] == 1
        assert not run('capture', '--file', str(evidence))['created']
        assert run('pending')['count'] == 1
        checks.append('capture and exact deduplication')
        meta = {'id':'smoke-decision', 'title':'Synthetic decision', 'kind':'decision', 'scope':'smoke',
                'summary':'Synthetic evidence only.', 'as_of':'2000-01-01', 'status':'active',
                'aliases':['smoke'], 'keywords':['verification'], 'sources':[source['source']]}
        note = '---\n' + ''.join(k+': '+json.dumps(v, ensure_ascii=False)+'\n' for k,v in meta.items())
        note += '---\n\n# Synthetic decision\n\n## Conclusion\n\n合成测试，不是真实用户知识。\n'
        rel = 'wiki/decisions/smoke.md'
        payload = {'notes':[{'path':rel, 'expected_sha256':None, 'content':note}],
                   'resolved':[{'source':source['source'], 'sha256':source['sha256'], 'status':'compiled',
                                'targets':['smoke-decision'], 'reason':'Synthetic verification'}]}
        change = write('change.json', payload)
        assert run('apply', '--file', change) == {'changed':True, 'notes':1, 'sources':1}
        assert run('pending')['count'] == 0 and run('check')['issues'] == []
        assert run('search', 'smoke', '--scope', 'smoke')[0]['id'] == 'smoke-decision'
        assert '合成测试' in run('read', rel, '--section', 'Conclusion')['text']
        checks.append('compile, ledger, bounded recall and UTF-8 sections')
        assert 'Stale note' in run('apply', '--file', change, fails=True)['error']
        assert (root / rel).read_text(encoding='utf-8') == note
        checks.append('stale writes rejected')
        payload['notes'][0]['expected_sha256'] = hashlib.sha256(note.encode()).hexdigest()
        change = write('same.json', payload)
        assert run('apply', '--file', change) == {'changed':False, 'notes':0, 'sources':0}
        checks.append('idempotent publication')
        review = run('review')
        assert review['count'] == 1
        assert run('review', '--ack', '--file', write('review.json', review))['acknowledged'] == 1
        before = snapshot(root)
        assert run('pending')['count'] == 0
        assert run('review')['count'] == 0
        assert run('check')['issues'] == []
        assert snapshot(root) == before
        checks.append('acknowledged review and no-op preserve file bytes and mtimes')
    return {'passed':checks, 'private_wiki_modified':False, 'scope':'isolated CLI integration; not model judgment or scheduler access'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wiki', required=True)
    args = parser.parse_args()
    tool = Path(args.wiki).expanduser().resolve() / '_system/tools/wiki.py'
    if not tool.is_file():
        parser.error('Installed tool not found')
    print(json.dumps(run_smoke(tool), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    main()
