"""Scene-start context boundaries without inventing historical state."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import novelctl

ROOT = Path(__file__).resolve().parent.parent


class ContextTimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / 'data', self.root / 'data')
        self.db = novelctl.load(self.root)
        self.db['characters']['characters'][0]['knowledge'] = [
            {'after_scene': 'SC-003', 'knows': 'EARLIER_KNOWLEDGE'},
            {'after_scene': 'SC-006', 'knows': 'LATER_KNOWLEDGE'},
        ]
        self.db['characters']['characters'][0]['known_traits'] = ['UNTIMED_FUTURE_TRAIT']

    def tearDown(self):
        self.temp.cleanup()

    def brief(self, target):
        for kind in novelctl.REQUIRED_DATA:
            (self.root / 'data' / f'{kind}.json').write_text(
                json.dumps(self.db[kind], ensure_ascii=False), encoding='utf-8')
        return novelctl.build_brief(self.root, target)

    def test_knowledge_uses_strict_scene_start_boundary(self):
        for target in ('SC-001', 'SC-003'):
            with self.subTest(target=target):
                text = self.brief(target)
                self.assertNotIn('EARLIER_KNOWLEDGE', text)
                self.assertNotIn('LATER_KNOWLEDGE', text)
        text = self.brief('SC-004')
        self.assertIn('EARLIER_KNOWLEDGE', text)
        self.assertIn('planned knowledge, not approved', text)
        self.assertNotIn('LATER_KNOWLEDGE', text)

    def test_episode_pack_uses_first_scene_boundary(self):
        text = self.brief('EP-001')
        self.assertNotIn('EARLIER_KNOWLEDGE', text)
        self.assertNotIn('LATER_KNOWLEDGE', text)

    def test_untimed_traits_and_unknown_knowledge_are_withheld(self):
        self.db['characters']['characters'][0]['knowledge'].append(
            {'after_scene': 'SC-UNKNOWN', 'knows': 'UNKNOWN_SOURCE_KNOWLEDGE'})
        text = self.brief('SC-008')
        self.assertNotIn('UNTIMED_FUTURE_TRAIT', text)
        self.assertNotIn('UNKNOWN_SOURCE_KNOWLEDGE', text)
        self.assertIn('acquisition time is UNKNOWN', text)

    def test_approved_knowledge_is_labelled(self):
        self.db['scenes']['scenes'][2]['status'] = 'APPROVED'
        text = self.brief('SC-004')
        self.assertIn('After SC-003 (approved knowledge): EARLIER_KNOWLEDGE', text)

    def test_episode_registry_order_and_scene_order_define_time(self):
        first = self.db['episodes']['episodes'][0]
        second = copy.deepcopy(first)
        first['id'], first['scene_ids'] = 'EP-Z', ['SC-001', 'SC-002', 'SC-003', 'SC-004']
        second['id'], second['scene_ids'] = 'EP-A', ['SC-005', 'SC-006', 'SC-007', 'SC-008']
        self.db['episodes']['episodes'] = [first, second]
        for n, scene in enumerate(self.db['scenes']['scenes']):
            scene['episode_id'] = 'EP-Z' if n < 4 else 'EP-A'
            scene['order'] = n % 4 + 1
        self.db['scenes']['scenes'].reverse()
        early = self.brief('SC-002')
        self.assertNotIn('LATER_KNOWLEDGE', early)
        later = self.brief('SC-005')
        self.assertIn('EARLIER_KNOWLEDGE', later)
        self.assertNotIn('LATER_KNOWLEDGE', later)
        self.assertIn('EARLIER_KNOWLEDGE', self.brief('EP-A'))

    def test_latest_state_is_withheld_when_revisiting_or_at_marker(self):
        state = self.db['story_state']
        state['approved_through_scene'] = 'SC-006'
        state['phase'] = 'APPROVED_PROSE'
        state['avatar']['location'] = 'FUTURE_LOCATION_SENTINEL'
        state['flags'] = {'FUTURE_FLAG_SENTINEL': True}
        self.db['scenes']['scenes'][5]['status'] = 'APPROVED'
        for target in ('SC-001', 'SC-006', 'EP-001'):
            with self.subTest(target=target):
                text = self.brief(target)
                self.assertNotIn('FUTURE_LOCATION_SENTINEL', text)
                self.assertNotIn('FUTURE_FLAG_SENTINEL', text)
                self.assertIn('"availability": "UNKNOWN"', text)

    def test_prior_approved_snapshot_keeps_source_marker(self):
        state = self.db['story_state']
        state['approved_through_scene'] = 'SC-003'
        state['phase'] = 'APPROVED_PROSE'
        state['avatar']['location'] = 'PAST_LOCATION_SENTINEL'
        self.db['scenes']['scenes'][2]['status'] = 'CANON'
        text = self.brief('SC-004')
        self.assertIn('PAST_LOCATION_SENTINEL', text)
        self.assertIn('"approved_through_scene": "SC-003"', text)

    def test_initial_baseline_preserved_without_inventing_progress(self):
        text = self.brief('SC-008')
        self.assertIn('NOT_LOGGED_IN_IN_APPROVED_PROSE', text)
        self.assertIn('"flags": {}', text)

    def test_missing_or_unapproved_marker_has_no_safe_snapshot(self):
        self.db['story_state']['phase'] = 'APPROVED_PROSE'
        self.db['story_state']['avatar']['location'] = 'UNSAFE_LOCATION_SENTINEL'
        for marker in (None, 'SC-UNKNOWN', 'SC-003'):
            with self.subTest(marker=marker):
                self.db['story_state']['approved_through_scene'] = marker
                text = self.brief('SC-008')
                self.assertNotIn('UNSAFE_LOCATION_SENTINEL', text)
                self.assertIn('"availability": "UNKNOWN"', text)


if __name__ == '__main__':
    unittest.main()
