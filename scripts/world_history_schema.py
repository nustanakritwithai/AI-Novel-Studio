"""Offline Draft 2020-12 validators for S2 world-state history inputs."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

try:
    from scripts import registry_schema
except ImportError:
    import registry_schema

SCHEMA_ROOT = Path(__file__).resolve().parents[1] / 'schemas' / 'world_state'
SCHEMA_BASE = 'https://ai-novel-studio.local/schemas/world_state/'
HISTORY_SCHEMA = 'world_history.schema.json'
SCHEMA_NAMES = ('common', 'position', 'holding', 'hierarchy', 'world_model', 'world_history')


@lru_cache(maxsize=1)
def _schema_resources():
    """Load only fixed engine resources and refuse every unresolved URI."""
    Draft202012Validator, _, Registry, Resource, NoSuchResource = registry_schema._dependencies()
    from jsonschema.exceptions import SchemaError
    from referencing.exceptions import CannotDetermineSpecification, Unresolvable

    def refuse_remote(uri):
        raise NoSuchResource(ref=uri)

    registry = Registry(retrieve=refuse_remote)
    schemas = {}
    for name in SCHEMA_NAMES:
        path = SCHEMA_ROOT / (name + '.schema.json')
        try:
            schema = registry_schema.read_json(path)
            Draft202012Validator.check_schema(schema)
            expected_id = SCHEMA_BASE + path.name
            if schema.get('$id') != expected_id:
                raise ValueError(f'Invalid engine world schema identity: {path.name}')
            resource = Resource.from_contents(schema)
            for uri in (expected_id, path.as_uri()):
                registry = registry.with_resource(uri, resource)
            schemas[name] = schema
        except (OSError, ValueError, SchemaError, CannotDetermineSpecification, Unresolvable) as exc:
            cause = exc.message if isinstance(exc, SchemaError) else str(exc)
            raise ValueError(f'{path}: invalid engine schema ({cause})') from exc
    return Draft202012Validator, schemas, registry


@lru_cache(maxsize=None)
def validator(kind: str = 'history'):
    """Return a real local-resource Draft202012Validator for history or cursor."""
    if kind not in ('history', 'cursor'):
        raise ValueError(f'Unsupported world-history schema: {kind}')
    Draft202012Validator, schemas, registry = _schema_resources()
    if kind == 'history':
        schema = schemas.get('world_history')
        if schema is None:
            raise ValueError('Missing engine world schema: world_history.schema.json')
    else:
        schema = {'$ref': SCHEMA_BASE + HISTORY_SCHEMA + '#/$defs/cursor'}
    return Draft202012Validator(schema, registry=registry)


def _validate(kind: str, instance: object, label: str) -> list[str]:
    checker = validator(kind)
    from referencing.exceptions import Unresolvable

    try:
        errors = sorted(checker.iter_errors(instance),
                        key=lambda error: (tuple(str(part) for part in error.absolute_path), error.message))
    except Unresolvable as exc:
        raise ValueError(f'{SCHEMA_ROOT / HISTORY_SCHEMA}: engine schema reference cannot be resolved ({exc})') from exc
    return [f'{label} {registry_schema._path(error)}: {error.message}' for error in errors]


def validate(history: object) -> list[str]:
    """Return structural errors for a v1 world-history document."""
    return _validate('history', history, 'data/world_history.json')


def validate_cursor(cursor: object) -> list[str]:
    """Return structural errors for one explicit S2 cursor."""
    return _validate('cursor', cursor, 'data/world_history.json cursor')
