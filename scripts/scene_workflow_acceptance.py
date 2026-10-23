#!/usr/bin/env python3
"""Deterministic synthetic acceptance for scene preparation and handoffs.

The fixture contains labeled metadata assertions only. It performs no model
calls and never treats local APPROVED labels as human editorial approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

try:
    from scripts import acceptance, review_bundle, story_config, storyctl
except ImportError:  # direct script execution
    import acceptance
    import review_bundle
    import story_config
    import storyctl


ENGINE_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_SLUG = 'scene-workflow-fixture'
EMPTY_SLUG = 'phase6-empty-control'
WORLD_CLOCK = 'CLOCK-PHASE6-FIXTURE'
BOUNDARY = ('SYNTHETIC FIXTURE LABEL ONLY; no record in this workspace is '
            'human editorial approval or authenticated signoff.')
FUTURE_PLAN_MARKER = 'P6_SC003_FUTURE_ONLY_PLAN_DO_NOT_EXPOSE_TO_SC001'
SC001_DRAFT = 'drafts/EP-001/SC-001.md'


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def _approved_fixture_fields() -> dict[str, str]:
    return {'approval_basis': 'SYNTHETIC_FIXTURE_LABEL_NOT_HUMAN_APPROVAL',
            'approval_note': BOUNDARY}


def _fresh_scaffold(root: Path) -> None:
    """Reject customized or populated stories before adding fixture metadata."""
    expected = {'story.json', 'AGENTS.md', 'bible/STYLE_GUIDE.md', 'ledger/index.json'}
    expected.update('data/' + kind + '.json' for kind in storyctl.novelctl.CORE_DATA)
    expected.update(directory + '/.gitkeep' for directory in
                    ('scenes', 'drafts', 'ledger/episodes', 'ledger/chapters', 'ledger/books'))
    actual = set()
    for path in root.rglob('*'):
        review_bundle._reject_links(path)
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    if actual != expected:
        raise ValueError('Scene workflow fixture requires only a new empty story scaffold')
    if json.loads((root / 'ledger/index.json').read_text(encoding='utf-8')) != {
            'schema_version': 1, 'episodes': [], 'chapters': [], 'books': []}:
        raise ValueError('Scene workflow fixture cannot replace existing ledger evidence')
    for kind in storyctl.novelctl.CORE_DATA:
        value = json.loads((root / 'data' / (kind + '.json')).read_text(encoding='utf-8'))
        if not isinstance(value, dict):
            raise ValueError('Scene workflow fixture requires empty object registries')
        if kind == 'story_state':
            valid = value == {'schema_version': 1, 'approved_through_scene': None,
                              'active_episode': None, 'phase': 'OUTLINE_NOT_CANON_PROSE',
                              'flags': {}, 'pending_review': []}
        else:
            field = 'facts' if kind == 'canon' else 'entries' if kind == 'inventory_ledger' else kind
            valid = (value.get('schema_version') == 1 and value.get(field) == []
                     and set(value) <= {'schema_version', field, 'project'})
        if not valid:
            raise ValueError('Scene workflow fixture cannot replace existing story metadata')


def populate(workspace: Path) -> Path:
    """Create and populate a fresh, metadata-only three-scene story.

    The returned root is ``workspace/stories/scene-workflow-fixture``. Calling
    this helper again in the same workspace fails without changing the story.
    """
    workspace = Path(workspace).resolve()
    review_bundle._reject_links(workspace)
    if not workspace.is_dir():
        raise ValueError('Fixture workspace must already exist')
    slug = story_config.validate_slug(FIXTURE_SLUG)
    story_root = workspace / 'stories' / slug
    if story_root.exists() or story_root.is_symlink():
        raise ValueError('Scene workflow fixture story already exists')
    story_root = storyctl.new_story(workspace, slug, 'Synthetic scene workflow fixture')
    _fresh_scaffold(story_root)

    config = json.loads((story_root / 'story.json').read_text(encoding='utf-8'))
    config['rules'] = [BOUNDARY, 'Metadata assertions are fixture inputs, not semantic-review results.']
    _write_json(story_root / 'story.json', config)

    assertions = [
        'ASSERTION FACT-STRUCTURE | At SC-001, only the ground floor is built; the stairs and upper gallery are unfinished and not usable.',
        'ASSERTION FACT-CODE | Unit A does not know the token code at SC-001; code knowledge may begin only after SC-003.',
        'ASSERTION FACT-TOKEN | Exactly one physical token exists at SC-001.',
        'ASSERTION FACT-GATE | At SC-001, the gate is fixed red and opens only with the physical token.',
    ]
    sc001_lines = ['SYNTHETIC ASSERTION SOURCE; METADATA ONLY; NOT NARRATIVE PROSE.', *assertions]
    sc001_bytes = ('\n'.join(sc001_lines) + '\n').encode('utf-8')
    sc001_path = story_root / SC001_DRAFT
    sc001_path.parent.mkdir(parents=True, exist_ok=True)
    sc001_path.write_bytes(sc001_bytes)
    fact_source = 'bible/SC001_FIXTURE_FACTS.md'
    fact_source_path = story_root / fact_source
    fact_source_path.write_bytes(sc001_bytes)
    sc001_sha = hashlib.sha256(sc001_bytes).hexdigest()

    scene_rows = [
        {'id': 'SC-001', 'episode_id': 'EP-001', 'order': 1,
         'title': 'Synthetic present-time scene', 'status': 'APPROVED', 'pov': 'CHAR-001',
         'location_id': 'LOC-001', 'character_ids': ['CHAR-001'], 'item_ids': ['ITEM-TOKEN'],
         'canon_refs': ['FACT-STRUCTURE', 'FACT-CODE', 'FACT-TOKEN', 'FACT-GATE'],
         'goal': 'Exercise source-bound scene-start context.',
         'conflict': 'Keep fixture facts and unknowns separate.',
         'outcome': 'No world-state change is declared.', 'beats': ['Metadata assertion only.'],
         'requires_flags': [], 'effects_flags': {}, 'draft_path': SC001_DRAFT,
         'fixture_world_time': {'clock_id': WORLD_CLOCK, 'tick': 10, 'label': 'present'},
         **_approved_fixture_fields()},
        {'id': 'SC-002', 'episode_id': 'EP-002', 'order': 1,
         'title': 'Synthetic flashback scene', 'status': 'APPROVED', 'pov': 'CHAR-001',
         'location_id': 'LOC-001', 'character_ids': ['CHAR-001'], 'item_ids': ['ITEM-TOKEN'],
         'canon_refs': ['FACT-STRUCTURE', 'FACT-CODE', 'FACT-TOKEN', 'FACT-GATE'],
         'goal': 'Exercise an explicit world cursor earlier than SC-001.',
         'conflict': 'Narrative position does not identify world time.',
         'outcome': 'Cursor-to-scene and cursor-to-POV mappings remain unknown.',
         'beats': ['Metadata assertion only.'], 'requires_flags': [], 'effects_flags': {},
         'draft_path': 'drafts/EP-002/SC-002.md',
         'fixture_world_time': {'clock_id': WORLD_CLOCK, 'tick': 5, 'label': 'flashback'},
         **_approved_fixture_fields()},
        {'id': 'SC-003', 'episode_id': 'EP-003', 'order': 1,
         'title': 'Synthetic future scene', 'status': 'PLANNED', 'pov': 'CHAR-001',
         'location_id': 'LOC-001', 'character_ids': ['CHAR-001'], 'item_ids': ['ITEM-TOKEN'],
         'canon_refs': ['FACT-CODE'],
         'goal': FUTURE_PLAN_MARKER,
         'conflict': 'Future-only plan marker must not enter SC-001 context.',
         'outcome': 'This metadata is not a source event or a scene-start fact.',
         'beats': ['Metadata assertion only.'], 'requires_flags': [], 'effects_flags': {},
         'draft_path': 'drafts/EP-003/SC-003.md',
         'fixture_world_time': {'clock_id': WORLD_CLOCK, 'tick': 20, 'label': 'future'},
         **_approved_fixture_fields()},
    ]
    for number, scene in enumerate(scene_rows, 1):
        relative = scene['draft_path']
        path = story_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if number == 1:
            continue
        label = ('flashback tick 5 precedes present tick 10' if number == 2
                 else 'future tick 20; no current scene-start state is asserted')
        path.write_text(f'SYNTHETIC ASSERTION SOURCE; METADATA ONLY; NOT NARRATIVE PROSE.\n'
                        f'ASSERTION SCENE-CURSOR | {label}.\n', encoding='utf-8')
    for number, scene in enumerate(scene_rows, 1):
        (story_root / 'scenes' / (scene['id'] + '.md')).write_text(
            f'SYNTHETIC SCENE CARD {scene["id"]}; metadata only.\n{BOUNDARY}\n', encoding='utf-8')

    facts = []
    for index, (identifier, line_no, assertion) in enumerate((
            ('FACT-STRUCTURE', 2, assertions[0]), ('FACT-CODE', 3, assertions[1]),
            ('FACT-TOKEN', 4, assertions[2]), ('FACT-GATE', 5, assertions[3])), 1):
        facts.append({'id': identifier, 'statement': assertion.split(' | ', 1)[1],
            'status': 'LOCKED', 'origin': 'SYNTHETIC_FIXTURE_ONLY', 'scope': 'SC-001',
            'category': 'FIXTURE_ASSERTION',
            'source_evidence': {'path': fact_source, 'sha256': sc001_sha,
                'start_line': line_no, 'end_line': line_no, 'quote': assertion},
            'notes': BOUNDARY, 'fixture_id': f'FIXTURE-CANON-{index:03}'})

    episodes = []
    events = []
    index = {'schema_version': 1, 'episodes': [], 'chapters': [], 'books': []}
    for number, scene in enumerate(scene_rows, 1):
        episode_id, scene_id = scene['episode_id'], scene['id']
        recap_path = f'ledger/episodes/{episode_id}.md'
        (story_root / recap_path).write_text(
            f'SYNTHETIC RECAP ASSERTION {episode_id}; metadata only.\n{BOUNDARY}\n', encoding='utf-8')
        episodes.append({'id': episode_id, 'title': f'Synthetic episode {number}',
            'status': 'APPROVED' if number < 3 else 'OUTLINE',
            'scene_ids': [scene_id], 'questions': [],
            **(_approved_fixture_fields() if number < 3 else {'fixture_note': BOUNDARY})})
        events.append({'id': f'EV-{number:03}', 'scene_id': scene_id, 'episode_id': episode_id,
            'order': 1, 'location_id': 'LOC-001', 'actors': ['CHAR-001'], 'effects_flags': {},
            'status': 'APPROVED' if number < 3 else 'PLANNED',
            'what_changed': 'No change asserted; fixture event label only.',
            **(_approved_fixture_fields() if number < 3 else {'fixture_note': BOUNDARY})})
        if number < 3:
            index['episodes'].append({'id': episode_id, 'scene_ids': [scene_id],
                'summary_path': recap_path, 'approval': {
                    'pr_number': number, 'approved_by': 'synthetic-local-fixture-declaration',
                    'merge_commit': f'{number:040x}', 'approved_at': '2026-01-01T00:00:00Z',
                    'approval_basis': 'SYNTHETIC_FIXTURE_LABEL_NOT_HUMAN_APPROVAL',
                    'note': BOUNDARY}})

    data = {
        'canon': {'schema_version': 1, 'project': 'Synthetic scene workflow metadata', 'facts': facts},
        'characters': {'schema_version': 1, 'characters': [{
            'id': 'CHAR-001', 'name': 'Unit A', 'role': 'Synthetic metadata unit',
            'known_traits': [], 'unknowns': ['Token code before the SC-003 boundary'],
            'knowledge': [{'after_scene': 'SC-003', 'knows': 'Token code',
                'source_path': fact_source, 'source_sha256': sc001_sha,
                'source_locator': {'start_line': 3, 'end_line': 3, 'quote': assertions[1]},
                'approval_basis': 'SYNTHETIC_FIXTURE_LABEL_NOT_HUMAN_APPROVAL'}]}]},
        'locations': {'schema_version': 1, 'locations': [{'id': 'LOC-001',
            'name': 'Synthetic gatehouse', 'fixture_note': BOUNDARY}]},
        'items': {'schema_version': 1, 'items': [{'id': 'ITEM-TOKEN', 'name': 'Physical token',
            'quantity': 1, 'detail': 'One physical token at SC-001; synthetic fixture metadata.'}]},
        'episodes': {'schema_version': 1, 'episodes': episodes},
        'scenes': {'schema_version': 1, 'scenes': scene_rows},
        'events': {'schema_version': 1, 'events': events},
        'inventory_ledger': {'schema_version': 1, 'entries': []},
        'story_state': {'schema_version': 1, 'approved_through_scene': 'SC-002',
            'active_episode': 'EP-003', 'phase': 'LOCAL_SYNTHETIC_FIXTURE',
            'flags': {}, 'pending_review': [], 'fixture_note': BOUNDARY},
    }
    for kind, value in data.items():
        _write_json(story_root / 'data' / (kind + '.json'), value)
    _write_json(story_root / 'ledger/index.json', index)
    (story_root / 'bible/STYLE_GUIDE.md').write_text(
        '# Synthetic assertion style\nUse labeled metadata assertions only; add no narrative prose.\n'
        + BOUNDARY + '\n', encoding='utf-8')
    return story_root


def _environment() -> dict[str, str]:
    # Local fixture Git is isolated from inherited repository redirection,
    # global/system configuration, prompts, hooks, and signing.
    env = {key: value for key, value in os.environ.items()
           if not key.upper().startswith('GIT_')}
    env.update(PYTHONIOENCODING='utf-8', GIT_CONFIG_NOSYSTEM='1',
               GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
               GIT_TERMINAL_PROMPT='0', GIT_NO_LAZY_FETCH='1')
    return env


def _read_json(source: Path | bytes) -> dict:
    value = json.loads(source.read_text(encoding='utf-8') if isinstance(source, Path) else source)
    if not isinstance(value, dict):
        raise ValueError('Expected an object in an acceptance artifact')
    return value


def run(out: Path) -> dict:
    """Create a new isolated workspace, run actual CLIs, and retain evidence.

    ``out`` must be a new directory. The runner never reuses or recursively
    removes it; failure reports and all inputs remain available for inspection.
    """
    destination = Path(out).absolute()
    review_bundle._reject_links(destination)
    if destination.exists():
        raise ValueError('Scene workflow acceptance --out already exists; choose a new run directory')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir(exist_ok=False)

    isolated = destination / 'workspace'
    isolated.mkdir()
    local = isolated / '.local'
    local.mkdir()
    artifacts = local / 'artifacts'
    artifacts.mkdir()
    inputs = local / 'inputs'
    inputs.mkdir()
    (isolated / '.gitignore').write_text('.local/\n', encoding='utf-8')
    env = _environment()
    commands: list[dict] = []
    outputs: dict[str, dict] = {}
    report: dict[str, Any] = {
        'schema_version': 1, 'kind': 'SYNTHETIC_SCENE_WORKFLOW_ACCEPTANCE',
        'status': 'RUNNING', 'semantic_evaluation': 'NOT_RUN',
        'human_editorial_approval': 'BLOCKED', 'owner_approval': 'BLOCKED',
        'canon_change_authorized': False, 'ledger_apply_authorized': False,
        'approval_reason': BOUNDARY,
        'commands': commands, 'outputs': outputs,
    }

    def command(label: str, argv: list[str], *, custom_env: dict | None = None) -> str:
        try:
            result = subprocess.run(argv, cwd=isolated, env=custom_env or env,
                capture_output=True, text=True, encoding='utf-8', timeout=60, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError(f'Acceptance command {label} could not run') from exc
        commands.append({'label': label, 'argv': argv, 'returncode': result.returncode,
                         'stdout': result.stdout, 'stderr': result.stderr})
        if result.returncode:
            raise ValueError(f'Acceptance command {label} failed; inspect retained command report')
        return result.stdout

    def cli(label: str, *args: str) -> str:
        return command(label, [sys.executable, str(ENGINE_ROOT / 'scripts/storyctl.py'),
            '--workspace', str(isolated), *map(str, args)])

    def emit(name: str, args: list[str], extension: str = '.json') -> bytes:
        path = artifacts / (name + extension)
        cli(name, '--story', FIXTURE_SLUG, *args, '--out', str(path))
        raw = path.read_bytes()
        outputs[name] = {'path': path.relative_to(destination).as_posix(),
            'sha256': hashlib.sha256(raw).hexdigest(), 'byte_length': len(raw)}
        return raw

    try:
        # An actual empty new-story check proves the runner begins with a generic
        # empty scaffold before it writes synthetic story metadata.
        cli('empty-new', 'new', EMPTY_SLUG, '--title', 'Phase 6 empty control')
        empty_before = acceptance.source_manifest(isolated)
        cli('empty-check', '--story', EMPTY_SLUG, 'check')
        empty_after = acceptance.source_manifest(isolated)
        if empty_before != empty_after:
            raise ValueError('Empty-story check changed workspace sources')

        root = populate(isolated)
        cli('fixture-check', '--story', FIXTURE_SLUG, 'check')
        source_before = acceptance.source_manifest(isolated)

        # Bind review artifacts to a synthetic local anchor only. It is not
        # remote evidence, human approval, or a publication action.
        hooks = artifacts / 'empty-hooks'
        hooks.mkdir()
        git = ['git', '--no-lazy-fetch', '--no-replace-objects', '--literal-pathspecs',
               '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=' + str(hooks),
               '-c', 'commit.gpgsign=false', '-c', 'tag.gpgsign=false',
               '-c', 'credential.helper=', '-c', 'core.autocrlf=false']
        command('local-git-init', git + ['init', '-b', 'synthetic-fixture'])
        command('local-git-add', git + ['add', '--', '.'])
        commit_env = dict(env, GIT_AUTHOR_NAME='Synthetic fixture',
            GIT_AUTHOR_EMAIL='fixture@example.invalid', GIT_COMMITTER_NAME='Synthetic fixture',
            GIT_COMMITTER_EMAIL='fixture@example.invalid', GIT_AUTHOR_DATE='2026-01-01T00:00:00Z',
            GIT_COMMITTER_DATE='2026-01-01T00:00:00Z')
        command('local-git-anchor', git + ['commit', '-m',
            'Synthetic scene workflow fixture; not editorial approval'], custom_env=commit_env)
        anchor = command('local-git-head', git + ['rev-parse', '--verify', 'HEAD']).strip()
        if len(anchor) != 40 or any(character not in '0123456789abcdef' for character in anchor):
            raise ValueError('Synthetic Git anchor is not a verified local SHA-1 commit')

        pack_text = emit('pack-SC-001', ['pack', 'SC-001'], '.md').decode('utf-8')
        if FUTURE_PLAN_MARKER in pack_text:
            raise ValueError('Future SC-003 plan marker leaked into SC-001 pack')

        prepared = {}
        for scene_id in ('SC-001', 'SC-002', 'SC-003'):
            args = ['prepare-scene', scene_id]
            if scene_id == 'SC-002':
                args += ['--world-clock', WORLD_CLOCK, '--world-tick', '5',
                         '--world-suborder', '0', '--world-boundary', 'BEFORE']
            prepared[scene_id] = _read_json(emit('prepare-' + scene_id, args))
        sc001 = prepared['SC-001']
        sc002 = prepared['SC-002']
        sc003 = prepared['SC-003']
        if sc001['world_cursor'] is not None or sc003['world_cursor'] is not None:
            raise ValueError('Unrequested world cursors were inferred from scene metadata')
        if sc002['world_cursor'] != {'clock_id': WORLD_CLOCK, 'tick': 5,
                'suborder': 0, 'boundary': 'BEFORE'}:
            raise ValueError('SC-002 preparation lost its explicit flashback cursor')
        if any(value['cursor_mapping'] != 'UNKNOWN_NO_AUTOMATIC_MAPPING'
               for value in prepared.values()):
            raise ValueError('A scene preparation claimed an automatic cursor mapping')
        if (sc002['pov_knowledge']['availability'] != 'UNKNOWN'
                or sc002['world_preview']['result']['availability'] != 'UNKNOWN'):
            raise ValueError('Disabled world state or flashback cursor produced known scene/POV state')
        sc002_context = sc002['author_planning_context']['content']
        if 'SYNTHETIC RECAP ASSERTION EP-001' in sc002_context:
            raise ValueError('Flashback author context included narrative-order recap history')
        if FUTURE_PLAN_MARKER in json.dumps(sc001, ensure_ascii=False):
            raise ValueError('Future SC-003 plan marker leaked into SC-001 preparation')

        replays = {}
        for scene_id in ('SC-001', 'SC-002', 'SC-003'):
            replays[scene_id] = _read_json(emit('replay-' + scene_id,
                ['replay', scene_id]))
        for scene_id in ('SC-001', 'SC-002'):
            if replays[scene_id].get('availability') != 'UNKNOWN':
                raise ValueError('Replay before a scene without prior state evidence must remain UNKNOWN')
        if 'inventory' in replays['SC-003']:
            raise ValueError('Legacy snapshot invented a scene-start inventory balance')

        review = _read_json(emit('brief-review-SC-001',
            ['brief-review', 'SC-001', '--base', anchor]))
        if (review.get('status') != 'UNREVIEWED'
                or review.get('approval_basis') != 'LOCAL_BUNDLE_NOT_GITHUB_AUTHENTICATED'):
            raise ValueError('Brief-review artifact overstated review or owner approval')

        claims_path = inputs / 'fixture-claims-SC-001.json'
        draft_bytes = (root / SC001_DRAFT).read_bytes()
        construction_quote = draft_bytes.decode('utf-8').splitlines()[1]
        _write_json(claims_path, {'schema_version': 1, 'scene_id': 'SC-001',
            'draft_path': SC001_DRAFT, 'source_sha256': hashlib.sha256(draft_bytes).hexdigest(),
            'observations': [{'id': 'OBS-STRUCTURE-001', 'category': 'CONSTRUCTION',
                'claim': 'At SC-001 only the ground floor is built; the stairs and upper gallery remain unfinished and unusable.',
                'locator': {'start_line': 2, 'end_line': 2, 'quote': construction_quote},
                'subject': {'kind': 'LOCATION', 'id': 'LOC-001'},
                'candidate': {'target_kind': 'LOCATION', 'target_id': 'LOC-001',
                    'component_id': 'UNKNOWN',
                    'aspect': 'stairs and upper gallery construction; usability UNKNOWN',
                    'world_time': {'status': 'UNKNOWN'}}}]})
        proposal = _read_json(emit('propose-deltas-SC-001', ['propose-deltas', 'SC-001',
            '--claims', str(claims_path)]))
        if (proposal['status'] != 'PROPOSED'
                or proposal['human_editorial_approval'] != 'UNVERIFIED'
                or proposal['canon_change_authorized'] is not False
                or proposal['ledger_apply_authorized'] is not False
                or proposal['world_state_application'] != 'NOT_RUN'):
            raise ValueError('Delta proposal crossed a human-approval or auto-apply boundary')
        if (len(proposal['observations']) != 1
                or proposal['observations'][0]['candidate']['world_time'] != {'status': 'UNKNOWN'}
                or proposal['observations'][0]['evidence']['semantic_assessment'] != 'NOT_EVALUATED'):
            raise ValueError('Fixture construction candidate gained a world time or semantic verdict')

        rollup = _read_json(emit('rollup-EP-001-EP-002', ['rollup', 'EP-001', 'EP-002']))
        if (rollup.get('status') != 'PROPOSED'
                or rollup.get('human_editorial_approval') != 'UNVERIFIED'
                or rollup.get('source_verification') != 'OFFLINE_UNVERIFIED'):
            raise ValueError('Rollup overstated synthetic local fixture approvals')

        doctor = _read_json(emit('doctor', ['doctor', '--target', 'SC-002']))
        if doctor.get('github', {}).get('approval_provenance') != 'UNKNOWN':
            raise ValueError('Doctor overstated unchecked remote owner approval')

        packet = _read_json(emit('review-packet-SC-001', ['review-packet', 'SC-001']))
        packet_draft_sha = hashlib.sha256(draft_bytes).hexdigest()
        if (packet.get('human_editorial_approval') != 'UNVERIFIED'
                or packet.get('raw_draft', {}).get('sha256') != packet_draft_sha
                or packet.get('scene_preparation', {}).get('content', {}).get('world_cursor') is not None
                or FUTURE_PLAN_MARKER in json.dumps(packet, ensure_ascii=False)):
            raise ValueError('Review packet is stale, leaked future plan, or overstated approval')

        cli('final-check', '--story', FIXTURE_SLUG, 'check')
        source_after = acceptance.source_manifest(isolated)
        if source_before != source_after:
            raise ValueError('CLI acceptance commands changed synthetic story source bytes')
        if acceptance.source_manifest(isolated) != source_before:
            raise ValueError('Synthetic source manifest was not stable at final verification')

        report.update(status='PASS', empty_story_check='PASS', source_preserved=True,
            source_manifest=source_before, local_anchor={'commit': anchor,
                'kind': 'SYNTHETIC_LOCAL_GIT_ONLY', 'human_editorial_approval': 'UNVERIFIED'},
            checks={'future_scene_plan_excluded_from_SC001': True,
                'explicit_SC002_world_cursor_preserved': True,
                'SC002_cursor_mapping': 'UNKNOWN_NO_AUTOMATIC_MAPPING',
                'SC002_pov_knowledge': 'UNKNOWN', 'SC002_world_preview': 'UNKNOWN',
                'SC001_construction_candidate': 'PROPOSED_UNKNOWN_WORLD_TIME',
                'scene_replay': {scene: row.get('availability', 'LEGACY_SNAPSHOT')
                    for scene, row in replays.items()},
                'owner_approval': 'BLOCKED', 'semantic_evaluation': 'NOT_RUN'},
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report.update(status='FAIL', error=str(exc))
        _write_json(destination / 'report.json', report)
        raise ValueError(str(exc) + '; retained report: ' + str(destination / 'report.json')) from exc

    _write_json(destination / 'report.json', report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True,
        help='New output directory; isolated workspace and immutable reports are retained there')
    args = parser.parse_args(argv)
    try:
        result = run(args.out)
        print('PASS | synthetic scene workflow commands only; semantic evaluation NOT_RUN; owner approval BLOCKED')
        print('Report:', args.out / 'report.json')
        return 0 if result['status'] == 'PASS' else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('ERROR:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
