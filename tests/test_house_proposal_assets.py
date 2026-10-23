"""Integrity of the isolated proposal package; these are not gameplay tests."""
import importlib.util
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "stories/last-island-active/design/proposals/house-atlas-v1"


class HouseProposalAssetTests(unittest.TestCase):
    def test_writer_card_matches_scene_snapshots_and_real_route_ids(self):
        card = json.loads((PACKAGE/'writer_reference_card.json').read_text(encoding='utf-8'))
        data = json.loads((PACKAGE/'construction_stages.json').read_text(encoding='utf-8'))
        pilot = json.loads((PACKAGE/'pilot_workshop_versions.json').read_text(encoding='utf-8'))
        snapshots = {s['synthetic_scene_id']: s for s in data['snapshots']}
        for retrieval in card['worked_synthetic_retrievals']:
            snapshot = snapshots[retrieval['synthetic_scene_id']]
            self.assertEqual(retrieval['namespace'], 'SYNTHETIC-NOT-STORY')
            self.assertIsNone(retrieval['story_scene_ref'])
            self.assertEqual(retrieval['world_construction_tick'], snapshot['world_tick'])
            self.assertEqual(retrieval['target_blueprint']['version_id'], snapshot['target_design_version'])
            for key in ['available_room_refs','available_route_refs','event_refs']:
                self.assertEqual(retrieval[key], snapshot[key])
            states = {p['part_id']: p for p in snapshot['parts']}
            for part in retrieval['as_built_parts']:
                for key in ['construction_status','usability']:
                    self.assertEqual(part[key], states[part['part_id']][key])
        version = next(v for v in pilot['house']['versions'] if v['version_id'] == 'V02')
        steps = card['declared_pilot_route_trace']['steps']
        door = next(d for d in version['doors'] if d['door_id'] == steps[0]['ref'])
        self.assertEqual(steps[0]['boundary_tile_id'], door['boundary_tile_id'])
        self.assertEqual(steps[0]['boundary_segment_xy'], door['boundary_segment_xy'])
        stair = next(s for s in version['stairs'] if s['stair_id'] == steps[1]['ref'])
        for prefix, endpoint in [('from',stair['from']),('to',stair['to'])]:
            self.assertEqual(steps[1][prefix+'_room_id'], endpoint['room_id'])
            self.assertEqual(steps[1][prefix+'_landing_ref'], endpoint['landing_ref'])
            self.assertEqual(steps[1][prefix+'_opening_ref'], endpoint['opening_ref'])

    def test_synthetic_snapshots_do_not_inherit_future_blueprint(self):
        data = json.loads((PACKAGE / 'construction_stages.json').read_text(encoding='utf-8'))
        pilot = json.loads((PACKAGE / 'pilot_workshop_versions.json').read_text(encoding='utf-8'))
        versions = {v['version_id']: v for v in pilot['house']['versions']}
        events = {e['event_id']: e for e in data['events']}
        self.assertEqual(data['runtime_replay'], 'NOT_IMPLEMENTED')
        self.assertEqual(data['human_editorial_approval'], 'UNVERIFIED')
        for snapshot in data['snapshots']:
            version = versions[snapshot['target_design_version']]
            self.assertTrue(set(snapshot['available_room_refs']) <= {r['room_id'] for r in version['rooms']})
            self.assertTrue(set(snapshot['available_route_refs']) <=
                            ({d['door_id'] for d in version['doors']} | {s['stair_id'] for s in version['stairs']}))
            self.assertTrue(all(events[ref]['world_tick'] <= snapshot['world_tick'] for ref in snapshot['event_refs']))
            self.assertEqual(snapshot['pov_knowledge']['status'], 'UNKNOWN')
            self.assertEqual(snapshot['pov_knowledge']['known_room_refs'], [])
        snapshots = {s['synthetic_scene_id']: s for s in data['snapshots']}
        self.assertEqual(snapshots['SYN-SC-A']['available_room_refs'], [])
        self.assertEqual(snapshots['SYN-SC-B']['available_room_refs'], ['ROOM-CORE'])
        self.assertNotIn('STAIR-EXT-E', snapshots['SYN-SC-B']['available_route_refs'])
        self.assertIn('STAIR-EXT-E', snapshots['SYN-SC-C']['available_route_refs'])
        self.assertIn('OPEN-011', snapshots['SYN-SC-C']['event_refs'])
        self.assertEqual(events['BUILD-009']['result_status'], 'COMPLETED')
        self.assertEqual(events['BUILD-009']['result_usability'], 'UNAVAILABLE')

    def test_pilot_diagrams_match_current_blueprint_data(self):
        spec = importlib.util.spec_from_file_location('pilot_renderer', PACKAGE/'tools/render_pilot.py')
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)
        pilot = json.loads((PACKAGE/'pilot_workshop_versions.json').read_text(encoding='utf-8'))
        for version in pilot['house']['versions']:
            raw = (PACKAGE/'diagrams'/('WORKSHOP-'+version['version_id']+'.svg')).read_text(encoding='utf-8')
            self.assertEqual(raw, renderer.render(version))
            ET.fromstring(raw)
            self.assertIn('Blueprint only', raw)
            self.assertIn('UNKNOWN', raw)

    def test_unplaced_programs_have_no_canon_bindings(self):
        document = json.loads((PACKAGE / "archetype_programs.json").read_text(encoding="utf-8"))
        self.assertEqual(document["human_editorial_approval"], "UNVERIFIED")
        self.assertIs(document["canon_change_authorized"], False)
        self.assertIs(document["ledger_apply_authorized"], False)
        self.assertEqual({p["id"] for p in document["programs"]},
                         {"STARTER", "MAKER", "COMMUNAL", "EXCHANGE", "ARCHIVE", "REST", "GARDEN", "REUSE"})
        for program in document["programs"]:
            self.assertEqual(program["status"], "PROPOSED")
            for field in ("owner_player_ref", "owner_group_ref", "canon_location_ref"):
                self.assertIsNone(program[field])
            self.assertEqual(program["chapter_refs"], [])
            self.assertTrue(program["unknowns_th"])
            self.assertTrue(program["vertical_strategy_th"])

    def test_sources_preserve_evidence_limits(self):
        sources = json.loads((PACKAGE / "research/sources.json").read_text(encoding="utf-8"))
        self.assertEqual(sources["status"], "PROPOSED")
        records = sources["sources"]
        self.assertEqual(len(records), 14)
        self.assertEqual(len({s["id"] for s in records}), 14)
        for source in records:
            self.assertTrue(source["url"].startswith("https://"))
            self.assertTrue(source["evidence_level"])
            self.assertTrue(source["not_verified_th"])
            if source["id"].startswith("RB-"):
                self.assertIn("NO_TRANSCRIPT", source["evidence_level"])

    def test_original_concept_diagrams_are_current_and_passive(self):
        path = PACKAGE / "tools/render_concepts.py"
        spec = importlib.util.spec_from_file_location("house_concepts", path)
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)
        programs = json.loads((PACKAGE / "archetype_programs.json").read_text(encoding="utf-8"))
        for program in programs["programs"]:
            raw = (PACKAGE / "diagrams" / (program["id"] + ".svg")).read_text(encoding="utf-8")
            self.assertEqual(raw, renderer.render(program["id"], program["name_th"]))
            root = ET.fromstring(raw)
            self.assertTrue(root.tag.endswith("svg"))
            self.assertIn("UNPLACED CONCEPT", raw)
            self.assertIn("UNKNOWN", raw)
            for node in root.iter():
                self.assertNotIn(node.tag.split("}")[-1], {"script", "image", "foreignObject"})
                self.assertFalse(any(key.split("}")[-1].lower().startswith("on") or
                                     key.split("}")[-1] == "href" for key in node.attrib))


if __name__ == "__main__":
    unittest.main()
