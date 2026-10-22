# CONTEXT PACK: SC-006

> Generated from repository data. Do not treat this file as a replacement for approved prose.

## PROJECT STATUS
# AI Novel Studio — สถานะ
โครงการ: LAST ISLAND — AI NOVEL STUDIO
เฟส: OUTLINE_NOT_CANON_PROSE
ตอนที่วางโครงแล้ว: 1 | ฉากทั้งหมด: 8
ฉาก: PLANNED=8 DRAFT=0 REVIEW=0 APPROVED=0 CANON=0
ข้อมูล Canon ล็อกแล้ว: 13
รายละเอียดกลไกเกมที่ยังไม่ยืนยัน: 4 (UNKNOWN ≠ PASS)
Plot Threads ยังเปิดอยู่: 2
สถานะหลังฉากที่อนุมัติ: ยังไม่มีฉาก prose ที่อนุมัติ
คำสั่งถัดไป: python scripts/novelctl.py brief SC-001

## NON-NEGOTIABLE AGENT RULES

1. LOCKED user directives override AI proposals. No retroactive changes without approval.

2. The world-championship of 100 contestants is FUTURE, never in the private-game opening.

3. Distinguish STORY directive from GAMEPLAY verification; UNVERIFIED ≠ PASS.

4. Write only draft prose. Do not update canon or approved story_state before editor review.

5. Preserve POV knowledge, known inventory, injury ambiguity, 2×2 single story and single scrap crate.

## APPROVED CANON IN SCOPE

- **FACT-001** โลกของนิยายเป็นยุค Full-Dive VR ผู้เล่นเข้าไปสัมผัสและใช้ชีวิตในเกมเสมือนจริง

- **FACT-009** พระเอกถูกผู้เล่นอื่นซุ่มโจมตีด้วยไม้เบสบอล และเกิดการต่อสู้ด้วยไม้เบสบอลทั้งสองฝ่าย

- **FACT-010** พระเอกชนะอย่างเฉียดฉิว และเก็บหินกับเศษวัสดุที่ผู้แพ้ทำตกไว้

- **FACT-012** ใช้เกมเพลย์จริงของสตรีมเมอร์เป็นหลักฐานกฎและพฤติกรรม แต่ต้องแยกจากกฎการแข่งขันและการแต่งเติมเพื่อความบันเทิง

- **FACT-013** พระเอกไม่ถูกกำหนดให้ชนะเพราะเป็นตัวละครหลัก; การแพ้ชนะและของที่มีต้องสอดคล้องกับเหตุการณ์และกฎในเรื่อง

## SELECTED SCENE: SC-006

## RELEVANT SCENES & CAUSAL ORDER

### SC-005 กล่องเศษวัสดุ (PLANNED)

Goal: กล่องเศษวัสดุ / Conflict: โลภเก็บของบนถนนอันตราย

Beats: เดินตามถนนพบกล่องเศษวัสดุหนึ่งกล่อง หยุดเก็บใส่กระเป๋าโดยไม่มีใครป้องกัน

Outcome: ได้เศษวัสดุจากกล่อง; ยังไม่มีข้อมูลจำนวนชิ้น

Preconditions: journey_started, bat_crafted

Effects: {"road_crate_collected": true}

### SC-006 การปะทะแรก (PLANNED)

Goal: การปะทะแรก / Conflict: ซุ่มโจมตีจากผู้เล่นอื่น

Beats: ถูกผู้เล่นอื่นซุ่มโจมตีด้วยไม้เบสบอล; ต่อสู้ดุเดือดด้วยอาวุธเท่ากันและชนะเฉียดฉิว

Outcome: พระเอกรอด แต่สุขภาพ/ความเสียหายที่แน่นอนยังไม่กำหนด

Preconditions: road_crate_collected, bat_crafted

Effects: {"first_pvp_won": true}

### SC-007 ของจากผู้แพ้ (PLANNED)

Goal: ของจากผู้แพ้ / Conflict: ทรัพยากรสำคัญกับความเสี่ยง

Beats: เก็บหินและเศษวัสดุที่ผู้แพ้ทำตก และตัดสินใจกลับไปทำบ้านก่อนเสี่ยงต่อ

Outcome: เพิ่มทรัพยากรที่ไม่มีการระบุตัวเลขแล้วมุ่งกลับจุดสร้างบ้าน

Preconditions: first_pvp_won

Effects: {"defeated_player_loot_collected": true, "heading_to_base_site": true}

## CHARACTERS IN SCOPE

- **CHAR-001 พระเอก** — POV ตัวหลักช่วงเริ่มเกม; known: สังเกตว่าบริเวณเริ่มต้นมีบ้านคนอื่นหนาแน่น; ตัดสินใจย้ายทำเล; ชนะการปะทะแรกอย่างเฉียดฉิว; unknown: ชื่อจริง; อายุ; อาชีพ; ทักษะเกมก่อนเข้ามา; ภูมิหลัง; ความสัมพันธ์ในโลกจริง

  - After SC-003: knows บริเวณเริ่มต้นมีผู้เล่นตั้งฐานหนาแน่น

  - After SC-006: knows อาจถูกผู้เล่นอื่นโจมตีระหว่างเก็บของ

- **CHAR-002 ผู้เล่นซุ่มโจมตีข้างถนน** — คู่ต่อสู้ครั้งแรก; known: ใช้ไม้เบสบอล; ซุ่มโจมตีพระเอก; แพ้ในการปะทะ; unknown: ชื่อ; เพศ; ภูมิหลัง; สังกัดแคลน; ความตั้งใจ; จะกลับมาในอนาคตหรือไม่

## MECHANIC RESEARCH STATUS (DO NOT OVERSTATE)

- MECH-002 คราฟต์ไม้เบสบอลจากไม้เป็นอาวุธชิ้นแรก: GAMEPLAY=UNVERIFIED; STORY=LOCKED; sources=NONE; ผู้ใช้กำหนดฉากแล้ว แต่ต้องยืนยันสูตร/อาวุธจากคลิปเกมจริง ห้ามกล่าวว่า verified gameplay

## INVENTORY EVENTS IN RELEVANT SCENES (PLANNED ≠ APPROVED)

- SC-005 CHAR-001 FIND ITEM-003 x1 — พบกล่องริมถนนหนึ่งกล่อง

- SC-005 CHAR-001 GAIN ITEM-004 xUNKNOWN — เก็บเศษวัสดุจากกล่อง ไม่เดาจำนวน

- SC-007 CHAR-001 LOOT ITEM-004 xUNKNOWN — เก็บเศษวัสดุจากผู้แพ้

- SC-007 CHAR-001 LOOT ITEM-005 xUNKNOWN — เก็บหินจากผู้แพ้

## OPEN PLOT THREADS

- THREAD-001 จากผู้เล่นส่วนตัวสู่อีสปอร์ตโลก (do not resolve unless assigned)

- THREAD-002 บทบาทสตรีมเมอร์จะเกิดขึ้นเมื่อใด (do not resolve unless assigned)

## CURRENT APPROVED WORLD STATE

{
  "schema_version": 1,
  "approved_through_scene": null,
  "active_episode": "EP-001",
  "phase": "OUTLINE_NOT_CANON_PROSE",
  "real_world": {
    "player_at_home": true,
    "world_championship_started": false
  },
  "avatar": {
    "location": "NOT_LOGGED_IN_IN_APPROVED_PROSE",
    "health": "UNKNOWN",
    "inventory_quantities": "UNKNOWN",
    "base_status": "NOT_CONFIRMED_BUILT",
    "name": "UNCONFIRMED"
  },
  "flags": {},
  "pending_review": [
    "EP-001 outline has user-approved beats but no full scene prose approved",
    "Baseball bat crafting details await gameplay verification",
    "End-of-episode bed placement and final house state not yet locked"
  ],
  "last_commit_handoff": "HANDOFF.md"
}

## OPEN ISSUES

- จะวางจุดเกิดในแผนที่ส่วนใด?

- สูตรคราฟต์ไม้เบสบอลตรงกับเกมเวอร์ชัน/โหมดที่เลือกหรือไม่?

- เตียงและบ้านเสร็จภายในตอนแรกหรือไม่?

## REQUIRED OUTPUT FROM WRITER
1. Draft for the requested scene(s) only.
2. List of newly proposed facts, not silently promoted to CANON.
3. Change log for character state/items/locations and knowledge.
4. Continuity & game-mechanics uncertainty report.
