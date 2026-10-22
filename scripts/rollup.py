"""Deterministic recap assembly proposals, never new prose or approval records."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path, PureWindowsPath

try:
    from scripts import novelctl, provenance, review_bundle, story_config, story_engine
except ImportError:  # direct CLI import
    import novelctl
    import provenance
    import review_bundle
    import story_config
    import story_engine


APPROVAL_FIELDS = ('pr_number', 'approved_by', 'merge_commit', 'approved_at')
PROVENANCE_FIELDS = ('repository', 'pr_number', 'head_commit', 'merge_commit', 'source_path', 'source_sha256')
MAX_ASSEMBLY_BYTES = 8 * review_bundle.MAX_SOURCE_BYTES
SEPARATOR = '\n\n'


def _selection(db: dict, index: dict, episode_ids) -> list[dict]:
    if (not isinstance(episode_ids, (list, tuple)) or not episode_ids
            or any(not isinstance(value, str) or not value.strip() for value in episode_ids)):
        raise ValueError('Rollup requires a nonempty list of episode IDs')
    episode_ids = list(episode_ids)
    if len(set(episode_ids)) != len(episode_ids):
        raise ValueError('Rollup episode IDs must be unique')
    series = [episode['id'] for episode in novelctl.rows(db, 'episodes')]
    if any(value not in series for value in episode_ids):
        raise ValueError('Rollup references an unknown episode')
    positions = [series.index(value) for value in episode_ids]
    if positions != list(range(positions[0], positions[0] + len(positions))):
        raise ValueError('Rollup episode IDs must be contiguous in series order')
    records = {record['id']: record for record in index['episodes']}
    if any(value not in records for value in episode_ids):
        raise ValueError('Every rollup episode must be present in the approved episode ledger')
    return [records[value] for value in episode_ids]


def _declared_path(value: str) -> str:
    if (not isinstance(value, str) or not value or '\\' in value
            or any(ord(char) < 32 or ord(char) == 127 for char in value)
            or value.startswith('/') or PureWindowsPath(value).drive
            or any(part in ('', '.', '..') for part in value.split('/'))):
        raise ValueError('Provenance source_path must be a canonical repository-relative path')
    return value


def _repository(value: str) -> str:
    if (not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', value)
            or any(part in ('.', '..') for part in value.split('/'))):
        raise ValueError('Remote verification requires an explicit owner/repository')
    return value


def _repository_root(root: Path) -> Path:
    repository = Path(review_bundle._git(root, 'rev-parse', '--show-toplevel').decode('utf-8').strip()).resolve()
    review_bundle._reject_links(repository)
    if not root.is_relative_to(repository):
        raise ValueError('Selected story is outside the local Git repository')
    return repository


def _bound_observation(report, expected: dict, value: bytes) -> dict:
    """Require the runtime report to prove this exact requested immutable source."""
    def fail():
        raise ValueError('Remote provenance report does not bind matching merged metadata and immutable source bytes')

    def same_text(actual, wanted):
        return isinstance(actual, str) and actual.lower() == wanted.lower()

    if (not isinstance(report, dict) or type(report.get('schema_version')) is not int
            or report['schema_version'] != 1 or report.get('status') != 'OBSERVED_MERGED_METADATA'
            or report.get('errors') != [] or report.get('metadata_consistency') != 'CONSISTENT'
            or report.get('human_editorial_approval') != 'UNVERIFIED'):
        fail()
    requested, observed, transport = (report.get(key) for key in ('requested', 'observed', 'transport'))
    if not all(isinstance(part, dict) for part in (requested, observed, transport)):
        fail()
    if (transport.get('mode') != 'LIVE_GH_API' or transport.get('hostname') != 'github.com'
            or transport.get('network_attempted') is not True
            or type(transport.get('requests_attempted')) is not int or transport['requests_attempted'] < 1):
        fail()
    for key in PROVENANCE_FIELDS:
        if key == 'pr_number':
            if type(requested.get(key)) is not int or requested[key] != expected[key]:
                fail()
        elif key == 'source_path':
            if requested.get(key) != expected[key]:
                fail()
        elif not same_text(requested.get(key), expected[key]):
            fail()
    pr, commit, source = (observed.get(key) for key in ('pull_request', 'merge_commit', 'source'))
    if not all(isinstance(part, dict) for part in (pr, commit, source)):
        fail()
    if (not same_text(pr.get('repository'), expected['repository'])
            or type(pr.get('number')) is not int or pr['number'] != expected['pr_number']
            or not same_text(pr.get('head_commit'), expected['head_commit'])
            or not same_text(pr.get('merge_commit'), expected['merge_commit'])
            or pr.get('merged') is not True or pr.get('state') != 'closed'
            or not isinstance(pr.get('merged_at'), str)
            or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', pr['merged_at'])
            or not same_text(commit.get('sha'), expected['merge_commit'])
            or not isinstance(commit.get('tree_sha'), str)
            or not re.fullmatch(r'[0-9a-fA-F]{40}', commit['tree_sha'])):
        fail()
    blob = hashlib.sha1(b'blob ' + str(len(value)).encode('ascii') + b'\0' + value,
                        usedforsecurity=False).hexdigest()
    if (source.get('status') != 'MATCHED_IMMUTABLE_BLOB' or source.get('path') != expected['source_path']
            or not same_text(source.get('at_commit'), expected['merge_commit'])
            or not same_text(source.get('sha256'), expected['source_sha256'])
            or not same_text(source.get('blob_sha'), blob)
            or type(source.get('byte_length')) is not int or source['byte_length'] != len(value)
            or source.get('mode') not in ('100644', '100755')
            or source.get('matches_requested_sha256') is not True
            or source.get('relationship') != 'PRESENT_AT_MERGE_NOT_PROOF_OF_PR_CHANGE_OR_EDITORIAL_REVIEW'):
        fail()
    # Project only checked fields, never arbitrary response or ledger claims.
    return {
        'schema_version': 1, 'status': 'OBSERVED_MERGED_METADATA',
        'human_editorial_approval': 'UNVERIFIED', 'metadata_consistency': 'CONSISTENT',
        'transport': {key: transport[key] for key in ('mode', 'hostname', 'network_attempted', 'requests_attempted')},
        'requested': {key: requested[key] for key in PROVENANCE_FIELDS},
        'observed': {
            'pull_request': {key: pr[key] for key in ('repository', 'number', 'head_commit', 'merge_commit',
                                                     'merged', 'state', 'merged_at')},
            'merge_commit': {key: commit[key] for key in ('sha', 'tree_sha')},
            'source': {key: source[key] for key in ('status', 'path', 'at_commit', 'blob_sha', 'sha256',
                                                   'byte_length', 'mode', 'matches_requested_sha256', 'relationship')},
        },
    }


def build(root: Path, episode_ids, repository: str | None = None, verify_remote: bool = False) -> dict:
    """Assemble exact selected recaps and hashes from stable local inputs.

    Offline declarations stay unverified. Opt-in remote checks can observe merged
    metadata and immutable source bytes, never authenticate human editorial
    approval. This function performs no writes; only that explicit opt-in may
    call the bounded provenance transport.
    """
    if type(verify_remote) is not bool:
        raise ValueError('verify_remote must be boolean')
    if verify_remote:
        repository = _repository(repository)
    review_bundle._reject_links(Path(root).absolute())
    root = story_config.resolve_root(root)
    review_bundle._reject_links(root)
    fixed = review_bundle._fixed_snapshot(root)
    configuration = story_config.load_config(root)
    db, index = novelctl.load(root), story_engine.load_index(root)
    records = _selection(db, index, episode_ids)

    # The existing helper enumerates every validator input, including approved
    # scene evidence, all recap layers, and optional history baseline evidence.
    # The ledger index is the focal source here instead of a selected draft.
    paths = review_bundle._sources(root, 'ledger/index.json')
    paths.update(name for name, metadata in fixed.items() if metadata is not None)
    before = review_bundle._snapshot(root, paths)
    if (fixed != review_bundle._fixed_snapshot(root)
            or any(before.get(name) != metadata for name, metadata in fixed.items())):
        raise ValueError('Rollup registry inputs changed while selecting sources; retry from stable inputs')
    errors, warnings = story_engine.validate(root)
    if errors:
        raise ValueError('Rollup source validation failed: ' + '; '.join(errors))

    repo = _repository_root(root) if verify_remote else None
    sources, recaps = [], []
    total = 0
    for record in records:
        path = review_bundle._story_source(root, record['summary_path'])
        expected = story_engine.within(root, record['summary_path'], 'ledger/episodes')
        if path != expected:
            raise ValueError('Rollup recap path does not belong to the selected story ledger')
        relative = path.relative_to(root).as_posix()
        value = review_bundle._bytes(path)
        metadata = review_bundle._metadata(value)
        if before.get(record['summary_path']) != metadata:
            raise ValueError('Rollup recap changed while assembling sources; retry from stable inputs')
        text = review_bundle._text(value, 'Episode recap')
        total += len(value) + (len(SEPARATOR.encode('utf-8')) if recaps else 0)
        if total > MAX_ASSEMBLY_BYTES:
            raise ValueError('Rollup assembly exceeds the 8 MiB limit; select fewer episodes')
        recaps.append(text)
        source = {
            'episode_id': record['id'], 'path': relative, 'content': text, **metadata,
            'local_approval': {'status': 'UNVERIFIED',
                               'declared_metadata': {key: record['approval'][key]
                                                     for key in APPROVAL_FIELDS if key in record['approval']}},
        }
        declared = record.get('provenance')
        if declared is not None:
            _declared_path(declared['source_path'])
            if (declared['pr_number'] != record['approval']['pr_number']
                    or declared['merge_commit'].lower() != record['approval']['merge_commit'].lower()):
                raise ValueError(f"{record['id']}: provenance PR/merge identity contradicts local approval declarations")
            if declared['source_sha256'].lower() != metadata['sha256']:
                raise ValueError(f"{record['id']}: declared source_sha256 does not match current recap bytes")
            source['declared_provenance'] = {key: declared[key] for key in PROVENANCE_FIELDS}
        if verify_remote:
            if declared is None:
                raise ValueError(f"{record['id']}: complete provenance is required for remote verification")
            if declared['repository'].lower() != repository.lower():
                raise ValueError(f"{record['id']}: provenance repository does not match the explicit repository")
            repository_path = path.relative_to(repo).as_posix()
            if declared['source_path'] != repository_path:
                raise ValueError(f"{record['id']}: provenance source_path does not match the selected story recap")
            observed = provenance.verify(repository, declared['pr_number'], declared['head_commit'],
                                         declared['merge_commit'], repository_path, metadata['sha256'])
            expected_observation = {key: declared[key] for key in PROVENANCE_FIELDS}
            expected_observation.update(repository=repository, source_path=repository_path,
                                        source_sha256=metadata['sha256'])
            source['verification'] = _bound_observation(observed, expected_observation, value)
        else:
            source['verification'] = {'status': 'OFFLINE_UNVERIFIED',
                                      'human_editorial_approval': 'UNVERIFIED',
                                      'reason': 'Local declarations only; no remote verification requested.'}
        sources.append(source)

    if (fixed != review_bundle._fixed_snapshot(root) or before != review_bundle._snapshot(root, paths)
            or (verify_remote and repo != _repository_root(root))):
        raise ValueError('Rollup sources changed while building the proposal; retry from stable inputs')
    assembly = SEPARATOR.join(recaps)
    return {
        'schema_version': 1, 'kind': 'ROLLUP_PROPOSAL', 'status': 'PROPOSED',
        'story': {'slug': configuration['slug']}, 'episode_ids': [record['id'] for record in records],
        'approval_basis': 'UNVERIFIED_LOCAL_DECLARATIONS', 'human_editorial_approval': 'UNVERIFIED',
        'source_verification': 'OBSERVED_MERGED_METADATA' if verify_remote else 'OFFLINE_UNVERIFIED',
        'sources': sources,
        'assembly': {'method': 'EXACT_RECAP_CONCATENATION', 'separator': SEPARATOR,
                     'content': assembly, **review_bundle._metadata(assembly.encode('utf-8'))},
        'inputs': [{'path': path, **metadata} for path, metadata in before.items()],
        'warnings': warnings,
    }
