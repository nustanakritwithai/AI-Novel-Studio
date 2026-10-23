"""Engine-owned version-one registry schemas, validated with JSON Schema 2020-12.

This module validates data structure, not cross-record references, narrative truth,
or authenticated human approval. Editorial extension fields remain permitted by
the registry schemas. All schema references resolve from local engine resources;
validation never retrieves a remote schema or reads a story-supplied schema.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

SCHEMA_ROOT = Path(__file__).resolve().parent.parent / 'schemas' / 'v1'
SCHEMA_BASE = 'https://ai-novel-studio.local/schemas/v1/'
REGISTRY_KINDS = (
    'canon', 'characters', 'locations', 'items', 'sources', 'mechanics',
    'scenes', 'episodes', 'events', 'inventory_ledger', 'threads',
    'relationships', 'decisions', 'story_state',
)
SCHEMA_KINDS = (*REGISTRY_KINDS, 'ledger', 'state_history', 'house_references',
                'scene_delta_claims', 'scene_delta_proposal')


def _dependencies():
    try:
        from jsonschema import Draft202012Validator, FormatChecker
        from referencing import Registry, Resource
        from referencing.exceptions import NoSuchResource
        if 'date-time' not in FormatChecker.checkers:
            raise ImportError('RFC 3339 date-time format checker unavailable')
    except ImportError as exc:
        raise ValueError('JSON Schema dependency unavailable; run python -m pip install -r requirements.txt using the documented PyPI source') from exc
    return Draft202012Validator, FormatChecker, Registry, Resource, NoSuchResource


def read_json(path: Path):
    """Read actual UTF-8 JSON; reject Python's permissive NaN/Infinity extensions."""
    def reject_nonfinite(value):
        raise ValueError(f'{path.name}: non-finite constant {value} is not valid JSON')

    return json.loads(Path(path).read_text(encoding='utf-8'), parse_constant=reject_nonfinite)


@lru_cache(maxsize=1)
def _schema_resources():
    """Check and cache fixed engine schemas once, never story data or state."""
    Draft202012Validator, _, Registry, Resource, NoSuchResource = _dependencies()
    from jsonschema.exceptions import SchemaError
    from referencing.exceptions import CannotDetermineSpecification, Unresolvable

    def refuse_remote(uri):
        raise NoSuchResource(ref=uri)

    registry = Registry(retrieve=refuse_remote)
    schemas = {}
    for path in sorted(SCHEMA_ROOT.glob('*.schema.json')):
        try:
            schema = read_json(path)
            Draft202012Validator.check_schema(schema)
            resource = Resource.from_contents(schema)
            for uri in {path.as_uri(), SCHEMA_BASE + path.name, schema.get('$id', SCHEMA_BASE + path.name)}:
                registry = registry.with_resource(uri, resource)
        except (OSError, ValueError, SchemaError, CannotDetermineSpecification, Unresolvable) as exc:
            cause = exc.message if isinstance(exc, SchemaError) else str(exc)
            raise ValueError(f'{path}: invalid engine schema ({cause})') from exc
        schemas[path.stem.removesuffix('.schema')] = schema
    return schemas, registry


@lru_cache(maxsize=None)
def validator(kind: str):
    """Return a real Draft202012Validator using an offline local reference registry."""
    if kind not in SCHEMA_KINDS:
        raise ValueError(f'Unsupported registry schema: {kind}')
    Draft202012Validator, FormatChecker, _, _, _ = _dependencies()
    schemas, registry = _schema_resources()
    if kind not in schemas:
        raise ValueError(f'Missing engine schema: {kind}.schema.json')
    return Draft202012Validator(schemas[kind], registry=registry, format_checker=FormatChecker())


def validation_errors(kind: str, instance: object) -> list:
    """Expose standard ValidationError objects for callers preserving safe semantic diagnostics."""
    checker = validator(kind)
    from referencing.exceptions import Unresolvable
    try:
        return sorted(checker.iter_errors(instance),
                      key=lambda error: (tuple(str(part) for part in error.absolute_path), error.message))
    except Unresolvable as exc:
        path = SCHEMA_ROOT / f'{kind}.schema.json'
        raise ValueError(f'{path}: engine schema reference cannot be resolved ({exc})') from exc


def _path(error) -> str:
    result = '$'
    for part in error.absolute_path:
        result += f'[{part}]' if isinstance(part, int) else '[' + json.dumps(part, ensure_ascii=False) + ']'
    return result


def validate(kind: str, instance: object) -> list[str]:
    """Return file-qualified JSON paths and all standard schema validation errors."""
    label = 'ledger/index.json' if kind == 'ledger' else f'data/{kind}.json'
    output = []
    for error in validation_errors(kind, instance):
        message = error.message
        path = list(error.absolute_path)
        if kind == 'inventory_ledger' and path and path[-1] == 'quantity':
            message = 'quantity must be positive integer or null for unknown; ' + message
        output.append(f'{label} {_path(error)}: {message}')
    return output


def ensure_valid(kind: str, instance: object) -> None:
    """Fail before unsafe field access when registry structure is invalid."""
    errors = validate(kind, instance)
    if errors:
        raise ValueError('; '.join(errors))
