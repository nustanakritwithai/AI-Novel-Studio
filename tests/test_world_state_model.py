"""Adversarial checks for the opt-in S1 declaration model.

These tests exercise the pure schema/reference validator with synthetic
metadata only. They do not replay state, query a projection, inspect source
bytes, or treat local approval labels as human approval.
"""
import copy
import unittest

from scripts import world_state_model


SOURCE = {"path": "evidence/baseline.txt", "sha256": "0" * 64}


def catalog_db(suffix=""):
    """Separate selected-story catalogs; labels are display text, not IDs."""
    return {
        "characters": {"schema_version": 1, "characters": [
            {"id": "CHAR-A" + suffix, "name": "อรุณ", "aliases": []},
            {"id": "CHAR-B" + suffix, "name": "มะลิ", "aliases": []},
        ]},
        "locations": {"schema_version": 1, "locations": [
            {"id": "LOC-WORLD" + suffix, "name": "โลก"},
            {"id": "LOC-SITE" + suffix, "name": "สถานที่"},
            {"id": "LOC-ROOM" + suffix, "name": "ห้องสีฟ้า"},
        ]},
        "items": {"schema_version": 1, "items": [
            {"id": "ITEM-KEY" + suffix, "name": "กุญแจ"},
            {"id": "ITEM-STOCK" + suffix, "name": "เสบียง"},
        ]},
        "scenes": {"schema_version": 1, "scenes": [
            {"id": "SC-001" + suffix}, {"id": "SC-002" + suffix},
            {"id": "SC-003" + suffix},
        ]},
    }


def record(record_id="BASE-001", scene="SC-001", narration=0, boundary="BEFORE",
           tick=10, tick_suborder=0):
    if tick is None:
        world_time = {"status": "UNKNOWN"}
    elif isinstance(tick, dict):
        world_time = copy.deepcopy(tick)
    else:
        world_time = {"status": "KNOWN", "clock_id": "CLOCK-MAIN",
                      "tick": tick, "suborder": tick_suborder}
    return {
        "id": record_id,
        "anchor": {"scene_id": scene, "narration_suborder": narration,
                   "boundary": boundary, "world_time": world_time},
        "source": copy.deepcopy(SOURCE),
        "local_status": "PROPOSED",
        "positions": [],
        "holdings": [],
    }


def valid_model(slug="alpha"):
    base = record()
    base["local_status"] = "APPROVED"
    base["positions"] = [
        {"character_id": "CHAR-A", "location": {"status": "KNOWN", "location_id": "LOC-ROOM"}},
    ]
    base["holdings"] = [
        {"item_id": "ITEM-KEY", "holder": {"kind": "CHARACTER", "character_id": "CHAR-A"},
         "quantity": 1},
        {"item_id": "ITEM-STOCK", "holder": {"kind": "LOCATION", "location_id": "LOC-ROOM"},
         "quantity": 0},
    ]
    observation = record("OBS-001", "SC-002", 1, "AFTER", 4)
    observation["positions"] = [
        {"character_id": "CHAR-A", "location": {"status": "UNKNOWN"}},
    ]
    observation["holdings"] = [
        {"item_id": "ITEM-STOCK", "holder": {"kind": "UNKNOWN"}, "quantity": None},
    ]
    return {
        "schema_version": 1,
        "story_slug": slug,
        "baseline": base,
        "observations": [observation],
        "item_policies": [
            {"item_id": "ITEM-KEY", "tracking": "UNIQUE", "important": True},
            {"item_id": "ITEM-STOCK", "tracking": "STACK", "important": False},
        ],
        "hierarchy": [
            {"location_id": "LOC-WORLD", "parent": {"kind": "ROOT"}, "level": "WORLD"},
            {"location_id": "LOC-SITE", "parent": {"kind": "LOCATION", "location_id": "LOC-WORLD"},
             "level": "SITE"},
            {"location_id": "LOC-ROOM", "parent": {"kind": "LOCATION", "location_id": "LOC-SITE"},
             "level": "ROOM"},
        ],
        "metadata": {"display_label": "โลกตัวอย่าง"},
    }


class WorldStateModelTests(unittest.TestCase):
    def assert_invalid(self, model, db=None, slug="alpha", contains=None):
        errors = world_state_model.validation_errors(model, db or catalog_db(), slug)
        self.assertTrue(errors, "expected model to be rejected")
        if contains:
            self.assertIn(contains.lower(), " ".join(errors).lower(), errors)
        return errors

    def test_valid_declarations_are_scoped_to_each_story_even_when_ids_repeat(self):
        # The same opaque IDs can be reused in isolated story roots.
        alpha, beta = catalog_db(), catalog_db()
        self.assertEqual(world_state_model.validation_errors(valid_model("alpha"), alpha, "alpha"), [])
        self.assertEqual(world_state_model.validation_errors(valid_model("beta"), beta, "beta"), [])

    def test_flashback_world_time_inversion_is_valid_and_not_sorted_or_filtered(self):
        model = valid_model()
        before = copy.deepcopy(model)
        # Narration advances from SC-001 to SC-002 while the world clock moves back.
        self.assertEqual(model["baseline"]["anchor"]["world_time"]["tick"], 10)
        self.assertEqual(model["observations"][0]["anchor"]["world_time"]["tick"], 4)
        self.assertEqual(world_state_model.validation_errors(model, catalog_db(), "alpha"), [])
        self.assertEqual(model, before)
        self.assertEqual([row["id"] for row in model["observations"]], ["OBS-001"])

    def test_missing_facts_explicit_unknown_and_known_zero_remain_valid_distinct_values(self):
        model = valid_model()
        # Baseline arrays can omit facts; explicit UNKNOWN does not mean absent,
        # and a zero balance is distinct from a null (UNKNOWN) balance.
        model["baseline"]["positions"] = []
        self.assertEqual(world_state_model.validation_errors(model, catalog_db(), "alpha"), [])
        self.assertEqual(model["observations"][0]["positions"][0]["location"], {"status": "UNKNOWN"})
        self.assertIsNone(model["observations"][0]["holdings"][0]["quantity"])
        self.assertEqual(model["baseline"]["holdings"][1]["quantity"], 0)

    def test_catalog_membership_does_not_create_baseline_position_or_holding_facts(self):
        model = valid_model()
        model["baseline"]["positions"] = []
        model["baseline"]["holdings"] = []
        model["observations"] = []
        before = copy.deepcopy(model)
        self.assertEqual(world_state_model.validation_errors(model, catalog_db(), "alpha"), [])
        self.assertEqual(model, before)
        self.assertEqual(model["baseline"]["positions"], [])
        self.assertEqual(model["baseline"]["holdings"], [])

    def test_schema_version_rejects_wrong_and_boolean_versions(self):
        for version in (2, True):
            with self.subTest(version=version):
                model = valid_model()
                model["schema_version"] = version
                self.assert_invalid(model)

    def test_boolean_values_are_not_integer_time_suborders_or_quantities(self):
        mutations = [
            lambda m: m["baseline"]["anchor"].update(narration_suborder=True),
            lambda m: m["baseline"]["anchor"]["world_time"].update(tick=True),
            lambda m: m["baseline"]["anchor"]["world_time"].update(suborder=True),
            lambda m: m["baseline"]["holdings"][0].update(quantity=True),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                model = valid_model()
                mutate(model)
                self.assert_invalid(model)

    def test_closed_model_and_clock_shapes_reject_extra_or_malformed_fields(self):
        mutations = [
            lambda m: m.update(unrecognized="extra"),
            lambda m: m["baseline"]["anchor"]["world_time"].update(narration_order=3),
            lambda m: m["observations"][0]["positions"][0]["location"].update(location_id="LOC-ROOM"),
            lambda m: m["baseline"]["holdings"][0]["holder"].update(name="Arun"),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                model = valid_model()
                mutate(model)
                self.assert_invalid(model)

    def test_stable_tracked_ids_are_english_while_display_labels_can_be_thai(self):
        model = valid_model()
        db = catalog_db()
        db["characters"]["characters"][0]["name"] = "ตัวละครภาษาไทย"
        self.assertEqual(world_state_model.validation_errors(model, db, "alpha"), [])
        model["baseline"]["positions"][0]["character_id"] = "ตัวละคร-A"
        self.assert_invalid(model)

    def test_untracked_legacy_non_english_catalog_id_does_not_force_migration(self):
        model = valid_model()
        model["baseline"]["positions"] = []
        model["observations"] = []
        db = catalog_db()
        db["characters"]["characters"].append({"id": "ตัวละครเดิม", "name": "ตัวละครเก่า"})
        self.assertEqual(world_state_model.validation_errors(model, db, "alpha"), [])

    def test_selected_story_slug_must_match_exactly(self):
        self.assert_invalid(valid_model("beta"), slug="alpha", contains="story_slug")

    def test_cross_story_reference_never_falls_through_to_other_catalog(self):
        alpha_db = catalog_db()
        model = valid_model()
        model["baseline"]["positions"][0]["character_id"] = "CHAR-A-BETA"
        self.assert_invalid(model, db=alpha_db, contains="selected-story characters")

    def test_dangling_scene_character_location_item_and_holder_references_fail(self):
        mutations = [
            (lambda m: m["baseline"]["anchor"].update(scene_id="SC-MISSING"), "scenes reference"),
            (lambda m: m["baseline"]["positions"][0].update(character_id="CHAR-MISSING"),
             "characters reference"),
            (lambda m: m["baseline"]["positions"][0]["location"].update(location_id="LOC-MISSING"),
             "locations reference"),
            (lambda m: m["baseline"]["holdings"][0].update(item_id="ITEM-MISSING"),
             "items reference"),
            (lambda m: m["baseline"]["holdings"][0]["holder"].update(character_id="CHAR-MISSING"),
             "characters reference"),
            (lambda m: m["baseline"]["holdings"][0]["holder"].update(kind="LOCATION", location_id="LOC-MISSING")
             or m["baseline"]["holdings"][0]["holder"].pop("character_id", None), "locations reference"),
        ]
        for mutate, expected in mutations:
            with self.subTest(expected=expected):
                model = valid_model()
                mutate(model)
                self.assert_invalid(model, contains=expected)

    def test_duplicate_catalog_ids_and_malformed_selected_catalogs_fail_closed(self):
        db = catalog_db()
        db["items"]["items"].append(copy.deepcopy(db["items"]["items"][0]))
        self.assert_invalid(valid_model(), db=db, contains="duplicate selected-story items")
        malformed = catalog_db()
        malformed["scenes"]["scenes"] = None
        self.assert_invalid(valid_model(), db=malformed, contains="invalid selected-story scenes")

    def test_record_ids_are_unique_across_baseline_and_observations(self):
        model = valid_model()
        model["observations"][0]["id"] = model["baseline"]["id"]
        self.assert_invalid(model, contains="duplicate record id")

    def test_narrative_anchor_requires_unique_scene_suborder_and_boundary(self):
        model = valid_model()
        duplicate = record("OBS-002", "SC-001", 0, "BEFORE", 20)
        model["observations"].append(duplicate)
        self.assert_invalid(model, contains="duplicate narrative anchor")

    def test_exact_known_world_anchor_cannot_silently_define_same_tick_order(self):
        model = valid_model()
        duplicate = record("OBS-002", "SC-003", 2, "BEFORE", 10)
        model["observations"].append(duplicate)
        self.assert_invalid(model, contains="duplicate world anchor")

    def test_same_world_tick_with_explicit_suborders_and_boundaries_is_valid(self):
        model = valid_model()
        first = record("OBS-002", "SC-003", 2, "BEFORE", 10, 1)
        second = record("OBS-003", "SC-003", 3, "AFTER", 10, 2)
        model["observations"].extend((first, second))
        self.assertEqual(world_state_model.validation_errors(model, catalog_db(), "alpha"), [])

    def test_before_and_after_are_distinct_explicit_boundary_coordinates(self):
        model = valid_model()
        before = record("OBS-BEFORE", "SC-003", 5, "BEFORE", 20)
        after = record("OBS-AFTER", "SC-003", 5, "AFTER", 20)
        model["observations"].extend((before, after))
        self.assertEqual(world_state_model.validation_errors(model, catalog_db(), "alpha"), [])

    def test_distinct_clocks_and_unknown_world_times_are_not_compared_or_inferred(self):
        model = valid_model()
        model["observations"] = [
            record("OBS-CLOCK-B", "SC-002", 1, "AFTER", {
                "status": "KNOWN", "clock_id": "CLOCK-OTHER", "tick": 10, "suborder": 0}),
            record("OBS-UNKNOWN", "SC-003", 2, "AFTER", None),
        ]
        self.assertEqual(world_state_model.validation_errors(model, catalog_db(), "alpha"), [])
        self.assertEqual(model["observations"][1]["anchor"]["world_time"], {"status": "UNKNOWN"})

    def test_duplicate_unique_item_holders_fail_and_known_quantity_must_be_one(self):
        for holder in ({"kind": "CHARACTER", "character_id": "CHAR-B"},
                       {"kind": "UNKNOWN"},
                       {"kind": "LOCATION", "location_id": "LOC-ROOM"}):
            with self.subTest(holder=holder):
                model = valid_model()
                model["baseline"]["holdings"].append({
                    "item_id": "ITEM-KEY", "holder": holder, "quantity": 1})
                self.assert_invalid(model, contains="unique item has multiple holders")
        model = valid_model()
        model["baseline"]["holdings"][0]["quantity"] = 2
        self.assert_invalid(model, contains="unique item quantity")

    def test_unique_item_quantity_unknown_or_one_is_valid(self):
        for quantity in (None, 1):
            with self.subTest(quantity=quantity):
                model = valid_model()
                model["baseline"]["holdings"][0]["quantity"] = quantity
                self.assertEqual(world_state_model.validation_errors(model, catalog_db(), "alpha"), [])

    def test_stack_item_can_have_distinct_holders_but_not_duplicate_same_holder(self):
        model = valid_model()
        model["baseline"]["holdings"].append({
            "item_id": "ITEM-STOCK", "holder": {"kind": "CHARACTER", "character_id": "CHAR-B"},
            "quantity": 3})
        self.assertEqual(world_state_model.validation_errors(model, catalog_db(), "alpha"), [])
        model["baseline"]["holdings"].append({
            "item_id": "ITEM-STOCK", "holder": {"kind": "CHARACTER", "character_id": "CHAR-B"},
            "quantity": None})
        self.assert_invalid(model, contains="duplicate item/holder")

    def test_important_unique_item_without_holder_remains_unknown(self):
        model = valid_model()
        model["baseline"]["holdings"] = []
        model["observations"] = []
        self.assertEqual(world_state_model.validation_errors(model, catalog_db(), "alpha"), [])
        self.assertEqual(model["baseline"]["holdings"], [])
        self.assertTrue(model["item_policies"][0]["important"])

    def test_duplicate_or_missing_item_policies_fail_for_declared_holdings(self):
        duplicate = valid_model()
        duplicate["item_policies"].append(copy.deepcopy(duplicate["item_policies"][0]))
        self.assert_invalid(duplicate, contains="duplicate item policy")
        missing = valid_model()
        missing["item_policies"] = [p for p in missing["item_policies"] if p["item_id"] != "ITEM-KEY"]
        self.assert_invalid(missing, contains="missing item policy")

    def test_optional_hierarchy_allows_absence_root_and_unknown_parent(self):
        model = valid_model()
        model.pop("hierarchy")
        self.assertEqual(world_state_model.validation_errors(model, catalog_db(), "alpha"), [])
        model["hierarchy"] = [
            {"location_id": "LOC-WORLD", "parent": {"kind": "ROOT"}},
            {"location_id": "LOC-SITE", "parent": {"kind": "UNKNOWN"}},
            {"location_id": "LOC-ROOM", "parent": {"kind": "LOCATION", "location_id": "LOC-SITE"}},
        ]
        self.assertEqual(world_state_model.validation_errors(model, catalog_db(), "alpha"), [])

    def test_hierarchy_rejects_self_cycles_long_cycles_and_dangling_parents(self):
        cases = [
            ([{"location_id": "LOC-ROOM", "parent": {"kind": "LOCATION", "location_id": "LOC-ROOM"}}],
             "hierarchy cycle"),
            ([{"location_id": "LOC-SITE", "parent": {"kind": "LOCATION", "location_id": "LOC-ROOM"}},
              {"location_id": "LOC-ROOM", "parent": {"kind": "LOCATION", "location_id": "LOC-SITE"}}],
             "hierarchy cycle"),
            ([{"location_id": "LOC-ROOM", "parent": {"kind": "LOCATION", "location_id": "LOC-MISSING"}}],
             "missing selected-story locations reference"),
        ]
        for hierarchy, expected in cases:
            with self.subTest(hierarchy=hierarchy):
                model = valid_model()
                model["hierarchy"] = hierarchy
                self.assert_invalid(model, contains=expected)

    def test_duplicate_hierarchy_nodes_and_unknown_locations_fail(self):
        model = valid_model()
        model["hierarchy"].append(copy.deepcopy(model["hierarchy"][0]))
        self.assert_invalid(model, contains="duplicate hierarchy location")
        model = valid_model()
        model["hierarchy"] = [{"location_id": "LOC-MISSING", "parent": {"kind": "ROOT"}}]
        self.assert_invalid(model, contains="missing selected-story locations reference")

    def test_local_approved_or_forged_editorial_metadata_does_not_authenticate_humans(self):
        model = valid_model()
        model["metadata"] = {
            "human_approval": {"verified": True, "reviewer": "synthetic-fixture"},
            "source_revision": "STALE-SYNTHETIC-REVISION",
        }
        self.assertEqual(world_state_model.validation_errors(model, catalog_db(), "alpha"), [])
        self.assertEqual(world_state_model.HUMAN_APPROVAL, "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
