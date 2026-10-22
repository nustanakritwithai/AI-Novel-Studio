"""Exact recap proposals from synthetic metadata; no actual approval or network."""
import base64
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import registry_schema, rollup, story_engine, storyctl


REPOSITORY = 'fixture-owner/fixture-studio'
APPROVAL_BASIS = 'UNVERIFIED_LOCAL_DECLARATIONS'


class RollupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name).resolve()
        self.root = self.fixture('alpha')
        self.beta = self.fixture('beta')

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def read(path):
        return json.loads(path.read_text(encoding='utf-8'))

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    @staticmethod
    def digest(value):
        return hashlib.sha256(value).hexdigest()

    @staticmethod
    def snapshot(root):
        return {str(path.relative_to(root)): path.read_bytes()
                for path in root.rglob('*') if path.is_file()}

    def fixture(self, slug):
        """Three local declared episodes, each with metadata-only source evidence."""
        root = storyctl.new_story(self.workspace, slug, 'Synthetic metadata fixture ' + slug)
        values = {
            'characters': {'characters': [{
                'id': 'CHAR-001', 'name': 'Synthetic fixture character', 'role': 'Metadata only',
                'known_traits': [], 'unknowns': [], 'knowledge': [],
            }]},
            'locations': {'locations': [{'id': 'LOC-001', 'name': 'Synthetic fixture location'}]},
            'episodes': {'episodes': []}, 'scenes': {'scenes': []}, 'events': {'events': []},
            'story_state': {'approved_through_scene': 'SC-003', 'active_episode': 'EP-003',
                            'phase': 'LOCAL_FIXTURE_STATE', 'flags': {}},
        }
        index = {'schema_version': 1, 'episodes': [], 'chapters': [], 'books': []}
        for number in range(1, 4):
            episode, scene = f'EP-{number:03}', f'SC-{number:03}'
            draft = f'drafts/{scene}.md'
            values['episodes']['episodes'].append({
                'id': episode, 'title': 'Synthetic episode metadata', 'status': 'APPROVED',
                'scene_ids': [scene], 'questions': [],
            })
            values['scenes']['scenes'].append({
                'id': scene, 'episode_id': episode, 'order': 1, 'title': 'Synthetic scene metadata',
                'status': 'APPROVED', 'pov': 'CHAR-001', 'location_id': 'LOC-001',
                'character_ids': ['CHAR-001'], 'item_ids': [], 'canon_refs': [],
                'goal': 'Metadata goal', 'conflict': 'Metadata constraint', 'outcome': 'Metadata outcome',
                'beats': ['Synthetic fixture metadata'], 'requires_flags': [], 'effects_flags': {},
                'draft_path': draft,
            })
            values['events']['events'].append({
                'id': f'EV-{number:03}', 'scene_id': scene, 'episode_id': episode, 'order': 1,
                'location_id': 'LOC-001', 'actors': ['CHAR-001'], 'effects_flags': {},
            })
            (root / draft).write_bytes(b'# Synthetic source evidence fixture; no narrative or actual review.\n')
            (root / 'scenes' / f'{scene}.md').write_bytes(b'# Synthetic scene card metadata fixture.\n')
            recap = ('# Synthetic recap metadata ' + slug + ' ' + episode + '\r\n'
                     + 'FIXTURE_FIELD_ONLY; NOT ACTUAL NARRATIVE OR AUTHENTICATED APPROVAL.\r\n' * 3)
            if number == 2:
                recap = recap.rstrip('\r\n')  # Deliberately no final newline.
            relative = f'ledger/episodes/{episode}.md'
            (root / relative).write_bytes(recap.encode('utf-8'))
            index['episodes'].append({
                'id': episode, 'scene_ids': [scene], 'summary_path': relative,
                'approval': {'pr_number': number, 'approved_by': 'synthetic-local-declaration',
                             'merge_commit': 'a' * 40, 'approved_at': '2026-10-22T13:00:00Z'},
            })
        for kind, value in values.items():
            self.write(root / 'data' / f'{kind}.json', {'schema_version': 1, **value})
        self.write(root / 'ledger/index.json', index)
        return root

    def add_provenance(self, root=None):
        root = root or self.root
        index = self.read(root / 'ledger/index.json')
        for record in index['episodes']:
            source = root / record['summary_path']
            record['provenance'] = {
                'repository': REPOSITORY, 'pr_number': record['approval']['pr_number'],
                'head_commit': 'b' * 40, 'merge_commit': 'a' * 40,
                'source_path': source.relative_to(self.workspace).as_posix(),
                'source_sha256': self.digest(source.read_bytes()),
            }
        self.write(root / 'ledger/index.json', index)
        return index

    def git_root(self, root, *args):
        self.assertEqual(args, ('rev-parse', '--show-toplevel'))
        return (str(self.workspace) + '\n').encode('utf-8')

    def observation(self, repository, pr_number, head_commit, merge_commit, source_path, source_sha256):
        """Synthetic full verifier response; this helper performs no API request."""
        repository, head_commit, merge_commit = repository.lower(), head_commit.lower(), merge_commit.lower()
        source_sha256 = source_sha256.lower()
        source = (self.workspace / source_path).read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(source)).encode('ascii') + b'\0' + source).hexdigest()
        return {
            'schema_version': 1, 'status': 'OBSERVED_MERGED_METADATA',
            'human_editorial_approval': 'UNVERIFIED', 'metadata_consistency': 'CONSISTENT',
            'transport': {'mode': 'LIVE_GH_API', 'hostname': 'github.com',
                          'network_attempted': True, 'requests_attempted': 8},
            'requested': {
                'repository': repository, 'pr_number': pr_number, 'head_commit': head_commit,
                'merge_commit': merge_commit, 'source_path': source_path, 'source_sha256': source_sha256,
            },
            'observed': {
                'pull_request': {'repository': repository, 'number': pr_number,
                                 'head_commit': head_commit, 'merge_commit': merge_commit,
                                 'merged': True, 'state': 'closed', 'merged_at': '2026-10-22T13:00:00Z'},
                'merge_commit': {'sha': merge_commit, 'tree_sha': 'd' * 40},
                'source': {'status': 'MATCHED_IMMUTABLE_BLOB', 'path': source_path,
                           'at_commit': merge_commit, 'blob_sha': blob, 'sha256': self.digest(source),
                           'byte_length': len(source), 'mode': '100644', 'matches_requested_sha256': True,
                           'relationship': 'PRESENT_AT_MERGE_NOT_PROOF_OF_PR_CHANGE_OR_EDITORIAL_REVIEW'},
            },
            'errors': [],
        }

    def online(self, episodes=None, response=None, verify=None):
        def observed(*args, **kwargs):
            if verify is not None:
                return verify(*args, **kwargs)
            report = self.observation(*args, **kwargs)
            if response is not None:
                report.update(copy.deepcopy(response))
            return report

        with patch('scripts.rollup.review_bundle._git', side_effect=self.git_root), \
                patch('scripts.rollup.provenance.verify', side_effect=observed) as checker:
            result = rollup.build(self.root, episodes or ['EP-001', 'EP-002'],
                                  repository=REPOSITORY, verify_remote=True)
        return result, checker

    def test_offline_exact_recap_bytes_and_proposal_boundaries(self):
        result = rollup.build(self.root, ['EP-001', 'EP-002'])
        self.assertEqual(result['schema_version'], 1)
        self.assertEqual(result['kind'], 'ROLLUP_PROPOSAL')
        self.assertEqual(result['status'], 'PROPOSED')
        self.assertEqual(result['approval_basis'], APPROVAL_BASIS)
        self.assertEqual(result['human_editorial_approval'], 'UNVERIFIED')
        self.assertEqual(result['source_verification'], 'OFFLINE_UNVERIFIED')
        self.assertEqual(result['story']['slug'], 'alpha')
        self.assertEqual(result['episode_ids'], ['EP-001', 'EP-002'])
        exact = []
        for record, episode in zip(result['sources'], result['episode_ids']):
            relative = f'ledger/episodes/{episode}.md'
            source = (self.root / relative).read_bytes()
            exact.append(source.decode('utf-8'))
            self.assertEqual(record['episode_id'], episode)
            self.assertEqual(record['path'], relative)
            self.assertEqual(record['content'].encode('utf-8'), source)
            self.assertEqual(record['sha256'], self.digest(source))
            self.assertEqual(record['byte_length'], len(source))
            self.assertEqual(record['local_approval']['status'], 'UNVERIFIED')
        assembly = result['assembly']
        value = '\n\n'.join(exact).encode('utf-8')
        self.assertEqual(assembly['method'], 'EXACT_RECAP_CONCATENATION')
        self.assertEqual(assembly['separator'], '\n\n')
        self.assertEqual(assembly['content'].encode('utf-8'), value)
        self.assertEqual(assembly['sha256'], self.digest(value))
        self.assertEqual(assembly['byte_length'], len(value))
        self.assertIn('\r\n', assembly['content'])
        self.assertFalse(result['sources'][1]['content'].endswith('\n'))

    def test_inputs_manifest_hashes_actual_fixed_and_source_bytes(self):
        result = rollup.build(self.root, ['EP-002', 'EP-003'])
        inputs = {record['path']: record for record in result['inputs']}
        for relative in ('story.json', 'data/episodes.json', 'data/scenes.json',
                         'data/story_state.json', 'ledger/index.json', 'bible/STYLE_GUIDE.md',
                         'ledger/episodes/EP-002.md', 'ledger/episodes/EP-003.md', 'drafts/SC-001.md'):
            self.assertIn(relative, inputs)
            value = (self.root / relative).read_bytes()
            self.assertEqual(inputs[relative]['sha256'], self.digest(value))
            self.assertEqual(inputs[relative]['byte_length'], len(value))

    def test_offline_repeatability_no_git_network_or_writes(self):
        before = self.snapshot(self.workspace)
        with patch('scripts.rollup.review_bundle._git', side_effect=AssertionError('offline used Git')), \
                patch('scripts.rollup.provenance.verify', side_effect=AssertionError('offline verified remotely')), \
                patch('pathlib.Path.write_text', side_effect=AssertionError('rollup wrote text')), \
                patch('pathlib.Path.write_bytes', side_effect=AssertionError('rollup wrote bytes')), \
                patch('pathlib.Path.mkdir', side_effect=AssertionError('rollup created a directory')), \
                patch('pathlib.Path.unlink', side_effect=AssertionError('rollup removed a file')), \
                patch('pathlib.Path.rename', side_effect=AssertionError('rollup renamed a file')), \
                patch('urllib.request.urlopen') as opener, patch('socket.create_connection') as connection:
            first = rollup.build(self.root, ['EP-001', 'EP-002'])
            second = rollup.build(self.root, ['EP-001', 'EP-002'])
        self.assertEqual(first, second)
        self.assertEqual(before, self.snapshot(self.workspace))
        opener.assert_not_called()
        connection.assert_not_called()

    def test_episode_selection_requires_nonempty_unique_contiguous_series_order(self):
        for episodes in ([], 'EP-001', [None], [''], ['EP-001', 'EP-001'],
                         ['EP-002', 'EP-001'], ['EP-001', 'EP-003'], ['EP-MISSING']):
            with self.subTest(episodes=episodes):
                with self.assertRaises(ValueError):
                    rollup.build(self.root, episodes)

    def test_missing_recap_or_source_evidence_is_rejected(self):
        for relative in ('ledger/episodes/EP-001.md', 'drafts/SC-001.md'):
            with self.subTest(source=relative):
                path = self.root / relative
                original = path.read_bytes()
                path.unlink()
                with self.assertRaises(ValueError):
                    rollup.build(self.root, ['EP-001'])
                path.write_bytes(original)

    def test_unapproved_episode_or_scene_cannot_be_included(self):
        for kind, field, status in (('episodes', 'episodes', 'OUTLINE'), ('scenes', 'scenes', 'PLANNED')):
            with self.subTest(kind=kind):
                path = self.root / 'data' / f'{kind}.json'
                original = self.read(path)
                value = copy.deepcopy(original)
                value[field][0]['status'] = status
                self.write(path, value)
                with self.assertRaises(ValueError):
                    rollup.build(self.root, ['EP-001'])
                self.write(path, original)

    def test_missing_ledger_record_or_unknown_registry_reference_is_rejected(self):
        index_path = self.root / 'ledger/index.json'
        index = self.read(index_path)
        self.write(index_path, {**index, 'episodes': []})
        with self.assertRaises(ValueError):
            rollup.build(self.root, ['EP-001'])
        self.write(index_path, index)
        scenes_path = self.root / 'data/scenes.json'
        scenes = self.read(scenes_path)
        scenes['scenes'][0]['location_id'] = 'LOC-MISSING'
        self.write(scenes_path, scenes)
        with self.assertRaises(ValueError):
            rollup.build(self.root, ['EP-001'])

    def test_cross_story_recap_path_cannot_be_read(self):
        path = self.root / 'ledger/index.json'
        index = self.read(path)
        index['episodes'][0]['summary_path'] = '../beta/ledger/episodes/EP-001.md'
        self.write(path, index)
        with self.assertRaises(ValueError):
            rollup.build(self.root, ['EP-001'])

    def test_legacy_direct_root_remains_supported_offline(self):
        (self.root / 'story.json').unlink()
        result = rollup.build(self.root, ['EP-001'])
        self.assertEqual(result['story']['slug'], 'legacy')
        self.assertEqual(result['source_verification'], 'OFFLINE_UNVERIFIED')

    def test_self_claimed_verified_fields_never_establish_approval(self):
        index = self.add_provenance()
        record = index['episodes'][0]
        record['approval'].update(status='VERIFIED', authenticated_human=True)
        record['provenance'].update(verified=True, human_editorial_approval='VERIFIED',
                                    verification_status='OBSERVED_MERGED_METADATA')
        self.write(self.root / 'ledger/index.json', index)
        result = rollup.build(self.root, ['EP-001'])
        source = result['sources'][0]
        self.assertEqual(result['source_verification'], 'OFFLINE_UNVERIFIED')
        self.assertEqual(result['human_editorial_approval'], 'UNVERIFIED')
        self.assertEqual(source['local_approval']['status'], 'UNVERIFIED')
        self.assertEqual(set(source['local_approval']['declared_metadata']),
                         {'pr_number', 'approved_by', 'merge_commit', 'approved_at'})
        self.assertEqual(set(source['declared_provenance']),
                         {'repository', 'pr_number', 'head_commit', 'merge_commit', 'source_path', 'source_sha256'})

    def test_optional_provenance_requires_full_valid_schema_shape(self):
        original = self.add_provenance()
        for change in ('missing', 'invalid_hash', 'invalid_pr'):
            with self.subTest(change=change):
                index = copy.deepcopy(original)
                record = index['episodes'][0]['provenance']
                if change == 'missing':
                    del record['head_commit']
                elif change == 'invalid_hash':
                    record['source_sha256'] = 'not-a-digest'
                else:
                    record['pr_number'] = True
                errors = registry_schema.validate('ledger', index)
                self.assertTrue(any('provenance' in error for error in errors), errors)

    def test_online_observed_metadata_never_promotes_editorial_approval(self):
        index = self.add_provenance()
        result, checker = self.online()
        self.assertEqual(checker.call_count, 2)
        for call, record in zip(checker.call_args_list, index['episodes']):
            declaration = record['provenance']
            self.assertEqual(call.args, tuple(declaration[field] for field in (
                'repository', 'pr_number', 'head_commit', 'merge_commit', 'source_path', 'source_sha256')))
        self.assertEqual(result['source_verification'], 'OBSERVED_MERGED_METADATA')
        self.assertEqual(result['status'], 'PROPOSED')
        self.assertEqual(result['approval_basis'], APPROVAL_BASIS)
        self.assertEqual(result['human_editorial_approval'], 'UNVERIFIED')
        self.assertTrue(all(source['verification']['status'] == 'OBSERVED_MERGED_METADATA'
                            for source in result['sources']))

    def test_real_verifier_binds_mocked_rest_and_git_evidence_into_rollup(self):
        """Mock transport objects, not verifier reports; no actual GitHub approval."""
        declaration = self.add_provenance()['episodes'][0]['provenance']
        value = (self.workspace / declaration['source_path']).read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(value)).encode('ascii') + b'\0' + value).hexdigest()
        parts = declaration['source_path'].split('/')
        trees = [hashlib.sha1(f'synthetic-tree-{number}'.encode('ascii')).hexdigest()
                 for number in range(len(parts))]
        prefix = f'repos/{REPOSITORY}/'
        responses = {
            prefix + 'pulls/1': {
                'number': 1, 'merged': True, 'state': 'closed', 'merged_at': '2026-10-22T13:00:00Z',
                'base': {'repo': {'full_name': REPOSITORY}}, 'head': {'sha': declaration['head_commit']},
                'merge_commit_sha': declaration['merge_commit'],
            },
            prefix + 'git/commits/' + declaration['merge_commit']: {
                'sha': declaration['merge_commit'], 'tree': {'sha': trees[0]},
            },
            prefix + 'git/blobs/' + blob: {
                'sha': blob, 'size': len(value), 'encoding': 'base64',
                'content': base64.b64encode(value).decode('ascii'),
            },
        }
        for number, name in enumerate(parts):
            leaf = number == len(parts) - 1
            entry = {'path': name, 'mode': '100644' if leaf else '040000',
                     'type': 'blob' if leaf else 'tree', 'sha': blob if leaf else trees[number + 1]}
            if leaf:
                entry['size'] = len(value)
            responses[prefix + 'git/trees/' + trees[number]] = {
                'sha': trees[number], 'truncated': False, 'tree': [entry],
            }

        def read(endpoint):
            self.assertIn(endpoint, responses)
            return copy.deepcopy(responses[endpoint])

        with patch('scripts.rollup.review_bundle._git', side_effect=self.git_root), \
                patch('scripts.rollup.provenance._gh_get', side_effect=read) as transport, \
                patch('scripts.rollup.provenance.subprocess.Popen') as process, \
                patch('urllib.request.urlopen') as opener, patch('socket.create_connection') as connection:
            result = rollup.build(self.root, ['EP-001'], repository=REPOSITORY, verify_remote=True)
            proof = result['sources'][0]['verification']['observed']['source']
            self.assertEqual(proof['status'], 'MATCHED_IMMUTABLE_BLOB')
            self.assertEqual(proof['at_commit'], declaration['merge_commit'])
            self.assertEqual(proof['blob_sha'], blob)
            self.assertEqual(proof['sha256'], self.digest(value))
            self.assertEqual(result['assembly']['content'].encode('utf-8'), value)
            self.assertEqual(result['human_editorial_approval'], 'UNVERIFIED')
            self.assertEqual(transport.call_count, len(parts) + 4)
            # Preserve the declared tree/blob identity while replacing its bytes.
            # The real verifier must detect this before rollup accepts a report.
            tampered = b'X' + value[1:]
            responses[prefix + 'git/blobs/' + blob]['content'] = base64.b64encode(tampered).decode('ascii')
            with self.assertRaises(ValueError):
                rollup.build(self.root, ['EP-001'], repository=REPOSITORY, verify_remote=True)
        process.assert_not_called()
        opener.assert_not_called()
        connection.assert_not_called()

    def test_online_requires_declared_provenance_and_explicit_repository(self):
        with patch('scripts.rollup.review_bundle._git', side_effect=self.git_root), \
                patch('scripts.rollup.provenance.verify') as checker:
            with self.assertRaises(ValueError):
                rollup.build(self.root, ['EP-001'], repository=REPOSITORY, verify_remote=True)
            with self.assertRaises(ValueError):
                rollup.build(self.root, ['EP-001'], verify_remote=True)
        checker.assert_not_called()

    def test_declared_current_recap_digest_mismatch_is_rejected_even_offline(self):
        index = self.add_provenance()
        index['episodes'][0]['provenance']['source_sha256'] = '0' * 64
        self.write(self.root / 'ledger/index.json', index)
        with patch('scripts.rollup.provenance.verify') as checker:
            with self.assertRaises(ValueError):
                rollup.build(self.root, ['EP-001'])
        checker.assert_not_called()

    def test_declared_source_paths_must_be_canonical_even_offline(self):
        original = self.add_provenance()
        for value in ('../beta/ledger/episodes/EP-001.md', '/absolute/recap.md',
                      'stories\\alpha\\recap.md', 'stories/./alpha/recap.md',
                      'stories/alpha/recap\n.md'):
            with self.subTest(source_path=value):
                index = copy.deepcopy(original)
                index['episodes'][0]['provenance']['source_path'] = value
                self.write(self.root / 'ledger/index.json', index)
                with self.assertRaises(ValueError):
                    rollup.build(self.root, ['EP-001'])

    def test_provenance_cannot_contradict_local_approval_identity_even_offline(self):
        original = self.add_provenance()
        for field, value in (('pr_number', 99), ('merge_commit', 'c' * 40)):
            with self.subTest(field=field):
                index = copy.deepcopy(original)
                index['episodes'][0]['provenance'][field] = value
                self.write(self.root / 'ledger/index.json', index)
                with patch('scripts.rollup.provenance.verify') as checker:
                    with self.assertRaises(ValueError):
                        rollup.build(self.root, ['EP-001'])
                checker.assert_not_called()

    def test_sha_declarations_are_case_insensitive_without_becoming_verified(self):
        index = self.add_provenance()
        for record in index['episodes']:
            for field in ('head_commit', 'merge_commit', 'source_sha256'):
                record['provenance'][field] = record['provenance'][field].upper()
        self.write(self.root / 'ledger/index.json', index)
        result = rollup.build(self.root, ['EP-001'])
        self.assertEqual(result['source_verification'], 'OFFLINE_UNVERIFIED')
        self.assertEqual(result['human_editorial_approval'], 'UNVERIFIED')

    def test_online_binds_repository_path_and_current_recap_digest(self):
        original = self.add_provenance()
        for field, value in (
                ('repository', 'different-owner/different-repository'),
                ('source_path', 'stories/beta/ledger/episodes/EP-001.md'),
                ('source_sha256', '0' * 64)):
            with self.subTest(field=field):
                index = copy.deepcopy(original)
                index['episodes'][0]['provenance'][field] = value
                self.write(self.root / 'ledger/index.json', index)
                with patch('scripts.rollup.review_bundle._git', side_effect=self.git_root), \
                        patch('scripts.rollup.provenance.verify') as checker:
                    with self.assertRaises(ValueError):
                        rollup.build(self.root, ['EP-001'], repository=REPOSITORY, verify_remote=True)
                checker.assert_not_called()

    def test_online_rejects_missing_git_or_nonobserved_verification(self):
        self.add_provenance()
        with patch('scripts.rollup.review_bundle._git', side_effect=ValueError('No local Git repository')), \
                patch('scripts.rollup.provenance.verify') as checker:
            with self.assertRaises(ValueError):
                rollup.build(self.root, ['EP-001'], repository=REPOSITORY, verify_remote=True)
        checker.assert_not_called()
        for response in ({'status': 'UNKNOWN', 'errors': []},
                         {'status': 'OBSERVED_MERGED_METADATA', 'errors': ['Source does not match merged blob']}):
            with self.subTest(response=response):
                with self.assertRaises(ValueError):
                    self.online(['EP-001'], response=response)

    def test_online_rejects_unbound_or_incomplete_success_report(self):
        self.add_provenance()
        mutations = (
            lambda report: report['requested'].update(repository='different-owner/different-repository'),
            lambda report: report['observed']['pull_request'].update(head_commit='c' * 40),
            lambda report: report['observed'].pop('source'),
            lambda report: report['observed']['source'].update(path='stories/beta/ledger/episodes/EP-001.md'),
            lambda report: report['observed']['source'].update(sha256='0' * 64),
            lambda report: report['observed']['source'].update(blob_sha='0' * 40),
            lambda report: report.update(status='OFFLINE_UNVERIFIED'),
        )
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                def invalid(*args, **kwargs):
                    report = self.observation(*args, **kwargs)
                    mutate(report)
                    return report

                with self.assertRaises(ValueError):
                    self.online(['EP-001'], verify=invalid)

    def test_recap_or_fixed_registry_change_during_validation_is_rejected(self):
        original_validate = story_engine.validate
        for relative in ('ledger/episodes/EP-001.md', 'data/story_state.json'):
            with self.subTest(path=relative):
                path = self.root / relative
                original = path.read_bytes()

                def changed(root):
                    result = original_validate(root)
                    path.write_bytes(original + b'\n')
                    return result

                with patch('scripts.rollup.story_engine.validate', side_effect=changed):
                    with self.assertRaisesRegex(ValueError, 'chang|stable'):
                        rollup.build(self.root, ['EP-001'])
                path.write_bytes(original)

    def test_source_change_during_remote_verification_is_rejected(self):
        self.add_provenance()
        recap = self.root / 'ledger/episodes/EP-001.md'

        def changed(*args, **kwargs):
            report = self.observation(*args, **kwargs)
            recap.write_bytes(recap.read_bytes() + b'\n')
            return report

        with self.assertRaisesRegex(ValueError, 'chang|stable'):
            self.online(['EP-001'], verify=changed)

    def test_new_optional_history_cannot_enter_after_snapshot(self):
        original_validate = story_engine.validate

        def changed(root):
            result = original_validate(root)
            self.write(self.root / 'data/state_history.json', {
                'schema_version': 1, 'baseline': None, 'deltas': [],
            })
            return result

        with patch('scripts.rollup.story_engine.validate', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'chang|stable'):
                rollup.build(self.root, ['EP-001'])

    def test_recap_size_and_utf8_boundaries_fail_without_truncation(self):
        recap = self.root / 'ledger/episodes/EP-001.md'
        for value in (b'M' * (1024 * 1024 + 1), b'Invalid UTF-8 fixture: \xff'):
            with self.subTest(size=len(value)):
                recap.write_bytes(value)
                with self.assertRaises(ValueError):
                    rollup.build(self.root, ['EP-001'])


if __name__ == '__main__':
    unittest.main()
