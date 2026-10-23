"""Bounded QA for the Last Island workshop proposal pilot (not engine geometry)."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


DEFAULT_INPUT = Path(__file__).resolve().parents[1] / "pilot_workshop_versions.json"
EPS = 1e-9


def _segment_key(a, b):
    return tuple(sorted((tuple(a), tuple(b))))


def _poly_edges(poly):
    return [_segment_key(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))]


def _area(poly):
    return abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly))) / 2)


def _centroid(polygons):
    cross_sum = cx_sum = cy_sum = 0.0
    for poly in polygons:
        for i, (x1, y1) in enumerate(poly):
            x2, y2 = poly[(i + 1) % len(poly)]
            cross = x1 * y2 - x2 * y1
            cross_sum += cross
            cx_sum += (x1 + x2) * cross
            cy_sum += (y1 + y2) * cross
    if abs(cross_sum) < EPS:
        return None
    return (cx_sum / (3 * cross_sum), cy_sum / (3 * cross_sum))


def _positive_overlap(a, b):
    """Separating-axis test for positive-area overlap of convex polygons."""
    for poly in (a, b):
        for p, q in zip(poly, poly[1:] + poly[:1]):
            axis = (-(q[1] - p[1]), q[0] - p[0])
            pa = [x * axis[0] + y * axis[1] for x, y in a]
            pb = [x * axis[0] + y * axis[1] for x, y in b]
            if min(max(pa), max(pb)) - max(min(pa), min(pb)) <= EPS:
                break
        else:
            continue
        break
    else:
        return True
    return False


def _connected(ids, adjacency):
    if not ids:
        return False
    seen, todo = {ids[0]}, [ids[0]]
    while todo:
        for other in adjacency.get(todo.pop(), ()):
            if other in ids and other not in seen:
                seen.add(other)
                todo.append(other)
    return seen == set(ids)


def _fail(errors, condition, message):
    if not condition:
        errors.append(message)


def validate_pilot(data):
    """Return focused proposal-data errors; an empty list is schematic QA only."""
    errors = []
    _fail(errors, data.get("status") == "PROPOSED", "top-level status must be PROPOSED")
    _fail(errors, data.get("human_editorial_approval") == "UNVERIFIED", "editorial approval must remain UNVERIFIED")
    house = data.get("house", {})
    versions = house.get("versions", [])
    _fail(errors, [v.get("version_id") for v in versions] == ["V01", "V02", "V03"], "expected pilot versions V01, V02, V03")
    _fail(errors, house.get("status") == "PROPOSED" and house.get("owner_player_ref") is None and house.get("owner_group_ref") is None and house.get("canon_location_ref") is None and house.get("chapter_refs") == [], "house must remain an unbound proposal")
    pillar_id = None
    for vi, version in enumerate(versions):
        prefix = version.get("version_id", "?")
        _fail(errors, version.get("status") == "PROPOSED" and version.get("lineage_kind") == "DESIGN_PROPOSAL_ONLY", f"{prefix}: version must be proposal-only")
        _fail(errors, version.get("parent_version_id") == (None if vi == 0 else versions[vi - 1]["version_id"]), f"{prefix}: invalid design parent lineage")
        _validate_version(version, house, prefix, errors)
        pillars = version.get("pillars", [])
        _fail(errors, len(pillars) == 1, f"{prefix}: expected exactly one whole-house pillar")
        if len(pillars) == 1:
            pillar = pillars[0]
            pillar_id = pillar_id or pillar.get("pillar_id")
            _fail(errors, pillar.get("pillar_id") == pillar_id, f"{prefix}: pillar identity must stay stable")
            _fail(errors, pillar.get("centering_metric_ref") == "ground_footprint_area_centroid_xy", f"{prefix}: centering metric must be explicit")
            center = _centroid([t["polygon_xy"] for t in version["tiles"] if t["floor_index"] == 0])
            target = pillar.get("centering_target_xy")
            _fail(errors, center is not None and target is not None and all(math.isclose(center[i], target[i], abs_tol=EPS) for i in (0, 1)), f"{prefix}: declared pillar target must equal ground footprint area centroid")
            _fail(errors, pillar.get("xy") == target and pillar.get("z_extent_h") is None, f"{prefix}: pillar needs declared XY and UNKNOWN vertical extent")
        _fail(errors, version.get("physical_feasibility") == "UNKNOWN", f"{prefix}: physical feasibility must remain UNKNOWN")
    return errors


def _validate_version(v, house, prefix, errors):
    tiles = {t["tile_id"]: t for t in v.get("tiles", [])}
    rooms = {r["room_id"]: r for r in v.get("rooms", [])}
    floors = {f["floor_index"]: f for f in v.get("floors", [])}
    by_floor = {fi: [tiles[t] for t in floor.get("tile_refs", []) if t in tiles] for fi, floor in floors.items()}
    adjacency = {fi: {t["tile_id"]: set() for t in ts} for fi, ts in by_floor.items()}
    actual_edges = {}
    for fi, ts in by_floor.items():
        floor = floors[fi]
        _fail(errors, len(ts) == len(floor.get("tile_refs", [])), f"{prefix}: floor {fi} has an unknown tile ref")
        _fail(errors, set(floor.get("room_refs", [])) <= set(rooms), f"{prefix}: floor {fi} has an unknown room ref")
        for tile in ts:
            p = tile.get("polygon_xy", [])
            if tile.get("shape") == "SQUARE":
                lengths = [math.dist(a, b) for a, b in zip(p, p[1:] + p[:1])]
                _fail(errors, len(p) == 4 and math.isclose(_area(p), 1, abs_tol=EPS) and all(math.isclose(x, 1, abs_tol=EPS) for x in lengths), f"{prefix}: {tile['tile_id']} violates square 1U convention")
            elif tile.get("shape") == "RIGHT_ISOSCELES_TRIANGLE":
                lengths = sorted(math.dist(a, b) for a, b in zip(p, p[1:] + p[:1]))
                _fail(errors, len(p) == 3 and math.isclose(_area(p), .5, abs_tol=EPS) and len(lengths) == 3 and math.isclose(lengths[0], 1, abs_tol=EPS) and math.isclose(lengths[1], 1, abs_tol=EPS), f"{prefix}: {tile['tile_id']} violates right-isosceles half-square convention")
            for other in ts:
                if tile["tile_id"] < other["tile_id"] and _positive_overlap(p, other.get("polygon_xy", [])):
                    errors.append(f"{prefix}: tiles {tile['tile_id']} and {other['tile_id']} overlap")
        for void in floor.get("voids", []):
            for tile in ts:
                _fail(errors, not _positive_overlap(void.get("polygon_xy", []), tile.get("polygon_xy", [])), f"{prefix}: {void['void_id']} overlaps {tile['tile_id']}")
        for i, a in enumerate(ts):
            for b in ts[i + 1:]:
                shared = set(_poly_edges(a["polygon_xy"])) & set(_poly_edges(b["polygon_xy"]))
                if shared:
                    actual_edges[(fi, *sorted((a["tile_id"], b["tile_id"])))] = sorted(shared)[0]
                    adjacency[fi][a["tile_id"]].add(b["tile_id"])
                    adjacency[fi][b["tile_id"]].add(a["tile_id"])
        _fail(errors, _connected([t["tile_id"] for t in ts], adjacency[fi]), f"{prefix}: floor {fi} footprint is disconnected")
    declared = {}
    for e in v.get("edge_connections", []):
        key = (next((fi for fi, ts in by_floor.items() if e.get("tile_a_id") in {t['tile_id'] for t in ts}), -1), *sorted((e.get("tile_a_id"), e.get("tile_b_id"))))
        declared[key] = _segment_key(*e.get("segment_xy", [[], []]))
    _fail(errors, declared == actual_edges, f"{prefix}: declared full-edge connections do not match tile geometry")

    for room in rooms.values():
        rid, fi = room["room_id"], room["floor_index"]
        refs = room.get("tile_refs", [])
        owned = [r for r in refs if r in tiles and tiles[r].get("floor_index") == fi and tiles[r].get("room_ref") == rid]
        _fail(errors, refs and len(owned) == len(refs), f"{prefix}: {rid} tile ownership/floor refs disagree")
        _fail(errors, _connected(owned, adjacency.get(fi, {})), f"{prefix}: room {rid} tiles are disconnected")
        _fail(errors, rid in floors.get(fi, {}).get("room_refs", []), f"{prefix}: {rid} is absent from its floor")

    room_graph = {rid: set() for rid in rooms}
    edge_by_id = {e.get("edge_id"): e for e in v.get("edge_connections", [])}
    for door in v.get("doors", []):
        source, dest = door.get("from_room_id"), door.get("to_room_id")
        _fail(errors, source in rooms and rooms[source].get("floor_index") == door.get("floor_index"), f"{prefix}: {door.get('door_id')} has invalid source room")
        if door.get("exterior"):
            tile = tiles.get(door.get("boundary_tile_id"))
            seg = _segment_key(*door.get("boundary_segment_xy", [[], []]))
            _fail(errors, tile is not None and tile.get("room_ref") == source and seg in _poly_edges(tile.get("polygon_xy", [])), f"{prefix}: {door.get('door_id')} is not on its source-room boundary")
        else:
            edge = edge_by_id.get(door.get("edge_ref"))
            _fail(errors, edge is not None and dest in rooms and rooms[dest].get("floor_index") == door.get("floor_index"), f"{prefix}: {door.get('door_id')} has invalid destination/edge")
            if edge and dest in rooms and source in rooms:
                a, b = tiles.get(edge["tile_a_id"]), tiles.get(edge["tile_b_id"])
                _fail(errors, {a.get("room_ref") if a else None, b.get("room_ref") if b else None} == {source, dest}, f"{prefix}: {door.get('door_id')} rooms do not own its adjacent edge tiles")
                room_graph[source].add(dest)
                room_graph[dest].add(source)

    landing_by_id = {x.get("landing_id"): x for x in v.get("landings", [])}
    void_by_id = {x.get("void_id"): (fi, x) for fi, f in floors.items() for x in f.get("voids", [])}
    for stair in v.get("stairs", []):
        endpoints = [stair.get("from", {}), stair.get("to", {})]
        _fail(errors, endpoints[0].get("floor_index") != endpoints[1].get("floor_index"), f"{prefix}: {stair.get('stair_id')} endpoints must use different floors")
        for end, opposite in zip(endpoints, reversed(endpoints)):
            landing, opening = landing_by_id.get(end.get("landing_ref")), void_by_id.get(end.get("opening_ref"))
            room_id, fi = end.get("room_id"), end.get("floor_index")
            _fail(errors, landing is not None and landing.get("floor_index") == fi and landing.get("room_id") == room_id and landing.get("opening_ref") == end.get("opening_ref"), f"{prefix}: {stair.get('stair_id')} landing does not match endpoint")
            _fail(errors, opening is not None and opening[0] == fi and opposite.get("floor_index") in opening[1].get("opens_to_floor_indices", []) and opening[1].get("stair_opening_for") == stair.get("stair_id"), f"{prefix}: {stair.get('stair_id')} opening is missing or mismatched")
            if opening and room_id in rooms and rooms[room_id].get("floor_index") == fi:
                void_poly = opening[1].get("polygon_xy", [])
                adjacent = any(set(_poly_edges(tiles[t]["polygon_xy"])) & set(_poly_edges(void_poly)) for t in rooms[room_id].get("tile_refs", []) if t in tiles)
                _fail(errors, adjacent, f"{prefix}: {stair.get('stair_id')} landing room is not edge-adjacent to opening")
        if endpoints[0].get("room_id") in room_graph and endpoints[1].get("room_id") in room_graph:
            a, b = endpoints[0]["room_id"], endpoints[1]["room_id"]
            room_graph[a].add(b)
            room_graph[b].add(a)
    if rooms:
        _fail(errors, _graph_reaches(v.get("entry_room_id"), room_graph, set(rooms)), f"{prefix}: not every occupied room is reachable from entry")


def _graph_reaches(start, graph, expected):
    if start not in graph:
        return False
    return _connected(list(expected), graph) and start in expected


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args(argv)
    errors = validate_pilot(json.loads(args.input.read_text(encoding="utf-8")))
    if errors:
        print("FAIL_WITHIN_DECLARED_SCHEMATIC_CONVENTION")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("PASS_WITHIN_DECLARED_SCHEMATIC_CONVENTION; physical feasibility remains UNKNOWN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
