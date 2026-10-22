"""Read-only local review inputs; commit anchors never authenticate approval.

Draft and base blobs are limited to 1 MiB each and decoded as strict UTF-8
without newline conversion. Working-tree context sources are hashed, never
claimed to match HEAD. This module writes no files and performs no network IO.
"""
from __future__ import annotations

import difflib
import hashlib
import os
import re
import subprocess
from pathlib import Path, PurePosixPath, PureWindowsPath

try:
    from scripts import novelctl, registry_schema, story_config, story_engine
except ImportError:  # direct CLI import
    import novelctl
    import registry_schema
    import story_config
    import story_engine

MAX_SOURCE_BYTES = 1024 * 1024
COMMIT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
OPTIONAL_FIXED = {'story.json', 'data/state_history.json', 'data/sources.json', 'data/mechanics.json'}


def _git(root: Path, *args: str) -> bytes:
    env = {name: value for name, value in os.environ.items() if not name.upper().startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0',
               GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_SYSTEM=os.devnull, GIT_CONFIG_GLOBAL=os.devnull)
    try:
        result = subprocess.run(
            ['git', '--no-lazy-fetch', '--no-replace-objects', '--literal-pathspecs', '-C', str(root),
             '-c', 'core.fsmonitor=false', *args],
            capture_output=True, timeout=30, check=False, env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f'Cannot read local Git repository: {exc}') from exc
    if result.returncode:
        detail = result.stderr.decode('utf-8', errors='replace').strip()
        raise ValueError(f'Cannot read local Git repository: {detail[:500]}')
    return result.stdout


def _commit(root: Path, ref: str) -> str:
    if not isinstance(ref, str) or not ref.strip() or '\x00' in ref:
        raise ValueError('Git base must be a nonempty commit or ref')
    value = _git(root, 'rev-parse', '--verify', '--end-of-options', ref + '^{commit}')
    commit = value.decode('ascii', errors='strict').strip()
    if not COMMIT_ID.fullmatch(commit):
        raise ValueError('Git did not resolve a full commit identifier')
    return commit


def _reject_links(path: Path) -> None:
    for part in (path, *path.parents):
        if part.is_symlink() or getattr(part, 'is_junction', lambda: False)():
            raise ValueError(f'Review sources cannot use symlinks or junctions: {path.name}')


def _story_source(root: Path, relative: str) -> Path:
    if (not isinstance(relative, str) or not relative.strip()
            or any(ord(char) < 32 for char in relative)
            or Path(relative).is_absolute() or PureWindowsPath(relative).drive):
        raise ValueError('Review source must be a nonempty story-relative path')
    normalized = relative.replace('\\', '/')
    if '..' in PurePosixPath(normalized).parts:
        raise ValueError('Review source path cannot traverse parent directories')
    path = root / normalized
    _reject_links(path)
    return story_config.story_path(root, normalized)


def _bytes(path: Path) -> bytes:
    try:
        if not path.is_file():
            raise ValueError(f'Cannot read review source {path.name}: source must be a regular file')
        with path.open('rb') as source:
            value = source.read(MAX_SOURCE_BYTES + 1)
    except OSError as exc:
        raise ValueError(f'Cannot read review source {path.name}: {exc}') from exc
    if len(value) > MAX_SOURCE_BYTES:
        raise ValueError(f'Review source {path.name} exceeds the 1 MiB limit')
    return value


def _text(value: bytes, label: str) -> str:
    try:
        text = value.decode('utf-8', errors='strict')
    except UnicodeDecodeError as exc:
        raise ValueError(f'{label}: review source must be valid UTF-8 text') from exc
    if any(ord(char) < 32 and char not in '\t\n\r' for char in text) or '\x7f' in text:
        raise ValueError(f'{label}: review source contains nontext control characters')
    return text


def _metadata(value: bytes) -> dict:
    return {'sha256': hashlib.sha256(value).hexdigest(), 'byte_length': len(value)}


def _base_blob(repo: Path, commit: str, relative: str) -> tuple[bytes, str | None]:
    """Read the selected path only, checking parent tree entries for symlinks."""
    parts = PurePosixPath(relative).parts
    entry = None
    for number in range(1, len(parts) + 1):
        name = '/'.join(parts[:number])
        records = _git(repo, 'ls-tree', '-z', commit, '--', name).split(b'\x00')
        entry = None
        for record in records:
            if not record:
                continue
            details, path = record.split(b'\t', 1)
            if path == name.encode('utf-8'):
                mode, kind, object_id = details.decode('ascii').split()
                entry = mode, kind, object_id
                break
        if entry is None:
            return b'', None  # Explicit addition at this path, not an invented base.
        mode, kind, object_id = entry
        if mode == '120000':
            raise ValueError('Base review source cannot use a Git symlink')
        if number < len(parts) and kind != 'tree':
            raise ValueError('Base review source parent is not a Git tree')
    mode, kind, object_id = entry
    if kind != 'blob' or mode not in ('100644', '100755'):
        raise ValueError('Base review source must be a regular Git blob')
    size = int(_git(repo, 'cat-file', '-s', object_id).decode('ascii').strip())
    if size > MAX_SOURCE_BYTES:
        raise ValueError('Base review source exceeds the 1 MiB limit')
    value = _git(repo, 'cat-file', 'blob', object_id)
    if len(value) != size:
        raise ValueError('Base review source changed while reading its Git object')
    return value, object_id


def _lines(text: str) -> list[str]:
    """Git-style LF lines, retaining CR bytes and missing final newlines."""
    pieces = text.split('\n')
    return [line + '\n' for line in pieces[:-1]] + ([pieces[-1]] if pieces[-1] else [])


def _diff(before: str, after: str, relative: str, exists: bool) -> str:
    lines = difflib.unified_diff(
        _lines(before), _lines(after),
        fromfile='base/' + relative if exists else '/dev/null',
        tofile='working-tree/' + relative, lineterm='\n',
    )
    output = []
    for line in lines:
        output.append(line)
        if not line.endswith('\n'):
            output.append('\n\\ No newline at end of file\n')
    return ''.join(output)


def _sources(root: Path, draft_relative: str) -> set[str]:
    """Explicit story inputs read by the existing pack/validation implementation."""
    config = story_config.load_config(root)
    kinds = novelctl.REQUIRED_DATA if config['extensions']['gameplay'] else novelctl.CORE_DATA
    paths = {f'data/{kind}.json' for kind in kinds}
    paths.update(('ledger/index.json', 'bible/STYLE_GUIDE.md', draft_relative))
    if (root / 'story.json').exists() or (root / 'story.json').is_symlink():
        paths.add('story.json')
    if (root / 'data/state_history.json').exists() or (root / 'data/state_history.json').is_symlink():
        paths.add('data/state_history.json')
    # Check these fixed inputs before parsing any references from their contents.
    for relative in paths:
        _bytes(_story_source(root, relative))
    db, index = novelctl.load(root), story_engine.load_index(root)
    for scene in novelctl.rows(db, 'scenes'):
        if scene['status'] in story_engine.APPROVED:
            paths.add(scene['draft_path'])
    for layer in ('episodes', 'chapters', 'books'):
        paths.update(record['summary_path'] for record in index[layer])
    if 'data/state_history.json' in paths:
        history = registry_schema.read_json(_story_source(root, 'data/state_history.json'))
        registry_schema.ensure_valid('state_history', history)
        if history['baseline'] is not None and history['baseline']['status'] == 'APPROVED':
            paths.add(history['baseline']['evidence_path'])
    for relative in paths:
        _story_source(root, relative)
    return paths


def _snapshot(root: Path, paths: set[str]) -> dict[str, dict]:
    return {relative: _metadata(_bytes(_story_source(root, relative))) for relative in sorted(paths)}


def _fixed_snapshot(root: Path) -> dict[str, dict | None]:
    """Fingerprint fixed inputs before selecting scenes or enumerating pointers.

    Optional absence is evidence too: a newly created history file cannot enter
    a pack between reference enumeration and the final stability check.
    """
    paths = {f'data/{kind}.json' for kind in novelctl.REQUIRED_DATA}
    paths.update(('story.json', 'data/state_history.json', 'ledger/index.json', 'bible/STYLE_GUIDE.md'))
    observed = {}
    for relative in sorted(paths):
        original = root / relative
        if relative in OPTIONAL_FIXED and not original.exists() and not original.is_symlink():
            observed[relative] = None
        else:
            observed[relative] = _metadata(_bytes(_story_source(root, relative)))
    return observed


def build(root: Path, target: str, base: str = 'HEAD') -> dict:
    """Package one selected scene for local review, without changing any source.

    HEAD and base are actual local commit anchors only. The draft and context
    are observed working-tree inputs, and are UNREVIEWED regardless of any
    source registry's local approval labels. No GitHub approval is verified.
    """
    _reject_links(Path(root).absolute())
    root = story_config.resolve_root(root)
    _reject_links(root)
    repo = Path(_git(root, 'rev-parse', '--show-toplevel').decode('utf-8').strip()).resolve()
    if not root.is_relative_to(repo):
        raise ValueError('Selected story is outside the local Git repository')
    head_commit, base_commit = _commit(repo, 'HEAD'), _commit(repo, base)
    fixed = _fixed_snapshot(root)
    config = story_config.load_config(root)
    db = novelctl.load(root)
    scene = novelctl.get(db, 'scenes', target)
    if scene is None:
        raise ValueError(f'Review bundle requires a known scene target: {target}')
    draft = _story_source(root, scene.get('draft_path'))
    drafts = _story_source(root, 'drafts')
    if not draft.is_relative_to(drafts) or draft.suffix.lower() != '.md':
        raise ValueError('Selected review draft must be Markdown inside this story\'s drafts/')
    relative = draft.relative_to(root).as_posix()
    repository_path = draft.relative_to(repo).as_posix()
    draft_bytes = _bytes(draft)
    draft_text = _text(draft_bytes, 'Working-tree draft')
    base_bytes, base_object = _base_blob(repo, base_commit, repository_path)
    base_text = _text(base_bytes, 'Base draft')
    paths = _sources(root, relative) | {name for name, metadata in fixed.items() if metadata is not None}
    before = _snapshot(root, paths)
    if (fixed != _fixed_snapshot(root) or before[relative] != _metadata(draft_bytes)
            or any(before.get(name) != metadata for name, metadata in fixed.items())):
        raise ValueError('Selected draft or registry changed while building review bundle; retry from stable inputs')
    context = story_engine.pack(root, target)
    if (fixed != _fixed_snapshot(root) or before != _snapshot(root, paths)
            or head_commit != _commit(repo, 'HEAD')):
        raise ValueError('Working-tree sources or HEAD changed while building review bundle; retry from stable inputs')
    difference = _diff(base_text, draft_text, repository_path, base_object is not None)
    return {
        'schema_version': 1, 'status': 'UNREVIEWED', 'target': target,
        'approval_basis': 'LOCAL_BUNDLE_NOT_GITHUB_AUTHENTICATED',
        'story': {'slug': config['slug'], 'repository_path': root.relative_to(repo).as_posix()},
        'git': {'head_commit': head_commit, 'base_commit': base_commit,
                'relationship': 'ANCHORS_ONLY_NOT_WORKING_TREE_CONTENT_IDENTITIES'},
        'draft': {'origin': 'WORKING_TREE', 'path': repository_path, 'story_path': relative,
                  'content': draft_text, **_metadata(draft_bytes)},
        'base_draft': {'origin': 'GIT_OBJECT', 'commit': base_commit, 'path': repository_path,
                       'exists': base_object is not None, 'blob_id': base_object,
                       'content': base_text, **_metadata(base_bytes)},
        'diff': {'format': 'UNIFIED', 'content': difference,
                 **_metadata(difference.encode('utf-8'))},
        'context': {'origin': 'WORKING_TREE', 'content': context,
                    **_metadata(context.encode('utf-8')),
                    'source_scope': 'SELECTED_STORY_INPUTS_ENGINE_CODE_NOT_AUTHENTICATED',
                    'sources': [{'path': name, **metadata} for name, metadata in before.items()]},
    }
