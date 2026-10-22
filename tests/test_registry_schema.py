"""Draft 2020-12 registry validation with preserved and synthetic metadata."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator, ValidationError
from referencing.exceptions import Unresolvable

from scripts import registry_schema, storyctl


ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / 'stories/last-island'
KINDS = (
    'canon', 'characters', 'locations', 'items', 'sources', 'mechanics',
    'scenes', 'episodes', 'events', 'inventory_ledger', 'threads',
    'relationships', 'decisions', 'story_state',
)


class RegistrySchemaTests(unittest.TestCase):
    @staticmethod
    def example(kind):
        path = EXAMPLE / ('ledger/index.json' if kind == 'ledger' else f'data/{kind}.json')
        return json.loads(path.read_text(encoding='utf-8'))

    def schema_validator(self, kind):
        factory = getattr(registry_schema, 'validator', None)
        if factory is None:
            factory = registry_schema._validator
        return factory(kind)

    def assert_invalid(self, kind, payload, field=None):
        errors = registry_schema.validate(kind, payload)
        self.assertTrue(errors, (kind, payload))
        if field is not None:
            self.assertTrue(any(field in message for message in errors), errors)
        with self.assertRaises(ValueError):
            registry_schema.ensure_valid(kind, payload)

    def test_all_preserved_registries_and_ledger_match_v1_schemas(self):
        for kind in (*KINDS, 'ledger'):
            with self.subTest(kind=kind):
                self.assertEqual(registry_schema.validate(kind, self.example(kind)), [])

    def test_empty_generic_scaffold_matches_core_schemas(self):
        with tempfile.TemporaryDirectory() as temporary:
            story = storyctl.new_story(Path(temporary), 'schema-fixture', 'Schema metadata fixture')
            for path in (story / 'data').glob('*.json'):
                with self.subTest(registry=path.stem):
                    registry_schema.ensure_valid(path.stem, json.loads(path.read_text(encoding='utf-8')))
            registry_schema.ensure_valid('ledger', json.loads(
                (story / 'ledger/index.json').read_text(encoding='utf-8')))

    def test_strict_json_loader_rejects_nonfinite_constants(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'metadata.json'
            for constant in ('NaN', 'Infinity', '-Infinity'):
                with self.subTest(constant=constant):
                    path.write_text('{"value": ' + constant + '}', encoding='utf-8')
                    with self.assertRaisesRegex(ValueError, 'not valid JSON'):
                        registry_schema.read_json(path)
            path.write_text('{"value": null, "unknown": "UNKNOWN"}', encoding='utf-8')
            self.assertEqual(registry_schema.read_json(path), {'value': None, 'unknown': 'UNKNOWN'})

    def test_actual_draft_2020_12_validator_checks_schema_keywords(self):
        validator = self.schema_validator('canon')
        self.assertIsInstance(validator, Draft202012Validator)
        schema = {
            '$schema': 'https://json-schema.org/draft/2020-12/schema',
            'type': 'object',
            'properties': {'mode': {'enum': ['A', 'B']}, 'count': {'type': 'integer'}},
            'required': ['mode'],
            'if': {'properties': {'mode': {'const': 'A'}}},
            'then': {'required': ['count']},
            'else': {'not': {'required': ['count']}},
            'unevaluatedProperties': False,
        }
        checker = validator.evolve(schema=schema)
        checker.check_schema(schema)
        checker.validate({'mode': 'A', 'count': 1})
        checker.validate({'mode': 'B'})
        for invalid in ({'mode': 'A'}, {'mode': 'B', 'count': 1},
                        {'mode': 'A', 'count': True}, {'mode': 'A', 'count': 1, 'extra': 2}):
            with self.subTest(payload=invalid):
                with self.assertRaises(ValidationError):
                    checker.validate(invalid)

    def test_version_is_required_and_rejects_unknown_or_boolean_values(self):
        for kind in (*KINDS, 'ledger'):
            for version in (None, 2, True, '1'):
                with self.subTest(kind=kind, version=version):
                    payload = self.example(kind)
                    if version is None:
                        del payload['schema_version']
                    else:
                        payload['schema_version'] = version
                    self.assert_invalid(kind, payload, 'schema_version')

    def test_registry_envelopes_and_rows_have_expected_container_types(self):
        for kind in KINDS:
            with self.subTest(kind=kind, shape='envelope'):
                self.assert_invalid(kind, [])
            if kind == 'story_state':
                continue
            key = 'facts' if kind == 'canon' else 'entries' if kind == 'inventory_ledger' else kind
            for invalid in ({}, 'rows', None, [None], [[]]):
                with self.subTest(kind=kind, rows=invalid):
                    payload = self.example(kind)
                    payload[key] = invalid
                    self.assert_invalid(kind, payload, key)

    def test_nonempty_string_ids_are_required_before_reference_checks(self):
        for value in (None, '', '   ', [], {}, 10):
            with self.subTest(id=value):
                payload = self.example('scenes')
                payload['scenes'][0]['id'] = value
                self.assert_invalid('scenes', payload, 'id')
        payload = self.example('scenes')
        del payload['scenes'][0]['id']
        self.assert_invalid('scenes', payload, 'id')

    def test_required_operational_scene_fields_and_reference_arrays(self):
        for field in ('episode_id', 'order', 'pov', 'location_id', 'goal', 'conflict', 'outcome'):
            with self.subTest(missing=field):
                payload = self.example('scenes')
                del payload['scenes'][0][field]
                self.assert_invalid('scenes', payload, field)
        for field in ('character_ids', 'item_ids', 'canon_refs', 'requires_flags'):
            for value in ('SC-001', [None], [{}]):
                with self.subTest(field=field, value=value):
                    payload = self.example('scenes')
                    payload['scenes'][0][field] = value
                    self.assert_invalid('scenes', payload, field)

    def test_status_enums_and_scene_order_types_are_enforced(self):
        for kind, key in (('canon', 'facts'), ('scenes', 'scenes'), ('episodes', 'episodes')):
            with self.subTest(kind=kind):
                payload = self.example(kind)
                payload[key][0]['status'] = 'NOT_A_STATUS'
                self.assert_invalid(kind, payload, 'status')
        for order in (0, -1, True, '1', 1.5):
            with self.subTest(order=order):
                payload = self.example('scenes')
                payload['scenes'][0]['order'] = order
                self.assert_invalid('scenes', payload, 'order')

    def test_flags_are_objects_of_booleans(self):
        for value in ([], 'flags', None):
            with self.subTest(container=value):
                payload = self.example('story_state')
                payload['flags'] = value
                self.assert_invalid('story_state', payload, 'flags')
        for value in (1, 'true', None, []):
            with self.subTest(flag=value):
                state = self.example('story_state')
                state['flags']['synthetic_gate'] = value
                self.assert_invalid('story_state', state, 'synthetic_gate')
                scene = self.example('scenes')
                scene['scenes'][0]['effects_flags']['synthetic_gate'] = value
                self.assert_invalid('scenes', scene, 'synthetic_gate')
        state = self.example('story_state')
        state['flags'] = {'synthetic_gate': False}
        self.assertEqual(registry_schema.validate('story_state', state), [])

    def test_unknown_inventory_quantity_remains_null_not_fabricated(self):
        for quantity in (0, -1, True, 'unknown', 1.5):
            with self.subTest(quantity=quantity):
                payload = self.example('inventory_ledger')
                payload['entries'][0]['quantity'] = quantity
                self.assert_invalid('inventory_ledger', payload, 'quantity')
        for quantity in (None, 1):
            with self.subTest(quantity=quantity):
                payload = self.example('inventory_ledger')
                payload['entries'][0]['quantity'] = quantity
                self.assertEqual(registry_schema.validate('inventory_ledger', payload), [])

    def test_nested_knowledge_shape_is_validated_with_useful_location(self):
        payload = self.example('characters')
        payload['characters'][0]['knowledge'][0]['after_scene'] = {'invalid': 'reference'}
        errors = registry_schema.validate('characters', payload)
        self.assertTrue(errors)
        message = '\n'.join(errors)
        for part in ('data/characters.json', 'characters', 'knowledge', 'after_scene', '0'):
            self.assertIn(part, message)
        raw = registry_schema.validation_errors('characters', payload)
        self.assertTrue(raw)
        self.assertTrue(all(isinstance(error, ValidationError) for error in raw))

    def test_approval_timestamp_requires_an_actual_rfc3339_datetime(self):
        # Synthetic local metadata exercises shape only, not authenticated approval.
        payload = {'schema_version': 1, 'episodes': [{
            'id': 'EP-SYNTHETIC', 'scene_ids': ['SC-SYNTHETIC'],
            'summary_path': 'ledger/episodes/EP-SYNTHETIC.md',
            'approval': {'approved_at': '2026-10-22T13:00:00+07:00'},
        }], 'chapters': [], 'books': []}
        self.assertEqual(registry_schema.validate('ledger', payload), [])
        for timestamp in ('not-a-date', '2026-99-99T25:99:00Z',
                          '2026-02-30T13:00:00Z', '2026-10-22T13:00:00'):
            with self.subTest(timestamp=timestamp):
                payload['episodes'][0]['approval']['approved_at'] = timestamp
                self.assert_invalid('ledger', payload, 'approved_at')

    def test_missing_datetime_checker_fails_with_dependency_instructions(self):
        # Optional jsonschema formats must not quietly become no-op validation.
        with patch('jsonschema.FormatChecker.checkers', {}):
            with self.assertRaisesRegex(ValueError, 'pip install -r requirements.txt'):
                registry_schema._dependencies()

    def test_editorial_extra_metadata_is_intentionally_preserved(self):
        payload = self.example('scenes')
        payload['editorial_metadata'] = {'fixture_only': True}
        payload['scenes'][0]['editorial_metadata'] = {'fixture_only': [1, 2]}
        original = copy.deepcopy(payload)
        self.assertEqual(registry_schema.validate('scenes', payload), [])
        self.assertEqual(payload, original)

    def test_schema_selection_cannot_read_arbitrary_paths_or_urls(self):
        for kind in ('missing', '../story', 'http://example.invalid/schema', '/tmp/schema'):
            with self.subTest(kind=kind):
                with self.assertRaises(ValueError):
                    registry_schema.ensure_valid(kind, {})

    def test_unknown_schema_references_fail_without_network_access(self):
        checker = self.schema_validator('canon').evolve(schema={
            '$ref': 'https://schema-test.invalid/unregistered.schema.json',
        })
        with patch('urllib.request.urlopen') as opener, patch('socket.create_connection') as connection:
            with self.assertRaises(Unresolvable):
                checker.validate({})
        opener.assert_not_called()
        connection.assert_not_called()

    def test_invalid_engine_schema_reports_its_file_and_cause(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'schemas'
            shutil.copytree(registry_schema.SCHEMA_ROOT, root)
            path = root / 'canon.schema.json'
            schema = json.loads(path.read_text(encoding='utf-8'))
            schema['type'] = 17
            path.write_text(json.dumps(schema), encoding='utf-8')
            registry_schema.validator.cache_clear()
            registry_schema._schema_resources.cache_clear()
            try:
                with patch.object(registry_schema, 'SCHEMA_ROOT', root):
                    with self.assertRaises(ValueError) as error:
                        registry_schema.validation_errors('canon', {})
                self.assertIn(str(path), str(error.exception))
                self.assertIn('invalid engine schema', str(error.exception))
                self.assertIn('17', str(error.exception))
                self.assertIsNotNone(error.exception.__cause__)
            finally:
                registry_schema.validator.cache_clear()
                registry_schema._schema_resources.cache_clear()

    def test_unresolvable_engine_schema_reference_reports_file_without_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'schemas'
            shutil.copytree(registry_schema.SCHEMA_ROOT, root)
            path = root / 'canon.schema.json'
            schema = json.loads(path.read_text(encoding='utf-8'))
            reference = 'https://schema-test.invalid/unregistered.schema.json'
            schema['$ref'] = reference
            path.write_text(json.dumps(schema), encoding='utf-8')
            registry_schema.validator.cache_clear()
            registry_schema._schema_resources.cache_clear()
            try:
                with patch.object(registry_schema, 'SCHEMA_ROOT', root), \
                        patch('urllib.request.urlopen') as opener, \
                        patch('socket.create_connection') as connection:
                    with self.assertRaises(ValueError) as error:
                        registry_schema.validation_errors('canon', {})
                self.assertIn(str(path), str(error.exception))
                self.assertIn(reference, str(error.exception))
                self.assertIn('cannot be resolved', str(error.exception))
                opener.assert_not_called()
                connection.assert_not_called()
            finally:
                registry_schema.validator.cache_clear()
                registry_schema._schema_resources.cache_clear()


if __name__ == '__main__':
    unittest.main()
