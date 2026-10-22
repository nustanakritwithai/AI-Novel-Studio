import importlib.util
import tempfile
import unittest
import json
import shutil
from pathlib import Path

ENGINE_ROOT=Path(__file__).resolve().parents[1]
ROOT=ENGINE_ROOT/'stories'/'last-island'
spec=importlib.util.spec_from_file_location('novelctl', ENGINE_ROOT/'scripts/novelctl.py')
novelctl=importlib.util.module_from_spec(spec);spec.loader.exec_module(novelctl)

class NovelctlTest(unittest.TestCase):
    def test_repository_has_no_continuity_errors(self):
        errors,warnings=novelctl.validate(ROOT)
        self.assertEqual(errors,[])
        self.assertTrue(any('UNVERIFIED' in w or 'unverified' in w for w in warnings))
    def test_scene_context_includes_selected_and_neighbor(self):
        txt=novelctl.build_brief(ROOT,'SC-006')
        self.assertIn('SC-005',txt)
        self.assertIn('SC-006',txt)
        self.assertIn('SC-007',txt)
        self.assertNotIn('SC-001 เล่นเกมส่วนตัว',txt)
        self.assertIn('GAMEPLAY=UNVERIFIED',txt)
    def test_episode_context_covers_all_eight_scenes(self):
        txt=novelctl.build_brief(ROOT,'EP-001')
        for i in range(1,9):self.assertIn(f'SC-{i:03}',txt)
    def test_bad_reference_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);(base/'data').mkdir()
            for kind in novelctl.REQUIRED_DATA:
                (base/'data'/f'{kind}.json').write_bytes((ROOT/'data'/f'{kind}.json').read_bytes())
            p=base/'data'/'scenes.json'; db=json.loads(p.read_text(encoding='utf-8'))
            db['scenes'][0]['canon_refs'].append('FACT-999')
            p.write_text(json.dumps(db),encoding='utf-8')
            err,_=novelctl.validate(base)
            self.assertTrue(any('FACT-999' in x for x in err))
    def test_bad_causal_order_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);(base/'data').mkdir()
            for kind in novelctl.REQUIRED_DATA:
                (base/'data'/f'{kind}.json').write_bytes((ROOT/'data'/f'{kind}.json').read_bytes())
            p=base/'data'/'scenes.json'; db=json.loads(p.read_text(encoding='utf-8'))
            db['scenes'][0]['requires_flags'].append('first_pvp_won')
            p.write_text(json.dumps(db),encoding='utf-8')
            err,_=novelctl.validate(base)
            self.assertTrue(any('first_pvp_won' in x for x in err))
    def test_cannot_fabricate_zero_or_negative_inventory(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);(base/'data').mkdir()
            for kind in novelctl.REQUIRED_DATA:
                (base/'data'/f'{kind}.json').write_bytes((ROOT/'data'/f'{kind}.json').read_bytes())
            p=base/'data'/'inventory_ledger.json';db=json.loads(p.read_text(encoding='utf8'))
            db['entries'][0]['quantity']=-3
            p.write_text(json.dumps(db),encoding='utf8')
            err,_=novelctl.validate(base)
            self.assertTrue(any('positive integer or null' in x for x in err))
    def test_cannot_fake_visual_gameplay_verification(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);(base/'data').mkdir()
            for kind in novelctl.REQUIRED_DATA:
                (base/'data'/f'{kind}.json').write_bytes((ROOT/'data'/f'{kind}.json').read_bytes())
            p=base/'data'/'mechanics.json'; db=json.loads(p.read_text(encoding='utf-8'))
            db['mechanics'][0]['game_verification']='VISUALLY_VERIFIED'
            p.write_text(json.dumps(db),encoding='utf-8')
            err,_=novelctl.validate(base)
            self.assertTrue(any('cannot claim visual verification' in x for x in err))
    def test_ai_proposal_cannot_be_locked(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);(base/'data').mkdir()
            for kind in novelctl.REQUIRED_DATA:
                (base/'data'/f'{kind}.json').write_bytes((ROOT/'data'/f'{kind}.json').read_bytes())
            p=base/'data'/'canon.json'; db=json.loads(p.read_text(encoding='utf-8'))
            db['facts'][-1]['status']='LOCKED'
            p.write_text(json.dumps(db),encoding='utf-8')
            err,_=novelctl.validate(base)
            self.assertTrue(any('assistant proposal' in x for x in err))

class CausalFlagTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name in ('data', 'scenes'):
            shutil.copytree(ROOT / name, self.root / name)

    def tearDown(self):
        self.temp.cleanup()

    def edit(self, kind, change):
        path = self.root / 'data' / f'{kind}.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        change(data)
        path.write_text(json.dumps(data), encoding='utf-8')

    def require_flag(self, scene_index, name='test_gate'):
        self.edit('scenes', lambda data: data['scenes'][scene_index]['requires_flags'].append(name))

    def effect(self, scene_index, value, name='test_gate'):
        self.edit('scenes', lambda data: data['scenes'][scene_index]['effects_flags'].update({name: value}))
        # Keep the event mirror valid so only causal semantics are under test.
        self.edit('events', lambda data: data['events'][scene_index]['effects_flags'].update({name: value}))

    def test_false_initial_flag_does_not_establish_prerequisite(self):
        self.edit('story_state', lambda data: data['flags'].update(test_gate=False))
        self.require_flag(0)
        errors, _ = novelctl.validate(self.root)
        self.assertTrue(any("SC-001: needs flag 'test_gate'" in error for error in errors))

    def test_true_initial_flag_establishes_prerequisite(self):
        self.edit('story_state', lambda data: data['flags'].update(test_gate=True))
        self.require_flag(0)
        self.assertEqual(novelctl.validate(self.root)[0], [])

    def test_false_effect_does_not_establish_prerequisite(self):
        self.effect(0, False)
        self.require_flag(1)
        errors, warnings = novelctl.validate(self.root)
        self.assertTrue(any("SC-002: needs flag 'test_gate'" in error for error in errors))
        self.assertFalse(any('reset to false' in warning for warning in warnings))

    def test_false_effect_resets_previously_true_flag(self):
        self.effect(0, True)
        self.effect(1, False)
        self.require_flag(2)
        errors, warnings = novelctl.validate(self.root)
        self.assertTrue(any("SC-003: needs flag 'test_gate'" in error for error in errors))
        self.assertTrue(any('SC-002: a previous true flag is reset to false' in warning for warning in warnings))

    def test_true_effect_can_reestablish_reset_flag(self):
        self.effect(0, True)
        self.effect(1, False)
        self.effect(2, True)
        self.require_flag(3)
        self.assertEqual(novelctl.validate(self.root)[0], [])

    def test_nonboolean_initial_flags_are_rejected_and_do_not_satisfy_prerequisite(self):
        self.require_flag(0)
        for value in (1, 'true', None):
            with self.subTest(value=value):
                self.edit('story_state', lambda data: data['flags'].update(test_gate=value))
                errors, _ = novelctl.validate(self.root)
                self.assertIn('story_state.flags.test_gate must be boolean', errors)
                self.assertTrue(any("SC-001: needs flag 'test_gate'" in error for error in errors))

    def test_nonboolean_effects_are_rejected_and_do_not_establish_prerequisite(self):
        self.require_flag(1)
        for value in (1, 'true', None):
            with self.subTest(value=value):
                self.effect(0, value)
                errors, _ = novelctl.validate(self.root)
                self.assertIn('SC-001: effects_flags.test_gate must be boolean', errors)
                self.assertTrue(any("SC-002: needs flag 'test_gate'" in error for error in errors))

    def test_initial_flags_must_be_an_object(self):
        self.edit('story_state', lambda data: data.update(flags=['test_gate']))
        errors, _ = novelctl.validate(self.root)
        self.assertIn('story_state.flags must be an object of booleans', errors)


if __name__=='__main__':unittest.main()
