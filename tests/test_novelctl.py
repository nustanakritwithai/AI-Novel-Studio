import importlib.util
import tempfile
import unittest
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('novelctl', ROOT/'scripts/novelctl.py')
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

if __name__=='__main__':unittest.main()
