"""Compose private, scene-start writing inputs; never apply state or approval."""
from __future__ import annotations

import json
from pathlib import Path

try:
    from scripts import novelctl, story_config, story_engine, house_cards, world_history, review_bundle
    from scripts.source_evidence import SourceReader
except ImportError:
    import novelctl, story_config, story_engine, house_cards, world_history, review_bundle
    from source_evidence import SourceReader


def _metadata_snapshot(root: Path) -> dict:
    snapshot = review_bundle._fixed_snapshot(root)
    optional = {'data/house_references.json', 'data/world_model.json', 'data/world_history.json',
                'data/world_rules.json', 'author_memory/index.json'}
    optional.update(path.relative_to(root).as_posix() for path in (root / 'editorial').glob('*.json'))
    for relative in sorted(optional):
        path = root / relative
        snapshot[relative] = (review_bundle._snapshot(root, {relative})[relative]
                              if path.exists() or path.is_symlink() else None)
    return snapshot


def _world_cursor_context(root: Path, scene: dict, reader: SourceReader,
                          max_chars: int) -> str:
    """Build a cursor-safe author packet without narrative-time context.

    There is currently no authenticated mapping from a world clock to the
    scene order used by POV knowledge, inventory, threads, and replay. Validate
    the complete story with the shared reader, but only expose a finite,
    explicitly author-only plan plus style to the writer.
    """
    errors, _warnings = story_engine.validate(root, source_reader=reader)
    if errors:
        raise ValueError("Story Engine validation failed: " + "; ".join(errors[:5]))

    style = reader.text('bible/STYLE_GUIDE.md')
    plan = {key: scene[key] for key in (
        'id', 'title', 'goal', 'conflict', 'outcome', 'beats',
        'character_ids', 'location_id', 'item_ids',
    ) if key in scene}
    content = (
        "# SCENE START AUTHOR INPUT - WORLD CURSOR UNMAPPED\n"
        "The explicit world cursor has no authenticated mapping to this scene's "
        "narrative order or POV. Narrative-time knowledge, inventory, threads, "
        "house state, and replay state are withheld.\n"
        "The selected scene plan below is proposed author direction only; it is "
        "not event evidence, prior history, canon, or POV knowledge.\n\n"
        "## REQUIRED WRITING STYLE\n" + style + "\n\n"
        "## AUTHOR-ONLY SELECTED SCENE PLAN (PROPOSED)\n"
        + json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    )
    if len(content) > max_chars:
        raise ValueError(f"Safe author context size {len(content)} chars exceeds cap {max_chars}.")
    return content


def build(root: Path, scene_id: str, *, house_id: str | None = None,
          pov: str | None = None, source_mode: str = 'working-tree',
          world_cursor: dict | None = None, recent: int = 7,
          max_chars: int = 25000) -> dict:
    """All narrative sections use BEFORE; a world clock is never inferred."""
    if type(recent) is not int or not 0 <= recent <= 20 or type(max_chars) is not int or max_chars < 1000:
        raise ValueError('recent must be 0..20 and max_chars >=1000')
    root = story_config.resolve_root(root)
    metadata = _metadata_snapshot(root)
    db = novelctl.load(root)
    scene = novelctl.get(db, 'scenes', scene_id)
    if scene is None:
        raise ValueError('prepare-scene requires an existing scene ID, not an episode')
    pov = pov or scene['pov']
    if pov not in scene['character_ids']:
        raise ValueError('POV must be a character in the selected scene')
    if world_cursor is not None and (
            not isinstance(world_cursor, dict)
            or set(world_cursor) != {'clock_id', 'tick', 'suborder', 'boundary'}):
        raise ValueError('World cursor requires explicit clock_id, tick, suborder and boundary together')
    reader = SourceReader(root, source_mode)
    if world_cursor is None:
        context = story_engine.pack(root, scene_id, recent, max_chars, scene_only=True,
                                    source_reader=reader, pov_id=pov)
    else:
        context = _world_cursor_context(root, scene, reader, max_chars)
    house = {'availability': 'NOT_REQUESTED', 'reason': 'No house ID supplied; no house or ownership inferred.'}
    if house_id is not None:
        if world_cursor is None:
            house = house_cards.build(root, house_id, scene_id, boundary='BEFORE', pov=pov,
                                      source_mode=source_mode, source_reader=reader)
            if house['availability'] == 'INVALID':
                raise ValueError('House reference evidence is invalid; preparation refused')
        else:
            if novelctl.get(db, 'locations', house_id) is None:
                raise ValueError('Unknown house/location ID for selected story')
            house = {'availability': 'UNKNOWN', 'house_id': house_id,
                     'reason': 'World cursor has no authenticated mapping to scene order; narrative-time house facts withheld.'}
    world = {'availability': 'NOT_REQUESTED', 'reason': 'No world cursor supplied; scene order is not world time.'}
    if world_cursor is not None:
        world = world_history.preview(root, world_cursor, source_reader=reader)
        if world['availability'] == 'INVALID':
            raise ValueError('World preview input or evidence is invalid; preparation refused')
    positions = novelctl.scene_positions(db)
    cutoff = positions[scene_id]

    def earlier_approved(sid):
        source = novelctl.get(db, 'scenes', sid)
        return (source is not None and sid in positions and positions[sid] < cutoff
                and source['status'] in ('APPROVED', 'CANON'))

    if world_cursor is None:
        character = novelctl.get(db, 'characters', pov)
        knowledge = [{'after_scene': entry['after_scene'], 'knows': entry['knows'],
                      'source_path': novelctl.get(db, 'scenes', entry['after_scene']).get('draft_path'),
                      'approval_basis': 'LOCAL_DECLARATION_NOT_AUTHENTICATED_HUMAN_APPROVAL'}
                     for entry in character['knowledge'] if earlier_approved(entry.get('after_scene'))]
        inventory = [dict(entry) for entry in novelctl.rows(db, 'inventory_ledger')
                     if entry['owner_id'] == pov and entry['status'] in ('APPROVED', 'CANON')
                     and earlier_approved(entry['scene_id'])]
        threads = [{'id': row['id'], 'title': row['title'], 'setup_scene_id': row['setup_scene_id'],
                    'current_registry_status': row['status'], 'historical_status': 'UNKNOWN'}
                   for row in novelctl.rows(db, 'threads') if row['status'] == 'OPEN'
                   and earlier_approved(row.get('setup_scene_id'))]
    else:
        # Scene-order filtering cannot establish that narrative-time facts
        # existed at the supplied world cursor or were known to this POV.
        knowledge, inventory, threads = [], [], []
    location = novelctl.get(db, 'locations', scene['location_id'])
    evidence = reader.evidence()
    if _metadata_snapshot(root) != metadata:
        raise ValueError('Working-tree metadata changed during scene preparation')
    return {
        'schema_version': 1, 'kind': 'SCENE_PREPARATION', 'status': 'PROPOSED',
        'preparation': 'PREPARED_WITH_EXPLICIT_UNKNOWNS',
        'story': story_config.load_config(root)['slug'],
        'scene_cursor': {'scene_id': scene_id, 'boundary': 'BEFORE'},
        'world_cursor': world_cursor, 'cursor_mapping': 'UNKNOWN_NO_AUTOMATIC_MAPPING',
        'pov': pov, 'human_editorial_approval': 'UNVERIFIED',
        'canon_change_authorized': False, 'ledger_apply_authorized': False,
        'author_planning_context': {'content': context,
            'basis': 'WORKING_TREE_METADATA_WITH_EXPLICIT_SOURCE_MODE',
            'warning': ('World cursor has no authenticated scene-time/POV mapping; only the selected plan and style are supplied as author inputs.'
                        if world_cursor is not None else
                        'Target beats and user directives are author inputs, not events or POV knowledge.')},
        'scene_references': {
            'characters': ([{'id': cid} for cid in scene['character_ids']] if world_cursor is not None else
                           [{'id': cid, 'name': novelctl.get(db, 'characters', cid)['name']}
                            for cid in scene['character_ids']]),
            'location': ({'id': location['id'], 'pov_layout_knowledge': 'UNKNOWN'} if world_cursor is not None else
                         {'id': location['id'], 'name': location['name'], 'pov_layout_knowledge': 'UNKNOWN'}),
            'planned_item_ids': list(scene['item_ids']),
            'inventory': {'earlier_local_approved_events': inventory, 'current_balance': 'UNKNOWN',
                          'note': ('Narrative-time inventory withheld because world cursor has no scene mapping.'
                                   if world_cursor is not None else
                                   'No inferred totals, initial stock, zero quantities or planned gains.')},
            'open_threads': {'eligible_registry_references': threads, 'historical_open_state': 'UNKNOWN',
                             'note': ('Narrative-time thread history withheld because world cursor has no scene mapping.'
                                      if world_cursor is not None else
                                      'Untimed, future and unapproved setups withheld; current OPEN is not historical proof.')}},
        'pov_knowledge': {'availability': 'UNKNOWN' if world_cursor is not None else ('LOCAL_EVIDENCE' if knowledge else 'UNKNOWN'),
                          'entries': knowledge, 'untimed_traits': 'WITHHELD',
                          'note': ('No authenticated world-cursor-to-POV mapping; knowledge is withheld. World preview is not POV knowledge.'
                                   if world_cursor is not None else
                                   'House disclosure is separately source-labelled; world preview is not POV knowledge.')},
        'house_reference': house,
        'world_preview': {'audience': 'AUTHOR_ONLY_NOT_POV_KNOWLEDGE', 'result': world},
        'source_evidence': evidence,
        'metadata_evidence': {'basis': 'WORKING_TREE_BYTES', 'files': metadata},
    }
