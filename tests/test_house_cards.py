"""Synthetic contract tests for bounded, non-canonical house reference cards."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts import house_cards, novelctl, registry_schema, storyctl


REPO_ROOT = Path(__file__).resolve().parents[1]
STORY_SLUG = "synthetic-house"
SOURCE_PATH = "reference/house-notes.md"
SOURCE_BYTES = b"Synthetic reference metadata; no narrative prose.\n"


class HouseCardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        self.root = self._make_story(self.workspace)
        self._write_source()
        self.manifest = self._manifest()
        self._write_manifest()

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def _make_story(cls, workspace: Path) -> Path:
        root = storyctl.new_story(workspace, STORY_SLUG, "Synthetic house-card test")
        values = {
            "canon": {"project": "Synthetic", "facts": []},
            "characters": {"characters": [
                {"id": "CHAR-001", "name": "Synthetic protagonist", "role": "Metadata fixture",
                 "status": "IN_STORY", "aliases": [], "goals": [], "known_traits": [],
                 "unknowns": [], "first_scene": "SC-017", "knowledge": []},
                {"id": "CHAR-002", "name": "Synthetic other character", "role": "Metadata fixture",
                 "status": "IN_STORY", "aliases": [], "goals": [], "known_traits": [],
                 "unknowns": [], "first_scene": "SC-017", "knowledge": []},
            ]},
            "locations": {"locations": [{"id": "LOC-009", "name": "Protagonist house metadata alias"}]},
            "items": {"items": []},
            "episodes": {"episodes": [
                {"id": "EP-017", "title": "Synthetic earlier episode", "status": "OUTLINE",
                 "scene_ids": ["SC-017", "SC-018"], "questions": [], "approved_final_draft": None},
                {"id": "EP-018", "title": "Synthetic later episode", "status": "OUTLINE",
                 "scene_ids": ["SC-036", "SC-037", "SC-038"], "questions": [], "approved_final_draft": None},
            ]},
            "scenes": {"scenes": []},
            "events": {"events": []},
            "inventory_ledger": {"entries": []},
            "threads": {"threads": []},
            "relationships": {"relationships": []},
            "decisions": {"decisions": []},
            "story_state": {"active_episode": "EP-017", "phase": "OUTLINE_NOT_CANON_PROSE",
                            "approved_through_scene": None, "flags": {}, "pending_review": []},
        }
        scenes = values["scenes"]["scenes"]
        for episode_id, scene_ids, offset in (
            ("EP-017", ["SC-017", "SC-018"], 1),
            ("EP-018", ["SC-036", "SC-037", "SC-038"], 1),
        ):
            for order, scene_id in enumerate(scene_ids, start=offset):
                scenes.append({
                    "id": scene_id, "episode_id": episode_id, "order": order,
                    "title": "Synthetic scene metadata", "status": "PLANNED", "pov": "CHAR-001",
                    "location_id": "LOC-009", "character_ids": ["CHAR-001"], "item_ids": [],
                    "canon_refs": [], "goal": "Synthetic metadata", "conflict": "Synthetic metadata",
                    "outcome": "Synthetic metadata", "beats": ["Synthetic metadata"],
                    "requires_flags": [], "effects_flags": {}, "draft_path": f"drafts/{scene_id}.md",
                })
        for kind, value in values.items():
            cls._write_json(root / "data" / f"{kind}.json", {"schema_version": 1, **value})
        return root

    def _write_source(self, data: bytes = SOURCE_BYTES) -> None:
        path = self.root / SOURCE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def _source_row(self, sha: str | None = None) -> dict:
        return {
            "id": "SRC-HOUSE", "path": SOURCE_PATH,
            "git_blob_sha": sha or self._git_blob(SOURCE_BYTES),
            "status": "LOCAL_REFERENCE", "supporting_sources": [],
        }

    @staticmethod
    def _git_blob(data: bytes) -> str:
        return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()

    def _evidence(self) -> list[dict]:
        return [{"source_id": "SRC-HOUSE", "locator": "L1"}]

    def _manifest(self) -> dict:
        return {
            "schema_version": 1,
            "story_slug": STORY_SLUG,
            "enabled": True,
            "status": "CURATED_REFERENCE_NOT_CANON",
            "fields": ["material", "stairs", "furnace", "breach", "repair",
                       "owner_character_ref", "observed_material"],
            "sources": [self._source_row()],
            "houses": [{"id": "LOC-009", "label": "protagonist stone home", "design_target_ref": None}],
            "facts": [
                {"id": "F-STONE", "house_id": "LOC-009", "field": "material", "value": "STONE",
                 "observed_after_scene": "SC-017", "evidence": self._evidence()},
                {"id": "F-STAIRS", "house_id": "LOC-009", "field": "stairs", "value": True,
                 "observed_after_scene": "SC-018", "evidence": self._evidence()},
                {"id": "F-BREACH", "house_id": "LOC-009", "field": "breach", "value": "BREACHED",
                 "observed_after_scene": "SC-036", "evidence": self._evidence()},
                {"id": "F-REPAIR", "house_id": "LOC-009", "field": "repair", "value": "REPAIRED",
                 "observed_after_scene": "SC-037", "evidence": self._evidence()},
                {"id": "F-FURNACE", "house_id": "LOC-009", "field": "furnace", "value": True,
                 "observed_after_scene": "SC-038", "evidence": self._evidence()},
            ],
            "knowledge": [
                {"id": "K-STONE", "house_id": "LOC-009", "character_ref": "CHAR-001",
                 "field": "observed_material", "value": "STONE", "observed_after_scene": "SC-017",
                 "evidence": self._evidence()},
                {"id": "K-OTHER", "house_id": "LOC-009", "character_ref": "CHAR-002",
                 "field": "observed_material", "value": "WOOD", "observed_after_scene": "SC-018",
                 "evidence": self._evidence()},
            ],
            "views": [
                {"house_id": "LOC-009", "scene_id": "SC-017", "boundary": "BEFORE",
                 "fact_ids": [], "knowledge_ids": []},
                {"house_id": "LOC-009", "scene_id": "SC-017", "boundary": "AFTER",
                 "fact_ids": ["F-STONE"], "knowledge_ids": ["K-STONE"]},
                {"house_id": "LOC-009", "scene_id": "SC-018", "boundary": "BEFORE",
                 "fact_ids": ["F-STONE"], "knowledge_ids": ["K-STONE"]},
                {"house_id": "LOC-009", "scene_id": "SC-018", "boundary": "AFTER",
                 "fact_ids": ["F-STONE", "F-STAIRS"], "knowledge_ids": ["K-STONE", "K-OTHER"]},
                {"house_id": "LOC-009", "scene_id": "SC-036", "boundary": "AFTER",
                 "fact_ids": ["F-STONE", "F-STAIRS", "F-BREACH"], "knowledge_ids": ["K-STONE"]},
                {"house_id": "LOC-009", "scene_id": "SC-037", "boundary": "AFTER",
                 "fact_ids": ["F-STONE", "F-STAIRS", "F-BREACH", "F-REPAIR"], "knowledge_ids": ["K-STONE"]},
                {"house_id": "LOC-009", "scene_id": "SC-038", "boundary": "AFTER",
                 "fact_ids": ["F-STONE", "F-STAIRS", "F-BREACH", "F-REPAIR", "F-FURNACE"],
                 "knowledge_ids": ["K-STONE"]},
            ],
        }

    def _write_manifest(self, value: dict | None = None) -> None:
        self.manifest = value or self.manifest
        self._write_json(self.root / "data" / "house_references.json", self.manifest)

    def _build(self, scene: str = "SC-017", boundary: str = "AFTER", pov: str | None = None,
               source_mode: str = "working-tree") -> dict:
        return house_cards.build(self.root, "LOC-009", scene, boundary=boundary, pov=pov,
                                 source_mode=source_mode)

    def test_schema_is_real_draft_2020_12_and_manifest_validates(self):
        schema_path = REPO_ROOT / "schemas" / "v1" / "house_references.schema.json"
        self.assertTrue(schema_path.is_file())
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        registry_schema._dependencies()[0].check_schema(schema)
        self.assertIn("house_references", registry_schema.SCHEMA_KINDS)
        registry_schema.ensure_valid("house_references", self.manifest)
        self.assertEqual(house_cards.validate(self.root, novelctl.load(self.root)), [])

    def test_missing_and_disabled_modules_are_opt_in_unknown(self):
        path = self.root / "data" / "house_references.json"
        path.unlink()
        self.assertEqual(house_cards.validate(self.root), [])
        self.assertEqual(self._build()["availability"], "UNKNOWN")
        self.manifest["enabled"] = False
        self._write_manifest()
        self.assertEqual(house_cards.validate(self.root), [])
        self.assertEqual(self._build()["availability"], "UNKNOWN")

    def test_card_discloses_reference_only_and_keeps_unanswered_fields_unknown(self):
        card = self._build()
        self.assertEqual(card["availability"], "AVAILABLE")
        self.assertEqual(card["status"], "REFERENCE_ONLY_NOT_CANON")
        self.assertEqual(card["human_editorial_approval"], "UNVERIFIED")
        self.assertIs(card["canon_change_authorized"], False)
        self.assertIs(card["ledger_apply_authorized"], False)
        self.assertEqual(card["world_time"], "UNKNOWN")
        self.assertIn("furnace", card["unknown_fields"])
        self.assertIn("owner_character_ref", card["unknown_fields"])
        self.assertEqual(card["facts"]["material"]["value"], "STONE")
        self.assertEqual(card["facts"]["material"]["evidence"][0]["source_status"], "LOCAL_REFERENCE")
        self.assertNotIn("protagonist stone home", json.dumps(card, ensure_ascii=False))

    def test_exact_view_only_and_no_nearest_or_later_fallback(self):
        no_exact_view = copy.deepcopy(self.manifest)
        no_exact_view["views"] = [v for v in no_exact_view["views"]
                                  if not (v["scene_id"] == "SC-017" and v["boundary"] == "BEFORE")]
        self._write_manifest(no_exact_view)
        card = self._build("SC-017", "BEFORE")
        self.assertEqual(card["availability"], "UNKNOWN")
        self.assertFalse(any(v["scene_id"] == "SC-017" and v["boundary"] == "BEFORE"
                             for v in self.manifest["views"]))

    def test_before_and_after_boundaries_use_narrative_disclosure(self):
        before = self._build("SC-017", "BEFORE")
        after = self._build("SC-017", "AFTER")
        self.assertNotIn("material", before["facts"])
        self.assertIn("material", before["unknown_fields"])
        self.assertEqual(after["facts"]["material"]["value"], "STONE")
        stairs_before = self._build("SC-018", "BEFORE")
        stairs_after = self._build("SC-018", "AFTER")
        self.assertIn("stairs", stairs_before["unknown_fields"])
        self.assertTrue(stairs_after["facts"]["stairs"]["value"])

    def test_future_disclosure_uses_episode_and_scene_order_not_identifiers_or_clock(self):
        # Deliberately reverse lexical scene IDs relative to narrative order.
        db = json.loads((self.root / "data" / "scenes.json").read_text(encoding="utf-8"))
        scene_17 = next(s for s in db["scenes"] if s["id"] == "SC-017")
        scene_18 = next(s for s in db["scenes"] if s["id"] == "SC-018")
        scene_17["order"], scene_18["order"] = 2, 1
        # Explicitly provided clock labels conflict; disclosure must follow narrative order only.
        scene_17["world_time"] = "day-99"
        scene_18["world_time"] = "day-01"
        self._write_json(self.root / "data" / "scenes.json", db)
        episodes_path = self.root / "data" / "episodes.json"
        episodes = json.loads(episodes_path.read_text(encoding="utf-8"))
        episode = next(row for row in episodes["episodes"] if row["id"] == "EP-017")
        episode["scene_ids"] = ["SC-018", "SC-017"]
        self._write_json(episodes_path, episodes)
        reordered = copy.deepcopy(self.manifest)
        for view in reordered["views"]:
            if view["scene_id"] == "SC-018":
                view["fact_ids"] = [rid for rid in view["fact_ids"] if rid != "F-STONE"]
                view["knowledge_ids"] = [rid for rid in view["knowledge_ids"] if rid != "K-STONE"]
        self._write_manifest(reordered)
        # A future fact keyed to SC-017 remains hidden at the earlier narrative scene SC-018.
        card = self._build("SC-018", "AFTER")
        self.assertNotIn("material", card["facts"])

    def test_duplicate_scene_order_cannot_disclose_another_scenes_future_claim(self):
        scenes_path = self.root / "data" / "scenes.json"
        scenes = json.loads(scenes_path.read_text(encoding="utf-8"))
        scene_17 = next(scene for scene in scenes["scenes"] if scene["id"] == "SC-017")
        scene_18 = next(scene for scene in scenes["scenes"] if scene["id"] == "SC-018")
        scene_17["order"] = scene_18["order"]
        self._write_json(scenes_path, scenes)
        ambiguous = copy.deepcopy(self.manifest)
        after_17 = next(view for view in ambiguous["views"]
                        if view["scene_id"] == "SC-017" and view["boundary"] == "AFTER")
        after_17["fact_ids"].append("F-STAIRS")
        self._write_manifest(ambiguous)
        # Equal narrative order must not let AFTER SC-017 expose a claim disclosed after SC-018.
        with self.assertRaises(ValueError):
            self._build("SC-017", "AFTER")

    def test_pov_knowledge_is_separate_and_never_copied_from_actual_facts(self):
        no_knowledge = copy.deepcopy(self.manifest)
        no_knowledge["views"][1]["knowledge_ids"] = []
        self._write_manifest(no_knowledge)
        card = self._build("SC-017", "AFTER", "CHAR-001")
        self.assertEqual(card["facts"]["material"]["value"], "STONE")
        self.assertEqual(card["pov_knowledge"]["facts"], {})
        self.assertEqual(card["pov_knowledge"]["status"], "UNKNOWN")

    def test_other_valid_pov_does_not_receive_protagonist_knowledge(self):
        card = self._build("SC-017", "AFTER", "CHAR-002")
        self.assertEqual(card["facts"]["material"]["value"], "STONE")
        self.assertEqual(card["pov_knowledge"]["character_ref"], "CHAR-002")
        self.assertEqual(card["pov_knowledge"]["facts"], {})

    def test_invalid_pov_and_unknown_cross_references_fail_closed(self):
        with self.assertRaises(ValueError):
            self._build("SC-017", "AFTER", "CHAR-MISSING")
        changed = copy.deepcopy(self.manifest)
        changed["facts"][0]["house_id"] = "LOC-UNKNOWN"
        self._write_manifest(changed)
        with self.assertRaises(ValueError):
            self._build()
        bad_location = copy.deepcopy(self.manifest)
        bad_location["fields"].append("location_refs")
        bad_location["facts"][0].update(field="location_refs", value=["LOC-MISSING"])
        self._write_manifest(bad_location)
        with self.assertRaises(ValueError):
            self._build()

    def test_duplicate_story_character_or_location_registry_ids_fail_closed(self):
        for kind, collection in (("characters", "characters"), ("locations", "locations")):
            with self.subTest(kind=kind):
                path = self.root / "data" / f"{kind}.json"
                original = json.loads(path.read_text(encoding="utf-8"))
                duplicate = copy.deepcopy(original)
                duplicate[collection].append(copy.deepcopy(duplicate[collection][0]))
                self._write_json(path, duplicate)
                with self.assertRaises(ValueError):
                    self._build()
                self.assertTrue(house_cards.validate(self.root))
                self._write_json(path, original)

    def test_unstated_connection_is_unknown_not_false(self):
        card = self._build("SC-017", "AFTER")
        self.assertIn("stairs", card["unknown_fields"])
        self.assertNotIn("stairs", card["facts"])

    def test_duplicate_ids_and_view_fields_are_rejected(self):
        duplicate_id = copy.deepcopy(self.manifest)
        duplicate_id["facts"].append(copy.deepcopy(duplicate_id["facts"][0]))
        self._write_manifest(duplicate_id)
        self.assertTrue(house_cards.validate(self.root))
        with self.assertRaises(ValueError):
            self._build()
        duplicate_field = copy.deepcopy(self.manifest)
        duplicate_field["facts"].append({
            "id": "F-STONE-SECOND", "house_id": "LOC-009", "field": "material", "value": "BRICK",
            "observed_after_scene": "SC-017", "evidence": self._evidence(),
        })
        duplicate_field["views"][1]["fact_ids"].append("F-STONE-SECOND")
        self._write_manifest(duplicate_field)
        with self.assertRaises(ValueError):
            self._build()

    def test_schema_version_and_malformed_enabled_module_are_errors(self):
        wrong_version = copy.deepcopy(self.manifest)
        wrong_version["schema_version"] = 2
        self._write_manifest(wrong_version)
        self.assertTrue(house_cards.validate(self.root))
        with self.assertRaises(ValueError):
            self._build()
        self._write_manifest()
        path = self.root / "data" / "house_references.json"
        path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
        with self.assertRaises(ValueError):
            self._build()
        path.write_text('{"enabled":NaN}', encoding="utf-8")
        with self.assertRaises(ValueError):
            self._build()
        self._write_manifest(self._manifest())
        raw = path.read_text(encoding="utf-8")
        self.assertIn('"value": "STONE"', raw)
        (self.root / "data" / "house_references.json").write_text(
            raw.replace('"value": "STONE"', '"value": 1e999', 1), encoding="utf-8")
        with self.assertRaises(ValueError):
            self._build()

    def test_missing_stale_and_mismatched_source_evidence_fail_closed(self):
        self._write_manifest(copy.deepcopy(self.manifest))
        (self.root / SOURCE_PATH).unlink()
        with self.assertRaises(ValueError):
            self._build()
        self._write_source()
        stale = copy.deepcopy(self.manifest)
        stale["sources"][0]["git_blob_sha"] = "0" * 40
        self._write_manifest(stale)
        with self.assertRaises(ValueError):
            self._build()

    def test_same_id_in_fact_and_knowledge_namespaces_still_checks_knowledge_source(self):
        overlapping = copy.deepcopy(self.manifest)
        overlapping["sources"].append({
            "id": "SRC-STALE-KNOWLEDGE", "path": SOURCE_PATH, "git_blob_sha": "0" * 40,
            "status": "LOCAL_REFERENCE", "supporting_sources": [],
        })
        knowledge = next(row for row in overlapping["knowledge"] if row["id"] == "K-STONE")
        knowledge["id"] = "F-STONE"  # Same opaque ID is allowed in the separate registries.
        knowledge["evidence"][0]["source_id"] = "SRC-STALE-KNOWLEDGE"
        for view in overlapping["views"]:
            view["knowledge_ids"] = ["F-STONE" if claim_id == "K-STONE" else claim_id
                                      for claim_id in view["knowledge_ids"]]
        self._write_manifest(overlapping)
        errors = house_cards.validate(self.root)
        self.assertTrue(errors)
        self.assertTrue(any("SRC-STALE-KNOWLEDGE" in error for error in errors), errors)

    def test_supporting_source_hashes_and_cycles_fail_closed(self):
        stale_support = copy.deepcopy(self.manifest)
        stale_support["sources"].append({
            "id": "SRC-SUPPORT", "path": SOURCE_PATH, "git_blob_sha": "0" * 40,
            "status": "LOCAL_REFERENCE", "supporting_sources": [],
        })
        stale_support["sources"][0]["supporting_sources"] = ["SRC-SUPPORT"]
        self._write_manifest(stale_support)
        with self.assertRaises(ValueError):
            self._build()
        self.assertTrue(house_cards.validate(self.root))

        cycle = copy.deepcopy(self.manifest)
        cycle["sources"].append({
            "id": "SRC-SUPPORT", "path": SOURCE_PATH, "git_blob_sha": self._git_blob(SOURCE_BYTES),
            "status": "LOCAL_REFERENCE", "supporting_sources": ["SRC-HOUSE"],
        })
        cycle["sources"][0]["supporting_sources"] = ["SRC-SUPPORT"]
        self._write_manifest(cycle)
        with self.assertRaises(ValueError):
            self._build()
        self.assertTrue(house_cards.validate(self.root))

    def test_invalid_or_unresolved_evidence_locators_fail_closed(self):
        for locator in ("L0", "L2", "/missing"):
            with self.subTest(locator=locator):
                invalid = copy.deepcopy(self._manifest())
                invalid["facts"][0]["evidence"][0]["locator"] = locator
                self._write_manifest(invalid)
                with self.assertRaises(ValueError):
                    self._build()
                self.assertTrue(house_cards.validate(self.root))

    def test_path_traversal_and_story_mismatch_are_rejected(self):
        escaping = copy.deepcopy(self.manifest)
        escaping["sources"][0]["path"] = "../other-story/secret.md"
        self._write_manifest(escaping)
        with self.assertRaises(ValueError):
            self._build()
        wrong_story = copy.deepcopy(self.manifest)
        wrong_story["story_slug"] = "another-story"
        self._write_manifest(wrong_story)
        with self.assertRaises(ValueError):
            self._build()

    def test_symlink_source_is_rejected(self):
        source = self.root / SOURCE_PATH
        target = self.workspace / "outside.md"
        target.write_bytes(SOURCE_BYTES)
        source.unlink()
        try:
            source.symlink_to(target)
        except OSError as exc:
            self.skipTest(f"symlink creation is unavailable: {exc}")
        with self.assertRaises(ValueError):
            self._build()

    def test_repeated_builds_are_deterministic_and_do_not_change_sources(self):
        before = (self.root / SOURCE_PATH).read_bytes()
        first = self._build("SC-018", "AFTER")
        second = self._build("SC-018", "AFTER")
        self.assertEqual(first, second)
        self.assertEqual((self.root / SOURCE_PATH).read_bytes(), before)

    def test_working_tree_hashes_raw_bytes_and_rejects_crlf_mismatch(self):
        self._write_source(SOURCE_BYTES.replace(b"\n", b"\r\n"))
        with self.assertRaises(ValueError):
            self._build("SC-017", "AFTER", source_mode="working-tree")

    def test_committed_mode_reads_pinned_blob_and_labels_commit(self):
        self._write_source(SOURCE_BYTES)
        self._git("init")
        self._git("config", "user.email", "test@example.invalid")
        self._git("config", "user.name", "Synthetic Test")
        self._git("add", "reference/house-notes.md")
        self._git("commit", "-m", "synthetic source")
        self._write_source(SOURCE_BYTES.replace(b"\n", b"\r\n"))
        with self.assertRaises(ValueError):
            self._build("SC-017", "AFTER", source_mode="working-tree")
        card = self._build("SC-017", "AFTER", source_mode="committed")
        self.assertEqual(card["source_mode"], "committed")
        self.assertEqual(card["source_evidence_mode"], "COMMITTED_GIT_BLOBS")
        self.assertRegex(card["source_commit"], r"^[0-9a-f]{40,64}$")

    def test_cli_private_out_guard_keeps_artifacts_out_of_story_sources(self):
        manifest_path = self.root / "data" / "house_references.json"
        original_manifest = manifest_path.read_bytes()
        forbidden_out = self.root / "data" / "card.json"
        denied = self._run_cli("house-card", "LOC-009", "--scene", "SC-017", "--boundary", "AFTER",
                               "--out", forbidden_out)
        self.assertNotEqual(denied.returncode, 0)
        self.assertFalse(forbidden_out.exists())
        self.assertEqual(manifest_path.read_bytes(), original_manifest)
        private_out = self.workspace / ".local" / "cards" / "loc-009-sc-017.json"
        allowed = self._run_cli("house-card", "LOC-009", "--scene", "SC-017", "--boundary", "AFTER",
                                "--out", private_out)
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        payload = json.loads(private_out.read_text(encoding="utf-8"))
        self.assertEqual(payload["availability"], "AVAILABLE")

    def test_active_pilot_boundaries_preserve_source_status_and_caveats(self):
        active_root = REPO_ROOT / "stories" / "last-island-active"
        manifest_path = active_root / "data" / "house_references.json"
        self.assertTrue(manifest_path.is_file(), "active pilot metadata must be present for source-backed checks")

        def card(scene_id: str, boundary: str) -> dict:
            result = house_cards.build(active_root, "LOC-009", scene_id, boundary=boundary,
                                       source_mode="committed")
            self.assertEqual(result["availability"], "AVAILABLE")
            self.assertEqual(result["source_mode"], "committed")
            self.assertEqual(result["source_evidence_mode"], "COMMITTED_GIT_BLOBS")
            self.assertEqual(result["human_editorial_approval"], "UNVERIFIED")
            self.assertIs(result["canon_change_authorized"], False)
            self.assertIs(result["ledger_apply_authorized"], False)
            return result

        stone = card("SC-017", "AFTER")
        self.assertEqual(stone["facts"]["main_material"]["value"], "STONE_MAIN_STRUCTURE")
        self.assertEqual(stone["facts"]["main_material"]["evidence"][0]["source_status"],
                         "AUTHOR_ACCEPTED_SOURCE_NOT_GITHUB_APPROVED")
        self.assertIn("stairs", stone["unknown_fields"])
        self.assertIn("floors", stone["unknown_fields"])

        before_stairs = card("SC-018", "BEFORE")
        after_stairs = card("SC-018", "AFTER")
        self.assertIn("stairs", before_stairs["unknown_fields"])
        self.assertIn("floors", before_stairs["unknown_fields"])
        self.assertNotIn("stairs", before_stairs["facts"])
        self.assertEqual(after_stairs["facts"]["stairs"]["value"]["presence"], "DESCRIBED")
        self.assertEqual(after_stairs["facts"]["floors"]["value"]["upper"],
                         "open firing position with low wall")
        self.assertEqual(after_stairs["facts"]["floors"]["value"]["enclosed_upper_room"],
                         "NOT_ESTABLISHED")
        self.assertEqual(after_stairs["pov_knowledge"]["character_ref"], "CHAR-001")
        self.assertIn("main_pillar", after_stairs["unknown_fields"])
        self.assertNotIn("main_pillar", after_stairs["facts"])
        self.assertNotIn("main_pillar", after_stairs["pov_knowledge"]["facts"])

        before_breach = card("SC-036", "BEFORE")
        after_breach = card("SC-036", "AFTER")
        self.assertIn("reported_damage", before_breach["facts"])
        self.assertIn("damage", before_breach["unknown_fields"])
        self.assertNotIn("damage", before_breach["facts"])
        self.assertEqual(after_breach["facts"]["damage"]["value"]["condition"], "visible breach/open gap")
        self.assertEqual(after_breach["facts"]["damage"]["evidence"][0]["source_status"], "DRAFT_SOURCE")

        before_repair = card("SC-037", "BEFORE")
        after_repair = card("SC-037", "AFTER")
        self.assertIn("repair", before_repair["unknown_fields"])
        self.assertNotIn("repair", before_repair["facts"])
        self.assertEqual(after_repair["facts"]["repair"]["value"]["scene"], "SC-037")
        self.assertEqual({item["source_status"] for item in after_repair["facts"]["repair"]["evidence"]},
                         {"LOCAL_REFERENCE", "DRAFT_SOURCE"})
        self.assertEqual(after_repair["facts"]["damage"]["value"]["entrance"],
                         "source describes repaired closure")
        self.assertIsNone(after_repair["facts"]["damage"]["value"]["whole_house_damage"])

        furnace = card("SC-038", "AFTER")
        self.assertIs(furnace["facts"]["furnace"]["value"]["present_in_source"], True)
        self.assertEqual(furnace["facts"]["furnace"]["value"]["processing"],
                         "started, outputs not yet collected")
        self.assertEqual(furnace["pov_knowledge"]["facts"]["furnace"]["id"], "K-FURNACE")

        ep5 = card("SC-047", "AFTER")
        fortification = ep5["facts"]["defensive_extensions"]
        self.assertIs(fortification["value"]["built_in_EP005"], False)
        self.assertEqual(fortification["value"]["improvement"], "CONSIDERED_NOT_BUILT")
        self.assertEqual(fortification["evidence"][0]["source_status"],
                         "AUTHOR_CHAT_ACCEPTED_WORKING_DRAFT")
        self.assertEqual(ep5["facts"]["furnace"]["value"]["processing"], "RUNNING_NOT_HARVESTED")
        self.assertIsNone(ep5["facts"]["furnace"]["value"]["completed_outputs"])
        self.assertEqual(ep5["pov_knowledge"]["facts"]["furnace"]["id"], "K-FURNACE47")

    def _run_cli(self, *args: object) -> subprocess.CompletedProcess:
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        return subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "storyctl.py"),
             "--workspace", str(self.workspace), "--story", STORY_SLUG, *map(str, args)],
            cwd=self.workspace, env=env, capture_output=True, text=True, encoding="utf-8", timeout=30,
        )

    def _git(self, *args: str) -> bytes:
        env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_TERMINAL_PROMPT="0", GIT_NO_LAZY_FETCH="1")
        result = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True,
                                check=False, env=env, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        return result.stdout


if __name__ == "__main__":
    unittest.main()
