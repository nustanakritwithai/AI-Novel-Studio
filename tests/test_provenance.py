"""Synthetic GitHub metadata fixtures; never real approval or live network."""
import base64
import copy
import hashlib
import io
import json
import subprocess
import unittest
from unittest import mock

from scripts import provenance

REPOSITORY = 'fixture-owner/fixture-repo'
PR_NUMBER = 7
HEAD_COMMIT = 'a' * 40
MERGE_COMMIT = 'b' * 40
SOURCE_PATH = 'stories/alpha/drafts/SC-001.md'
SOURCE_BYTES = b'# Synthetic source metadata fixture; no narrative or real approval\n'


def make_evidence(source=SOURCE_BYTES, path=SOURCE_PATH):
    """Return offline-only PR snapshots and a SHA-keyed tree/blob fixture."""
    parts = path.split('/')
    tree_ids = [hashlib.sha1(f'synthetic-tree-{index}'.encode()).hexdigest()
                for index in range(len(parts))]
    blob_sha = hashlib.sha1(b'blob ' + str(len(source)).encode() + b'\x00' + source).hexdigest()
    trees = {}
    for index, name in enumerate(parts):
        leaf = index == len(parts) - 1
        entry = {'path': name, 'mode': '100644' if leaf else '040000',
                 'type': 'blob' if leaf else 'tree',
                 'sha': blob_sha if leaf else tree_ids[index + 1]}
        if leaf:
            entry['size'] = len(source)
        trees[tree_ids[index]] = {'sha': tree_ids[index], 'truncated': False, 'tree': [entry]}
    pr = {'number': PR_NUMBER, 'base': {'repo': {'full_name': REPOSITORY}},
          'head': {'sha': HEAD_COMMIT}, 'merge_commit_sha': MERGE_COMMIT,
          'merged': True, 'state': 'closed', 'merged_at': '2026-01-01T00:00:00Z'}
    return {'pull_request': pr, 'pull_request_after': copy.deepcopy(pr),
            'merge_commit': {'sha': MERGE_COMMIT, 'tree': {'sha': tree_ids[0]}},
            'trees': trees,
            'blobs': {blob_sha: {'sha': blob_sha, 'size': len(source), 'encoding': 'base64',
                                 'content': base64.encodebytes(source).decode('ascii')}}}


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.evidence = make_evidence()
        self.digest = hashlib.sha256(SOURCE_BYTES).hexdigest()
        self.pr_reads = 0
        self.reader = mock.patch.object(provenance, '_gh_get', side_effect=self.read_api)
        self.api = self.reader.start()
        self.addCleanup(self.reader.stop)

    def read_api(self, endpoint):
        prefix = 'repos/' + REPOSITORY + '/'
        self.assertTrue(endpoint.startswith(prefix), endpoint)
        relative = endpoint[len(prefix):]
        if relative == 'pulls/' + str(PR_NUMBER):
            self.pr_reads += 1
            key = 'pull_request' if self.pr_reads == 1 else 'pull_request_after'
            return copy.deepcopy(self.evidence[key])
        group, identifier = relative.rsplit('/', 1)
        if group == 'git/commits':
            self.assertEqual(identifier, MERGE_COMMIT)
            return copy.deepcopy(self.evidence['merge_commit'])
        mapping = self.evidence['trees' if group == 'git/trees' else 'blobs']
        return copy.deepcopy(mapping[identifier])

    def verify(self, **overrides):
        values = {'repository': REPOSITORY, 'pr_number': PR_NUMBER,
                  'head_commit': HEAD_COMMIT, 'merge_commit': MERGE_COMMIT,
                  'source_path': SOURCE_PATH, 'source_sha256': self.digest}
        values.update(overrides)
        return provenance.verify(**values)

    def assert_unverified(self, report, offline=False):
        self.assertEqual(report['status'], 'OFFLINE_UNVERIFIED' if offline else 'UNVERIFIED')
        self.assertTrue(report['errors'], report)
        self.assertEqual(report['human_editorial_approval'], 'UNVERIFIED')
        self.assertEqual(report['observed'], {})

    def test_live_metadata_and_immutable_source_binding(self):
        report = self.verify()
        self.assertEqual(report['status'], 'OBSERVED_MERGED_METADATA')
        self.assertEqual(report['errors'], [])
        self.assertEqual(report['human_editorial_approval'], 'UNVERIFIED')
        self.assertTrue(report['transport']['network_attempted'])
        self.assertEqual(report['transport']['requests_attempted'], len(SOURCE_PATH.split('/')) + 4)
        source = report['observed']['source']
        self.assertEqual(source['status'], 'MATCHED_IMMUTABLE_BLOB')
        self.assertEqual(source['path'], SOURCE_PATH)
        self.assertEqual(source['at_commit'], MERGE_COMMIT)
        self.assertEqual(source['sha256'], self.digest)
        self.assertTrue(source['matches_requested_sha256'])
        self.assertEqual(source['relationship'], 'PRESENT_AT_MERGE_NOT_PROOF_OF_PR_CHANGE_OR_EDITORIAL_REVIEW')
        self.assertEqual(report['observed']['pull_request']['head_commit'], HEAD_COMMIT)
        self.assertEqual(report['observed']['merge_commit']['sha'], MERGE_COMMIT)

    def test_metadata_only_success_is_not_source_hash_proof(self):
        report = self.verify(source_path=None, source_sha256=None)
        self.assertEqual(report['status'], 'OBSERVED_MERGED_METADATA')
        self.assertNotIn('source', report['observed'])
        self.assertEqual(report['transport']['requests_attempted'], 3)

    def test_offline_consistency_never_becomes_live_or_human_approval(self):
        self.evidence.update(status='OBSERVED_MERGED_METADATA', verified=True,
                             authenticated=True, transport={'mode': 'LIVE_GH_API', 'network_attempted': True})
        report = self.verify(offline_evidence=self.evidence)
        self.assertEqual(report['status'], 'OFFLINE_UNVERIFIED')
        self.assertEqual(report['metadata_consistency'], 'CONSISTENT')
        self.assertEqual(report['errors'], [])
        self.assertFalse(report['transport']['network_attempted'])
        self.assertEqual(report['transport']['requests_attempted'], 0)
        self.assertEqual(report['human_editorial_approval'], 'UNVERIFIED')
        self.api.assert_not_called()

    def test_offline_missing_or_invalid_evidence_never_falls_back_to_network(self):
        for evidence in ({}, {'status': 'OBSERVED_MERGED_METADATA'}, 'not an object'):
            with self.subTest(evidence=evidence):
                self.assert_unverified(self.verify(offline_evidence=evidence), offline=True)
        self.api.assert_not_called()

    def test_invalid_inputs_fail_before_any_network(self):
        cases = [
            {'repository': 'https://TOKEN@github.com/owner/repo'},
            {'repository': '../repo'}, {'repository': 'owner/repo/extra'},
            {'pr_number': True}, {'pr_number': 0}, {'pr_number': '7'},
            {'head_commit': 'HEAD'}, {'merge_commit': 'b' * 39},
            {'source_path': None}, {'source_sha256': None},
            {'source_sha256': 'x' * 64}, {'source_path': '../private.md'},
            {'source_path': '/absolute.md'}, {'source_path': 'a\\b.md'},
            {'source_path': 'a/./b.md'}, {'source_path': 'a//' + 'b'},
            {'source_path': '/'.join(['a'] * 33)},
        ]
        for values in cases:
            with self.subTest(values=values):
                report = self.verify(**values)
                self.assert_unverified(report)
                self.assertFalse(report['transport']['network_attempted'])
                self.assertNotIn('TOKEN', json.dumps(report))
        self.api.assert_not_called()

    def test_wrong_repository_number_head_merge_and_unmerged_are_rejected(self):
        cases = [('repo', 'other/repo'), ('number', PR_NUMBER + 1),
                 ('head', 'c' * 40), ('merge', 'd' * 40), ('merged', False)]
        for field, value in cases:
            with self.subTest(field=field):
                self.evidence = make_evidence()
                pr = self.evidence['pull_request']
                if field == 'repo':
                    pr['base']['repo']['full_name'] = value
                elif field == 'head':
                    pr['head']['sha'] = value
                elif field == 'merge':
                    pr['merge_commit_sha'] = value
                else:
                    pr[field] = value
                self.pr_reads = 0
                self.assert_unverified(self.verify())

    def test_merged_true_with_null_merge_sha_is_rejected(self):
        self.evidence['pull_request']['merge_commit_sha'] = None
        report = self.verify()
        self.assert_unverified(report)
        self.assertTrue(any('merge commit' in error for error in report['errors']))

    def test_stale_second_snapshot_fails_closed(self):
        for field in ('head', 'merge', 'repo', 'merged', 'merged_at'):
            with self.subTest(field=field):
                self.evidence = make_evidence()
                after = self.evidence['pull_request_after']
                if field == 'head':
                    after['head']['sha'] = 'e' * 40
                elif field == 'merge':
                    after['merge_commit_sha'] = 'f' * 40
                elif field == 'repo':
                    after['base']['repo']['full_name'] = 'other/repo'
                elif field == 'merged':
                    after['merged'] = False
                else:
                    after['merged_at'] = '2026-01-02T00:00:00Z'
                self.pr_reads = 0
                report = self.verify()
                self.assert_unverified(report)
                self.assertTrue(any('changed between observations' in error for error in report['errors']))

    def test_review_states_and_user_account_labels_are_not_human_proof(self):
        for pr in ('pull_request', 'pull_request_after'):
            self.evidence[pr].update(merged_by={'login': 'SECRET_ACCOUNT', 'type': 'User'},
                                     reviews=[{'state': 'APPROVED', 'user': {'type': 'User'}}],
                                     body='SECRET_PR_BODY')
        self.evidence['merge_commit']['verification'] = {'verified': True, 'signature': 'SECRET_SIGNATURE'}
        report = self.verify()
        self.assertEqual(report['status'], 'OBSERVED_MERGED_METADATA')
        self.assertEqual(report['human_editorial_approval'], 'UNVERIFIED')
        rendered = json.dumps(report)
        for secret in ('SECRET_ACCOUNT', 'SECRET_PR_BODY', 'SECRET_SIGNATURE', SOURCE_BYTES.decode()):
            self.assertNotIn(secret, rendered)

    def test_merge_git_object_identity_must_match(self):
        self.evidence['merge_commit']['sha'] = 'c' * 40
        self.assert_unverified(self.verify())

    def test_truncated_wrong_or_duplicate_tree_entries_are_rejected(self):
        root_sha = self.evidence['merge_commit']['tree']['sha']
        for mode in ('truncated', 'wrong_sha', 'duplicate', 'missing'):
            with self.subTest(mode=mode):
                self.evidence = make_evidence()
                tree = self.evidence['trees'][root_sha]
                if mode == 'truncated':
                    tree['truncated'] = True
                elif mode == 'wrong_sha':
                    tree['sha'] = 'e' * 40
                elif mode == 'duplicate':
                    tree['tree'].append(copy.deepcopy(tree['tree'][0]))
                else:
                    tree['tree'] = []
                self.pr_reads = 0
                self.assert_unverified(self.verify())

    def test_parent_or_leaf_symlink_and_submodule_modes_are_rejected(self):
        for leaf in (False, True):
            for mode, kind in (('120000', 'blob'), ('160000', 'commit')):
                with self.subTest(leaf=leaf, mode=mode):
                    self.evidence = make_evidence()
                    tree = list(self.evidence['trees'].values())[-1 if leaf else 0]
                    tree['tree'][0].update(mode=mode, type=kind)
                    self.pr_reads = 0
                    self.assert_unverified(self.verify())

    def test_expected_source_hash_and_blob_content_identity_must_both_match(self):
        self.assert_unverified(self.verify(source_sha256='0' * 64))
        self.pr_reads = 0
        blob = next(iter(self.evidence['blobs'].values()))
        tampered = b'X' + SOURCE_BYTES[1:]
        blob['content'] = base64.b64encode(tampered).decode()
        report = self.verify(source_sha256=hashlib.sha256(tampered).hexdigest())
        self.assert_unverified(report)
        self.assertTrue(any('Git blob SHA' in error for error in report['errors']))

    def test_invalid_base64_encoding_size_and_oversize_are_rejected(self):
        for mode in ('base64', 'encoding', 'size', 'oversize'):
            with self.subTest(mode=mode):
                self.evidence = make_evidence()
                blob = next(iter(self.evidence['blobs'].values()))
                if mode == 'base64':
                    blob['content'] = '!!!!'
                elif mode == 'encoding':
                    blob['encoding'] = 'utf-8'
                elif mode == 'size':
                    blob['size'] = True
                else:
                    leaf = list(self.evidence['trees'].values())[-1]['tree'][0]
                    leaf['size'] = provenance.MAX_SOURCE_BYTES + 1
                self.pr_reads = 0
                self.assert_unverified(self.verify())

    def test_transport_failure_and_unavailable_cli_return_redacted_error(self):
        for attempted in (True, False):
            with self.subTest(attempted=attempted):
                self.api.side_effect = provenance._TransportError('GitHub API read failed', attempted)
                report = self.verify()
                self.assertEqual(report['status'], 'ERROR')
                self.assertEqual(report['transport']['network_attempted'], attempted)
                self.assertEqual(report['observed'], {})
                self.assertEqual(report['human_editorial_approval'], 'UNVERIFIED')


class _Process:
    def __init__(self, output, returncode=0, timeout=False):
        self.stdout = io.BytesIO(output)
        self.returncode = returncode
        self.timeout = timeout
        self.killed = False

    def poll(self):
        return None if self.timeout else self.returncode

    def kill(self):
        self.killed = True
        self.timeout = False

    def wait(self, timeout=None):
        if self.timeout:
            raise subprocess.TimeoutExpired('SECRET_COMMAND', timeout)
        return self.returncode


class ProvenanceTransportTests(unittest.TestCase):
    def test_transport_is_fixed_get_host_version_and_discards_stderr(self):
        process = _Process(b'{"number":7}')
        with mock.patch.object(provenance.subprocess, 'Popen', return_value=process) as spawn:
            value = provenance._gh_get('repos/fixture-owner/fixture-repo/pulls/7')
        self.assertEqual(value, {'number': 7})
        command = spawn.call_args.args[0]
        self.assertEqual(command[:6], ['gh', 'api', '--hostname', 'github.com', '--method', 'GET'])
        self.assertIn('X-GitHub-Api-Version: 2022-11-28', command)
        self.assertEqual(spawn.call_args.kwargs['stderr'], subprocess.DEVNULL)
        self.assertEqual(spawn.call_args.kwargs['stdin'], subprocess.DEVNULL)
        self.assertEqual(spawn.call_args.kwargs['env']['GH_PROMPT_DISABLED'], '1')
        self.assertNotIn('--verbose', command)

    def test_arbitrary_urls_endpoints_queries_and_post_operations_are_rejected(self):
        with mock.patch.object(provenance.subprocess, 'Popen') as spawn:
            for endpoint in ('https://evil.invalid/secret', 'repos/a/b/issues/1',
                             'repos/a/b/pulls/1?token=SECRET', 'graphql', '--method=POST'):
                with self.subTest(endpoint=endpoint):
                    with self.assertRaises(provenance._TransportError):
                        provenance._gh_get(endpoint)
            spawn.assert_not_called()

    def test_raw_stderr_and_exception_strings_never_appear_in_errors(self):
        for failure in (OSError('SECRET_OS_ERROR'), FileNotFoundError('SECRET_PATH')):
            with mock.patch.object(provenance.subprocess, 'Popen', side_effect=failure):
                report = provenance.verify(REPOSITORY, PR_NUMBER, HEAD_COMMIT, MERGE_COMMIT)
            self.assertEqual(report['status'], 'ERROR')
            self.assertNotIn('SECRET', json.dumps(report))
            self.assertFalse(report['transport']['network_attempted'])
        with mock.patch.object(provenance.subprocess, 'Popen', return_value=_Process(b'SECRET_RESPONSE', 1)):
            report = provenance.verify(REPOSITORY, PR_NUMBER, HEAD_COMMIT, MERGE_COMMIT)
        self.assertEqual(report['status'], 'ERROR')
        self.assertNotIn('SECRET', json.dumps(report))

    def test_invalid_duplicate_nonfinite_and_oversized_json_fail_closed(self):
        payloads = (b'{"a":1,"a":2}', b'{"a":NaN}', b'\xff', b'SECRET_NON_JSON',
                    b' ' * (provenance.MAX_RESPONSE_BYTES + 1))
        for payload in payloads:
            with self.subTest(length=len(payload)):
                process = _Process(payload)
                with mock.patch.object(provenance.subprocess, 'Popen', return_value=process):
                    report = provenance.verify(REPOSITORY, PR_NUMBER, HEAD_COMMIT, MERGE_COMMIT)
                self.assertEqual(report['status'], 'ERROR')
                self.assertNotIn('SECRET', json.dumps(report))

    def test_process_timeout_is_redacted_and_stopped(self):
        process = _Process(b'{}', timeout=True)
        with mock.patch.object(provenance.subprocess, 'Popen', return_value=process):
            report = provenance.verify(REPOSITORY, PR_NUMBER, HEAD_COMMIT, MERGE_COMMIT)
        self.assertEqual(report['status'], 'ERROR')
        self.assertTrue(process.killed)
        self.assertNotIn('SECRET', json.dumps(report))


if __name__ == '__main__':
    unittest.main()
