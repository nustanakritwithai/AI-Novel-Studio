"""Original writer-reference plans/section from the fixed proposed pilot data."""
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def label(x, y, value, size=14, color="#243b4a"):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color}">{escape(value)}</text>'


def section_interval(polygon, y=-0.5):
    """Intersection with the declared horizontal section, excluding parallel edges."""
    values = []
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        if min(a[1], b[1]) <= y < max(a[1], b[1]):
            values.append(a[0] + (y-a[1])*(b[0]-a[0])/(b[1]-a[1]))
    return (min(values), max(values)) if len(values) >= 2 else None


def render(version):
    identifier = version["version_id"]
    tiles = {t["tile_id"]: t for t in version["tiles"]}
    rooms = {r["room_id"]: r for r in version["rooms"]}
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="920" viewBox="0 0 1200 920">',
             f'<title>Workshop {identifier}: proposed floor plans and section</title>',
             '<desc>Illustrative geometry only. A target blueprint is not an as-built snapshot or POV knowledge.</desc>',
             '<rect width="1200" height="920" fill="#f6f4ed"/><g font-family="Arial, sans-serif">',
             label(30, 36, f'HOUSE-PROP-WORKSHOP-001 / {identifier} / PROPOSED', 23),
             label(30, 64, 'Blueprint only. Check construction_stages.json and writer card before describing a scene.', 16),
             label(30, 89, 'Illustrative unit square + 45/45/90 triangle convention; U/H have NO metre or game conversion.', 14, '#a34631')]
    colors = ['#c4ddd2', '#d6dfed', '#e5d4b7', '#d9c8e4', '#badde4', '#e8d8ce']
    room_colors = {name: colors[i % len(colors)] for i, name in enumerate(rooms)}
    for floor in version["floors"]:
        index = floor["floor_index"]
        offset = 30 + index*580
        scale, cx, cy = 70, offset+240, 310
        xy = lambda point: (cx+point[0]*scale, cy-point[1]*scale)
        points = lambda polygon: ' '.join(f'{x:.1f},{y:.1f}' for x, y in map(xy, polygon))
        parts.append(label(offset, 125, f'PLAN: floor {index} / elevation {floor["elevation_h"]} H', 18))
        for tile in version["tiles"]:
            if tile["floor_index"] != index:
                continue
            polygon = tile["polygon_xy"]
            parts.append(f'<polygon points="{points(polygon)}" fill="{room_colors[tile["room_ref"]]}" stroke="#4f6870" stroke-width="2"/>')
            x, y = xy([sum(p[0] for p in polygon)/len(polygon), sum(p[1] for p in polygon)/len(polygon)])
            parts.append(label(x-31, y, tile["tile_id"].replace('TILE-', ''), 11))
        for void in floor["voids"]:
            parts.append(f'<polygon points="{points(void["polygon_xy"])}" fill="#ffffff" stroke="#af5485" stroke-dasharray="5 4" stroke-width="2"/>')
            polygon = void["polygon_xy"]
            x, y = xy([sum(p[0] for p in polygon)/len(polygon), sum(p[1] for p in polygon)/len(polygon)])
            parts.append(label(x-24, y, 'OPENING' if void["stair_opening_for"] else 'VOID', 11, '#99436d'))
        edges = {e["edge_id"]: e for e in version["edge_connections"]}
        for door in version["doors"]:
            if door["floor_index"] != index:
                continue
            segment = door.get('boundary_segment_xy') if door["exterior"] else edges[door["edge_ref"]]["segment_xy"]
            a, b = map(xy, segment)
            parts.append(f'<path d="M{a[0]},{a[1]} L{b[0]},{b[1]}" stroke="#e28032" stroke-width="6"/>')
        if index == 0:
            x, y = xy(version["pillars"][0]["xy"])
            parts.append(f'<circle cx="{x}" cy="{y}" r="7" fill="#233b4b"/>')
            parts.append(label(x+10, y-10, 'ONE HOUSE PILLAR', 11))
        parts.append(label(offset, 475, 'Orange: explicit doorway edge | dashed magenta: no floor', 13))
        parts.append(label(offset, 499, 'Stair endpoints: use IDs/landings below; no physical stair plan.', 13))
    if len(version["floors"]) == 1:
        parts.append(label(630, 230, 'No upper floor / stair in V01', 22))
        parts.append(label(630, 261, 'Later expansions do not exist in this design version.', 15))
    parts.append(label(30, 550, 'SECTION A: y = -0.5 U (room-volume cut; gaps remain gaps)', 17))
    for room in version["rooms"]:
        bottom, top = room["vertical_extent_h"]
        for ref in room["tile_refs"]:
            interval = section_interval(tiles[ref]["polygon_xy"])
            if interval:
                left, right = interval
                x, y = 270+left*90, 755-top*50
                parts.append(f'<rect x="{x}" y="{y}" width="{(right-left)*90}" height="{(top-bottom)*50}" fill="{room_colors[room["room_id"]]}" stroke="#4f6870"/>')
    parts.append(label(30, 780, 'Section heights symbolic H; pillar vertical extent/support UNKNOWN (not drawn as a tall column).', 14))
    for number, stair in enumerate(version["stairs"]):
        a, b = stair['from'], stair['to']
        parts.append(label(30, 805+number*23, f'{stair["stair_id"]}: F{a["floor_index"]} {a["room_id"]} -> F{b["floor_index"]} {b["room_id"]}', 14))
    roof_kinds = ', '.join(sorted({r['kind'] for r in version['roofs']}))
    parts.append(label(30, 851, 'Roof records: '+roof_kinds+' (see data for coverage/access; not all roof is walkable)', 13))
    parts.append(label(30, 878, 'Room uses / change history: pilot JSON and Thai writer guide. No owner/group/chapter assignment.', 14))
    parts.append(label(30, 903, 'Game feasibility / structural safety UNKNOWN | human approval UNVERIFIED | no canon/ledger application', 14, '#a34631'))
    return '\n'.join(parts+['</g></svg>'])+'\n'


def main():
    document = json.loads((ROOT/'pilot_workshop_versions.json').read_text(encoding='utf-8'))
    for version in document['house']['versions']:
        (ROOT/'diagrams'/('WORKSHOP-'+version['version_id']+'.svg')).write_text(render(version),encoding='utf-8')
    print('Rendered 3 proposed blueprint floor-plan/section diagrams, not as-built or game validation.')


if __name__ == '__main__':
    main()
