#!/usr/bin/env python3
"""AI Novel Studio v0.1: deterministic continuity checks and scoped context packs.
Uses versioned JSON Schemas; no AI API needed. This tool does not write narrative prose.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from collections import Counter
try:
    from scripts import story_config, registry_schema, state_replay, world_state_model, world_history
except ImportError:
    import story_config
    import registry_schema
    import state_replay
    import world_state_model
    import world_history

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_DATA = ("canon", "characters", "locations", "items", "sources", "mechanics", "scenes", "episodes", "events", "inventory_ledger", "threads", "relationships", "decisions", "story_state")
CORE_DATA = tuple(kind for kind in REQUIRED_DATA if kind not in ('sources', 'mechanics'))


def load(root: Path, validate_schema: bool = True) -> dict:
    root = story_config.resolve_root(root)
    config = story_config.load_config(root)
    kinds = REQUIRED_DATA if config['extensions']['gameplay'] else CORE_DATA
    db = {}
    for kind in kinds:
        path = story_config.story_path(root, f'data/{kind}.json')
        value = registry_schema.read_json(path)
        if validate_schema:
            registry_schema.ensure_valid(kind, value)
        db[kind] = value
    for kind in ('sources', 'mechanics'):
        db.setdefault(kind, {'schema_version': 1, kind: []})
    return db


def rows(db: dict, kind: str):
    key = 'facts' if kind == 'canon' else 'entries' if kind == 'inventory_ledger' else kind
    return db[kind][key]


def ids(db: dict, kind: str) -> set[str]:
    return {record['id'] for record in rows(db, kind)}


def validate(root: Path):
    errors, warnings = [], []
    try:
        root = story_config.resolve_root(root)
        config = story_config.load_config(root)
        db = load(root, validate_schema=False)
        shape_errors = [(kind, error) for kind in REQUIRED_DATA
                        for error in registry_schema.validation_errors(kind, db[kind])]
        if shape_errors:
            for kind in REQUIRED_DATA:
                errors.extend(registry_schema.validate(kind, db[kind]))
            # Existing causal diagnostics can still run when only flag values have
            # wrong types: their explicit boolean guards handle those cases safely.
            def safe_flag_error(kind, error):
                path = list(error.absolute_path)
                return (kind == 'story_state' and path and path[0] == 'flags'
                        and len(path) <= 2) or (
                            kind in ('scenes', 'events') and len(path) == 4
                            and path[0] == kind and path[2] == 'effects_flags')
            if not all(safe_flag_error(kind, error) for kind, error in shape_errors):
                return errors, warnings
    except (OSError, ValueError, KeyError) as exc:
        return [f'Cannot read data JSON: {exc}'], []
    kinds = ('canon', 'characters', 'locations', 'items', 'sources', 'mechanics', 'scenes', 'episodes', 'events', 'inventory_ledger', 'threads', 'relationships', 'decisions')
    index = {}
    for kind in kinds:
        try:
            source = rows(db, kind)
            values = [v['id'] for v in source]
        except (KeyError, TypeError) as exc:
            errors.append(f'{kind}: invalid item structure ({exc})')
            continue
        repeat = [x for x, n in Counter(values).items() if n > 1]
        for duplicate in repeat:
            errors.append(f'{kind}: duplicate id {duplicate}')
        index[kind] = {v['id']: v for v in source}
    if len(index) != len(kinds):
        return errors, warnings
    # Namespaced IDs should be globally unique (across different record kinds too).
    all_ids = [x for k in kinds for x in index[k]]
    for duplicate, count in Counter(all_ids).items():
        if count > 1: errors.append(f'global duplicate ID {duplicate}')
    def require(kind, value, context):
        if value not in index[kind]:
            errors.append(f'{context}: missing {kind} reference {value}')
    for fact in rows(db, 'canon'):
        if fact.get('status') not in ('LOCKED', 'PROPOSED', 'UNKNOWN', 'DISPUTED'):
            errors.append(f"{fact['id']}: unsupported canon status")
        if fact.get('origin') == 'ASSISTANT_PROPOSAL' and fact.get('status') == 'LOCKED':
            errors.append(f"{fact['id']}: an assistant proposal cannot be LOCKED without a user decision")
        if fact.get('source_id'):
            require('sources', fact['source_id'], fact['id'])
        if not str(fact.get('statement', '')).strip():
            errors.append(f"{fact['id']}: empty statement")
    for char in rows(db, 'characters'):
        if char.get('first_scene'):
            require('scenes', char['first_scene'], char['id'])
        for k in char.get('knowledge', []):
            require('scenes', k.get('after_scene'), char['id'] + ' knowledge')
    for item in rows(db, 'items'):
        if config['extensions']['gameplay'] or item.get('gameplay_mechanic_id'):
            require('mechanics', item.get('gameplay_mechanic_id'), item['id'])
    for mechanic in rows(db, 'mechanics'):
        if mechanic.get('game_verification') not in ('TRANSCRIPT_SUPPORTED', 'VISUALLY_VERIFIED', 'UNVERIFIED', 'TITLE_ONLY', 'FICTIONAL_TOURNAMENT'):
            errors.append(f"{mechanic['id']}: unknown verification status")
        if mechanic.get('game_verification') == 'TRANSCRIPT_SUPPORTED' and not mechanic.get('source_ids'):
            errors.append(f"{mechanic['id']}: transcript claim must cite a source")
        for src in mechanic.get('source_ids', []):
            require('sources', src, mechanic['id'])
            if src in index['sources']:
                confidence = index['sources'][src].get('access_level')
                if mechanic.get('game_verification') == 'VISUALLY_VERIFIED' and confidence != 'VIDEO_REVIEWED':
                    errors.append(f"{mechanic['id']}: cannot claim visual verification from source {src} marked {confidence}")
                if mechanic.get('game_verification') == 'TRANSCRIPT_SUPPORTED' and confidence not in ('TRANSCRIPT_ONLY','VIDEO_REVIEWED'):
                    errors.append(f"{mechanic['id']}: cannot claim transcript evidence from source {src} marked {confidence}")
        if mechanic.get('game_verification') == 'UNVERIFIED':
            warnings.append(f"{mechanic['id']} {mechanic.get('title')}: game mechanic unverified (NOT PASS)")
    initial_flags = db['story_state'].get('flags', {})
    if not isinstance(initial_flags, dict):
        errors.append('story_state.flags must be an object of booleans')
        initial_flags = {}
    for flag, value in initial_flags.items():
        if not isinstance(value, bool):
            errors.append(f'story_state.flags.{flag} must be boolean')
    episode_scenes = set()
    for ep in rows(db, 'episodes'):
        scids = ep.get('scene_ids', [])
        if len(scids) != len(set(scids)):
            errors.append(f"{ep['id']}: scene_ids contain duplicates")
        for sid in scids:
            require('scenes', sid, ep['id'])
            if sid in episode_scenes:
                errors.append(f'{sid}: assigned to more than one episode')
            episode_scenes.add(sid)
        if ep.get('status') not in ('OUTLINE', 'DRAFT', 'REVIEW', 'APPROVED', 'CANON'):
            errors.append(f"{ep['id']}: invalid episode status")
        actual = sorted([s for s in rows(db, 'scenes') if s.get('episode_id') == ep['id']], key=lambda s: s['order'])
        if [s['id'] for s in actual] != scids:
            errors.append(f"{ep['id']}: scene_ids mismatch chronological order")
        if sorted(s['order'] for s in actual) != list(range(1, len(actual) + 1)):
            errors.append(f"{ep['id']}: order must be consecutive 1..N")
        flags = dict(initial_flags) if ep['id'] == db['story_state'].get('active_episode') else {}
        for scene in actual:
            if scene['id'] not in episode_scenes:
                errors.append(f"{scene['id']}: orphan scene")
            prerequisite_flags = flags
            if scene.get('requires_flags'):
                # Explicit history is authoritative at this scene's start.
                # Current snapshots and planned effects cannot fill its gaps.
                # With no history, preserve the legacy causal plan simulation.
                try:
                    prior = state_replay.replay_before(root, scene['id'], db)
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    errors.append(f"{scene['id']}: cannot establish causal prerequisites from state history ({exc})")
                    prerequisite_flags = {}
                else:
                    if prior is not None:
                        state = prior.get('state') if prior.get('availability') == 'KNOWN' else None
                        historical_flags = state.get('flags') if isinstance(state, dict) else None
                        if (isinstance(historical_flags, dict)
                                and all(isinstance(value, bool) for value in historical_flags.values())):
                            prerequisite_flags = historical_flags
                        else:
                            errors.append(f"{scene['id']}: causal prerequisites need known historical flags as an object of booleans; "
                                          "missing, UNKNOWN or malformed flags cannot establish them")
                            prerequisite_flags = {}
            for req in scene.get('requires_flags', []):
                if prerequisite_flags.get(req) is not True:
                    errors.append(f"{scene['id']}: needs flag '{req}' before this scene, but it is not established")
            for flag, value in scene.get('effects_flags', {}).items():
                if not isinstance(value, bool):
                    errors.append(f"{scene['id']}: effects_flags.{flag} must be boolean")
                    continue
                if flags.get(flag) is True and value is False:
                    warnings.append(f"{scene['id']}: a previous true flag is reset to false; check continuity")
                flags[flag] = value
            require('characters', scene.get('pov'), scene['id'] + ' POV')
            require('locations', scene.get('location_id'), scene['id'])
            for field, kind in [('character_ids','characters'), ('item_ids','items'),('canon_refs','canon'),('mechanic_refs','mechanics'),('source_refs','sources')]:
                for ref in scene.get(field, []): require(kind, ref, scene['id'])
            for field in ('title','goal','conflict','outcome'):
                if not str(scene.get(field, '')).strip():
                    errors.append(f"{scene['id']}: empty {field}")
            if scene.get('status') not in ('PLANNED','DRAFT','REVIEW','APPROVED','CANON'):
                errors.append(f"{scene['id']}: invalid scene status")
            try:
                path = story_config.story_path(root, scene.get('draft_path', 'INVALID_PATH'))
                if scene.get('status') in ('DRAFT','REVIEW','APPROVED','CANON') and not path.is_file():
                    errors.append(f"{scene['id']}: status {scene['status']} but no draft at {scene.get('draft_path')}")
                card = story_config.story_path(root, f"scenes/{scene['id']}.md")
                if not card.is_file(): errors.append(f'{scene["id"]}: missing scene card {card.relative_to(root)}')
            except ValueError as exc:
                errors.append(f"{scene['id']}: {exc}")
    for scene in rows(db, 'scenes'):
        if scene['id'] not in episode_scenes:
            errors.append(f"{scene['id']}: missing from episode scene_ids")
        require('episodes', scene.get('episode_id'), scene['id'])
    for ev in rows(db, 'events'):
        require('scenes', ev.get('scene_id'), ev['id'])
        require('episodes', ev.get('episode_id'), ev['id'])
        require('locations', ev.get('location_id'), ev['id'])
        for actor in ev.get('actors', []): require('characters', actor, ev['id'])
        matched_scene = index['scenes'].get(ev.get('scene_id'))
        if matched_scene:
            if matched_scene['order'] != ev.get('order') or matched_scene['episode_id'] != ev.get('episode_id'):
                errors.append(f"{ev['id']}: event order or episode mismatch with scene")
            if matched_scene.get('effects_flags') != ev.get('effects_flags'):
                errors.append(f"{ev['id']}: event effects differ from scene effects")
    if Counter(ev['scene_id'] for ev in rows(db, 'events')) != Counter(scene['id'] for scene in rows(db, 'scenes')):
        errors.append('Each scene needs exactly one event summary; event/scene coverage differs')
    # Planned inventory ledger: unknown quantities remain null and never become invented counts.
    for entry in rows(db, 'inventory_ledger'):
        require('scenes', entry.get('scene_id'), entry['id'])
        require('characters', entry.get('owner_id'), entry['id'])
        require('items', entry.get('item_id'), entry['id'])
        qty=entry.get('quantity')
        if qty is not None and (type(qty) is not int or qty < 1):
            errors.append(f"{entry['id']}: quantity must be positive integer or null for unknown")
        if entry.get('operation') not in ('GAIN', 'SPEND', 'CRAFT', 'FIND', 'LOOT', 'LOSE', 'TRANSFER'):
            errors.append(f"{entry['id']}: unknown inventory operation")
        if entry.get('status') not in ('PLANNED','APPROVED'):
            errors.append(f"{entry['id']}: invalid ledger status")
    for t in rows(db,'threads'):
        if t.get('status') not in ('IDEA','OPEN','PLANNED','RESOLVED'):
            errors.append(f"{t['id']}: invalid thread status")
        for field in ('setup_scene_id','payoff_scene_id'):
            if t.get(field): require('scenes',t[field],t['id'])
        if t.get('owner_character_id'):require('characters',t['owner_character_id'],t['id'])
        for f in t.get('canon_refs',[]):require('canon',f,t['id'])
    for rel in rows(db,'relationships'):
        require('characters',rel.get('from_id'),rel['id'])
        require('characters',rel.get('to_id'),rel['id'])
        if rel.get('after_scene'):require('scenes',rel['after_scene'],rel['id'])
    for decision in rows(db,'decisions'):
        if decision.get('status') == 'APPROVED_BY_USER' and decision.get('authority') != 'USER':
            errors.append(f"{decision['id']}: cannot claim user approval without USER authority")
        for f in decision.get('canon_refs',[]):require('canon',f,decision['id'])
    approved = db['story_state'].get('approved_through_scene')
    if approved:
        require('scenes', approved, 'approved_through_scene')
        if approved in index['scenes'] and index['scenes'][approved]['status'] not in ('APPROVED','CANON'):
            errors.append('approved_through_scene points to unapproved scene')
    if db['story_state']['phase'].startswith('OUTLINE') and approved:
        warnings.append('Phase is outline but an approved scene exists; update state phase')
    for src in rows(db,'sources'):
        if src.get('access_level') not in ('TRANSCRIPT_ONLY','VIDEO_REVIEWED','TITLE_AND_METADATA','TITLE_AND_DESCRIPTION'):
            errors.append(f"{src['id']}: invalid source access_level")
    errors.extend(state_replay.validate(root, db))
    errors.extend(world_state_model.validate(root, db))
    errors.extend(world_history.validate(root, db))
    return errors, warnings


def fmt(text): return str(text or 'UNKNOWN')

def get(db, kind, id_):
    return next((x for x in rows(db,kind) if x['id']==id_), None)


def scene_positions(db: dict) -> dict:
    """Series order comes from the episode registry, then scene order, never IDs."""
    episodes = {ep['id']: n for n, ep in enumerate(rows(db, 'episodes'))}
    return {s['id']: (episodes[s['episode_id']], s['order']) for s in rows(db, 'scenes')}


def approved_state_before(db: dict, cutoff: tuple, positions: dict) -> dict:
    """Use a past snapshot as evidence; the registry has no historical snapshots."""
    state = db['story_state']
    marker = state.get('approved_through_scene')
    if marker is None:
        if state.get('phase', '').startswith('OUTLINE') and not any(
                s.get('status') in ('APPROVED', 'CANON') for s in rows(db, 'scenes')):
            return state  # Explicit initial baseline, not progress inferred from plans.
    elif marker in positions and positions[marker] < cutoff:
        if get(db, 'scenes', marker).get('status') in ('APPROVED', 'CANON'):
            return state
    return {
        'availability': 'UNKNOWN',
        'reason': 'No approved state snapshot is available before the requested scene. '
                  'The latest snapshot cannot reconstruct earlier state; do not infer it from planned effects.',
    }


def state_before_target(root: Path, target: str, db: dict | None = None) -> dict:
    """Replay explicit local history, or retain the legacy snapshot/UNKNOWN path."""
    root = story_config.resolve_root(root)
    if db is None:
        errors, _ = validate(root)
        if errors:
            raise ValueError('Cannot replay invalid registry: ' + '; '.join(errors))
        db = load(root)
    replay = state_replay.replay_before(root, target, db)
    if replay is not None:
        return replay
    scene = get(db, 'scenes', target)
    episode = get(db, 'episodes', scene['episode_id'] if scene else target)
    if not episode or not episode.get('scene_ids'):
        raise ValueError(f'Unknown or empty scene/episode: {target}')
    positions = scene_positions(db)
    cutoff = positions[scene['id']] if scene else min(positions[sid] for sid in episode['scene_ids'])
    return approved_state_before(db, cutoff, positions)


def status(root: Path) -> str:
    root = story_config.resolve_root(root)
    db=load(root)
    config = story_config.load_config(root)
    allsc=rows(db,'scenes')
    counts=Counter(s['status'] for s in allsc)
    unknown=[m for m in rows(db,'mechanics') if m['game_verification']=='UNVERIFIED']
    e=rows(db,'episodes')
    return '\n'.join([
      '# AI Novel Studio — สถานะ',
      f"โครงการ: {db['canon']['project']}",
      f"เฟส: {db['story_state']['phase']}",
      f"ตอนที่วางโครงแล้ว: {len(e)} | ฉากทั้งหมด: {len(allsc)}",
      f"ฉาก: PLANNED={counts['PLANNED']} DRAFT={counts['DRAFT']} REVIEW={counts['REVIEW']} APPROVED={counts['APPROVED']} CANON={counts['CANON']}",
      f"ข้อมูล Canon ล็อกแล้ว: {sum(f['status']=='LOCKED' for f in rows(db,'canon'))}",
      *([f"รายละเอียดกลไกเกมที่ยังไม่ยืนยัน: {len(unknown)} (UNKNOWN ≠ PASS)"]
        if config['extensions']['gameplay'] else []),
      f"Plot Threads ยังเปิดอยู่: {sum(t['status'] == 'OPEN' for t in rows(db,'threads'))}",
      f"สถานะหลังฉากที่อนุมัติ: {db['story_state'].get('approved_through_scene') or 'ยังไม่มีฉาก prose ที่อนุมัติ'}",
      'Next: request a brief for an assigned scene ID in this story.',
    ])


def build_brief(root: Path, target: str) -> str:
    root = story_config.resolve_root(root)
    config = story_config.load_config(root)
    db=load(root)
    scene=get(db,'scenes',target)
    ep=get(db,'episodes', scene['episode_id'] if scene else target)
    if not ep: raise ValueError(f'Unknown scene/episode: {target}')
    if scene:
        allsc = sorted([s for s in rows(db,'scenes') if s['episode_id']==ep['id']],key=lambda s:s['order'])
        chosen=[s for s in allsc if abs(s['order']-scene['order'])<=1]
        focus=[scene]
    else:
        chosen=sorted([get(db,'scenes',s) for s in ep['scene_ids']],key=lambda s:s['order'])
        focus=chosen
    if not focus:
        raise ValueError(f'{target}: no scene metadata available for a context pack')
    positions = scene_positions(db)
    cutoff = min(positions[s['id']] for s in focus)
    canon_ids=set(c for s in focus for c in s.get('canon_refs',[]))
    # Core global facts are always required; avoid entire series lore for every scene.
    relevant=[f for f in rows(db,'canon') if f['status']=='LOCKED' and (f['scope']=='GLOBAL' or f['id'] in canon_ids)]
    characters=[get(db,'characters',cid) for cid in sorted({a for s in chosen for a in s['character_ids']})]
    mechanic_ids = sorted({m for s in focus for m in s.get('mechanic_refs',[])})
    if mechanic_ids and not config['extensions']['gameplay']:
        raise ValueError('Mechanic references require the gameplay extension')
    mechanisms=[get(db,'mechanics',mid) for mid in mechanic_ids]
    if any(m is None for m in mechanisms):
        raise ValueError('Unknown mechanic reference in selected scene')
    parts=[f'# CONTEXT PACK: {target}',
           '> Generated from repository data. Do not treat this file as a replacement for approved prose.',
           f'## PROJECT STATUS\n{status(root)}',
           '## NON-NEGOTIABLE AGENT RULES',
           '1. LOCKED user directives override AI proposals. No retroactive changes without approval.',
           '2. Proposed material and planned beats are not approved history.',
           '3. Do not update canon or approved story_state before human review.',
           '4. Preserve scene-start knowledge, inventory and state boundaries; UNKNOWN is not verified.']
    if config['rules']:
        parts.append('## STORY-SPECIFIC RULES')
        parts.extend(f'- {rule}' for rule in config['rules'])
    parts.append('## APPROVED CANON IN SCOPE')
    parts += [f"- **{f['id']}** {f['statement']}" for f in relevant]
    if scene: parts+= [f'## SELECTED SCENE: {scene["id"]}']
    else: parts+= [f'## EPISODE: {ep["id"]} — {ep["title"]}']
    parts.append('## RELEVANT SCENES & CAUSAL ORDER')
    parts.append('Beats and outcomes are scene plans, not knowledge available to the POV at scene start.')
    for s in chosen:
        parts.extend([f"### {s['id']} {s['title']} ({s['status']})",f"Goal: {s['goal']} / Conflict: {s['conflict']}",f"Beats: {'; '.join(s['beats'])}",f"Outcome: {s['outcome']}",f"Preconditions: {', '.join(s['requires_flags']) or 'none'}",f"Effects: {json.dumps(s['effects_flags'],ensure_ascii=False)}"])
    parts.append('## CHARACTERS IN SCOPE')
    for c in characters:
        parts+= [f"- **{c['id']} {c['name']}** — {c['role']}; unknown: {'; '.join(c['unknowns']) or 'none'}"]
        if c['known_traits']:
            parts.append('  - Untimed registry traits withheld: acquisition time is UNKNOWN.')
        known = [k for k in c['knowledge'] if k.get('after_scene') in positions
                 and positions[k['after_scene']] < cutoff]
        for k in known:
            source = get(db, 'scenes', k['after_scene'])
            label = 'approved knowledge' if source['status'] in ('APPROVED', 'CANON') else 'planned knowledge, not approved'
            parts.append(f"  - After {k['after_scene']} ({label}): {k['knows']}")
        if not known:
            parts.append('  - Knowledge at scene start: UNKNOWN (no earlier scene-linked entries).')
    if config['extensions']['gameplay']:
        parts.append('## MECHANIC RESEARCH STATUS (DO NOT OVERSTATE)')
    for m in mechanisms:
        parts.append(f"- {m['id']} {m['title']}: GAMEPLAY={m['game_verification']}; STORY={m['story_requirement']}; sources={','.join(m['source_ids']) or 'NONE'}; {m['notes']}")
    parts.append('## INVENTORY EVENTS IN RELEVANT SCENES (PLANNED ≠ APPROVED)')
    chosen_ids={s['id'] for s in chosen}
    for entry in rows(db,'inventory_ledger'):
        if entry['scene_id'] in chosen_ids:
            parts.append(f"- {entry['scene_id']} {entry['owner_id']} {entry['operation']} {entry['item_id']} x{entry['quantity'] if entry['quantity'] is not None else 'UNKNOWN'} — {entry['notes']}")
    parts.append('## OPEN PLOT THREADS')
    for thread in rows(db,'threads'):
        if thread['status'] == 'OPEN':
            parts.append(f"- {thread['id']} {thread['title']} (do not resolve unless assigned)")
    parts.append('## APPROVED WORLD STATE BEFORE TARGET (INITIAL BASELINE IF NO PROSE APPROVED)')
    parts.append('Only explicit prior local evidence is used. Local approval labels are not authenticated GitHub approval; later progress is not inferred.')
    parts.append(json.dumps(state_before_target(root, target, db),ensure_ascii=False,indent=2))
    parts.append('## OPEN ISSUES')
    parts.extend('- '+str(x) for x in ep.get('questions',[]))
    parts.append('## REQUIRED OUTPUT CONTRACT\n1. Work within the requested scene scope only.\n2. List newly proposed facts, never silently promoted to CANON.\n3. Record proposed state/items/locations and knowledge changes.\n4. Report continuity and evidence uncertainty; human approval remains required.')
    return '\n\n'.join(parts)+'\n'


def handoff(root):
    root = story_config.resolve_root(root)
    db=load(root)
    return '\n'.join(['# AUTO HANDOFF — AI NOVEL STUDIO',status(root),
        f"Story root: {root}; canon registry: data/canon.json; events: data/events.json",
        'Read the selected story configuration, AGENTS.md, approved state, and assigned scene brief before work.',
        f"Active episode: {db['story_state']['active_episode']}",
        'Next: request a brief for the assigned scene in this story; do not assume another story or scene.',
        'Never write to main or claim approval without an explicit editorial decision.',
        'Run `python scripts/novelctl.py check` before PR.'])+'\n'


def main(argv=None):
    parser=argparse.ArgumentParser(description='AI Novel Studio continuity manager (JSON Schema validation)')
    parser.add_argument('--root',type=Path,default=DEFAULT_ROOT)
    parser.add_argument('--story', help='Story slug under --root/stories (otherwise use workspace default)')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('check'); sub.add_parser('status'); sub.add_parser('research')
    brief=sub.add_parser('brief'); brief.add_argument('target'); brief.add_argument('--out',type=Path)
    hand=sub.add_parser('handoff'); hand.add_argument('--out',type=Path)
    args=parser.parse_args(argv)
    try:
        root=story_config.resolve_root(args.root, args.story)
        if args.command=='check':
            errors,warnings=validate(root)
            for w in warnings: print('WARN:',w)
            for e in errors: print('ERROR:',e)
            print(f"{'PASS' if not errors else 'FAIL'} | {len(errors)} errors; {len(warnings)} warnings")
            return 0 if not errors else 1
        if args.command=='status':print(status(root));return 0
        if args.command=='research':
            db=load(root)
            for m in rows(db,'mechanics'):
                print(f"[{m['game_verification']}] {m['id']} {m['title']} — {m['notes']}")
            return 0
        result=build_brief(root,args.target) if args.command=='brief' else handoff(root)
        out=args.out
        if out:
            out.parent.mkdir(parents=True,exist_ok=True)
            out.write_text(result,encoding='utf-8')
            print('Wrote:',out)
        else: print(result)
        return 0
    except (KeyError, ValueError, OSError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
