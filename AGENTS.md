# AGENTS.md — AI Novel Studio operating contract

**อ่านไฟล์นี้ทุกครั้งเมื่อ AI รับช่วงต่อ**

## Source of truth / precedence

1. `data/canon.json`: รายการ `LOCKED` ที่ผู้ใช้กำหนด ต้องมาก่อนความคิด AI
2. `data/story_state.json` + `STATE.md`: สถานะจาก prose ที่อนุมัติเท่านั้น ไม่เอา planned beats มาทึกทักว่าเขียนแล้ว
3. `data/episodes.json`, `data/scenes.json`, `data/events.json`, `data/inventory_ledger.json`, `data/threads.json`: ลำดับ ไอเทม ปมค้าง และการเปลี่ยนสถานะที่วางแผน
4. `bible/*`: รายละเอียดโลกและตัวละคร
5. `research/*`, `data/mechanics.json`: หลักฐานเกมเพลย์ พร้อม verification level
6. `drafts/*`: ข้อความร่าง; `PROPOSED` ไม่ใช่ `LOCKED`

เมื่อพบความขัดแย้ง **หยุดก่อนแก้ canon**; แจ้งความขัดแย้งพร้อม ID และทางเลือกให้ editor

## ขั้นตอนรับงาน

1. `python scripts/novelctl.py status`
2. `python scripts/novelctl.py brief SC-xxx --out context.md` / `brief EP-xxx`
3. อ่าน Context Pack + `scenes/SC-xxx.md` + draft ล่าสุด (ถ้ามี)
4. ทำงานบน branch เช่น `draft/EP-001-SC-001` เท่านั้น
5. เขียนเฉพาะ scope ที่มอบหมาย; ใหม่ทุกข้อเท็จจริงต้องอยู่ `PROPOSED` จนอนุมัติ
6. `python scripts/novelctl.py check` + `python -m unittest discover -s tests -v`
7. ส่ง PR พร้อมบันทึก Change Log/Continuity Report; ห้าม merge เอง

## กฎห้ามผิด

- `UNKNOWN ≠ PASS`. หากกลไกยัง `UNVERIFIED` อธิบายใน review ไม่แอบระบุว่าเป็นเกมจริง
- ตอนแรกเป็นการเล่นส่วนตัวจากในห้องพระเอก; แข่งขันอีสปอร์ตโลก **เป็นเรื่องภายหลัง**
- พระเอกตั้งใจทำบ้าน 2×2 ชั้นเดียว, เห็นบ้านมาก, เปิดแผนที่ย้ายที่, คราฟต์ไม้เบสบอล, เก็บกล่องข้างถนน **หนึ่งกล่อง**, ถูกซุ่มตีไม้เบสบอล, ชนะเฉียดฉิว, เก็บหิน+เศษวัสดุแล้วกลับสร้างบ้าน
- ห้ามยืนยันชื่อ "บอส", อายุ 20, ปี 2045, $100M เป็น canon
- มุมมองและสิ่งที่ตัวละครรู้ต้องไม่ข้ามเวลา/สถานที่อย่างไร้เหตุผล
- ห้ามอ้างว่าเกมจริงจัดแข่งขัน 100 คนจากข้อกำหนดภาพยนตร์
- ห้ามคัดลอกบทพูดของสตรีมเมอร์/เนื้อหาเจ้าของสิทธิ์เป็นบทนิยายยาว ๆ

## Output contract ของ AI writer

1. **Draft**: ร่างภาษาไทยที่ตรงกับ Scene Card
2. **Continuity table**: ก่อน/หลังฉาก — ที่อยู่/บาดเจ็บ/ไอเทม/ความรู้/พันธมิตร (ถ้าไม่ทราบให้เขียน UNKNOWN)
3. **New facts**: แต่ละข้อระบุ LOCKED(existing ID) / PROPOSED(new) / GAMEPLAY_EVIDENCE(source ID)
4. **Open gaps**: ข้อสงสัยที่ยังไม่ควรเดา
5. **Git changes**: รายชื่อไฟล์ที่เปลี่ยนและเหตุผล

## No silent canon writes

AI เปลี่ยน `data/story_state.json` และ promote facts to `LOCKED` ได้เฉพาะหลังบทผ่านการตรวจและมี human approval เท่านั้น. งานที่ยังไม่เผยแพร่เก็บเป็น DRAFT พร้อม branch/PR.

## v0.2 GitHub-only Story Engine addendum

- There is no external state database. All durable approved story data is versioned in this GitHub repository.
- Read `STORY_ENGINE_V02.md` and `ledger/README.md` before managing recurring chapters or changing story memory.
- `python scripts/story_engine.py pack SC-001 --recent 7` constructs the full scoped prompt; never copy future unapproved drafts into approved history.
- New `ledger/index.json` is **approved-only**: summaries must be backed by approved prose and real human GitHub PR review provenance; an AI checker cannot authorize approval.
- n8n, Claude and Kimi may be orchestrators/reviewers but are never the source of truth; LINE may notify the author only.
- Running `story_engine.py check` proves format/coherence of ledger pointers only, not authenticity of GitHub review or quality of prose.
