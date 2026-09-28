import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / 'skills/agent-wiki-setup'
SETUP = SKILL / 'scripts/setup_wiki.py'
TOOL = SKILL / 'assets/wiki/_system/tools/wiki.py'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = load('wiki_runtime', TOOL)
installer = load('wiki_installer', SETUP)
smoke = load('wiki_smoke', SKILL / 'scripts/smoke_test.py')


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='agent-wiki-test-')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()
        self.vault = self.folder / 'My Vault 知识'; self.vault.mkdir()
        self.home = self.folder / 'home'
        self.root = self.vault / 'Agent Wiki'

    def setup_cli(self, *args, ok=True, mode='subfolder', vault=None):
        r = subprocess.run([sys.executable, str(SETUP), '--vault', str(vault or self.vault), '--mode', mode,
                            '--home', str(self.home), *args],
                           capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode == 0, ok, r.stderr)
        return json.loads(r.stdout if ok else r.stderr)

    def initialize(self):
        self.setup_cli('--apply')
        return runtime.Wiki(self.root)

    def note(self, wiki, title='Test', note_id='test'):
        file = self.folder / (note_id + '.md'); file.write_text(title, encoding='utf-8')
        source = wiki.capture(file, 'conversations')
        meta = dict(id=note_id, title=title, kind='decision', scope='test', summary='A synthetic decision.',
                    as_of='2000-01-01', status='active', aliases=[], keywords=['test'], sources=[source['source']])
        text = '---\n'+''.join(k+': '+json.dumps(v)+'\n' for k,v in meta.items())+'---\n\n## Conclusion\nTest.\n'
        return {'notes':[dict(path=f'wiki/decisions/{note_id}.md', expected_sha256=None, content=text)],
                'resolved':[dict(source=source['source'], sha256=source['sha256'], status='compiled', targets=[note_id], reason='Test')]}

    def test_isolated_end_to_end(self):
        result = smoke.run_smoke(TOOL)
        self.assertEqual(len(result['passed']), 6)
        self.assertFalse(result['private_wiki_modified'])

    def test_preview_creates_nothing(self):
        before = smoke.snapshot(self.folder)
        self.assertEqual(self.setup_cli('--agents','codex','claude')['mode'], 'preview')
        self.assertEqual(before, smoke.snapshot(self.folder))

    def test_standalone_vault_is_default_and_has_no_nested_folder(self):
        root = self.folder / 'Agent Wiki'
        command = [sys.executable, str(SETUP), '--vault', str(root), '--home', str(self.home)]
        preview = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(json.loads(preview.stdout)['layout'], 'new-vault')
        self.assertFalse(root.exists())
        subprocess.run(command + ['--apply'], check=True, capture_output=True)
        self.assertTrue((root / '.obsidian/app.json').is_file())
        self.assertTrue((root / 'Home.md').is_file())
        self.assertFalse((root / 'Agent Wiki').exists())
        self.assertIn('[[_system/GUIDE|', (root / 'Home.md').read_text(encoding='utf-8'))
        wiki = runtime.Wiki(root)
        payload = self.note(wiki)
        payload['notes'][0]['content'] += '\n[[' + payload['resolved'][0]['source'][:-3] + '|Evidence]]\n'
        wiki.apply(payload)
        self.assertFalse(wiki.check()['issues'])

    def test_standalone_repeat_install_preserves_obsidian_settings(self):
        root = self.folder / 'Agent Wiki'
        self.setup_cli('--apply', mode='new-vault', vault=root)
        settings = root / '.obsidian/app.json'
        settings.write_text('{"showLineNumber": true}', encoding='utf-8')
        before = smoke.snapshot(self.folder)
        self.assertEqual(self.setup_cli('--apply', mode='new-vault', vault=root)['changed_files'], [])
        self.assertEqual(before, smoke.snapshot(self.folder))

    def test_existing_vault_uses_root_and_preserves_unrelated_files(self):
        settings = self.vault / '.obsidian/app.json'
        settings.parent.mkdir()
        settings.write_bytes(b'{"showLineNumber": true}\n')
        (self.vault / 'Personal.md').write_bytes(b'Existing personal note\n')
        (self.vault / '.gitignore').write_bytes(b'attachments/\n')
        before = smoke.snapshot(self.vault)
        self.setup_cli('--agents', 'codex', '--apply', mode='existing-vault')
        self.assertTrue((self.vault / '_system/installation.json').is_file())
        self.assertFalse((self.vault / 'Agent Wiki').exists())
        after = smoke.snapshot(self.vault)
        for path in ('Personal.md', '.obsidian/app.json'):
            self.assertEqual(before[path], after[path])
        ignores = (self.vault / '.gitignore').read_text(encoding='utf-8')
        self.assertTrue(ignores.startswith('attachments/\n'))
        self.assertNotIn('\n*\n', ignores)
        self.assertEqual(self.setup_cli('--agents', 'codex', '--apply', mode='existing-vault')['changed_files'], [])
        self.assertEqual(after, smoke.snapshot(self.vault))

    def test_existing_vault_conflict_prevents_partial_installation(self):
        (self.vault / 'Home.md').write_bytes(b'My existing home page')
        before = smoke.snapshot(self.folder)
        self.setup_cli('--apply', mode='existing-vault', ok=False)
        self.assertEqual(before, smoke.snapshot(self.folder))

    def test_existing_vault_namespace_is_not_adopted(self):
        folder = self.vault / 'wiki'
        folder.mkdir()
        (folder / 'notes.md').write_bytes(b'Unrelated wiki')
        before = smoke.snapshot(self.folder)
        self.setup_cli('--apply', mode='existing-vault', ok=False)
        self.assertEqual(before, smoke.snapshot(self.folder))

    def test_new_vault_does_not_nest_inside_another_vault(self):
        (self.vault / '.obsidian').mkdir()
        self.setup_cli('--apply', mode='new-vault', vault=self.vault / 'Agent Wiki', ok=False)
        self.assertFalse(self.root.exists())
        self.setup_cli('--apply')
        self.assertTrue((self.root / 'Home.md').is_file())
        self.assertFalse((self.root / '.obsidian').exists())

    def test_new_vault_does_not_adopt_nonempty_folder(self):
        (self.vault / 'Personal.md').write_bytes(b'My note')
        before = smoke.snapshot(self.folder)
        self.setup_cli('--apply', mode='new-vault', ok=False)
        self.assertEqual(before, smoke.snapshot(self.folder))

    def test_current_folder_can_be_selected_explicitly_as_vault(self):
        result = subprocess.run([sys.executable, str(SETUP), '--vault', '.', '--mode', 'existing-vault',
                                 '--home', str(self.home), '--apply'], cwd=self.vault,
                                check=True, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(Path(json.loads(result.stdout)['wiki_root']), self.vault)
        self.assertTrue((self.vault / 'wiki').is_dir())
        self.assertFalse(self.root.exists())

    def test_both_agents_preserve_instructions_and_repeat_install(self):
        instruction = self.home / '.codex/AGENTS.md'; instruction.parent.mkdir(parents=True)
        original = '# My rules\nKeep my projects private.\n'; instruction.write_text(original)
        self.setup_cli('--agents','codex','claude','--apply')
        self.assertTrue(instruction.read_text().startswith(original))
        self.assertTrue((self.home/'.agents/skills/agent-wiki/SKILL.md').exists())
        self.assertTrue((self.home/'.claude/skills/agent-wiki/SKILL.md').exists())
        self.assertEqual(len(list((self.root/'_system/setup-backups').glob('*'))), 1)
        before = smoke.snapshot(self.folder)
        self.assertEqual(self.setup_cli('--agents','codex','claude','--apply')['changed_files'], [])
        self.assertEqual(before, smoke.snapshot(self.folder))

    def test_reinstall_preserves_knowledge_and_state(self):
        wiki = self.initialize(); wiki.apply(self.note(wiki)); wiki.acknowledge(wiki.review())
        before = smoke.snapshot(self.root)
        self.assertEqual(self.setup_cli('--apply')['changed_files'], [])
        self.assertEqual(before, smoke.snapshot(self.root))

    def test_foreign_nonempty_wiki_is_not_overwritten(self):
        self.root.mkdir(); (self.root/'note.md').write_text('irreplaceable')
        before = smoke.snapshot(self.folder)
        self.setup_cli('--apply',ok=False)
        self.assertEqual(before,smoke.snapshot(self.folder))

    def test_existing_skill_conflict_prevents_all_writes(self):
        path = self.home/'.agents/skills/agent-wiki/SKILL.md'; path.parent.mkdir(parents=True)
        path.write_text('custom skill')
        before = smoke.snapshot(self.folder)
        self.setup_cli('--agents','codex','--apply',ok=False)
        self.assertEqual(before,smoke.snapshot(self.folder))

    def test_alternate_codex_skill_collision(self):
        (self.home/'.codex/skills/agent-wiki').mkdir(parents=True)
        self.setup_cli('--agents','codex','--apply',ok=False)
        self.assertFalse(self.root.exists())

    def test_shared_instruction_symlink_preserved(self):
        codex = self.home/'.codex/AGENTS.md'; codex.parent.mkdir(parents=True); codex.write_text('# Shared rules\n')
        claude = self.home/'.claude/CLAUDE.md'; claude.parent.mkdir(parents=True)
        try:
            claude.symlink_to(codex)
        except OSError:
            self.skipTest('Creating symlinks is unavailable on this host')
        self.setup_cli('--agents','codex','claude','--apply')
        self.assertTrue(claude.is_symlink())
        self.assertEqual(codex.read_text().count(installer.START), 1)

    def test_custom_name_and_obsidian_links(self):
        self.setup_cli('--wiki-name','Shared Brain','--apply')
        wiki = runtime.Wiki(self.vault/'Shared Brain'); payload=self.note(wiki)
        payload['notes'][0]['content']+='\n[[Shared Brain/'+payload['resolved'][0]['source'][:-3]+'|Evidence]]\n'
        wiki.apply(payload)
        self.assertFalse(wiki.check()['issues'])

    def test_path_escape_rejected(self):
        wiki=self.initialize()
        for path in ['../outside.md','wiki/../../outside.md','/absolute.md','wiki/..\\outside.md']:
            with self.subTest(path=path), self.assertRaises(ValueError): wiki.path(path)

    def test_broken_link_rejects_batch_without_publication(self):
        wiki=self.initialize(); payload=self.note(wiki)
        payload['notes'][0]['content']+='\n[[Agent Wiki/wiki/decisions/missing]]\n'
        before=smoke.snapshot(self.root)
        with self.assertRaises(ValueError):wiki.apply(payload)
        self.assertEqual(before,smoke.snapshot(self.root))

    def test_changed_source_rejected(self):
        wiki=self.initialize(); payload=self.note(wiki)
        (self.root/payload['resolved'][0]['source']).write_text('changed')
        with self.assertRaisesRegex(ValueError,'Source changed'):wiki.apply(payload)
        self.assertEqual(wiki.check()['pages'],0)

    def test_semantic_duplicate_does_not_make_another_page(self):
        wiki=self.initialize(); wiki.apply(self.note(wiki))
        f=self.folder/'duplicate.md';f.write_text('Equivalent idea expressed differently')
        source=wiki.capture(f,'conversations')
        result=wiki.apply({'resolved':[dict(source=source['source'],sha256=source['sha256'],status='duplicate',targets=['test'],reason='Same conclusion')]})
        self.assertEqual(result,{'changed':True,'notes':0,'sources':1})
        self.assertEqual(wiki.check()['pages'],1)
        self.assertEqual(wiki.pending()['count'],0)

    def test_conflict_can_be_resolved_without_losing_history(self):
        wiki = self.initialize()
        payload = self.note(wiki)
        disposition = dict(payload['resolved'][0], status='needs-review', targets=[], reason='Uncertain claim')
        wiki.apply({'resolved': [disposition]})
        self.assertEqual(wiki.check()['awaiting_review'], [disposition['source']])
        wiki.apply(payload)
        self.assertEqual(wiki.check()['awaiting_review'], [])
        history = [r['status'] for r in wiki.ledger() if r.get('type') == 'source']
        self.assertEqual(history, ['needs-review', 'compiled'])
        self.assertFalse(wiki.apply({'resolved': payload['resolved']})['changed'])

    def test_recovery_preserves_manual_edits_after_interruption(self):
        wiki = self.initialize()
        payload = self.note(wiki)
        original = wiki.atomic
        def interruption(rel, data):
            if rel == '_system/catalog.jsonl':
                raise KeyboardInterrupt()
            return original(rel, data)
        with patch.object(wiki, 'atomic', side_effect=interruption), self.assertRaises(KeyboardInterrupt):
            wiki.apply(payload)
        note = self.root / payload['notes'][0]['path']
        note.write_text('A manual correction after the interruption', encoding='utf-8')
        before = note.read_bytes()
        with self.assertRaisesRegex(ValueError, 'File changed after interruption'):
            wiki.recover()
        self.assertEqual(note.read_bytes(), before)

    def test_review_snapshot_cannot_ack_unread_new_page(self):
        wiki=self.initialize();wiki.apply(self.note(wiki));snapshot=wiki.review()
        wiki.apply(self.note(wiki,'Another','another'))
        with self.assertRaisesRegex(ValueError,'Review scope changed'):wiki.acknowledge(snapshot)
        self.assertEqual(wiki.review()['count'],2)

    def test_publish_rolls_back_on_io_error(self):
        wiki=self.initialize();payload=self.note(wiki)
        before=smoke.snapshot(self.root); original=wiki.atomic; failed=False
        def failure(rel,data):
            nonlocal failed
            if rel=='_system/catalog.jsonl' and not failed:
                failed=True;raise OSError('Synthetic disk failure')
            return original(rel,data)
        with patch.object(wiki,'atomic',side_effect=failure),self.assertRaises(OSError):wiki.apply(payload)
        self.assertEqual({k:v[0] for k,v in before.items()},{k:v[0] for k,v in smoke.snapshot(self.root).items()})
        self.assertEqual(wiki.check()['pending'],1)

    def test_interrupted_publication_can_be_recovered(self):
        wiki=self.initialize();payload=self.note(wiki);original=wiki.atomic
        def interruption(rel,data):
            if rel=='_system/catalog.jsonl':raise KeyboardInterrupt()
            return original(rel,data)
        with patch.object(wiki,'atomic',side_effect=interruption),self.assertRaises(KeyboardInterrupt):wiki.apply(payload)
        self.assertTrue(any('interrupted-publication' in x for x in wiki.check()['issues']))
        with self.assertRaisesRegex(ValueError,'Interrupted publication'):wiki.apply(payload)
        self.assertTrue(wiki.recover()['recovered'])
        self.assertEqual(wiki.check()['pages'],0)
        self.assertEqual(wiki.pending()['count'],1)

    def test_setup_detects_file_change_after_planning(self):
        path=self.folder/'settings.md';path.write_bytes(b'original')
        writes={path:(b'original',b'new')};path.write_bytes(b'other agent')
        with self.assertRaisesRegex(ValueError,'File changed'):installer.execute(writes)
        self.assertEqual(path.read_bytes(),b'other agent')


if __name__=='__main__':unittest.main()
