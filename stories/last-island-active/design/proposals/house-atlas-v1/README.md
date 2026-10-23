# คู่มืออ้างอิงบ้านเพื่อเขียนนิยาย — House Atlas v1

เริ่มที่ [คู่มือเอเจนต์นักเขียน](./WRITER_AGENT_RUNBOOK_TH.md) และ [บัตรอ้างอิงต่อบ้าน/ฉาก](./writer_reference_card.json) เป้าหมายคือเขียนห้อง ทางเดิน ชั้น และลำดับต่อเติมได้ต่อเนื่อง ไม่ใช่สร้างเกมหรือ CAD **พร้อมใช้เป็นตัวอย่างอ้างอิง PROPOSED; ยังไม่พร้อมอ้างว่าเป็นบ้านของกลุ่มจริงที่ ADOPTED แล้ว** ไม่ผูก archetype ทั้ง 8 กับกลุ่มใดโดยไม่มีหลักฐาน

[สภาพก่อสร้างสี่ช่วง](./construction_stages.json) แยก target blueprint จาก as-built และ usability: โครงเริ่มต้น → ผนัง/หลังคาบางส่วน → ชั้นล่างใช้งาน → เปิดบันได/ชั้นบน ทั้งหมดเป็น fixture สังเคราะห์ที่เขียนด้วยมือ ไม่ใช่ผล replay หรือลำดับเหตุการณ์จริง ภาพ pilot แสดงแบบเป้าหมาย ต้องอ่าน snapshot ของฉากก่อนใช้อ้างอิง

**Status: PROPOSED / UNVERIFIED.** This package contains design concepts and research notes. It is not an engine-supported schema or input format, does not establish story facts, and does not authorize canon or ledger changes.

All eight archetypes are unplaced schematic programs; none claims geometry validity. The separate workshop pilot is the only placed example intended for bounded static proposal QA, under its declared diagram convention. That QA cannot establish in-game buildability, movement, structural safety, support, or performance.

The Last Island design direction uses square and triangle module vocabulary and exactly one main pillar per whole house. Triangle angles and dimensions remain unknown; a right-isosceles triangle is only a declared pilot diagram convention. Centrality has no defined metric; pillar height, influence, relocation, and structural effects remain unknown. Other stories do not inherit these rules. No resource costs, game HP, raid resistance, or structural-performance values are modeled.

## Package index

- [Development roadmap](../../../../../docs/BUILDING_MODULE_ROADMAP_TH.md) — proposed phases and open decisions.
- [Thai design brief](./DESIGN_BRIEF_TH.md) — eight original unplaced archetypes and their vertical programs.
- [Archetype programs](./archetype_programs.json) — machine-readable proposal descriptions; not geometry or engine input.
- [Source audit](./research/SOURCE_AUDIT_TH.md) and [source index](./research/sources.json) — evidence levels and limits. Sources inform vocabulary only; no Rust floorplans, mechanics, images, or costs are imported.
- [Fillable proposal template](./house_template_proposed.json) — human-editable proposal scaffold, explicitly outside the engine contract.
- [Workshop pilot proposal](./pilot_workshop_versions.json) — versioned placed example.
- [Illustration directory](./diagrams/) — original proposal diagrams. The eight archetype SVGs show unplaced room/massing concepts; pilot SVGs show floor plans and a section for each version.
- [Concept diagram renderer](./tools/render_concepts.py), [pilot plan/section renderer](./tools/render_pilot.py) and [pilot static QA](./tools/qa_pilot.py) — local proposal-only tools.

## Local proposal QA

Run from the repository root:

```powershell
python stories/last-island-active/design/proposals/house-atlas-v1/tools/qa_pilot.py
python -m unittest discover -s tests -p test_house_proposal.py -v
python -m unittest discover -s tests -p test_house_proposal_assets.py -v
```

The pilot checker is a standalone static proposal preflight. It does not feed the engine, CLI, story context, canon, or ledger. Unplaced archetypes receive no geometry-valid claim. A static pass only means the declared proposal data satisfies the checks implemented for that convention; game rules and physical feasibility stay unknown.

All owner/player/group/occupant/location bindings and chapter references remain empty or null unless separately authorized and evidenced. `PROPOSED`, local validation, hashes, and CI do not establish editorial approval. Keep historical versions immutable; any future canon or ledger work requires its own explicit authorization and review.

Source check against current main: existing `data/canon.json`, `data/scenes.json` and `data/locations.json` describe the protagonist's 2×2 plan/wooden house and later stone upgrade. Their original statuses and the separate author-memory/empty-approved-ledger boundary remain intact. This package does not bind `HOUSE-PROP-WORKSHOP-001`, new room plans or archetypes to those records, and does not reinterpret accepted manuscripts. No structured adopted house-version card was found in the inspected data.

Static pilot QA checks declared tile edges/overlap, room/door relationships, floor/void separation, stair endpoints and illustrative centroid. It is not a complete schema validator, room-volume/roof/clearance solver or gameplay test. Construction snapshots/cards are checked as static examples; construction replay, idempotency and automated POV retrieval are future acceptance criteria only. Existing engine checks do not load this proposal as story state.
