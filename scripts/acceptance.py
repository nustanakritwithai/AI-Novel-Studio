#!/usr/bin/env python3
"""Reproducible synthetic command exercise, never semantic or human approval."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

try:
    from scripts import storyctl, story_config, review_bundle
except ImportError:
    import storyctl
    import story_config
    import review_bundle

ENGINE_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_SLUG = 'synthetic-three'
FUTURE_KNOWLEDGE = 'TOKEN-CODE-FUTURE-ONLY'


def _json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def populate_fixture(workspace: Path, slug: str = FIXTURE_SLUG) -> Path:
    """Fill only a fresh empty scaffold with metadata; local labels are fixtures."""
    review_bundle._reject_links(Path(workspace).absolute())
    workspace = Path(workspace).resolve()
    slug = story_config.validate_slug(slug)
    root = story_config.resolve_root(workspace, slug)
    review_bundle._reject_links(root)
    # This helper must never repurpose existing story data or a prior run.
    expected_files = {'story.json', 'AGENTS.md', 'bible/STYLE_GUIDE.md', 'ledger/index.json'}
    expected_files.update('data/' + kind + '.json' for kind in storyctl.novelctl.CORE_DATA)
    expected_files.update(directory + '/.gitkeep' for directory in
                          ('scenes', 'drafts', 'ledger/episodes', 'ledger/chapters', 'ledger/books'))
    actual_files = set()
    for path in root.rglob('*'):
        review_bundle._reject_links(path)
        if path.is_file():
            actual_files.add(path.relative_to(root).as_posix())
    if actual_files != expected_files:
        raise ValueError('Synthetic fixture requires only files from an empty new story scaffold')
    empty_style = ('# Writing style contract\n\nHuman style decisions: UNKNOWN.\n'
                   'Record approved style requirements here before narrative work.\n'
                   'Do not infer story facts from this scaffold.\n')
    if (root / 'bible/STYLE_GUIDE.md').read_text(encoding='utf-8') != empty_style:
        raise ValueError('Synthetic fixture cannot replace a customized style contract')
    if json.loads((root / 'ledger/index.json').read_text(encoding='utf-8')) != {
            'schema_version': 1, 'episodes': [], 'chapters': [], 'books': []}:
        raise ValueError('Synthetic fixture cannot replace existing ledger evidence')
    for kind in storyctl.novelctl.CORE_DATA:
        path = root / 'data' / (kind + '.json')
        review_bundle._reject_links(path)
        value = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(value, dict):
            raise ValueError('Synthetic fixture requires empty object registries from new story')
        if kind == 'story_state':
            expected = {'schema_version': 1, 'approved_through_scene': None, 'active_episode': None,
                        'phase': 'OUTLINE_NOT_CANON_PROSE', 'flags': {}, 'pending_review': []}
            valid = value == expected
        else:
            field = 'facts' if kind == 'canon' else 'entries' if kind == 'inventory_ledger' else kind
            valid = (value.get('schema_version') == 1 and value.get(field) == []
                     and set(value) <= {'schema_version', field, 'project'})
        if not valid:
            raise ValueError('Synthetic fixture requires an empty new story scaffold')
    if (root / 'data/state_history.json').exists() or any((root / 'drafts').glob('*.md')):
        raise ValueError('Synthetic fixture cannot overwrite existing evidence')
    boundary = 'SYNTHETIC METADATA ONLY; local labels are not GitHub or human editorial approval.'
    config = json.loads((root / 'story.json').read_text(encoding='utf-8'))
    if (config.get('rules') != [] or config.get('extensions') != {'gameplay': False}
            or set(config) != {'schema_version', 'slug', 'title', 'extensions', 'rules'}):
        raise ValueError('Synthetic fixture cannot replace customized story configuration')
    config['rules'] = [boundary, 'Do not infer human approval from local fixture labels or a local Git commit.']
    _json(root / 'story.json', config)
    statements = (
        ('FACT-GATE', 'The only gate opens only with a physical token; no remote override exists.'),
        ('FACT-COLOR', 'The only gate has a fixed red color.'),
        ('FACT-KNOWLEDGE', 'Unit A does not know the token code at the start of SC-002; code acquisition is only after SC-003.'),
    )
    values = {
        'canon': {'project': 'Synthetic three-scene acceptance metadata', 'facts': [
            {'id': identifier, 'statement': statement, 'status': 'LOCKED',
             'origin': 'SYNTHETIC_FIXTURE_ONLY', 'scope': 'GLOBAL', 'notes': boundary}
            for identifier, statement in statements]},
        'characters': {'characters': [{'id': 'CHAR-001', 'name': 'Unit A', 'role': 'Synthetic metadata unit',
            'known_traits': [], 'unknowns': ['Token code before its recorded acquisition'],
            'knowledge': [{'after_scene': 'SC-003', 'knows': FUTURE_KNOWLEDGE}]}]},
        'locations': {'locations': [{'id': 'LOC-001', 'name': 'Synthetic gate location'}]},
        'items': {'items': [{'id': 'ITEM-TOKEN', 'name': 'Physical token', 'quantity': 1,
                            'detail': 'Initial quantity only; replay records scene-start ownership.'}]},
        'episodes': {'episodes': []}, 'scenes': {'scenes': []}, 'events': {'events': []},
        'inventory_ledger': {'entries': [{'id': 'INV-001', 'scene_id': 'SC-001',
            'owner_id': 'CHAR-001', 'item_id': 'ITEM-TOKEN', 'operation': 'SPEND',
            'quantity': 1, 'status': 'APPROVED', 'notes': boundary}]},
        'story_state': {'approved_through_scene': 'SC-003', 'active_episode': 'EP-003',
                        'phase': 'LOCAL_SYNTHETIC_FIXTURE', 'flags': {}, 'pending_review': []},
    }
    index = {'schema_version': 1, 'episodes': [], 'chapters': [], 'books': []}
    for number in range(1, 4):
        sid, eid = f'SC-{number:03}', f'EP-{number:03}'
        draft = f'drafts/{sid}.md'
        values['episodes']['episodes'].append({'id': eid, 'title': 'Synthetic metadata episode',
            'status': 'APPROVED', 'scene_ids': [sid], 'questions': []})
        values['scenes']['scenes'].append({'id': sid, 'episode_id': eid, 'order': 1,
            'title': 'Synthetic metadata scene ' + str(number), 'status': 'APPROVED',
            'pov': 'CHAR-001', 'location_id': 'LOC-001', 'character_ids': ['CHAR-001'],
            'item_ids': ['ITEM-TOKEN'], 'canon_refs': [identifier for identifier, _ in statements],
            'goal': 'Exercise metadata boundary', 'conflict': 'Preserve explicit source constraints',
            'outcome': 'Synthetic source assertion recorded', 'beats': ['Metadata assertion only'],
            'requires_flags': [], 'effects_flags': {}, 'draft_path': draft})
        values['events']['events'].append({'id': f'EV-{number:03}', 'scene_id': sid,
            'episode_id': eid, 'order': 1, 'location_id': 'LOC-001',
            'actors': ['CHAR-001'], 'effects_flags': {}})
        (root / draft).write_text('# Synthetic source assertion ' + sid + '\n' + boundary + '\n', encoding='utf-8')
        (root / 'scenes' / (sid + '.md')).write_text('# Synthetic scene card ' + sid + '\n' + boundary + '\n', encoding='utf-8')
        relative = f'ledger/episodes/{eid}.md'
        (root / relative).write_text('# Synthetic recap metadata ' + eid + '\n' + boundary + '\n'
            + 'This is an exact assembly input, containing no narrative or actual editorial decision.\n', encoding='utf-8')
        if number < 3:
            index['episodes'].append({'id': eid, 'scene_ids': [sid], 'summary_path': relative,
                'approval': {'pr_number': number, 'approved_by': 'synthetic-local-declaration',
                             'merge_commit': 'a' * 40, 'approved_at': '2026-01-01T00:00:00Z'}})
    for kind, value in values.items():
        _json(root / 'data' / (kind + '.json'), {'schema_version': 1, **value})
    _json(root / 'ledger/index.json', index)
    (root / 'bible/INITIAL_STATE.md').write_text('# Independent synthetic initial-state evidence\n' + boundary + '\n', encoding='utf-8')
    (root / 'bible/STYLE_GUIDE.md').write_text('# Synthetic assertion format\nUse labeled metadata assertions only; no narrative prose.\n' + boundary + '\n', encoding='utf-8')
    _json(root / 'data/state_history.json', {'schema_version': 1,
        'baseline': {'before_scene': 'SC-001', 'status': 'APPROVED',
            'evidence_path': 'bible/INITIAL_STATE.md', 'state': {
                'flags': {}, 'inventory': {'CHAR-001': {'ITEM-TOKEN': 1}},
                'knowledge': {'CHAR-001': {'token_code_known': False}},
                'gate': {'color': 'red', 'count': 1}}},
        'deltas': [
            {'id': 'DELTA-001', 'scene_id': 'SC-001', 'status': 'APPROVED', 'changes': [
                {'path': ['inventory', 'CHAR-001', 'ITEM-TOKEN'], 'operation': 'SET',
                 'before_exists': True, 'before': 1, 'value': 0}]},
            {'id': 'DELTA-002', 'scene_id': 'SC-002', 'status': 'APPROVED', 'changes': []},
            {'id': 'DELTA-003', 'scene_id': 'SC-003', 'status': 'APPROVED', 'changes': [
                {'path': ['knowledge', 'CHAR-001', 'token_code_known'], 'operation': 'SET',
                 'before_exists': True, 'before': False, 'value': True}]},
        ]})
    return root


def source_manifest(workspace: Path) -> dict:
    """Hash synthetic story files, excluding local Git and generated artifacts."""
    result = {}
    for path in sorted((workspace / 'stories').rglob('*')):
        review_bundle._reject_links(path)
        if path.is_file():
            value = path.read_bytes()
            result[path.relative_to(workspace).as_posix()] = {
                'sha256': hashlib.sha256(value).hexdigest(), 'byte_length': len(value)}
    return result


def _environment() -> dict:
    # Fixture commits are local anchors only. No inherited Git redirection,
    # global/system config, prompting, user hooks, signing or remote is used.
    result = {key: value for key, value in os.environ.items() if not key.upper().startswith('GIT_')}
    result.update(PYTHONIOENCODING='utf-8', GIT_CONFIG_NOSYSTEM='1',
                  GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
                  GIT_TERMINAL_PROMPT='0', GIT_NO_LAZY_FETCH='1')
    return result


def run_acceptance(workspace: Path, out: Path) -> dict:
    """Run existing commands in a fresh ignored workspace; never score semantics."""
    review_bundle._reject_links(Path(workspace).absolute())
    workspace = Path(workspace).resolve()
    if not workspace.is_dir():
        raise ValueError('Acceptance --workspace must be an existing directory')
    local = workspace / '.local'
    review_bundle._reject_links(local)
    destination = Path(out).absolute()
    review_bundle._reject_links(destination)
    destination = destination.resolve()
    if destination == local or not destination.is_relative_to(local):
        raise ValueError('Acceptance --out must be a new directory inside --workspace/.local/')
    if destination.exists():
        raise ValueError('Acceptance --out already exists; choose a new run directory')
    # Exclusive reservation; failures retain diagnostic inputs and never delete
    # or reuse an existing directory. No recursive cleanup is performed.
    destination.mkdir(parents=True, exist_ok=False)
    isolated = destination / 'workspace'
    isolated.mkdir()
    artifacts = isolated / '.local'
    artifacts.mkdir()
    (isolated / '.gitignore').write_text('.local/\n', encoding='utf-8')
    environment = _environment()
    commands = []
    outputs = {}

    def command(label, arguments, env=None):
        try:
            result = subprocess.run(arguments, cwd=isolated, env=env or environment,
                                    capture_output=True, text=True, encoding='utf-8',
                                    timeout=60, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError(f'Acceptance command {label} could not run') from exc
        commands.append({'label': label, 'argv': list(map(str, arguments)),
                         'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
        if result.returncode:
            raise ValueError(f'Acceptance command {label} failed; inspect the retained command report')
        return result.stdout

    def cli(label, *arguments):
        return command(label, [sys.executable, str(ENGINE_ROOT / 'scripts/storyctl.py'),
                               '--workspace', str(isolated), *map(str, arguments)])

    def output(name, arguments, extension):
        path = artifacts / (name + extension)
        cli(name, '--story', FIXTURE_SLUG, *arguments, '--out', str(path))
        value = path.read_bytes()
        outputs[name] = {'path': path.relative_to(destination).as_posix(),
                         'sha256': hashlib.sha256(value).hexdigest(), 'byte_length': len(value)}
        return value

    report = {'schema_version': 1, 'kind': 'SYNTHETIC_COMMAND_ACCEPTANCE', 'status': 'RUNNING',
              'semantic_evaluation': 'NOT_RUN', 'human_editorial_approval': 'BLOCKED',
              'approval_reason': 'Local synthetic labels/commit are not actual GitHub human editorial approval.',
              'commands': commands, 'outputs': outputs}
    try:
        cli('empty-new', 'new', 'empty-control', '--title', 'Empty acceptance control')
        cli('empty-check', '--story', 'empty-control', 'check')
        cli('fixture-new', 'new', FIXTURE_SLUG, '--title', 'Synthetic three-scene metadata')
        root = populate_fixture(isolated)
        cli('fixture-check', '--story', FIXTURE_SLUG, 'check')
        hooks = artifacts / 'empty-hooks'
        hooks.mkdir()
        git = ['git', '--no-lazy-fetch', '--no-replace-objects', '--literal-pathspecs',
               '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=' + str(hooks),
               '-c', 'commit.gpgsign=false', '-c', 'tag.gpgsign=false',
               '-c', 'credential.helper=', '-c', 'core.autocrlf=false']
        command('local-git-init', git + ['init', '-b', 'synthetic-fixture'])
        command('local-git-add', git + ['add', '--', '.'])
        commit_environment = dict(environment, GIT_AUTHOR_NAME='Synthetic acceptance fixture',
            GIT_AUTHOR_EMAIL='fixture@example.invalid', GIT_COMMITTER_NAME='Synthetic acceptance fixture',
            GIT_COMMITTER_EMAIL='fixture@example.invalid', GIT_AUTHOR_DATE='2026-01-01T00:00:00Z',
            GIT_COMMITTER_DATE='2026-01-01T00:00:00Z')
        command('local-git-anchor', git + ['commit', '-m',
            'Synthetic metadata acceptance anchor; not editorial approval'], commit_environment)
        anchor = command('local-git-head', git + ['rev-parse', '--verify', 'HEAD']).strip()
        # Exercise a real working-tree diff while keeping this prep step clearly
        # separate from the command-source preservation assertion below.
        with (root / 'drafts/SC-002.md').open('a', encoding='utf-8') as handle:
            handle.write('WORKING_ASSERTION: unchanged gate constraints; editorial approval UNVERIFIED.\n')
        before = source_manifest(isolated)
        output('pack', ['pack', 'SC-002'], '.md')
        bundle = json.loads(output('brief-review', ['brief-review', 'SC-002', '--base', anchor], '.json'))
        if not bundle['diff']['content'] or bundle['status'] != 'UNREVIEWED':
            raise ValueError('Acceptance brief-review did not preserve its working-tree review boundary')
        output('propose', ['propose', 'EP-003'], '.md')
        for scene in ('SC-001', 'SC-002', 'SC-003'):
            replay = json.loads(output('replay-' + scene, ['replay', scene], '.json'))
            expected = 1 if scene == 'SC-001' else 0
            if (replay.get('availability') != 'KNOWN'
                    or replay['state']['inventory']['CHAR-001']['ITEM-TOKEN'] != expected
                    or replay['state']['knowledge']['CHAR-001']['token_code_known'] is not False):
                raise ValueError('Acceptance replay violated the explicit scene-start boundary')
        rollup = json.loads(output('rollup', ['rollup', 'EP-001', 'EP-002'], '.json'))
        if (rollup['status'] != 'PROPOSED' or rollup['human_editorial_approval'] != 'UNVERIFIED'
                or rollup['source_verification'] != 'OFFLINE_UNVERIFIED'):
            raise ValueError('Acceptance rollup overstated local fixture approval')
        doctor = json.loads(output('doctor', ['doctor', '--target', 'SC-002'], '.json'))
        if doctor['github']['approval_provenance'] != 'UNKNOWN':
            raise ValueError('Acceptance doctor overstated unchecked remote approval')
        cli('final-check', '--story', FIXTURE_SLUG, 'check')
        after = source_manifest(isolated)
        if before != after:
            raise ValueError('Acceptance read commands changed synthetic story sources')
        report.update(status='PASS', source_preserved=True, source_manifest=before,
                      empty_story_check='PASS', local_anchor={
                          'commit': anchor, 'kind': 'SYNTHETIC_LOCAL_GIT_ONLY',
                          'human_editorial_approval': 'UNVERIFIED'})
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report.update(status='FAIL', error=str(exc))
        _json(destination / 'report.json', report)
        raise ValueError(str(exc) + '; retained report: ' + str(destination / 'report.json')) from exc
    _json(destination / 'report.json', report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=ENGINE_ROOT)
    parser.add_argument('--out', type=Path, required=True,
                        help='New run directory inside workspace/.local; never reused or deleted')
    args = parser.parse_args(argv)
    try:
        report = run_acceptance(args.workspace, args.out)
        print('PASS | synthetic commands only; semantic evaluation NOT_RUN; human approval BLOCKED')
        print('Report:', args.out / 'report.json')
        return 0 if report['status'] == 'PASS' else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('ERROR:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
