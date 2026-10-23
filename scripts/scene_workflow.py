"""Bound private native-agent handoffs; never run a model or approve canon.

Stage notes and hashes are bookkeeping, not authenticated identities. The owner
checkpoint always stays UNVERIFIED. Each call returns a new immutable artifact.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

try:
    from scripts import grounded_review, story_config
except ImportError:
    import grounded_review, story_config

STAGES = ('PLANNER', 'WRITER', 'REVIEWER', 'REVISION', 'OWNER_CHECKPOINT')
NEXT = {None: {'PLANNER'}, 'PLANNER': {'WRITER'}, 'WRITER': {'REVIEWER'},
        'REVIEWER': {'REVISION', 'OWNER_CHECKPOINT'}, 'REVISION': {'REVIEWER'},
        'OWNER_CHECKPOINT': set()}
MAX_RECORDS = 32


def digest(value: object) -> str:
    try:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError('Workflow requires bounded finite UTF-8 JSON') from exc
    return hashlib.sha256(raw).hexdigest()


def _without(value: dict, key: str) -> dict:
    return {name: item for name, item in value.items() if name != key}


def _artifact(stage: str, value: object) -> None:
    if not isinstance(value, dict):
        raise ValueError('Stage artifact must be an object')
    keys = {'packet_id', 'draft_sha256', 'notes'}
    if stage == 'REVIEWER':
        keys.add('report')
    if set(value) != keys:
        raise ValueError('Stage artifact has missing or unsupported fields')
    if not isinstance(value['notes'], str) or not value['notes'].strip() or len(value['notes']) > 8000:
        raise ValueError('Stage notes must contain 1..8000 characters')
    for key in ('packet_id', 'draft_sha256'):
        token = value[key]
        if not isinstance(token, str) or len(token) != 64 or any(c not in '0123456789abcdef' for c in token):
            raise ValueError('Stage artifact must bind exact packet and draft hashes')


def verify(flow: dict) -> dict:
    """Verify local chain consistency only; historical inputs are not reread."""
    fields = {'schema_version', 'kind', 'story_slug', 'target', 'records', 'status',
              'owner_gate', 'human_editorial_approval', 'canon_change_authorized',
              'ledger_apply_authorized', 'chain_sha256'}
    if (not isinstance(flow, dict) or set(flow) != fields
            or type(flow['schema_version']) is not int or flow['schema_version'] != 1
            or flow['kind'] != 'SCENE_WORKFLOW' or flow['status'] != 'PROPOSED'
            or flow['owner_gate'] != 'BLOCKED_AUTHENTICATED_SIGNOFF_NOT_ESTABLISHED'
            or flow['human_editorial_approval'] != 'UNVERIFIED'
            or flow['canon_change_authorized'] is not False or flow['ledger_apply_authorized'] is not False):
        raise ValueError('Workflow shape or authority boundary is invalid')
    if flow['chain_sha256'] != digest(_without(flow, 'chain_sha256')):
        raise ValueError('Workflow chain digest is stale')
    if (not isinstance(flow['story_slug'], str) or story_config.validate_slug(flow['story_slug']) != flow['story_slug']
            or not isinstance(flow['target'], dict) or set(flow['target']) != {'scene_id', 'draft_path'}
            or any(not isinstance(v, str) or not v for v in flow['target'].values())):
        raise ValueError('Workflow story/target is invalid')
    records = flow['records']
    if not isinstance(records, list) or not 1 <= len(records) <= MAX_RECORDS:
        raise ValueError('Workflow must contain 1..32 stage records')
    prior_stage = prior_sha = prior_packet = prior_draft = None
    prior_review = None
    for row in records:
        expected = {'stage', 'packet_id', 'draft_sha256', 'context_sha256', 'artifact',
                    'previous_record_sha256', 'record_sha256'}
        if (not isinstance(row, dict) or set(row) != expected
                or not isinstance(row['stage'], str) or row['stage'] not in NEXT[prior_stage]):
            raise ValueError('Workflow stage order is invalid')
        stage = row['stage']
        _artifact(stage, row['artifact'])
        context_sha = row['context_sha256']
        if not isinstance(context_sha, str) or len(context_sha) != 64 or any(c not in '0123456789abcdef' for c in context_sha):
            raise ValueError('Workflow context hash is invalid')
        if (row['record_sha256'] != digest(_without(row, 'record_sha256'))
                or row['previous_record_sha256'] != prior_sha
                or row['packet_id'] != row['artifact']['packet_id']
                or row['draft_sha256'] != row['artifact']['draft_sha256']):
            raise ValueError('Workflow stage hashes or links are inconsistent')
        if stage not in ('PLANNER', 'WRITER', 'REVISION') and row['packet_id'] != prior_packet:
            raise ValueError('New draft/context needs an explicit writer or revision stage')
        if stage == 'REVISION' and row['draft_sha256'] == prior_draft:
            raise ValueError('Revision stage must capture a changed draft')
        if stage == 'REVIEWER':
            report = row['artifact']['report']
            # Historical packets are external immutable inputs; the original
            # report was locator-checked on capture. Here validate the bounded
            # report shape and its hash binding, without claiming a rereview.
            grounded_review._validate_schema('grounded_review_report', report)
            if report['packet_id'] != row['packet_id'] or report['draft_sha256'] != row['draft_sha256']:
                raise ValueError('Historical report is bound to a different draft')
            prior_review = report
        if stage == 'OWNER_CHECKPOINT' and (prior_review is None or any(
                item['classification'] == 'CONTRADICTION' for item in prior_review['findings'])):
            raise ValueError('Known reviewer contradictions require revision and a fresh report')
        prior_stage, prior_sha = stage, row['record_sha256']
        prior_packet, prior_draft = row['packet_id'], row['draft_sha256']
    return {'status': 'CONSISTENT_LOCAL_CHAIN_NOT_APPROVAL', 'last_stage': prior_stage,
            'human_editorial_approval': 'UNVERIFIED', 'historical_source_verification': 'NOT_RUN',
            'canon_change_authorized': False, 'ledger_apply_authorized': False}


def assert_current(root: Path, packet: dict) -> None:
    """Rebuild from current selected inputs, refusing stale context or draft."""
    grounded_review.validate_packet(packet)
    preparation = packet['scene_preparation']['content']
    house = preparation['house_reference']
    fresh = grounded_review.build_packet(root, packet['target']['scene_id'],
        source_mode=packet['context_source_mode'], house_id=house.get('house_id'),
        world_cursor=preparation['world_cursor'])
    if fresh['packet_id'] != packet['packet_id']:
        raise ValueError('Workflow packet is stale; rebuild after any draft/context/HEAD change')


def advance(root: Path, packet: dict, stage: str, artifact: dict, *, previous: dict | None = None) -> dict:
    """Capture one supervised handoff, without executing its instructions."""
    if stage == 'DELTA_PROPOSAL':
        raise ValueError('Human editorial signoff is not authenticated; workflow stops at the owner checkpoint')
    if stage not in STAGES:
        raise ValueError('Unsupported workflow stage')
    grounded_review.validate_packet(packet)
    config = story_config.load_config(story_config.resolve_root(root))
    if packet['story_slug'] != config['slug']:
        raise ValueError('Packet belongs to another story')
    _artifact(stage, artifact)
    if artifact['packet_id'] != packet['packet_id'] or artifact['draft_sha256'] != packet['raw_draft']['sha256']:
        raise ValueError('Stage artifact is stale or belongs to another packet')
    if previous is not None:
        verify(previous)
        if previous['story_slug'] != packet['story_slug'] or previous['target'] != packet['target']:
            raise ValueError('Previous workflow belongs to another story/scene/source')
        records = copy.deepcopy(previous['records'])
    else:
        records = []
    if len(records) >= MAX_RECORDS:
        raise ValueError('Workflow stage limit reached')
    if stage == 'REVIEWER':
        grounded_review.validate_report(packet, artifact['report'])
    assert_current(root, packet)
    row = {'stage': stage, 'packet_id': packet['packet_id'],
           'draft_sha256': packet['raw_draft']['sha256'],
           'context_sha256': packet['scene_preparation']['sha256'],
           'artifact': copy.deepcopy(artifact),
           'previous_record_sha256': records[-1]['record_sha256'] if records else None}
    row['record_sha256'] = digest(row)
    records.append(row)
    result = {'schema_version': 1, 'kind': 'SCENE_WORKFLOW', 'story_slug': packet['story_slug'],
              'target': copy.deepcopy(packet['target']), 'records': records, 'status': 'PROPOSED',
              'owner_gate': 'BLOCKED_AUTHENTICATED_SIGNOFF_NOT_ESTABLISHED',
              'human_editorial_approval': 'UNVERIFIED',
              'canon_change_authorized': False, 'ledger_apply_authorized': False}
    result['chain_sha256'] = digest(result)
    verify(result)
    return result
