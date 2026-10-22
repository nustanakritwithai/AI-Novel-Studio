#!/usr/bin/env python3
"""AI Novel Studio v0.1: deterministic continuity checks and scoped context packs.
No external packages and no AI API needed. This tool does not write narrative prose.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from collections import Counter

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_DATA = ("canon", "characters", "locations", "items", "sources", "mechanics", "scenes", "episodes", "events", "inventory_ledger", "threads", "relationships", "decisions", "story_state")


def load(root: Path) -> dict:
    return {kind: json.loads((root / 'data' / f'{kind}.json').read_text(encoding='utf-8')) for kind in REQUIRED_DATA}


def rows(db: dict, kind: str):
    key = 'facts' if kind == 'canon' else 'entries' if kind == 'inventory_ledger' else kind
    return db[kind][key]


def ids(db: dict, kind: str) -> set[str]:
    return {record['id'] for record in rows(db, kind)}


def validate(root: Path):
    errors, warnings = [], []
    try:
        db = load(root)
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
        flags = set(db['story_state'].get('flags', {}).keys()) if ep['id'] == db['story_state'].get('active_episode') else set()
        for scene in actual:
            if scene['id'] not in episode_scenes:
                errors.append(f"{scene['id']}: orphan scene")
            for req in scene.get('requires_flags', []):
                if req not in flags:
                    errors.append(f"{scene['id']}: needs flag '{req}' before this scene, but it is not established")
            for flag, value in scene.get('effects_flags', {}).items():
                if not isinstance(value, bool):
                    errors.append(f"{scene['id']}: effects_flags.{flag} must be boolean")
                if flag in flags and value is False:
                    warnings.append(f"{scene['id']}: a previous true flag is reset to false; check continuity")
                flags.add(flag)
            require('characters', scene.get('pov'), scene['id'] + ' POV')
            require('locations', scene.get('location_id'), scene['id'])
            for field, kind in [('character_ids','characters'), ('item_ids','items'),('canon_refs','canon'),('mechanic_refs','mechanics'),('source_refs','sources')]:
                for ref in scene.get(field, []): require(kind, ref, scene['id'])
            for field in ('title','goal','conflict','outcome'):
                if not str(scene.get(field, '')).strip():
                    errors.append(f"{scene['id']}: empty {field}")
            if scene.get('status') not in ('PLANNED','DRAFT','REVIEW','APPROVED','CANON'):
                errors.append(f"{scene['id']}: invalid scene status")
            path = root / scene.get('draft_path', 'INVALID_PATH')
            if scene.get('status') in ('DRAFT','REVIEW','APPROVED','CANON') and not path.is_file():
                errors.append(f"{scene['id']}: status {scene['status']} but no draft at {scene.get('draft_path')}")
            card = root / 'scenes' / f"{scene['id']}.md"
            if not card.is_file(): errors.append(f'{scene["id"]}: missing scene card {card.relative_to(root)}')
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
    return errors, warnings


def fmt(text): return str(text or 'UNKNOWN')

def get(db, kind, id_):
    return next((x for x in rows(db,kind) if x['id']==id_), None)


def status(root: Path) -> str:
    db=load(root)
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
      f"รายละเอียดกลไกเกมที่ยังไม่ยืนยัน: {len(unknown)} (UNKNOWN ≠ PASS)",
      f"Plot Threads ยังเปิดอยู่: {sum(t['status'] == 'OPEN' for t in rows(db,'threads'))}",
      f"สถานะหลังฉากที่อนุมัติ: {db['story_state'].get('approved_through_scene') or 'ยังไม่มีฉาก prose ที่อนุมัติ'}",
      'คำสั่งถัดไป: python scripts/novelctl.py brief SC-001',
    ])


def build_brief(root: Path, target: str) -> str:
    db=load(root)
    scene=get(db,'scenes',target)
    ep=get(db,'episodes', target if target.startswith('EP-') else (scene['episode_id'] if scene else ''))
    if not ep: raise ValueError(f'Unknown scene/episode: {target}')
    if scene:
        allsc = sorted([s for s in rows(db,'scenes') if s['episode_id']==ep['id']],key=lambda s:s['order'])
        chosen=[s for s in allsc if abs(s['order']-scene['order'])<=1]
        focus=[scene]
    else:
        chosen=sorted([get(db,'scenes',s) for s in ep['scene_ids']],key=lambda s:s['order'])
        focus=chosen
    canon_ids=set(c for s in focus for c in s.get('canon_refs',[]))
    # Core global facts are always required; avoid entire series lore for every scene.
    relevant=[f for f in rows(db,'canon') if f['status']=='LOCKED' and (f['scope']=='GLOBAL' or f['id'] in canon_ids)]
    characters=[get(db,'characters',cid) for cid in sorted({a for s in chosen for a in s['character_ids']})]
    mechanisms=[get(db,'mechanics',mid) for mid in sorted({m for s in focus for m in s['mechanic_refs']})]
    parts=[f'# CONTEXT PACK: {target}',
           '> Generated from repository data. Do not treat this file as a replacement for approved prose.',
           f'## PROJECT STATUS\n{status(root)}',
           '## NON-NEGOTIABLE AGENT RULES',
           '1. LOCKED user directives override AI proposals. No retroactive changes without approval.',
           '2. The world-championship of 100 contestants is FUTURE, never in the private-game opening.',
           '3. Distinguish STORY directive from GAMEPLAY verification; UNVERIFIED ≠ PASS.',
           '4. Write only draft prose. Do not update canon or approved story_state before editor review.',
           '5. Preserve POV knowledge, known inventory, injury ambiguity, 2×2 single story and single scrap crate.',
           '## APPROVED CANON IN SCOPE']
    parts += [f"- **{f['id']}** {f['statement']}" for f in relevant]
    if scene: parts+= [f'## SELECTED SCENE: {scene["id"]}']
    else: parts+= [f'## EPISODE: {ep["id"]} — {ep["title"]}']
    parts.append('## RELEVANT SCENES & CAUSAL ORDER')
    for s in chosen:
        parts.extend([f"### {s['id']} {s['title']} ({s['status']})",f"Goal: {s['goal']} / Conflict: {s['conflict']}",f"Beats: {'; '.join(s['beats'])}",f"Outcome: {s['outcome']}",f"Preconditions: {', '.join(s['requires_flags']) or 'none'}",f"Effects: {json.dumps(s['effects_flags'],ensure_ascii=False)}"])
    parts.append('## CHARACTERS IN SCOPE')
    for c in characters:
        parts+= [f"- **{c['id']} {c['name']}** — {c['role']}; known: {'; '.join(c['known_traits']) or 'none'}; unknown: {'; '.join(c['unknowns']) or 'none'}"]
        for k in c['knowledge']: parts += [f"  - After {k['after_scene']}: knows {k['knows']}"]
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
    parts.append('## CURRENT APPROVED WORLD STATE')
    parts.append(json.dumps(db['story_state'],ensure_ascii=False,indent=2))
    parts.append('## OPEN ISSUES')
    parts.extend('- '+str(x) for x in ep.get('questions',[]))
    parts.append('## REQUIRED OUTPUT FROM WRITER\n1. Draft for the requested scene(s) only.\n2. List of newly proposed facts, not silently promoted to CANON.\n3. Change log for character state/items/locations and knowledge.\n4. Continuity & game-mechanics uncertainty report.')
    return '\n\n'.join(parts)+'\n'


def handoff(root):
    db=load(root)
    return '\n'.join(['# AUTO HANDOFF — AI NOVEL STUDIO',status(root),
        f"Canon registry: data/canon.json; source registry: data/sources.json; events: data/events.json",
        'Read AGENTS.md, STATE.md, PROJECT.md, and a generated scene brief before any writing.',
        f"Active episode: {db['story_state']['active_episode']}",
        'Next: run `python scripts/novelctl.py brief SC-001 --out /tmp/scene-brief.md`, read it, draft only scene SC-001.',
        'Never write to main or claim approval without an explicit editorial decision.',
        'Run `python scripts/novelctl.py check` before PR.'])+'\n'


def main(argv=None):
    parser=argparse.ArgumentParser(description='AI Novel Studio continuity manager (stdlib only)')
    parser.add_argument('--root',type=Path,default=DEFAULT_ROOT)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('check'); sub.add_parser('status'); sub.add_parser('research')
    brief=sub.add_parser('brief'); brief.add_argument('target'); brief.add_argument('--out',type=Path)
    hand=sub.add_parser('handoff'); hand.add_argument('--out',type=Path)
    args=parser.parse_args(argv)
    root=args.root.resolve()
    try:
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
