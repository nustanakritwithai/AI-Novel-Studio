# CONTEXT PACK: SC-001

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

- **FACT-002** เรื่องเปิดด้วยพระเอกเล่นเกมเป็นการส่วนตัวในห้องของตน ยังไม่เริ่มการแข่งขันอีสปอร์ตระดับโลก

- **FACT-012** ใช้เกมเพลย์จริงของสตรีมเมอร์เป็นหลักฐานกฎและพฤติกรรม แต่ต้องแยกจากกฎการแข่งขันและการแต่งเติมเพื่อความบันเทิง

- **FACT-013** พระเอกไม่ถูกกำหนดให้ชนะเพราะเป็นตัวละครหลัก; การแพ้ชนะและของที่มีต้องสอดคล้องกับเหตุการณ์และกฎในเรื่อง

## SELECTED SCENE: SC-001

## RELEVANT SCENES & CAUSAL ORDER

### SC-001 เล่นเกมส่วนตัว (PLANNED)

Goal: เล่นเกมส่วนตัว / Conflict: ความไม่รู้ระบบ

Beats: เปิดตัวพระเอกในห้องส่วนตัวแล้วเข้าสู่ Last Island ผ่าน Full-Dive VR; ยังไม่แข่งขันใหญ่

Outcome: คนดูรู้ว่านี่เป็นผู้เล่นธรรมดากำลังเริ่มเซสชันส่วนตัว

Preconditions: none

Effects: {"logged_in": true}

### SC-002 บทเรียนแรก (PLANNED)

Goal: บทเรียนแรก / Conflict: ทรัพยากรน้อย

Beats: ระบบนำทางชวนตัดไม้ สร้างบ้าน และทำเตียง; พระเอกวางแผนบ้าน 2×2 ชั้นเดียว

Outcome: เริ่มตัดไม้และตั้งเป้าบ้านหลังแรก

Preconditions: logged_in

Effects: {"tutorial_received": true, "wood_gathered": true, "base_plan_2x2": true}

## CHARACTERS IN SCOPE

- **CHAR-001 พระเอก** — POV ตัวหลักช่วงเริ่มเกม; known: สังเกตว่าบริเวณเริ่มต้นมีบ้านคนอื่นหนาแน่น; ตัดสินใจย้ายทำเล; ชนะการปะทะแรกอย่างเฉียดฉิว; unknown: ชื่อจริง; อายุ; อาชีพ; ทักษะเกมก่อนเข้ามา; ภูมิหลัง; ความสัมพันธ์ในโลกจริง

  - After SC-003: knows บริเวณเริ่มต้นมีผู้เล่นตั้งฐานหนาแน่น

  - After SC-006: knows อาจถูกผู้เล่นอื่นโจมตีระหว่างเก็บของ

## MECHANIC RESEARCH STATUS (DO NOT OVERSTATE)

## INVENTORY EVENTS IN RELEVANT SCENES (PLANNED ≠ APPROVED)

- SC-002 CHAR-001 GAIN ITEM-001 xUNKNOWN — เก็บไม้ช่วงเริ่มเกม

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
