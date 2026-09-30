"""Synthetic end-to-end intake and installation regression coverage."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_workflow import SETUP, SKILL, TOOL, installer, runtime, smoke

sys.path.insert(0, str(TOOL.parent))
import sessions
sys.path.pop(0)


class IntakeUpgradeTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix='wiki-intake-test-')
        self.addCleanup(folder.cleanup)
        self.base = Path(folder.name).resolve()
        self.root = self.base / 'Brain'
        self.home = self.base / 'home'
        self.setup('--apply')
        self.wiki = runtime.Wiki(self.root)
        self.intake = sessions.Sessions(self.wiki)
        self.codex = self.home / '.codex'
        self.claude = self.home / '.claude'
        (self.codex / 'sessions').mkdir(parents=True, exist_ok=True)
        (self.claude / 'projects/demo').mkdir(parents=True, exist_ok=True)

    def setup(self, *args, ok=True, root=None):
        r = subprocess.run([sys.executable, str(SETUP), '--vault', str(root or self.root),
                            '--home', str(self.home), *args], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode == 0, ok, r.stderr)
        return json.loads(r.stdout if ok else r.stderr)

    def configure(self, agents=None):
        return self.intake.configure(agents or {'codex': str(self.codex), 'claude': str(self.claude)}, '2026-09-28T00:00:00+00:00')

    def codex_row(self, text, at='2026-09-29T01:00:00Z', role='user'):
        return {'type': 'response_item', 'timestamp': at,
                'payload': {'type': 'message', 'role': role, 'phase': 'final_answer',
                            'content': [{'type': 'input_text' if role == 'user' else 'output_text', 'text': text}]}}

    def claude_row(self, text, uuid='message-one'):
        return {'type': 'user', 'uuid': uuid, 'timestamp': '2026-09-29T01:00:00Z',
                'message': {'role': 'user', 'content': text}}

    def log(self, rows, agent='codex', name='one'):
        path = self.codex / ('sessions/rollout-' + name + '.jsonl') if agent == 'codex' else self.claude / ('projects/demo/' + name + '.jsonl')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
        return path

    def ignore(self, batch):
        return {'batch_id': batch['id'], 'items': [{'id': x['id'], 'status': 'ignored', 'reason': 'Synthetic routine event'} for x in batch['items']]}

    def test_missed_capture_is_visible_even_when_source_queue_empty(self):
        self.configure()
        self.log([self.codex_row('We chose native maps to preserve platform interactions.')])
        self.assertEqual(self.wiki.pending()['count'], 0)
        batch = self.intake.scan()
        self.assertEqual(batch['count'], 1)
        self.assertIn('native maps', batch['items'][0]['text'])
        self.assertTrue(self.intake.status()['batch_pending'])

    def test_capture_ack_compile_and_recall(self):
        self.configure()
        self.log([self.claude_row('Keep important contributions concise and accurate.')], agent='claude')
        batch = self.intake.scan()
        evidence = self.base / 'evidence.md'
        evidence.write_text('# Synthetic decision\nSource: fixture line 1\nConcise and accurate contributions.\n')
        source = self.wiki.capture(evidence, 'conversations')
        receipt = {'batch_id': batch['id'], 'items': [dict(id=batch['items'][0]['id'], status='captured', reason='Confirmed constraint', source=source['source'], sha256=source['sha256'])]}
        self.intake.ack(receipt)
        self.assertEqual(self.intake.scan()['count'], 0)
        meta = dict(id='writing', title='Writing', kind='decision', scope='demo', summary='Concise accurate contributions.',
                    as_of='2026-09-29', status='active', aliases=[], keywords=['contributions'], sources=[source['source']])
        note = '---\n' + ''.join(k + ': ' + json.dumps(v) + '\n' for k,v in meta.items()) + '---\n\n## Decision\nConcise, accurate contributions.\n'
        self.wiki.apply({'notes': [dict(path='wiki/decisions/writing.md', expected_sha256=None, content=note)],
                         'resolved': [dict(**source, status='compiled', targets=['writing'], reason='Synthetic confirmed requirement')]})
        self.assertEqual(self.wiki.search('contributions', None, 4)[0]['id'], 'writing')
        self.assertFalse(self.wiki.check()['issues'])

    def test_unacknowledged_batch_retries_exactly_and_requires_all_items(self):
        self.configure()
        self.log([self.codex_row('one'), self.codex_row('two')])
        batch = self.intake.scan()
        self.assertEqual(batch, self.intake.scan())
        receipt = self.ignore(batch)
        receipt['items'].pop()
        with self.assertRaisesRegex(ValueError, 'every item'):
            self.intake.ack(receipt)
        self.assertEqual(batch, self.intake.scan())
        self.intake.ack(self.ignore(batch))
        self.assertEqual(self.intake.ack(self.ignore(batch))['acknowledged'], 0)

    def test_ack_does_not_accept_nonexistent_evidence(self):
        self.configure()
        self.log([self.codex_row('a decision')])
        batch = self.intake.scan()
        receipt = self.ignore(batch)
        receipt['items'][0].update(status='captured', source='sources/conversations/missing.md', sha256='bad')
        with self.assertRaises(OSError):
            self.intake.ack(receipt)
        self.assertEqual(batch, self.intake.scan())

    def test_ignored_work_creates_no_knowledge_and_does_not_repeat(self):
        self.configure()
        self.log([self.codex_row('Tests passed; delete the merged branch.')])
        before = smoke.snapshot(self.root / 'wiki')
        batch = self.intake.scan()
        self.intake.ack(self.ignore(batch))
        self.assertEqual(self.intake.scan()['count'], 0)
        self.assertEqual(before, smoke.snapshot(self.root / 'wiki'))
        self.assertEqual(self.wiki.pending()['count'], 0)
        self.assertFalse((self.root / sessions.BATCH).exists())

    def test_appended_messages_and_archived_session_keep_checkpoint(self):
        self.configure()
        path = self.log([self.codex_row('first')])
        batch = self.intake.scan(); self.intake.ack(self.ignore(batch))
        archived = self.codex / 'archived_sessions' / path.name
        archived.parent.mkdir(); path.rename(archived)
        with archived.open('a') as out:
            out.write(json.dumps(self.codex_row('second', at='2026-09-29T02:00:00Z')) + '\n')
        batch = self.intake.scan()
        self.assertEqual([x['text'] for x in batch['items']], ['second'])

    def test_fork_duplicate_ids_already_reviewed_are_skipped(self):
        self.configure()
        row = self.claude_row('shared message')
        self.log([row], agent='claude')
        batch = self.intake.scan(); self.intake.ack(self.ignore(batch))
        self.log([row, self.claude_row('fork new decision', 'new-id')], agent='claude', name='fork')
        self.assertEqual([x['text'] for x in self.intake.scan()['items']], ['fork new decision'])

    def test_same_batch_forks_are_deduplicated(self):
        self.configure()
        row = self.claude_row('shared message')
        self.log([row], agent='claude')
        self.log([row], agent='claude', name='fork')
        batch = self.intake.scan()
        self.assertEqual(batch['count'], 1)
        self.intake.ack(self.ignore(batch))
        self.assertEqual(self.intake.scan()['count'], 0)

    def test_archive_between_scan_and_ack_is_supported(self):
        self.configure(); path = self.log([self.codex_row('decision')]); batch = self.intake.scan()
        archived = self.codex/'archived_sessions'/path.name
        archived.parent.mkdir(); path.rename(archived)
        self.intake.ack(self.ignore(batch))
        self.assertEqual(self.intake.scan()['count'], 0)

    def test_partial_message_rewrite_is_detected_before_ack(self):
        self.configure(); path = self.log([self.codex_row('A' * 4000)]); batch = self.intake.scan(max_chars=1000)
        path.write_text(json.dumps(self.codex_row('B' * 4000)) + '\n')
        with self.assertRaisesRegex(ValueError, 'record changed'):
            self.intake.ack(self.ignore(batch))

    def test_long_message_is_delivered_without_dropping_suffix(self):
        self.configure()
        body = 'A' * 2500 + 'Confirmed final decision.'
        self.log([self.codex_row(body)])
        pieces = []
        for _ in range(4):
            batch = self.intake.scan(max_chars=1000)
            if not batch['count']: break
            pieces.extend(x['text'] for x in batch['items'])
            self.intake.ack(self.ignore(batch))
        self.assertEqual(''.join(pieces), body)
        self.assertEqual(self.intake.scan()['count'], 0)

    def test_partial_trailing_record_waits_for_completion(self):
        self.configure()
        path = self.log([])
        raw = json.dumps(self.codex_row('decision')) + '\n'
        path.write_text(raw[:50])
        self.assertEqual(self.intake.scan()['count'], 0)
        with path.open('a') as out: out.write(raw[50:])
        self.assertEqual(self.intake.scan()['count'], 1)

    def test_malformed_record_is_error_not_empty_success(self):
        self.configure(); path = self.log([]); path.write_text('not-json\n')
        self.assertTrue(self.intake.scan()['errors'])
        self.assertTrue(self.intake.status()['errors'])

    def test_missing_configured_home_is_not_noop(self):
        self.configure({'claude': str(self.base / 'missing')})
        self.assertTrue(self.intake.scan()['errors'])

    def test_rewrite_before_ack_is_rejected(self):
        self.configure(); path = self.log([self.codex_row('one')]); batch = self.intake.scan()
        path.write_text(json.dumps(self.codex_row('two')) + '\n')
        with self.assertRaisesRegex(ValueError, 'changed before'):
            self.intake.ack(self.ignore(batch))

    def test_checkpoint_write_then_interruption_is_recoverable(self):
        self.configure(); self.log([self.codex_row('one')]); batch = self.intake.scan()
        original = Path.unlink
        def fail(path, *args, **kwargs):
            if path.name == 'batch.json': raise OSError('synthetic interruption')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'unlink', fail), self.assertRaises(OSError):
            self.intake.ack(self.ignore(batch))
        self.assertEqual(self.intake.ack(self.ignore(batch))['acknowledged'], 0)
        self.assertEqual(self.intake.scan()['count'], 0)

    def test_excludes_injected_context_thinking_tools_and_maintenance(self):
        self.configure()
        self.log([self.codex_row('# AGENTS.md instructions\nInjected rules'),
                  {'type':'response_item','payload':{'type':'function_call','arguments':'private tool data'}},
                  self.codex_row('actual decision')])
        self.log([self.codex_row('Automation: Agent Wiki Maintenance\nRun cleanup'), self.codex_row('Maintenance report',role='assistant')], name='maintenance')
        self.assertEqual([x['text'] for x in self.intake.scan()['items']], ['actual decision'])

    def test_configure_is_idempotent_and_does_not_reset(self):
        self.configure(); self.log([self.codex_row('one')]); batch = self.intake.scan(); self.intake.ack(self.ignore(batch))
        before = smoke.snapshot(self.root)
        self.configure()
        self.assertEqual(before, smoke.snapshot(self.root))
        with self.assertRaisesRegex(ValueError, 'already configured'):
            self.intake.configure({'codex':str(self.codex)},'2026-01-01T00:00:00+00:00')

    def test_prior_messages_outside_selected_window_not_imported(self):
        self.configure(); self.log([self.codex_row('old', at='2026-01-01T00:00:00Z'),self.codex_row('new')])
        self.assertEqual([x['text'] for x in self.intake.scan()['items']], ['new'])

    def test_repeat_upgrade_is_noop_and_keeps_user_home_page(self):
        self.setup('--agents','codex','claude','--apply')
        (self.root / 'Home.md').write_text('My custom homepage')
        before = smoke.snapshot(self.root)
        self.assertEqual(self.setup('--agents','codex','claude','--apply')['changed_files'], [])
        self.assertEqual(before, smoke.snapshot(self.root))

    def test_existing_legacy_codex_location_is_reused(self):
        self.setup('--agents','codex','--apply')
        source = self.home / '.agents/skills/agent-wiki'
        destination = self.codex / 'skills/agent-wiki'
        destination.parent.mkdir(); source.rename(destination)
        # Same bytes are safe even when the installation predates the tracked location.
        self.setup('--agents','codex','--apply')
        self.assertTrue((destination / 'SKILL.md').exists())
        self.assertFalse(source.exists())

    def test_existing_other_wiki_blocks_duplicate_installation(self):
        self.setup('--agents','codex','--apply')
        other = self.base / 'Second Wiki'
        report = self.setup('--agents','codex','--apply',root=other,ok=False)
        self.assertIn('already connected', report['error'])
        self.assertFalse(other.exists())

    def test_two_skill_locations_require_reconciliation(self):
        self.setup('--agents','codex','--apply')
        other = self.codex / 'skills/agent-wiki'; other.mkdir(parents=True)
        (other / 'SKILL.md').write_text('duplicate')
        self.assertIn('Multiple Codex', self.setup('--agents','codex','--apply',ok=False)['error'])

    def test_custom_file_requires_exact_review_and_backup(self):
        target = self.root / '_system/ingest.md'
        target.write_text('Custom capture rules to review')
        before = smoke.snapshot(self.root)
        report = self.setup('--apply',ok=False)
        self.assertEqual(before, smoke.snapshot(self.root))
        self.assertEqual(report['conflicts'][0]['path'], str(target))
        plan = self.base / 'review.json'; plan.write_text(json.dumps(report))
        self.setup('--reviewed-plan', str(plan), '--apply')
        backups = list((self.root/'_system/setup-backups').glob('ingest.md.*.bak'))
        self.assertIn('Custom capture rules to review', [p.read_text() for p in backups])
        self.assertEqual(self.setup('--apply')['changed_files'], [])

    def test_reviewed_plan_cannot_overwrite_later_edits(self):
        target = self.root/'_system/ingest.md'; target.write_text('first custom')
        report = self.setup(ok=False); plan = self.base/'review.json'; plan.write_text(json.dumps(report))
        target.write_text('newer custom')
        self.setup('--reviewed-plan',str(plan),'--apply',ok=False)
        self.assertEqual(target.read_text(), 'newer custom')

    def test_public_v1_skill_upgrades_using_known_fingerprint(self):
        self.setup('--agents','codex','--apply')
        skill = self.home/'.agents/skills/agent-wiki/SKILL.md'
        old = '---\nname: agent-wiki\ndescription: Recall prior decisions, project intent, constraints and reusable lessons when current context is insufficient; capture confirmed durable knowledge or maintain the shared Agent Wiki. Skip routine progress and facts answered by current code alone.\n---\n\n# Agent Wiki\n\nShared root: `__WIKI_ROOT__`.\n\nChoose one mode and read only its file inside that directory:\n\n- Recall: `_system/recall.md`, when historical context is needed and missing.\n- Capture or compile: `_system/ingest.md`, for new durable knowledge with evidence.\n- Maintenance: `_system/maintain.md`, for an authorized maintenance run.\n\nUse `_system/tools/wiki.py` to filter the index before reading matched sections.\nDo not preload Home, the full index, project summaries or source archives.\nNo substantive new knowledge means no capture and no status report.\nConsult `_system/GUIDE.md` only when policy is unclear.\n'
        skill.write_text(old.replace('__WIKI_ROOT__', self.root.as_posix()))
        marker = self.root/'_system/installation.json'
        data = json.loads(marker.read_text())
        data = {k:v for k,v in data.items() if k not in ('managed','package_version','entrypoint_sha256','agents')}
        data['format'] = 1
        marker.write_text(json.dumps(data))
        self.setup('--apply')
        self.assertIn('Capture checkpoint', (self.codex/'AGENTS.md').read_text())
        self.assertEqual(json.loads(marker.read_text())['format'], 2)
        self.assertNotEqual(skill.read_text(), old.replace('__WIKI_ROOT__', self.root.as_posix()))
        self.assertEqual(self.setup('--agents','codex','--apply')['changed_files'], [])

    def test_existing_agent_choices_are_reused_when_omitted(self):
        self.setup('--agents','codex','claude','--apply')
        marker=json.loads((self.root/'_system/installation.json').read_text())
        self.assertEqual(marker['agents'], ['claude', 'codex'])
        self.assertEqual(self.setup('--apply')['changed_files'], [])

    def test_newer_release_in_same_format_is_not_downgraded(self):
        path=self.root/'_system/installation.json';meta=json.loads(path.read_text());meta['package_version']='2.1.0';path.write_text(json.dumps(meta))
        self.assertIn('newer', self.setup('--apply',ok=False)['error'])

    def test_newer_version_is_never_downgraded(self):
        path = self.root/'_system/installation.json'; meta=json.loads(path.read_text());meta['format']=99;path.write_text(json.dumps(meta))
        self.assertIn('newer', self.setup('--apply',ok=False)['error'])

    def test_adopts_existing_unversioned_wiki_without_reset(self):
        (self.root/'_system/installation.json').unlink()
        (self.root/'_system/ingest.md').write_text('Original private policy')
        evidence = self.root/'sources/conversations/keep.md'; evidence.write_text('Existing evidence')
        self.setup('--apply',ok=False)
        report=self.setup('--adopt-existing',ok=False)
        plan=self.base/'review.json';plan.write_text(json.dumps(report))
        self.setup('--adopt-existing','--reviewed-plan',str(plan),'--apply')
        self.assertEqual(evidence.read_text(),'Existing evidence')
        self.assertEqual(self.setup('--apply')['changed_files'], [])

    def test_managed_upgrade_preserves_unrelated_global_instructions(self):
        self.setup('--agents','codex','--apply')
        path=self.codex/'AGENTS.md';path.write_text('# My new unrelated rule\n\n'+path.read_text())
        self.setup('--agents','codex','--apply')
        self.assertTrue(path.read_text().startswith('# My new unrelated rule'))
        self.assertEqual(path.read_text().count(installer.START), 1)


if __name__ == '__main__':
    unittest.main()
