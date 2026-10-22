"""Opt-in S1 declarations for positions and holders; no reducer or state queries.

All references use engine-owned local Draft 2020-12 schemas. Records describe
independent, source-bound observations, not deltas. They are never fed into v1
history, packs, knowledge, or approval. Missing facts remain UNKNOWN; successful
validation is structural consistency, never authenticated editorial approval.
"""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

try:
    from scripts import registry_schema, story_config
except ImportError:
    import registry_schema
    import story_config

MODEL_PATH = 'data/world_model.json'
SCHEMA_ROOT = Path(__file__).resolve().parents[1] / 'schemas' / 'world_state'
SCHEMA_BASE = 'https://ai-novel-studio.local/schemas/world_state/'
HUMAN_APPROVAL = 'UNVERIFIED'


@lru_cache(maxsize=1)
def validator():
    """A real validator with a closed local resource registry; no HTTP retrieval."""
    Draft202012Validator, _, Registry, Resource, NoSuchResource = registry_schema._dependencies()

    def refuse_remote(uri):
        raise NoSuchResource(ref=uri)

    registry = Registry(retrieve=refuse_remote)
    schemas = {}
    for name in ('common', 'position', 'holding', 'hierarchy', 'world_model'):
        path = SCHEMA_ROOT / (name + '.schema.json')
        schema = registry_schema.read_json(path)
        Draft202012Validator.check_schema(schema)
        if schema.get('$id') != SCHEMA_BASE + path.name:
            raise ValueError(f'Invalid engine world schema identity: {path.name}')
        registry = registry.with_resource(schema['$id'], Resource.from_contents(schema))
        schemas[name] = schema
    return Draft202012Validator(schemas['world_model'], registry=registry)


def validation_errors(model: object, db: dict, story_slug: str) -> list[str]:
    """Pure model/reference checks against exactly one selected story's catalogs.

    File bytes are checked separately by load(). No ordering, filtering, replay,
    inventory conservation, movement inference or human authentication occurs.
    """
    errors = [f'{MODEL_PATH} {registry_schema._path(error)}: {error.message}'
              for error in sorted(validator().iter_errors(model),
                                  key=lambda error: (tuple(map(str, error.absolute_path)), error.message))]
    if errors:
        return errors
    if model['story_slug'] != story_slug:
        errors.append(f'{MODEL_PATH}: story_slug does not match selected story {story_slug}')
    catalogs = {}
    for kind in ('characters', 'locations', 'items', 'scenes'):
        source = db.get(kind, {}).get(kind)
        if (not isinstance(source, list) or any(not isinstance(row, dict) or not isinstance(row.get('id'), str)
                                                for row in source)):
            errors.append(f'{MODEL_PATH}: invalid selected-story {kind} catalog')
            continue
        catalogs[kind] = {row['id'] for row in source}
        if len(catalogs[kind]) != len(source):
            errors.append(f'{MODEL_PATH}: duplicate selected-story {kind} catalog ID')
    if len(catalogs) != 4:
        return errors

    def ref(kind, value, label):
        if value not in catalogs[kind]:
            errors.append(f'{MODEL_PATH} {label}: missing selected-story {kind} reference {value}')

    policies = {}
    for policy in model['item_policies']:
        item = policy['item_id']
        ref('items', item, 'item_policies')
        if item in policies:
            errors.append(f'{MODEL_PATH}: duplicate item policy {item}')
        policies[item] = policy

    parents = {}
    for node in model.get('hierarchy', []):
        location = node['location_id']
        ref('locations', location, 'hierarchy')
        if location in parents:
            errors.append(f'{MODEL_PATH}: duplicate hierarchy location {location}')
        parent = node['parent']
        parents[location] = parent.get('location_id') if parent['kind'] == 'LOCATION' else None
        if parents[location] is not None:
            ref('locations', parents[location], 'hierarchy parent')
    # Iterative coloring handles long hierarchies without recursion-limit failures.
    visited = set()
    for start in parents:
        path = set()
        current = start
        while current is not None and current in parents and current not in visited:
            if current in path:
                errors.append(f'{MODEL_PATH}: hierarchy cycle at {current}')
                break
            path.add(current)
            current = parents[current]
        visited.update(path)

    record_ids, narrative_keys, world_keys = set(), set(), set()
    records = ([] if model['baseline'] is None else [model['baseline']]) + model['observations']
    for record in records:
        label = record['id']
        if label in record_ids:
            errors.append(f'{MODEL_PATH}: duplicate record ID {label}')
        record_ids.add(label)
        anchor = record['anchor']
        ref('scenes', anchor['scene_id'], label + ' anchor')
        key = (anchor['scene_id'], anchor['narration_suborder'], anchor['boundary'])
        if key in narrative_keys:
            errors.append(f'{MODEL_PATH} {label}: duplicate narrative anchor')
        narrative_keys.add(key)
        clock = anchor['world_time']
        if clock['status'] == 'KNOWN':
            key = (clock['clock_id'], clock['tick'], clock['suborder'], anchor['boundary'])
            if key in world_keys:
                errors.append(f'{MODEL_PATH} {label}: duplicate world anchor; declare an explicit suborder')
            world_keys.add(key)
        positioned = set()
        for position in record['positions']:
            character = position['character_id']
            ref('characters', character, label + ' position')
            if character in positioned:
                errors.append(f'{MODEL_PATH} {label}: duplicate character position {character}')
            positioned.add(character)
            if position['location']['status'] == 'KNOWN':
                ref('locations', position['location']['location_id'], label + ' position')
        unique, held = set(), set()
        for holding in record['holdings']:
            item, holder = holding['item_id'], holding['holder']
            ref('items', item, label + ' holding')
            if holder['kind'] == 'CHARACTER':
                ref('characters', holder['character_id'], label + ' holder')
            elif holder['kind'] == 'LOCATION':
                ref('locations', holder['location_id'], label + ' holder')
            key = (item, holder['kind'], holder.get('character_id'), holder.get('location_id'))
            if key in held:
                errors.append(f'{MODEL_PATH} {label}: duplicate item/holder record {item}')
            held.add(key)
            policy = policies.get(item)
            if policy is None:
                errors.append(f'{MODEL_PATH} {label}: missing item policy {item}')
            elif policy['tracking'] == 'UNIQUE':
                if item in unique:
                    errors.append(f'{MODEL_PATH} {label}: UNIQUE item has multiple holders {item}')
                unique.add(item)
                if holding['quantity'] is not None and holding['quantity'] != 1:
                    errors.append(f'{MODEL_PATH} {label}: UNIQUE item quantity must be 1 or null {item}')
    return errors


def load(root: Path, db: dict | None = None) -> dict | None:
    """Read an enabled model and verify each source's immutable bytes.

    Disabled/missing opt-in never reads a stray model. The returned declarations
    remain local and unverified, including records labeled APPROVED. No catalog
    facts are copied into positions/holdings, and no baseline is synthesized.
    """
    root = story_config.resolve_root(root)
    config = story_config.load_config(root)
    if not config.get('world_state', {}).get('enabled', False):
        return None
    model_path = story_config.story_path(root, MODEL_PATH)
    try:
        model = registry_schema.read_json(model_path)
        if db is None:
            db = {kind: registry_schema.read_json(story_config.story_path(root, f'data/{kind}.json'))
                  for kind in ('characters', 'locations', 'items', 'scenes')}
            for kind, value in db.items():
                registry_schema.ensure_valid(kind, value)
        errors = validation_errors(model, db, config['slug'])
        if errors:
            raise ValueError('; '.join(errors))
        records = ([] if model['baseline'] is None else [model['baseline']]) + model['observations']
        for record in records:
            source = story_config.story_path(root, record['source']['path'])
            if source == model_path:
                raise ValueError(f"{record['id']}: world model cannot be its own source")
            content = source.read_bytes()
            if not content.strip():
                raise ValueError(f"{record['id']}: source evidence is blank")
            if hashlib.sha256(content).hexdigest() != record['source']['sha256']:
                raise ValueError(f"{record['id']}: source SHA256 mismatch; declaration is stale")
        return model
    except (OSError, ValueError) as exc:
        raise ValueError(f'{MODEL_PATH}: cannot validate enabled model ({exc})') from exc


def validate(root: Path, db: dict | None = None) -> list[str]:
    try:
        load(root, db)
        return []
    except (OSError, ValueError) as exc:
        return [str(exc)]
