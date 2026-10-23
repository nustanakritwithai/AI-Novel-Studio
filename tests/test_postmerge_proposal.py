"""Simulated postmerge metadata/permission boundaries, never a live trigger."""
import contextlib
import copy
import http.client
import io
import json
import os
from pathlib import Path
import socket
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/postmerge-proposal.yml'
REPOSITORY = 'fixture-owner/fixture-repository'
PREFIX = 'repos/' + REPOSITORY + '/'
RUN_ID = 41
WORKFLOW_ID = 23
PR_NUMBER = 7
HEAD = 'a' * 40
MERGE = 'b' * 40
BASE = 'c' * 40
TREE = 'd' * 40
WORKFLOW_SHA = 'e' * 40
UPLOAD_SHA = 'ea165f8d65b6e75b540449e92b4886f43607fa02'


def load_runtime():
    """Compile the exact canonical inline source; no workflow main is run."""
    workflow = json.loads(WORKFLOW.read_text(encoding='utf-8'))
    runs = [step['run'] for job in workflow['jobs'].values()
            for step in job['steps'] if 'run' in step]
    if len(runs) != 1:
        raise AssertionError('Expected one canonical isolated Python runtime')
    prefix = "python3 -I -S - <<'PY'\n"
    command = runs[0].rstrip('\n')
    if not command.startswith(prefix) or not command.endswith('\nPY'):
        raise AssertionError('Runtime must use the isolated stdlib-only heredoc')
    source = command[len(prefix):-3]
    module = types.ModuleType('postmerge_fixture')
    module.__file__ = str(WORKFLOW) + '::inline'
    exec(compile(source, module.__file__, 'exec'), module.__dict__)
    return workflow, source, module


def make_fixture():
    """GitHub-shaped synthetic responses; no identities or real approvals."""
    run = {
        'id': RUN_ID, 'run_attempt': 1, 'workflow_id': WORKFLOW_ID,
        'name': 'Novel continuity checks', 'path': '.github/workflows/continuity.yml',
        'repository': {'full_name': REPOSITORY}, 'head_repository': {'full_name': REPOSITORY},
        'event': 'push', 'head_branch': 'main', 'head_sha': MERGE,
        'status': 'completed', 'conclusion': 'success',
    }
    event = {'action': 'completed', 'repository': {'full_name': REPOSITORY, 'default_branch': 'main'},
             'workflow_run': copy.deepcopy(run)}
    pr = {
        'number': PR_NUMBER, 'merged': True, 'state': 'closed',
        'merged_at': '2026-01-01T00:00:00Z', 'merge_commit_sha': MERGE,
        'head': {'sha': HEAD, 'repo': {'full_name': REPOSITORY}},
        'base': {'sha': BASE, 'ref': 'main', 'repo': {'full_name': REPOSITORY}},
    }
    responses = {
        PREFIX + 'actions/workflows/continuity.yml': {
            'id': WORKFLOW_ID, 'path': '.github/workflows/continuity.yml',
            'state': 'active', 'name': 'Novel continuity checks'},
        PREFIX + 'actions/runs/' + str(RUN_ID): run,
        PREFIX + 'git/ref/heads/main': {'ref': 'refs/heads/main',
                                       'object': {'type': 'commit', 'sha': MERGE}},
        PREFIX + 'git/commits/' + MERGE: {'sha': MERGE, 'tree': {'sha': TREE},
                                        'parents': [{'sha': BASE}, {'sha': HEAD}]},
        PREFIX + 'commits/' + MERGE + '/pulls?per_page=100': [copy.deepcopy(pr)],
        PREFIX + 'pulls/' + str(PR_NUMBER): pr,
    }
    return event, responses


class PostmergeProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow, cls.source, cls.runtime = load_runtime()

    def setUp(self):
        self.event, self.responses = make_fixture()
        self.calls = []
        self.counts = {}
        self.after = {}
        self.network = self.enterContext(mock.patch('urllib.request.OpenerDirector.open',
            side_effect=AssertionError('Tests must never use real HTTP')))
        self.socket = self.enterContext(mock.patch('socket.create_connection',
            side_effect=AssertionError('Tests must never connect to a socket')))

    def get_json(self, endpoint):
        self.calls.append(endpoint)
        count = self.counts.get(endpoint, 0) + 1
        self.counts[endpoint] = count
        if count > 1 and endpoint in self.after:
            value = self.after[endpoint]
        else:
            if endpoint not in self.responses:
                raise AssertionError('Unexpected endpoint: ' + endpoint)
            value = self.responses[endpoint]
        if isinstance(value, BaseException):
            raise value
        return copy.deepcopy(value)

    def build(self, event=None, repository=REPOSITORY, workflow_sha=WORKFLOW_SHA):
        return self.runtime.build_proposal(self.event if event is None else event,
                                           repository, workflow_sha, self.get_json)

    def assert_rejected(self, event=None, **kwargs):
        with self.assertRaises((ValueError, RuntimeError, TypeError, KeyError)):
            self.build(event, **kwargs)

    def reset_fixture(self):
        self.event, self.responses = make_fixture()
        self.calls.clear()
        self.counts.clear()
        self.after.clear()

    def test_workflow_has_only_default_branch_trigger_read_permissions_and_fixed_upload(self):
        workflow = self.workflow
        self.assertEqual(set(workflow['on']), {'workflow_run'})
        self.assertEqual(workflow['on']['workflow_run'], {
            'workflows': ['Novel continuity checks'], 'branches': ['main'], 'types': ['completed']})
        self.assertEqual(workflow['permissions'], {
            'contents': 'read', 'pull-requests': 'read', 'actions': 'read'})
        self.assertEqual(len(workflow['jobs']), 1)
        job = next(iter(workflow['jobs'].values()))
        self.assertNotIn('permissions', job)
        self.assertEqual(len(job['steps']), 2)
        self.assertIn('success', job['if'])
        self.assertIn('push', job['if'])
        self.assertNotIn('secrets.', json.dumps(workflow))
        actions = [step for step in job['steps'] if 'uses' in step]
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['uses'], 'actions/upload-artifact@' + UPLOAD_SHA)
        upload = actions[0]['with']
        self.assertEqual(upload['if-no-files-found'], 'error')
        self.assertEqual(upload['retention-days'], 7)
        self.assertFalse(upload.get('overwrite', False))
        self.assertFalse(upload.get('include-hidden-files', False))
        self.assertEqual(upload['path'], '${{ runner.temp }}/postmerge-proposal/proposal.json')
        self.assertNotIn('${{', self.source)
        self.assertNotIn('subprocess', self.source)
        self.assertNotIn('os.system', self.source)

    def test_verified_simulated_metadata_produces_only_an_unapproved_proposal(self):
        report = self.build()
        self.assertEqual(report['status'], 'PROPOSED')
        self.assertEqual(report['human_editorial_approval'], 'UNVERIFIED')
        self.assertEqual(report['source'], {
            'repository': REPOSITORY, 'pr_number': PR_NUMBER,
            'head_commit': HEAD, 'merge_commit': MERGE, 'base_commit': BASE,
            'observed_pr_base_sha': BASE,
            'merge_tree': TREE, 'merged_at': '2026-01-01T00:00:00Z'})
        self.assertEqual(report['upstream_run']['id'], RUN_ID)
        self.assertEqual(report['upstream_run']['run_attempt'], 1)
        self.assertEqual(report['upstream_run']['workflow_id'], WORKFLOW_ID)
        self.assertEqual(report['upstream_run']['head_commit'], MERGE)
        self.assertEqual(report['upstream_run']['branch'], 'main')
        self.assertEqual(report['workflow_definition']['commit'], WORKFLOW_SHA)
        self.assertTrue(report['workflow_definition']['trust_basis'])
        self.assertRegex(report['event_sha256'], r'^[0-9a-f]{64}$')
        self.assertTrue(report['event_digest_basis'])
        for endpoint in ('actions/runs/' + str(RUN_ID), 'git/ref/heads/main', 'pulls/' + str(PR_NUMBER)):
            self.assertGreaterEqual(self.counts[PREFIX + endpoint], 2)
        self.network.assert_not_called()
        self.socket.assert_not_called()

    def test_untrusted_titles_bodies_accounts_and_injection_text_are_never_emitted(self):
        marker = 'SECRET_MARKER_$(touch /tmp/never);${{ secrets.DO_NOT_READ }}'
        self.event['untrusted_extra'] = marker
        for path in ('pulls/' + str(PR_NUMBER), 'commits/' + MERGE + '/pulls?per_page=100'):
            value = self.responses[PREFIX + path]
            rows = value if isinstance(value, list) else [value]
            for pr in rows:
                pr.update(title=marker, body=marker, user={'login': marker},
                          merged_by={'login': marker, 'type': 'User'},
                          reviews=[{'state': 'APPROVED', 'body': marker}])
        self.responses[PREFIX + 'git/commits/' + MERGE]['message'] = marker
        with mock.patch('subprocess.run') as run, mock.patch('os.system') as system:
            report = self.build()
        self.assertNotIn(marker, json.dumps(report))
        self.assertEqual(report['human_editorial_approval'], 'UNVERIFIED')
        run.assert_not_called()
        system.assert_not_called()

    def test_absent_and_invalid_event_structures_fail_before_network(self):
        for event in ({}, [], '', {'action': 'completed'}, None):
            with self.subTest(event=event):
                with self.assertRaises((ValueError, RuntimeError, TypeError, KeyError)):
                    self.runtime.build_proposal(event, REPOSITORY, WORKFLOW_SHA, self.get_json)
        self.assertEqual(self.calls, [])

    def test_invalid_expected_identity_and_workflow_sha_fail_before_network(self):
        for change in ({'repository': 'https://TOKEN@github.com/x/y'},
                       {'repository': 'owner/repo/extra'}, {'repository': '../repo'},
                       {'workflow_sha': 'HEAD'}, {'workflow_sha': 'f' * 39}):
            with self.subTest(change=change):
                self.assert_rejected(**change)
        self.assertEqual(self.calls, [])

    def test_wrong_event_repository_action_and_upstream_source_are_rejected(self):
        changes = [('action', 'requested'), ('repository', {'full_name': 'other/repo', 'default_branch': 'main'})]
        for field, value in changes:
            with self.subTest(field=field):
                self.reset_fixture()
                self.event[field] = value
                self.assert_rejected()
        for field, value in (
                ('event', 'pull_request'), ('head_branch', 'feature'), ('status', 'in_progress'),
                ('conclusion', 'failure'), ('repository', {'full_name': 'other/repo'}),
                ('head_repository', {'full_name': 'fork/repo'}), ('head_sha', 'HEAD'),
                ('id', True), ('run_attempt', 0), ('workflow_id', True)):
            with self.subTest(field=field):
                self.reset_fixture()
                self.event['workflow_run'][field] = value
                self.assert_rejected()

    def test_remote_run_must_match_event_identity_attempt_workflow_and_commit(self):
        for field, value in (
                ('id', RUN_ID + 1), ('run_attempt', 2), ('workflow_id', WORKFLOW_ID + 1),
                ('head_sha', 'f' * 40), ('head_branch', 'feature'), ('event', 'pull_request'),
                ('status', 'in_progress'), ('conclusion', 'failure'),
                ('repository', {'full_name': 'other/repo'}),
                ('head_repository', {'full_name': 'fork/repo'})):
            with self.subTest(field=field):
                self.reset_fixture()
                self.responses[PREFIX + 'actions/runs/' + str(RUN_ID)][field] = value
                self.assert_rejected()

    def test_remote_workflow_identity_path_name_and_active_state_are_required(self):
        for field, value in (('id', WORKFLOW_ID + 1), ('path', '.github/workflows/evil.yml'),
                             ('name', 'Another workflow'), ('state', 'disabled_manually')):
            with self.subTest(field=field):
                self.reset_fixture()
                self.responses[PREFIX + 'actions/workflows/continuity.yml'][field] = value
                self.assert_rejected()

    def test_current_main_must_be_the_event_merge_commit(self):
        for field, value in (('sha', 'f' * 40), ('type', 'tag')):
            with self.subTest(field=field):
                self.reset_fixture()
                self.responses[PREFIX + 'git/ref/heads/main']['object'][field] = value
                self.assert_rejected()
        self.reset_fixture()
        self.responses[PREFIX + 'git/ref/heads/main']['ref'] = 'refs/heads/feature'
        self.assert_rejected()

    def test_commit_tree_parent_and_merge_identity_cannot_be_forged(self):
        for change in ({'sha': 'f' * 40}, {'tree': {'sha': 'HEAD'}}, {'parents': []},
                       {'parents': [{'sha': 'f' * 40}]}, {'parents': [{'sha': 'not-a-sha'}]}):
            with self.subTest(change=change):
                self.reset_fixture()
                self.responses[PREFIX + 'git/commits/' + MERGE].update(change)
                self.assert_rejected()

    def test_impossible_duplicate_or_self_parent_is_rejected_even_with_matching_pr_metadata(self):
        for head in (BASE, MERGE):
            with self.subTest(head=head):
                self.reset_fixture()
                self.responses[PREFIX + 'git/commits/' + MERGE]['parents'] = [
                    {'sha': BASE}, {'sha': head}]
                self.responses[PREFIX + 'pulls/' + str(PR_NUMBER)]['head']['sha'] = head
                self.assert_rejected()

    def test_stale_observed_base_preserves_verified_merge_first_parent(self):
        self.responses[PREFIX + 'pulls/' + str(PR_NUMBER)]['base']['sha'] = 'f' * 40
        self.responses[PREFIX + 'commits/' + MERGE + '/pulls?per_page=100'][0]['base']['sha'] = 'f' * 40
        report = self.build()
        self.assertEqual(report['source']['base_commit'], BASE)
        self.assertEqual(report['source']['observed_pr_base_sha'], 'f' * 40)
        self.assertEqual(report['source']['head_commit'], HEAD)
        self.assertEqual(report['human_editorial_approval'], 'UNVERIFIED')
        self.assertFalse(report['canon_change_authorized'])
        self.assertFalse(report['ledger_apply_authorized'])

    def test_merge_second_parent_must_match_pr_head(self):
        self.responses[PREFIX + 'git/commits/' + MERGE]['parents'][1]['sha'] = '9' * 40
        self.assert_rejected()

    def test_single_parent_with_exact_observed_base_remains_supported(self):
        self.responses[PREFIX + 'git/commits/' + MERGE]['parents'] = [{'sha': BASE}]
        report = self.build()
        self.assertEqual(report['source']['base_commit'], BASE)
        self.assertEqual(report['source']['observed_pr_base_sha'], BASE)

    def test_single_parent_with_stale_observed_base_remains_rejected(self):
        self.responses[PREFIX + 'git/commits/' + MERGE]['parents'] = [{'sha': BASE}]
        self.responses[PREFIX + 'pulls/' + str(PR_NUMBER)]['base']['sha'] = 'f' * 40
        self.responses[PREFIX + 'commits/' + MERGE + '/pulls?per_page=100'][0]['base']['sha'] = 'f' * 40
        self.assert_rejected()

    def test_missing_ambiguous_or_truncated_associations_do_not_produce_a_proposal(self):
        key = PREFIX + 'commits/' + MERGE + '/pulls?per_page=100'
        for mode in ('empty', 'multiple', 'limit', 'wrong_merge', 'wrong_base', 'wrong_repo'):
            with self.subTest(mode=mode):
                self.reset_fixture()
                rows = self.responses[key]
                if mode == 'empty':
                    rows.clear()
                elif mode == 'multiple':
                    other = copy.deepcopy(rows[0])
                    other['number'] = PR_NUMBER + 1
                    rows.append(other)
                elif mode == 'limit':
                    rows[:] = [copy.deepcopy(rows[0]) for _ in range(100)]
                elif mode == 'wrong_merge':
                    rows[0]['merge_commit_sha'] = 'f' * 40
                elif mode == 'wrong_base':
                    rows[0]['base']['ref'] = 'feature'
                else:
                    rows[0]['base']['repo']['full_name'] = 'other/repo'
                self.assert_rejected()

    def test_direct_pr_requires_actual_closed_merge_and_matching_base(self):
        for field, value in (('merged', False), ('state', 'open'), ('merge_commit_sha', 'f' * 40),
                             ('merged_at', None), ('number', True)):
            with self.subTest(field=field):
                self.reset_fixture()
                self.responses[PREFIX + 'pulls/' + str(PR_NUMBER)][field] = value
                self.assert_rejected()
        for field, value in (('sha', 'not-a-sha'), ('ref', 'feature'), ('repo', {'full_name': 'other/repo'})):
            with self.subTest(base_field=field):
                self.reset_fixture()
                self.responses[PREFIX + 'pulls/' + str(PR_NUMBER)]['base'][field] = value
                self.assert_rejected()

    def test_late_rerun_head_and_branch_races_fail_closed(self):
        mutations = (
            ('actions/runs/' + str(RUN_ID), lambda value: value.update(run_attempt=2)),
            ('actions/workflows/continuity.yml', lambda value: value.update(id=WORKFLOW_ID + 1)),
            ('pulls/' + str(PR_NUMBER), lambda value: value['head'].update(sha='f' * 40)),
            ('pulls/' + str(PR_NUMBER), lambda value: value['base'].update(sha='9' * 40)),
            ('git/ref/heads/main', lambda value: value['object'].update(sha='f' * 40)),
            ('commits/' + MERGE + '/pulls?per_page=100', lambda value: value.clear()),
        )
        for relative, change in mutations:
            with self.subTest(endpoint=relative):
                self.reset_fixture()
                value = copy.deepcopy(self.responses[PREFIX + relative])
                change(value)
                self.after[PREFIX + relative] = value
                self.assert_rejected()

    def test_api_failure_does_not_return_a_partially_verified_proposal(self):
        for relative in ('actions/runs/' + str(RUN_ID), 'git/commits/' + MERGE,
                         'commits/' + MERGE + '/pulls?per_page=100', 'pulls/' + str(PR_NUMBER)):
            with self.subTest(endpoint=relative):
                self.reset_fixture()
                self.responses[PREFIX + relative] = ValueError('Synthetic unavailable metadata')
                self.assert_rejected()

    def main_environment(self, temporary):
        runner = Path(temporary).resolve()
        event_path = runner / 'event.json'
        event_path.write_text(json.dumps(self.event), encoding='utf-8')
        out = runner / 'postmerge-proposal/proposal.json'
        env = {
            'GITHUB_EVENT_NAME': 'workflow_run', 'GITHUB_EVENT_PATH': str(event_path),
            'GITHUB_REPOSITORY': REPOSITORY, 'EXPECTED_REPOSITORY': REPOSITORY,
            'GITHUB_WORKFLOW_SHA': WORKFLOW_SHA, 'EXPECTED_WORKFLOW_SHA': WORKFLOW_SHA,
            'GITHUB_WORKFLOW_REF': REPOSITORY + '/.github/workflows/postmerge-proposal.yml@refs/heads/main',
            'RUNNER_TEMP': str(runner), 'PROPOSAL_OUTPUT': str(out), 'GH_TOKEN': 'SECRET_TOKEN',
        }
        # Windows TLS initialization needs these OS paths; retain no user tokens.
        for key in ('SYSTEMROOT', 'WINDIR'):
            if key in os.environ:
                env[key] = os.environ[key]
        return env, out

    def call_main(self, env):
        stdout, stderr = io.StringIO(), io.StringIO()
        api = types.SimpleNamespace(get_json=self.get_json)
        actual_api = self.runtime.GitHubAPI

        def construct(token):
            actual_api(token)  # Validate the real token guard without opening HTTP.
            return api

        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(self.runtime, 'GitHubAPI', side_effect=construct) as factory, \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = self.runtime.main()
        return result, stdout.getvalue(), stderr.getvalue(), factory

    def test_simulated_main_writes_only_the_fixed_proposal_and_preserves_approval_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            env, out = self.main_environment(temporary)
            result, stdout, stderr, factory = self.call_main(env)
            self.assertEqual(result, 0, stdout + stderr)
            report = json.loads(out.read_text(encoding='utf-8'))
            self.assertEqual(report['status'], 'PROPOSED')
            self.assertEqual(report['human_editorial_approval'], 'UNVERIFIED')
            self.assertEqual(report['workflow_definition']['ref'], env['GITHUB_WORKFLOW_REF'])
            self.assertEqual(list(out.parent.iterdir()), [out])
            self.assertNotIn('SECRET_TOKEN', out.read_text(encoding='utf-8') + stdout + stderr)
            factory.assert_called_once()
        self.network.assert_not_called()
        self.socket.assert_not_called()

    def test_missing_token_wrong_event_and_untrusted_workflow_revision_fail_before_api(self):
        for field, value in (
                ('GH_TOKEN', ''), ('GITHUB_EVENT_NAME', 'pull_request_target'),
                ('GITHUB_WORKFLOW_SHA', 'f' * 40),
                ('GITHUB_WORKFLOW_REF', REPOSITORY + '/.github/workflows/postmerge-proposal.yml@refs/heads/feature')):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                self.reset_fixture()
                env, out = self.main_environment(temporary)
                env[field] = value
                result, stdout, stderr, factory = self.call_main(env)
                self.assertEqual(result, 1, stdout + stderr)
                self.assertFalse(out.exists())
                self.assertEqual(factory.call_count, 1 if field == 'GH_TOKEN' else 0)
                self.assertEqual(self.calls, [])
                self.assertNotIn('SECRET_TOKEN', stdout + stderr)

    def test_network_failure_and_malformed_payload_leave_no_artifact_or_raw_error(self):
        for mode in ('network', 'unexpected', 'incomplete_read', 'malformed'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                self.reset_fixture()
                env, out = self.main_environment(temporary)
                if mode == 'network':
                    self.responses[PREFIX + 'actions/workflows/continuity.yml'] = ValueError('SECRET_REMOTE_FAILURE')
                elif mode == 'unexpected':
                    self.responses[PREFIX + 'actions/workflows/continuity.yml'] = RuntimeError('SECRET_REMOTE_FAILURE')
                elif mode == 'incomplete_read':
                    self.responses[PREFIX + 'actions/workflows/continuity.yml'] = http.client.IncompleteRead(
                        b'SECRET_INCOMPLETE_RESPONSE')
                else:
                    Path(env['GITHUB_EVENT_PATH']).write_bytes(b'{"SECRET_EVENT": malformed')
                result, stdout, stderr, factory = self.call_main(env)
                self.assertEqual(result, 1, stdout + stderr)
                self.assertFalse(out.exists())
                self.assertFalse(out.parent.exists())
                for marker in ('SECRET_TOKEN', 'SECRET_EVENT', 'SECRET_REMOTE_FAILURE',
                               'SECRET_INCOMPLETE_RESPONSE', 'Traceback'):
                    self.assertNotIn(marker, stdout + stderr)

    def test_exclusive_open_race_cannot_delete_a_competing_file(self):
        report = self.build()
        original_open = Path.open
        competing_bytes = b'Competing owner: preserve these bytes.\n'
        with tempfile.TemporaryDirectory() as temporary:
            runner = Path(temporary).resolve()
            target = runner / 'postmerge-proposal/proposal.json'

            def competing_open(path, mode='r', *args, **kwargs):
                if path == target and mode == 'xb':
                    self.assertTrue(target.parent.is_dir())
                    with original_open(target, 'wb') as handle:
                        handle.write(competing_bytes)
                    raise FileExistsError('Synthetic competing output owner')
                return original_open(path, mode, *args, **kwargs)

            with mock.patch.object(Path, 'open', new=competing_open):
                with self.assertRaises(FileExistsError):
                    self.runtime.emit_proposal(report, target, runner)
            self.assertEqual(target.read_bytes(), competing_bytes)

    def test_output_cannot_overwrite_an_existing_file_or_escape_runner_temp(self):
        report = self.build()
        with tempfile.TemporaryDirectory() as temporary:
            runner = Path(temporary).resolve()
            valid = runner / 'postmerge-proposal/proposal.json'
            valid.parent.mkdir()
            valid.write_bytes(b'Existing artifact must remain byte-identical.\n')
            before = valid.read_bytes()
            for out in (valid, runner / 'elsewhere/proposal.json', runner / 'postmerge-proposal/wrong.json'):
                with self.subTest(out=str(out)):
                    with self.assertRaises((ValueError, RuntimeError, OSError)):
                        self.runtime.emit_proposal(report, out, runner)
            self.assertEqual(valid.read_bytes(), before)
            self.assertFalse((runner / 'elsewhere').exists())
            target = runner / 'real-directory'
            target.mkdir()
            valid.unlink()
            valid.parent.rmdir()
            valid.parent.symlink_to(target, target_is_directory=True)
            with self.assertRaises((ValueError, RuntimeError, OSError)):
                self.runtime.emit_proposal(report, valid, runner)
            self.assertEqual(list(target.iterdir()), [])


class _Response:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status
        self.requested_limit = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        self.requested_limit = limit
        return self.payload[:limit]


class PostmergeTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow, cls.source, cls.runtime = load_runtime()

    def setUp(self):
        self.enterContext(mock.patch('urllib.request.OpenerDirector.open',
            side_effect=AssertionError('Tests must never use real HTTP')))
        self.enterContext(mock.patch('socket.create_connection',
            side_effect=AssertionError('Tests must never connect to a socket')))

    def test_transport_uses_only_fixed_host_get_api_version_and_bounded_response(self):
        api = self.runtime.GitHubAPI('SECRET_TOKEN')
        response = _Response(b'{"id":41}')
        api.opener = mock.Mock()
        api.opener.open.return_value = response
        result = api.get_json(PREFIX + 'actions/runs/41')
        self.assertEqual(result, {'id': 41})
        request = api.opener.open.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.github.com/' + PREFIX + 'actions/runs/41')
        self.assertEqual(request.get_method(), 'GET')
        self.assertEqual(request.get_header('X-github-api-version'), '2022-11-28')
        self.assertEqual(request.get_header('Authorization'), 'Bearer SECRET_TOKEN')
        self.assertEqual(api.opener.open.call_args.kwargs['timeout'], 20)
        self.assertEqual(response.requested_limit, self.runtime.MAX_RESPONSE_BYTES + 1)

    def test_unavailable_or_injectable_token_cannot_create_a_transport(self):
        for token in (None, '', ' ', 'x\r\nSECRET_HEADER', 'x' * 4097):
            with self.subTest(token_length=None if token is None else len(token)):
                with self.assertRaises(ValueError):
                    self.runtime.GitHubAPI(token)

    def test_arbitrary_hosts_writes_urls_queries_and_source_downloads_are_rejected(self):
        api = self.runtime.GitHubAPI('SECRET_TOKEN')
        api.opener = mock.Mock()
        for endpoint in ('https://evil.invalid/SECRET', 'repos/x/y/contents/source.py',
                         PREFIX + 'pulls/7?token=SECRET', PREFIX + 'issues/7',
                         '--method=POST', 'graphql', PREFIX + 'git/commits/' + 'A' * 40):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(ValueError):
                    api.get_json(endpoint)
        api.opener.open.assert_not_called()

    def test_redirect_handler_never_follows_an_authentication_bearing_request(self):
        with self.assertRaises(ValueError):
            self.runtime.NoRedirect().redirect_request(None, None, 302, 'SECRET', {}, 'https://evil.invalid/')

    def test_http_status_network_and_raw_response_errors_are_redacted(self):
        failures = [OSError('SECRET_OS_FAILURE'), RuntimeError('SECRET_UNEXPECTED_FAILURE'),
                    http.client.IncompleteRead(b'SECRET_INCOMPLETE_RESPONSE'),
                    self.runtime.urllib.error.URLError('SECRET_NETWORK_FAILURE')]
        for error in failures:
            with self.subTest(error=type(error).__name__):
                api = self.runtime.GitHubAPI('SECRET_TOKEN')
                api.opener = mock.Mock()
                api.opener.open.side_effect = error
                with self.assertRaises(ValueError) as caught:
                    api.get_json(PREFIX + 'actions/runs/41')
                self.assertNotIn('SECRET', str(caught.exception))
        for payload, status in ((b'SECRET_UNAUTHORIZED', 401), (b'SECRET_RATE_LIMIT', 429),
                                (b'SECRET_NOT_JSON', 200), (b'{"id":NaN}', 200),
                                (b'{"id":1,"id":2}', 200), (b'\xff\xfe', 200)):
            with self.subTest(status=status, payload_length=len(payload)):
                api = self.runtime.GitHubAPI('SECRET_TOKEN')
                api.opener = mock.Mock()
                api.opener.open.return_value = _Response(payload, status)
                with self.assertRaises(ValueError) as caught:
                    api.get_json(PREFIX + 'actions/runs/41')
                self.assertNotIn('SECRET', str(caught.exception))

    def test_response_and_event_limits_reject_instead_of_silent_truncation(self):
        api = self.runtime.GitHubAPI('SECRET_TOKEN')
        response = _Response(b' ' * (self.runtime.MAX_RESPONSE_BYTES + 1))
        api.opener = mock.Mock()
        api.opener.open.return_value = response
        with self.assertRaises(ValueError):
            api.get_json(PREFIX + 'actions/runs/41')
        self.assertEqual(response.requested_limit, self.runtime.MAX_RESPONSE_BYTES + 1)
        for raw in (b' ' * (self.runtime.MAX_EVENT_BYTES + 1), b'{"a":NaN}', b'{"a":1e999}',
                    b'{"a":1,"a":2}', b'\xff', b'{ invalid }'):
            with self.subTest(length=len(raw)):
                with self.assertRaises(ValueError):
                    self.runtime.parse_json(raw)


if __name__ == '__main__':
    unittest.main()
