"""Observe immutable GitHub metadata through read-only, fixed-host gh API calls.

Merged PR metadata and matching source hashes do not establish a human editorial
decision. Supplied offline evidence is never promoted to a live observation.
No source content, raw API response, account identity, or CLI stderr is returned.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime

MAX_SOURCE_BYTES = 1024 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_PATH_DEPTH = 32
MAX_TREE_ENTRIES = 10000
SHA40 = re.compile(r'[0-9a-fA-F]{40}\Z')
SHA256 = re.compile(r'[0-9a-fA-F]{64}\Z')
OWNER = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\Z')
REPO = re.compile(r'[A-Za-z0-9_.-]{1,100}\Z')
ENDPOINT = re.compile(
    r'repos/[A-Za-z0-9-]+/[A-Za-z0-9_.-]+/'
    r'(?:pulls/[1-9][0-9]*|git/(?:commits|trees|blobs)/[0-9a-f]{40})\Z')


class _EvidenceError(ValueError):
    pass


class _TransportError(ValueError):
    def __init__(self, message, network_attempted=True):
        super().__init__(message)
        self.network_attempted = network_attempted


def _repository(value) -> str:
    if not isinstance(value, str) or value.count('/') != 1:
        raise _EvidenceError('repository must be an owner/repo name on github.com')
    owner, repo = value.split('/')
    if not OWNER.fullmatch(owner) or not REPO.fullmatch(repo) or repo in ('.', '..'):
        raise _EvidenceError('repository must be an owner/repo name on github.com')
    return value.lower()  # GitHub owner/repository identity is case-insensitive.


def _sha(value, label='commit') -> str:
    if not isinstance(value, str) or not SHA40.fullmatch(value):
        raise _EvidenceError(label + ' must be a full 40-character hexadecimal SHA')
    return value.lower()


def _path(value) -> str:
    if (not isinstance(value, str) or not value or len(value) > 1024
            or '\\' in value or ':' in value
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise _EvidenceError('source_path must be a bounded repository-relative Git path')
    parts = value.split('/')
    if len(parts) > MAX_PATH_DEPTH or any(part in ('', '.', '..') for part in parts):
        raise _EvidenceError('source_path must be a bounded repository-relative Git path')
    return value


def _object(value, label):
    if not isinstance(value, dict):
        raise _EvidenceError(label + ' evidence must be an object')
    return value


def _stop(process):
    try:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        pass


def _gh_get(endpoint: str):
    """Bound stdout while reading; discard stderr rather than exposing secrets."""
    if not ENDPOINT.fullmatch(endpoint):
        raise _TransportError('GitHub endpoint is outside the read-only allowlist', False)
    env = dict(os.environ)
    for name in ('GH_DEBUG', 'GH_HOST', 'GH_REPO'):
        env.pop(name, None)
    env.update(GH_PROMPT_DISABLED='1', GH_NO_UPDATE_NOTIFIER='1',
               GH_NO_EXTENSION_UPDATE_NOTIFIER='1', NO_COLOR='1')
    command = ['gh', 'api', '--hostname', 'github.com', '--method', 'GET',
               '--header', 'Accept: application/vnd.github+json',
               '--header', 'X-GitHub-Api-Version: 2022-11-28', endpoint]
    try:
        process = subprocess.Popen(
            command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env=env, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
    except OSError:
        raise _TransportError('GitHub CLI is unavailable; existing authentication was not changed', False) from None
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        pending = pool.submit(process.stdout.read, MAX_RESPONSE_BYTES + 1)
        try:
            output = pending.result(timeout=30)
        except FutureTimeout:
            raise _TransportError('GitHub API read timed out; provenance remains unverified') from None
        except OSError:
            raise _TransportError('GitHub API response could not be read') from None
        if not isinstance(output, bytes) or len(output) > MAX_RESPONSE_BYTES:
            raise _TransportError('GitHub API response exceeds the 2 MiB limit')
        try:
            returncode = process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            raise _TransportError('GitHub API process did not finish') from None
        if returncode:
            raise _TransportError('GitHub API read failed; access, rate limits, or network may be unavailable')

        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError('duplicate JSON key')
                result[key] = value
            return result

        def constant(_):
            raise ValueError('non-JSON constant')

        try:
            return json.loads(output.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
        except (UnicodeError, ValueError, RecursionError):
            raise _TransportError('GitHub API returned invalid JSON') from None
    finally:
        _stop(process)
        pool.shutdown(wait=True)
        process.stdout.close()


def _pr_snapshot(value) -> dict:
    pr = _object(value, 'PR')
    number = pr.get('number')
    if type(number) is not int or number <= 0 or type(pr.get('merged')) is not bool:
        raise _EvidenceError('PR number or merged flag is invalid')
    base = _object(pr.get('base'), 'PR base')
    repository = _repository(_object(base.get('repo'), 'PR base repository').get('full_name'))
    head = _sha(_object(pr.get('head'), 'PR head').get('sha'), 'PR head')
    merge = None if pr.get('merge_commit_sha') is None else _sha(pr['merge_commit_sha'], 'PR merge commit')
    state = pr.get('state')
    if state not in ('open', 'closed'):
        raise _EvidenceError('PR state is invalid')
    merged_at = pr.get('merged_at')
    if merged_at is not None:
        if not isinstance(merged_at, str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', merged_at):
            raise _EvidenceError('PR merged_at timestamp is invalid')
        try:
            datetime.fromisoformat(merged_at.replace('Z', '+00:00'))
        except ValueError:
            raise _EvidenceError('PR merged_at timestamp is invalid') from None
    return {'repository': repository, 'number': number, 'head_commit': head,
            'merge_commit': merge, 'merged': pr['merged'], 'state': state, 'merged_at': merged_at}


def _match_pr(pr: dict, requested: dict) -> None:
    if pr['repository'] != requested['repository'] or pr['number'] != requested['pr_number']:
        raise _EvidenceError('PR repository or number does not match the requested provenance')
    if pr['merged'] is not True or pr['state'] != 'closed' or pr['merged_at'] is None:
        raise _EvidenceError('PR is not observed as merged with a closed state and timestamp')
    if pr['head_commit'] != requested['head_commit']:
        raise _EvidenceError('PR head commit does not match the requested provenance')
    if pr['merge_commit'] != requested['merge_commit']:
        raise _EvidenceError('PR merge commit does not match the requested provenance')


def _source(requested: dict, tree_sha: str, read) -> dict:
    parts = requested['source_path'].split('/')
    leaf = None
    for number, name in enumerate(parts):
        tree = _object(read('tree', tree_sha), 'Git tree')
        if _sha(tree.get('sha'), 'Git tree') != tree_sha or tree.get('truncated') is not False:
            raise _EvidenceError('Git tree identity is mismatched or its listing is truncated')
        entries = tree.get('tree')
        if not isinstance(entries, list) or len(entries) > MAX_TREE_ENTRIES:
            raise _EvidenceError('Git tree listing is missing or exceeds the entry limit')
        if any(not isinstance(entry, dict) or not isinstance(entry.get('path'), str) for entry in entries):
            raise _EvidenceError('Git tree listing has invalid entries')
        matches = [entry for entry in entries if entry['path'] == name]
        if len(matches) != 1:
            raise _EvidenceError('Requested source path is absent or ambiguous in the merge tree')
        entry = matches[0]
        object_sha = _sha(entry.get('sha'), 'Git tree entry')
        if number < len(parts) - 1:
            if entry.get('mode') != '040000' or entry.get('type') != 'tree':
                raise _EvidenceError('Source path parent must be a Git tree; symlinks and submodules are rejected')
            tree_sha = object_sha
        else:
            if entry.get('mode') not in ('100644', '100755') or entry.get('type') != 'blob':
                raise _EvidenceError('Source must be a regular Git blob; symlinks and submodules are rejected')
            leaf = entry
    expected_size = leaf.get('size')
    if type(expected_size) is not int or not 0 <= expected_size <= MAX_SOURCE_BYTES:
        raise _EvidenceError('Source size is missing, invalid, or exceeds the 1 MiB limit')
    blob_sha = _sha(leaf.get('sha'), 'Git blob')
    blob = _object(read('blob', blob_sha), 'Git blob')
    if _sha(blob.get('sha'), 'Git blob') != blob_sha:
        raise _EvidenceError('Git blob identity does not match the merge tree')
    size = blob.get('size')
    content = blob.get('content')
    if (blob.get('encoding') != 'base64' or type(size) is not int
            or not 0 <= size <= MAX_SOURCE_BYTES or size != expected_size or not isinstance(content, str)):
        raise _EvidenceError('Git blob encoding or size is invalid or exceeds the 1 MiB limit')
    if len(content) > 2 * MAX_SOURCE_BYTES:
        raise _EvidenceError('Encoded Git blob exceeds its bounded source limit')
    # GitHub wraps base64 with LF. Other characters and whitespace are rejected.
    encoded = content.replace('\n', '')
    if len(encoded) > 4 * ((MAX_SOURCE_BYTES + 2) // 3):
        raise _EvidenceError('Encoded Git blob exceeds the 1 MiB source limit')
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise _EvidenceError('Git blob content is not strict base64') from None
    if len(decoded) != size or len(decoded) > MAX_SOURCE_BYTES:
        raise _EvidenceError('Decoded Git blob length does not match its bounded size')
    actual_blob_sha = hashlib.sha1(b'blob ' + str(size).encode('ascii') + b'\x00' + decoded).hexdigest()
    actual_sha256 = hashlib.sha256(decoded).hexdigest()
    if actual_blob_sha != blob_sha:
        raise _EvidenceError('Decoded source does not match its Git blob SHA')
    if actual_sha256 != requested['source_sha256']:
        raise _EvidenceError('Source SHA-256 does not match the requested provenance')
    return {'status': 'MATCHED_IMMUTABLE_BLOB', 'path': requested['source_path'],
            'at_commit': requested['merge_commit'], 'blob_sha': blob_sha,
            'sha256': actual_sha256, 'byte_length': size, 'mode': leaf['mode'],
            'matches_requested_sha256': True,
            'relationship': 'PRESENT_AT_MERGE_NOT_PROOF_OF_PR_CHANGE_OR_EDITORIAL_REVIEW'}


def verify(repository, pr_number, head_commit, merge_commit, source_path=None,
           source_sha256=None, offline_evidence=None) -> dict:
    """Observe exact PR/commit/source bindings; never infer human approval.

    Offline evidence keys are pull_request, pull_request_after, merge_commit,
    trees (SHA-keyed objects), and blobs (SHA-keyed objects). Its claims about
    transport, status, reviewers, or verification are ignored.
    """
    offline = offline_evidence is not None
    report = {
        'schema_version': 1, 'status': 'OFFLINE_UNVERIFIED' if offline else 'UNVERIFIED',
        'human_editorial_approval': 'UNVERIFIED', 'metadata_consistency': 'NOT_CHECKED',
        'basis': 'SUPPLIED_OFFLINE_EVIDENCE_NOT_AUTHENTICATED' if offline else 'FIXED_HOST_GITHUB_API_OBSERVATION',
        'transport': {'mode': 'OFFLINE_SUPPLIED_EVIDENCE' if offline else 'LIVE_GH_API',
                      'hostname': None if offline else 'github.com', 'network_attempted': False,
                      'requests_attempted': 0},
        'requested': {}, 'observed': {}, 'errors': [],
    }
    requested = report['requested']
    try:
        requested['repository'] = _repository(repository)
        if type(pr_number) is not int or not 0 < pr_number <= 2147483647:
            raise _EvidenceError('pr_number must be a positive integer within the GitHub API range')
        requested['pr_number'] = pr_number
        requested['head_commit'] = _sha(head_commit, 'head_commit')
        requested['merge_commit'] = _sha(merge_commit, 'merge_commit')
        if (source_path is None) != (source_sha256 is None):
            raise _EvidenceError('source_path and source_sha256 must be supplied together')
        if source_path is not None:
            requested['source_path'] = _path(source_path)
            if not isinstance(source_sha256, str) or not SHA256.fullmatch(source_sha256):
                raise _EvidenceError('source_sha256 must be a full 64-character hexadecimal digest')
            requested['source_sha256'] = source_sha256.lower()
        else:
            requested.update(source_path=None, source_sha256=None)
        if offline and not isinstance(offline_evidence, dict):
            raise _EvidenceError('offline_evidence must be a supplied JSON object')

        def read(kind, identifier=None):
            if offline:
                if kind in ('pr_before', 'pr_after', 'commit'):
                    key = {'pr_before': 'pull_request', 'pr_after': 'pull_request_after', 'commit': 'merge_commit'}[kind]
                    if key not in offline_evidence:
                        raise _EvidenceError('Offline evidence is missing a required observation')
                    return offline_evidence[key]
                mapping = offline_evidence.get('trees' if kind == 'tree' else 'blobs')
                if not isinstance(mapping, dict) or identifier not in mapping:
                    raise _EvidenceError('Offline evidence is missing a required Git object')
                return mapping[identifier]
            if kind in ('pr_before', 'pr_after'):
                endpoint = f"repos/{requested['repository']}/pulls/{requested['pr_number']}"
            else:
                group = {'commit': 'commits', 'tree': 'trees', 'blob': 'blobs'}[kind]
                endpoint = f"repos/{requested['repository']}/git/{group}/{identifier}"
            report['transport']['requests_attempted'] += 1
            try:
                value = _gh_get(endpoint)
            except _TransportError as exc:
                report['transport']['network_attempted'] |= exc.network_attempted
                raise
            report['transport']['network_attempted'] = True
            return value

        before = _pr_snapshot(read('pr_before'))
        _match_pr(before, requested)
        commit = _object(read('commit', requested['merge_commit']), 'Merge commit')
        if _sha(commit.get('sha'), 'Merge commit') != requested['merge_commit']:
            raise _EvidenceError('Merge Git object does not match the requested merge commit')
        tree_sha = _sha(_object(commit.get('tree'), 'Merge commit tree').get('sha'), 'Merge tree')
        source = _source(requested, tree_sha, read) if source_path is not None else None
        after = _pr_snapshot(read('pr_after'))
        if before != after:
            raise _EvidenceError('PR metadata changed between observations; retry from a stable snapshot')
        _match_pr(after, requested)
        report['observed'] = {'pull_request': before,
                              'merge_commit': {'sha': requested['merge_commit'], 'tree_sha': tree_sha}}
        if source is not None:
            report['observed']['source'] = source
        report['metadata_consistency'] = 'CONSISTENT'
        if not offline:
            report['status'] = 'OBSERVED_MERGED_METADATA'
    except _TransportError as exc:
        report['status'] = 'ERROR' if not offline else 'OFFLINE_UNVERIFIED'
        report['errors'].append(str(exc))
        report['metadata_consistency'] = 'INCOMPLETE'
    except (_EvidenceError, TypeError, KeyError, RecursionError) as exc:
        # Only our controlled diagnostics are emitted, never values from API JSON.
        message = str(exc) if isinstance(exc, _EvidenceError) else 'Provenance evidence has an invalid structure'
        report['errors'].append(message)
        report['metadata_consistency'] = 'INCONSISTENT'
    return report
