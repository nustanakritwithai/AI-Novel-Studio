"""Render original, UNPLACED program diagrams; no engine or geometry solver."""
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Positions below are page-layout pixels, NOT building coordinates or dimensions.
PROGRAMS = {
    "STARTER": ("Low core / partial loft / future upper", ["Rest", "Shared", "Store", "Entry"],
                [(0, 0, 2, 1), (2, 0, 1, 1)], "Partial loft", "Short route; privacy remains a design choice"),
    "MAKER": ("Tall workshop + adjacent planning mezzanine", ["Work", "Store", "Plan", "Entry"],
              [(0, 0, 1, 2), (1, 0, 2, 1), (1, 1, 2, 1)], "Quiet mezzanine", "Open volume may connect sound and sightlines"),
    "COMMUNAL": ("Double-height hall + bedroom gallery", ["Hall", "Shared", "Rest", "Gallery"],
                 [(0, 0, 1, 2), (1, 0, 1, 1), (1, 1, 1, 1), (2, 0, 1, 2)], "Upper gallery", "Shared hall / private edges; no occupant count"),
    "EXCHANGE": ("Public ground / private upper", ["Welcome", "Store", "Private", "Entry"],
                 [(0, 0, 3, 1), (0, 1, 2, 1)], "Private upper", "Separate visitor and resident circulation"),
    "ARCHIVE": ("Reading void + upper shelves / gallery", ["Reading", "Shelves", "Gallery", "Entry"],
                [(0, 0, 1, 2), (1, 0, 2, 1), (1, 1, 2, 1)], "Reading void", "Memory and access are proposed room uses only"),
    "REST": ("Essential guest rooms below / retreat above", ["Guest", "Shared", "Retreat", "Entry"],
             [(0, 0, 3, 1), (1, 1, 1, 1)], "Resident retreat", "Ground access does not prove accessibility compliance"),
    "GARDEN": ("Partial upper + stepped roof terraces", ["Utility", "Garden", "Drying", "Entry"],
               [(0, 0, 3, 1), (0, 1, 1, 1)], "Proposed terrace", "Occupied roof differs from covering roof; support UNKNOWN"),
    "REUSE": ("Alternative stairs / reopened gallery / infilled void", ["Old use?", "New use?", "Gallery?", "Entry?"],
              [(0, 0, 3, 1), (0, 1, 1, 1), (2, 1, 1, 1)], "Alternative revisions", "Hypothetical reuse lineage; no event or previous owner asserted"),
}


def text(x, y, value, size=16, color="#1f3345", extra=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" {extra}>{escape(value)}</text>'


def render(identifier, name):
    subtitle, rooms, masses, upper, implication = PROGRAMS[identifier]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1160" height="630" viewBox="0 0 1160 630">',
        f'<title>{escape(identifier + ": " + name)}</title>',
        '<desc>Original unplaced program concept. Page pixels are not geometry. No game or structural validation.</desc>',
        '<rect width="1160" height="630" fill="#f7f5ee"/>',
        '<g font-family="Arial, sans-serif">',
        text(34, 38, f"{identifier} / ORIGINAL PROPOSAL", 25),
        text(34, 69, subtitle, 19),
        text(34, 98, "UNPLACED CONCEPT - icons/massing are editorial sketches; module angles and dimensions UNKNOWN", 14, "#a4422d"),
        text(34, 142, "A. MODULE / ROOM RELATIONSHIPS", 17),
        text(570, 142, "B. SECTION / MASSING IDEA", 17),
    ]
    points = [(110, 220), (320, 220), (320, 390), (110, 390)]
    # Illustrative relationship sketches, never prescribed routes or floorplans.
    links = {
        "STARTER": [(0, 1), (1, 2), (1, 3)],
        "MAKER": [(0, 1), (0, 3), (1, 2)],
        "COMMUNAL": [(0, 1), (0, 2), (0, 3)],
        "EXCHANGE": [(3, 0), (0, 1), (1, 2)],
        "ARCHIVE": [(3, 0), (0, 2), (2, 1)],
        "REST": [(3, 1), (1, 0), (1, 2)],
        "GARDEN": [(3, 0), (0, 1), (1, 2)],
        "REUSE": [(3, 0), (0, 2), (2, 1)],
    }
    for a, b in links[identifier]:
        x, y = points[a]
        xx, yy = points[b]
        parts.append(f'<path d="M{x},{y} L{xx},{yy}" stroke="#86999f" stroke-width="3" stroke-dasharray="7 6"/>')
    for number, ((x, y), label) in enumerate(zip(points, rooms)):
        parts.append(f'<rect x="{x-64}" y="{y-39}" width="128" height="78" rx="3" fill="#dae6df" stroke="#35665b" stroke-width="2"/>')
        parts.append(text(x, y+5, label, 17, extra='text-anchor="middle"'))
    parts.append('<path d="M415,330 L475,330 L415,390 Z" fill="#efc985" stroke="#927340" stroke-width="2"/>')
    parts.append('<path d="M384,220 L445,330" fill="none" stroke="#86999f" stroke-dasharray="7 6"/>')
    parts.append(text(398, 418, "Triangle option", 13))
    parts.append(text(35, 475, "Symbols/links illustrate relationships, not a prescribed room graph.", 13))
    parts.append(text(35, 497, "One central whole-house pillar; metric location remains UNKNOWN.", 13))
    # Symbolic section and silhouette: no floor clearance or stair mechanics claimed.
    for x, level, width, height in masses:
        xx, yy = 605 + x*142, 420-(level+height)*100
        parts.append(f'<rect x="{xx}" y="{yy}" width="{width*142}" height="{height*100}" fill="#c4d8df" stroke="#365767" stroke-width="2"/>')
    parts += [text(595, 444, "Ground (ordinal 0)", 13), text(595, 208, "Upper / loft (proposed)", 13)]
    parts.append(text(595, 468, upper, 16))
    parts.append(text(595, 493, "Stair route, openings and local heights require a placed version.", 13))
    parts.append(text(35, 543, implication, 16))
    parts.append(text(35, 573, "Height units, support, headroom, pillar influence and gameplay feasibility: UNKNOWN", 15, "#a4422d"))
    parts.append(text(35, 602, "PROPOSED | no owner / group / canon location / chapter binding | human approval UNVERIFIED", 14))
    parts.append('</g></svg>')
    return "\n".join(parts) + "\n"


def main():
    programs = json.loads((ROOT / "archetype_programs.json").read_text(encoding="utf-8"))
    destination = ROOT / "diagrams"
    destination.mkdir(exist_ok=True)
    for program in programs["programs"]:
        (destination / (program["id"] + ".svg")).write_text(
            render(program["id"], program["name_th"]), encoding="utf-8")
    print("Rendered 8 original UNPLACED program diagrams; no geometry or game feasibility claimed.")


if __name__ == "__main__":
    main()
