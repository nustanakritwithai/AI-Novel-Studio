"""Resolve explicit, source-bound house reference views for a scene.

Cards are writing references only. This module does not replay world state,
promote canon, or infer missing facts from neighboring views.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path, PurePosixPath

try:
    from scripts import novelctl, registry_schema, review_bundle, story_config
except ImportError:  # direct CLI import
    import novelctl
    import registry_schema
    import review_bundle
    import story_config

MANIFEST = 'data/house_references.json'
MAX_DOCUMENT_BYTES = 1024 * 1024
_ID = re.compile(r'^[A-Za-z][A-Za-z0-9_-]{0,63}$')
_FIELD = re.compile(r'^[a-z][a-z0-9_]*$')
_SHA1 = re.compile(r'^[0-9a-f]{40}$')
_LINE_LOCATOR = re.compile(r'^L([1-9][0-9]*)(?:-L([1-9][0-9]*))?$')
_MISSING = object()


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key {key!r}')
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f'non-finite constant {value} is not valid JSON')


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f'non-finite number {value} is not valid JSON')
    return number


def _json_bytes(value: bytes, label: str):
    try:
        return json.loads(value.decode('utf-8', errors='strict'),
                          object_pairs_hook=_reject_duplicate_keys,
                          parse_constant=_reject_constant, parse_float=_finite_float)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f'{label}: invalid strict UTF-8 JSON ({exc})') from exc


def _read_manifest(root: Path) -> dict | None:
    path = review_bundle._story_source(root, MANIFEST)
    if not path.exists() and not path.is_symlink():
        return None
    raw = review_bundle._bytes(path)
    value = _json_bytes(raw, MANIFEST)
    if not isinstance(value, dict):
        raise ValueError(f'{MANIFEST}: expected a JSON object')
    registry_schema.ensure_valid('house_references', value)
    return value


def _indexes(db: dict):
    def registry_index(kind):
        rows = novelctl.rows(db, kind)
        result = {row['id']: row for row in rows}
        if len(result) != len(rows):
            raise ValueError(f'{kind}: ambiguous duplicate registry IDs')
        return result

    return {
        'houses': {},
        'sources': {},
        'facts': {},
        'knowledge': {},
        'scenes': registry_index('scenes'),
        'episodes': registry_index('episodes'),
        'characters': registry_index('characters'),
        'locations': registry_index('locations'),
    }


def _unique_index(rows, label: str, errors: list[str]) -> dict:
    result = {}
    for row in rows:
        key = row['id']
        if key in result:
            errors.append(f'{label}: duplicate id {key}')
        else:
            result[key] = row
    return result


def _scene_positions(db: dict) -> dict:
    # This is deliberately narrative disclosure order (episode registry order,
    # then scene order), never the story's world clock or event chronology.
    episodes = novelctl.rows(db, 'episodes')
    scenes = novelctl.rows(db, 'scenes')
    episode_ids = [row['id'] for row in episodes]
    scene_ids = [row['id'] for row in scenes]
    if len(set(episode_ids)) != len(episode_ids) or len(set(scene_ids)) != len(scene_ids):
        raise ValueError('Scene disclosure order requires unique episode and scene IDs')
    for scene in scenes:
        if scene.get('episode_id') not in episode_ids:
            raise ValueError(f"{scene['id']}: unknown disclosure episode")
        if type(scene.get('order')) is not int:
            raise ValueError(f"{scene['id']}: disclosure order must be an integer")
    for episode_id in episode_ids:
        orders = sorted(row['order'] for row in scenes if row['episode_id'] == episode_id)
        if orders != list(range(1, len(orders) + 1)):
            raise ValueError(f'{episode_id}: disclosure order must be unique and consecutive 1..N')
    return novelctl.scene_positions(db)


def _claim_is_disclosed(claim: dict, scene_id: str, boundary: str,
                         positions: dict) -> bool:
    target = positions.get(scene_id)
    disclosure = positions.get(claim['observed_after_scene'])
    if target is None or disclosure is None:
        return False
    return disclosure < target or (boundary == 'AFTER' and disclosure == target)


def _value_errors(claim: dict, indexes: dict) -> list[str]:
    errors = []
    field = claim['field']
    value = claim['value']
    if field == 'owner_character_ref' and value is not None:
        if not isinstance(value, str) or value not in indexes['characters']:
            errors.append(f"{claim['id']}: owner_character_ref must be null or a known character")
    elif field == 'owner_group_ref' and value is not None:
        errors.append(f"{claim['id']}: owner_group_ref must be null; no group registry is defined")
    elif field == 'location_refs' and value is not None:
        if not isinstance(value, list) or any(not isinstance(item, str) or item not in indexes['locations'] for item in value):
            errors.append(f"{claim['id']}: location_refs must be null or a list of known locations")
    return errors


def _semantic_errors(root: Path, manifest: dict, db: dict) -> tuple[list[str], dict, dict]:
    errors: list[str] = []
    if story_config.load_config(root)['slug'] != manifest['story_slug']:
        errors.append(f'{MANIFEST}: story_slug does not match the selected story')

    indexes = _indexes(db)
    indexes['houses'] = _unique_index(manifest['houses'], 'houses', errors)
    indexes['sources'] = _unique_index(manifest['sources'], 'sources', errors)
    indexes['facts'] = _unique_index(manifest['facts'], 'facts', errors)
    indexes['knowledge'] = _unique_index(manifest['knowledge'], 'knowledge', errors)
    fields = set(manifest['fields'])

    # Validate source paths even when their contents are not selected. Reading
    # and hashing is deferred until a cited source is selected by a view.
    for source in manifest['sources']:
        try:
            review_bundle._story_source(root, source['path'])
        except (OSError, ValueError) as exc:
            errors.append(f"{source['id']}: invalid story source path ({exc})")
        for support in source.get('supporting_sources', []):
            if support not in indexes['sources']:
                errors.append(f"{source['id']}: unknown supporting source {support}")

    # A cycle anywhere in the declared support graph is a malformed manifest;
    # iterative traversal avoids recursion limits for bounded but large files.
    colors: dict[str, int] = {}
    for start in indexes['sources']:
        if colors.get(start, 0):
            continue
        stack = [(start, False)]
        while stack:
            source_id, leaving = stack.pop()
            if leaving:
                colors[source_id] = 2
                continue
            color = colors.get(source_id, 0)
            if color == 2:
                continue
            if color == 1:
                errors.append(f'{source_id}: supporting_sources contain a cycle')
                continue
            colors[source_id] = 1
            stack.append((source_id, True))
            source = indexes['sources'][source_id]
            for child in reversed(source.get('supporting_sources', [])):
                if child in indexes['sources']:
                    if colors.get(child) == 1:
                        errors.append(f'{source_id}: supporting_sources contain a cycle through {child}')
                    elif colors.get(child, 0) == 0:
                        stack.append((child, False))

    try:
        positions = _scene_positions(db)
    except (KeyError, TypeError) as exc:
        positions = {}
        errors.append(f'Cannot determine scene disclosure order: {exc}')

    for kind in ('facts', 'knowledge'):
        for claim in manifest[kind]:
            if claim['house_id'] not in indexes['houses']:
                errors.append(f"{claim['id']}: unknown house {claim['house_id']}")
            if claim['field'] not in fields:
                errors.append(f"{claim['id']}: field {claim['field']} is not declared")
            if claim['observed_after_scene'] not in positions:
                errors.append(f"{claim['id']}: unknown disclosure scene {claim['observed_after_scene']}")
            errors.extend(_value_errors(claim, indexes))
            for evidence in claim['evidence']:
                if evidence['source_id'] not in indexes['sources']:
                    errors.append(f"{claim['id']}: unknown evidence source {evidence['source_id']}")
            if kind == 'knowledge' and claim['character_ref'] not in indexes['characters']:
                errors.append(f"{claim['id']}: unknown knowledge character {claim['character_ref']}")

    view_keys: set[tuple[str, str, str]] = set()
    for view in manifest['views']:
        key = (view['house_id'], view['scene_id'], view['boundary'])
        if key in view_keys:
            errors.append(f'{key}: duplicate house reference view')
        view_keys.add(key)
        if view['house_id'] not in indexes['houses']:
            errors.append(f'{key}: unknown house {view["house_id"]}')
        if view['scene_id'] not in positions:
            errors.append(f'{key}: unknown scene {view["scene_id"]}')
        fact_fields: set[str] = set()
        for claim_id in view['fact_ids']:
            claim = indexes['facts'].get(claim_id)
            if claim is None:
                errors.append(f'{key}: unknown fact {claim_id}')
                continue
            if claim['house_id'] != view['house_id']:
                errors.append(f'{key}: fact {claim_id} belongs to another house')
            if claim['field'] in fact_fields:
                errors.append(f'{key}: duplicate fact field {claim["field"]}')
            fact_fields.add(claim['field'])
            if view['scene_id'] in positions and claim['observed_after_scene'] in positions and not _claim_is_disclosed(claim, view['scene_id'], view['boundary'], positions):
                errors.append(f'{key}: fact {claim_id} is disclosed after this view')
        knowledge_fields: set[tuple[str, str]] = set()
        for claim_id in view['knowledge_ids']:
            claim = indexes['knowledge'].get(claim_id)
            if claim is None:
                errors.append(f'{key}: unknown knowledge row {claim_id}')
                continue
            if claim['house_id'] != view['house_id']:
                errors.append(f'{key}: knowledge row {claim_id} belongs to another house')
            marker = (claim['character_ref'], claim['field'])
            if marker in knowledge_fields:
                errors.append(f'{key}: duplicate knowledge field {claim["field"]} for {claim["character_ref"]}')
            knowledge_fields.add(marker)
            if view['scene_id'] in positions and claim['observed_after_scene'] in positions and not _claim_is_disclosed(claim, view['scene_id'], view['boundary'], positions):
                errors.append(f'{key}: knowledge row {claim_id} is disclosed after this view')

    return errors, indexes, positions


def _source_metadata(source: dict, supports: list[dict] | None = None) -> dict:
    result = {
        'id': source['id'], 'path': source['path'],
        'git_blob_sha': source['git_blob_sha'], 'status': source['status'],
    }
    if supports:
        result['supporting_sources'] = supports
    return result


def _strict_json_pointer(text: str, locator: str) -> None:
    document = _json_bytes(text.encode('utf-8'), 'evidence JSON pointer source')
    current = document
    for raw in locator[1:].split('/'):
        if re.search(r'~(?![01])', raw):
            raise ValueError(f'invalid JSON Pointer escape in {locator!r}')
        token = raw.replace('~1', '/').replace('~0', '~')
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and re.fullmatch(r'0|[1-9][0-9]*', token):
            index = int(token)
            if index >= len(current):
                raise ValueError(f'JSON Pointer does not resolve: {locator}')
            current = current[index]
        else:
            raise ValueError(f'JSON Pointer does not resolve: {locator}')


def _check_locator(text: str, locator: str) -> None:
    match = _LINE_LOCATOR.fullmatch(locator)
    if match:
        first = int(match.group(1))
        last = int(match.group(2) or first)
        line_count = len(text.splitlines())
        if last < first or last > line_count:
            raise ValueError(f'line locator {locator!r} does not resolve in source')
    elif locator.startswith('/'):
        _strict_json_pointer(text, locator)
    else:
        raise ValueError(f'evidence locator must be L<number>[-L<number>] or a JSON Pointer: {locator!r}')


def _commit_context(root: Path) -> tuple[Path, str]:
    repo = Path(review_bundle._git(root, 'rev-parse', '--show-toplevel').decode('utf-8', errors='strict').strip()).resolve()
    commit = review_bundle._commit(repo, 'HEAD')
    return repo, commit


def _read_source(root: Path, source: dict, source_mode: str,
                 commit_context: tuple[Path, str] | None,
                 cache: dict[str, tuple[bytes, str]]) -> tuple[bytes, str]:
    source_id = source['id']
    if source_id in cache:
        return cache[source_id]
    path = review_bundle._story_source(root, source['path'])
    if source_mode == 'working-tree':
        raw = review_bundle._bytes(path)
        git_sha = hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
    else:
        if commit_context is None:
            raise ValueError('Committed source context is unavailable')
        repo, commit = commit_context
        try:
            relative = path.relative_to(repo).as_posix()
        except ValueError as exc:
            raise ValueError(f"{source_id}: source path is outside the selected repository") from exc
        if PurePosixPath(relative).is_absolute() or '..' in PurePosixPath(relative).parts:
            raise ValueError(f'{source_id}: source path escapes the repository')
        raw, object_id = review_bundle._base_blob(repo, commit, relative)
        if object_id is None:
            raise ValueError(f"{source_id}: source path is absent from committed HEAD")
        git_sha = object_id
    if not _SHA1.fullmatch(git_sha) or git_sha != source['git_blob_sha']:
        raise ValueError(f"{source_id}: Git blob hash does not match pinned source at {source['path']}")
    text = review_bundle._text(raw, source['path'])
    cache[source_id] = (raw, text)
    return raw, text


def _selected_source_chain(source_id: str, indexes: dict) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    stack = [source_id]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        source = indexes['sources'].get(current)
        if source is None:
            raise ValueError(f'Unknown evidence source {current}')
        seen.add(current)
        result.append(current)
        stack.extend(reversed(source.get('supporting_sources', [])))
    return result


def _verify_claim_evidence(root: Path, claim: dict, indexes: dict,
                           source_mode: str, commit_context,
                           source_cache: dict) -> list[dict]:
    output = []
    for evidence in claim['evidence']:
        chain = _selected_source_chain(evidence['source_id'], indexes)
        for source_id in chain:
            source = indexes['sources'][source_id]
            _, text = _read_source(root, source, source_mode, commit_context, source_cache)
            if source_id == evidence['source_id']:
                _check_locator(text, evidence['locator'])
        direct = indexes['sources'][evidence['source_id']]
        source_info = _source_metadata(direct, [
            _source_metadata(indexes['sources'][support]) for support in chain[1:]
        ])
        output.append({
            'source_id': evidence['source_id'], 'path': direct['path'],
            'git_blob_sha': direct['git_blob_sha'], 'source_status': direct['status'],
            'locator': evidence['locator'], 'source': source_info,
        })
    return output


def _unknown_card(root: Path, house_id: str, scene_id: str, boundary: str,
                  source_mode: str, fields: list[str], pov: str | None,
                  source_commit: str | None = None) -> dict:
    card = {
        'status': 'REFERENCE_ONLY_NOT_CANON',
        'availability': 'UNKNOWN',
        'human_editorial_approval': 'UNVERIFIED',
        'canon_change_authorized': False,
        'ledger_apply_authorized': False,
        'story_slug': story_config.load_config(root)['slug'],
        'house_id': house_id, 'scene_id': scene_id, 'boundary': boundary,
        'source_mode': source_mode,
        'source_evidence_mode': 'COMMITTED_GIT_BLOBS' if source_mode == 'committed' else 'WORKING_TREE_RAW_BYTES',
        'world_time': 'UNKNOWN',
        'facts': {}, 'unknown_fields': list(fields),
        'pov_knowledge': {'status': 'UNKNOWN', 'character_ref': pov, 'facts': {}},
    }
    if source_commit is not None:
        card['source_commit'] = source_commit
    return card


def _db_for_build(root: Path) -> dict:
    return novelctl.load(root)


def build(root: Path, house_id: str, scene_id: str, boundary: str = 'BEFORE',
          pov: str | None = None, source_mode: str = 'working-tree') -> dict:
    """Build a card only from one exact declared scene/boundary view."""
    if boundary not in ('BEFORE', 'AFTER'):
        raise ValueError("boundary must be 'BEFORE' or 'AFTER'")
    if source_mode not in ('working-tree', 'committed'):
        raise ValueError("source_mode must be 'working-tree' or 'committed'")
    if not isinstance(house_id, str) or not _ID.fullmatch(house_id):
        raise ValueError('house_id must be a stable ASCII identifier')
    if not isinstance(scene_id, str) or not _ID.fullmatch(scene_id):
        raise ValueError('scene_id must be a stable ASCII identifier')

    root = story_config.resolve_root(Path(root))
    manifest = _read_manifest(root)
    db = _db_for_build(root)
    indexes = _indexes(db)
    positions = _scene_positions(db)
    scene = indexes['scenes'].get(scene_id)
    if scene is None or scene_id not in positions:
        raise ValueError(f'Unknown scene {scene_id} in selected story')
    selected_pov = scene.get('pov') if pov is None else pov
    if selected_pov is not None and selected_pov not in indexes['characters']:
        raise ValueError(f'Unknown POV character {selected_pov}')

    if source_mode == 'committed':
        commit_context = _commit_context(root)
        source_commit = commit_context[1]
    else:
        commit_context = None
        source_commit = None

    if manifest is None:
        return _unknown_card(root, house_id, scene_id, boundary, source_mode, [], selected_pov, source_commit)
    semantic, indexes, positions = _semantic_errors(root, manifest, db)
    if semantic:
        raise ValueError('; '.join(semantic))
    if not manifest['enabled']:
        return _unknown_card(root, house_id, scene_id, boundary, source_mode, manifest['fields'], selected_pov, source_commit)
    if house_id not in indexes['houses']:
        raise ValueError(f'Unknown house {house_id}')

    view = next((row for row in manifest['views'] if
                 row['house_id'] == house_id and row['scene_id'] == scene_id and row['boundary'] == boundary), None)
    if view is None:
        return _unknown_card(root, house_id, scene_id, boundary, source_mode, manifest['fields'], selected_pov, source_commit)

    source_cache: dict[str, tuple[bytes, str]] = {}
    cards = {}
    unknown = []
    for claim_id in view['fact_ids']:
        claim = indexes['facts'][claim_id]
        evidence = _verify_claim_evidence(root, claim, indexes, source_mode, commit_context, source_cache)
        card = {'id': claim['id'], 'value': claim['value'],
                'observed_after_scene': claim['observed_after_scene'], 'evidence': evidence}
        if 'qualification' in claim:
            card['qualification'] = claim['qualification']
        cards[claim['field']] = card
        if claim['value'] is None:
            unknown.append(claim['field'])
    unknown.extend(field for field in manifest['fields'] if field not in cards)

    pov_rows = [indexes['knowledge'][claim_id] for claim_id in view['knowledge_ids']
                if indexes['knowledge'][claim_id]['character_ref'] == selected_pov]
    pov_facts = {}
    for claim in pov_rows:
        evidence = _verify_claim_evidence(root, claim, indexes, source_mode, commit_context, source_cache)
        card = {'id': claim['id'], 'value': claim['value'],
                'observed_after_scene': claim['observed_after_scene'], 'evidence': evidence}
        if 'qualification' in claim:
            card['qualification'] = claim['qualification']
        pov_facts[claim['field']] = card
    result = {
        'status': 'REFERENCE_ONLY_NOT_CANON',
        'availability': 'AVAILABLE',
        'human_editorial_approval': 'UNVERIFIED',
        'canon_change_authorized': False,
        'ledger_apply_authorized': False,
        'story_slug': manifest['story_slug'],
        'house_id': house_id, 'scene_id': scene_id, 'boundary': boundary,
        'source_mode': source_mode,
        'source_evidence_mode': 'COMMITTED_GIT_BLOBS' if source_mode == 'committed' else 'WORKING_TREE_RAW_BYTES',
        'world_time': 'UNKNOWN',
        'facts': cards,
        'unknown_fields': list(dict.fromkeys(unknown)),
        'pov_knowledge': {
            'status': 'AVAILABLE' if pov_facts else 'UNKNOWN',
            'character_ref': selected_pov, 'facts': pov_facts,
        },
    }
    if source_commit is not None:
        result['source_commit'] = source_commit
    return result


def validate(root: Path, db: dict | None = None) -> list[str]:
    """Validate an enabled manifest and all explicitly selected views.

    Source reads and Git checks are cached per invocation, so shared evidence
    used by multiple views is checked once. This routine intentionally verifies
    exact raw working-tree bytes; committed mode is available only via build.
    """
    try:
        root = story_config.resolve_root(Path(root))
        manifest = _read_manifest(root)
        if manifest is None:
            return []
        if db is None:
            db = novelctl.load(root)
        if not manifest['enabled']:
            if story_config.load_config(root)['slug'] != manifest['story_slug']:
                return [f'{MANIFEST}: story_slug does not match the selected story']
            return []
        errors, indexes, _ = _semantic_errors(root, manifest, db)
        if errors:
            return errors
        source_cache: dict[str, tuple[bytes, str]] = {}
        for view in manifest['views']:
            for kind, key in (('facts', 'fact_ids'), ('knowledge', 'knowledge_ids')):
                for claim_id in view[key]:
                    claim = indexes[kind][claim_id]
                    try:
                        _verify_claim_evidence(root, claim, indexes, 'working-tree', None, source_cache)
                    except (OSError, ValueError) as exc:
                        errors.append(f"view {view['house_id']}/{view['scene_id']}/{view['boundary']} claim {claim_id}: {exc}")
        return errors
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return [f'Cannot validate {MANIFEST}: {exc}']
