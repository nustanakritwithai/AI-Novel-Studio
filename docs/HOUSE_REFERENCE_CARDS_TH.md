# การ์ดบ้านตามฉากสำหรับผู้เขียนนิยาย

ใช้ `house-card` เพื่อถามว่า “บ้านนี้เป็นของใคร และแหล่งข้อมูลบอกสภาพบ้านไว้อย่างไร ณ ขอบเขตฉากนี้” โดยไม่แก้ต้นฉบับ canon หรือ ledger คำตอบเป็น **ข้อมูลอ้างอิง ไม่ใช่ประวัติที่อนุมัติแล้ว** ค่า `AVAILABLE` หมายถึงพบการ์ดที่ตรวจแหล่งอ้างอิงได้ ไม่ได้หมายความว่าทุกคำถามมีคำตอบ

## เริ่มใช้งาน

ใช้ Python 3.11+ และ dependencies ที่ pin ใน `requirements.txt` ตาม [คู่มือเริ่มเรื่อง](../ENGINE_E7.md) จากราก repository:

```bash
python scripts/storyctl.py --story last-island-active house-card LOC-009 --scene SC-018 --boundary BEFORE --source-mode committed --out .local/house-before-sc018.json
python scripts/storyctl.py --story last-island-active house-card LOC-009 --scene SC-018 --boundary AFTER --source-mode committed --out .local/house-after-sc018.json
python scripts/storyctl.py --story last-island-active house-card LOC-009 --scene SC-037 --boundary AFTER --pov CHAR-001 --source-mode committed --out .local/house-after-repair.json
```

ไม่ระบุ `--boundary` จะใช้ BEFORE ไม่ระบุ `--pov` จะใช้ POV ของฉาก เก็บไฟล์ผลลัพธ์ได้เฉพาะใน `.local/` ของ workspace ที่เลือก หากไม่ระบุ `--out` จะพิมพ์ JSON ทาง stdout ไม่ส่งข้อมูลให้โมเดลหรือบริการภายนอก

Exit code: `0` พบการ์ด, `2` ไม่มีการ์ดตรงขอบเขตนี้/ปิดโมดูลและได้ UNKNOWN, `1` ข้อมูลหรือหลักฐานไม่ถูกต้อง เช่น hash เปลี่ยน path ข้ามเรื่อง หรืออ้างข้อเท็จจริงที่เปิดเผยหลังฉากเป้าหมาย ไม่มีการย้อนหา snapshot ใกล้เคียงโดยอัตโนมัติ

## อ่านการ์ดก่อนเขียน

1. ตรวจ `story_slug`, `house_id`, `scene_id`, `boundary` ให้ตรงงาน บ้านตัวเอกใช้ **LOC-009 เป็นรหัสค้นหาเดียว** ที่เชื่อมคำบรรยายเดิม LOC-005/006/009 ผ่าน `location_refs` ไม่ได้เปลี่ยนบ้านไม้ในอดีตเป็นบ้านหิน
2. อ่าน `facts` พร้อม `observed_after_scene`, `qualification` และ `evidence` แต่ละรายการคือคำบรรยายล่าสุดที่เลือกไว้ ไม่ใช่ข้อพิสูจน์ว่าไม่มีเหตุการณ์นอกจอหลังจากนั้น
3. อ่าน `unknown_fields` และค่า `null` ภายในโครงสร้างด้วย ขนาดบันได จำนวนชิ้นส่วน ตำแหน่งประตู/ห้องที่ไม่ระบุยังไม่ทราบ การไม่มีข้อมูลบันไดไม่ได้พิสูจน์ว่าไม่มีบันได
4. แยก `pov_knowledge.facts` ออกจากข้อมูลบ้าน ตัวละครอื่นไม่ได้รับความรู้ของตัวเอกอัตโนมัติ ถ้าไม่มีรายการความรู้ของ POV นั้นจะเป็น UNKNOWN
5. ตรวจเส้นทางเท่าที่แหล่งข้อมูลระบุ: ภายในชั้นล่าง → บันได → ลานยิงเปิดด้านบน ยังไม่มีแผนผังประตู ห้อง หรือทางเดินครบ จึงใช้การ์ดนี้ยืนยันเส้นทางละเอียดที่แต่งเพิ่มไม่ได้
6. ห้ามเลื่อนแบบแปลนเป้าหมายหรือ House Atlas ที่เป็น PROPOSED มาเป็นสิ่งที่สร้างแล้ว ห้ามเพิ่มห้องชั้นบนเต็มชั้น เสาหลักอีกต้น หรือกำแพงหลายชั้นจากการคาดเดา

ตัวอย่างย่อจากคำสั่งจริง (ตัดเฉพาะค่าที่ใช้เปรียบเทียบ ไม่ใช่ JSON ผลลัพธ์เต็ม):

| จุดที่ขอ | ข้อมูลจากแหล่งเดิม | สิ่งที่ยังสรุปไม่ได้ |
|---|---|---|
| SC-018 BEFORE | โครงสร้างหลักหิน ขนาดเดิม 2×2 อ้าง SC-017 | บันไดและชั้นบน UNKNOWN ณ ขอบเขตนี้ |
| SC-018 AFTER | มีบันไดขึ้นลานยิงเปิดและกำแพงเตี้ย | ห้องชั้นบนปิดเต็มห้อง ความสูง ตำแหน่งบันได/ประตู UNKNOWN |
| SC-036 BEFORE | ตัวเอกได้รับข้อความแจ้งผนังถูกโจมตี | สภาพช่องโหว่ที่มองเห็นยัง UNKNOWN |
| SC-036 AFTER | เห็นช่องเปิดบริเวณทางเข้าใน DRAFT | ความเสียหายทั้งหมด/ของหายเท่าไร UNKNOWN |
| SC-037 AFTER | แหล่ง DRAFT บรรยายซ่อมปิดทางเข้า | ไม่ใช่การรับรองความปลอดภัยทั้งบ้านหรือความทนทานเชิงตัวเลข |
| SC-038 AFTER | เตาหลอมสร้างและเริ่มทำงานใน DRAFT | ยังไม่ได้ผลผลิตเหล็ก/ดินปืน/กระสุนสำเร็จ |
| SC-047 AFTER | เตายังทำงาน; การเสริมป้องกันเป็นความคิด ยังไม่ได้สร้างใน EP-005 | จำนวนชั้นป้องกัน/ค่าแข็งแกร่ง UNKNOWN |

การ์ดทุกใบคง `status: REFERENCE_ONLY_NOT_CANON`, `human_editorial_approval: UNVERIFIED`, `canon_change_authorized: false`, `ledger_apply_authorized: false` การ merge โค้ดหรือ hash ตรงไม่ได้แปลว่าได้รับอนุมัติเนื้อเรื่อง

## แหล่งเดิมและขอบเขตตัวอย่าง

ตัวอย่างใช้ [BASE_TIMELINE.md](../stories/last-island-active/bible/BASE_TIMELINE.md), ต้นฉบับ EP-001–005 และ snapshot DRAFT เดิม พร้อม registry สำหรับเชื่อมรหัสตัวละคร/สถานที่ ไม่สร้าง timeline หรือ dashboard ซ้ำ [manifest](../stories/last-island-active/data/house_references.json) มี 26 รายการข้อมูล, 15 รายการความรู้ POV, 20 แหล่ง และ 18 มุมมองที่ผู้จัดทำเลือกไว้อย่างชัดเจน:

`SC-008 AFTER`, `SC-009 BEFORE`, `SC-010 AFTER`, `SC-017 BEFORE/AFTER`, `SC-018 BEFORE/AFTER`, `SC-020 AFTER`, `SC-026 AFTER`, `SC-036 BEFORE/AFTER`, `SC-037 BEFORE/AFTER`, `SC-038 AFTER`, `SC-039 BEFORE/AFTER`, `SC-043 AFTER`, `SC-047 AFTER`

ฉากอื่นยังไม่มีการ์ดตรงจุดนั้น ไม่แอบเลือกการ์ดท้ายบทมาใช้กับต้นบท โดยเฉพาะ snapshot ท้าย EP-003/005 ใช้เฉพาะหลังฉากจบบท ไม่ย้อนความรู้ไปฉากก่อนหน้า

สถานะแหล่งมีความหมายแยกกัน: EP-001/002 เป็น source ที่ผู้เขียนรับในแชตแต่ยังไม่ใช่ GitHub-approved ledger; EP-003/004 เป็น DRAFT; EP-005 เป็น author-chat-accepted working draft แต่สถานะ engine ยัง DRAFT; timeline และ registry เป็น LOCAL_REFERENCE ส่วน bridge การสร้างบ้านท้าย EP-001 มีข้อความ PROPOSED ภายในแหล่งเดิม จึงคง caveat ไว้ใน fact ที่เกี่ยวข้อง

มีความคลาดเคลื่อนของจุดแจ้งเตือนระหว่าง SC-034/035 ในเอกสารเดิม การ์ดเก็บ `conflicting_markers` และเวลาเริ่ม UNKNOWN โดยไม่แก้ snapshot เดิม หลักฐานช่องเปิดจริงแยกอยู่หลัง SC-036

ทิศทางจากผู้เขียนคือเสาหลักกลางบ้านหนึ่งต้นต่อบ้านทั้งหลัง ไม่ใช่ต่อชั้น แต่ตำแหน่งที่สร้างจริงและวิธีย้ายยัง UNKNOWN การ์ดจึงไม่ใส่กฎในแบบ PROPOSED มาเป็น fact ว่าได้สร้างเสาแล้ว ค่าแข็งแกร่งเชิงสัญลักษณ์ไม่ใช่ความหนาทางกายภาพ ไม่บวกความแข็งแกร่งหลายชั้นหรือคำนวณ HP/แรงระเบิด กลุ่มเจ้าของยัง UNKNOWN และไม่ผูกแปด archetype ของ Atlas เข้ากับกลุ่มจริง

## หลักฐานกับ Windows

ค่าเริ่มต้น `--source-mode working-tree` ตรวจ hash จาก **raw bytes** ของไฟล์ที่อ่าน หาก CRLF ใน checkout ไม่ตรง LF ของ Git blob จะปฏิเสธตรง ๆ เช่นเดียวกับต้นฉบับที่แก้แล้ว ไม่ normalize ข้อมูลหรือเปลี่ยน Git settings เพื่อให้ผ่าน

เลือก `--source-mode committed` อย่างชัดเจนเมื่อต้องการอ่านหลักฐานจาก **local HEAD Git blobs** ซึ่งผูกทั้ง path และ hash ผลลัพธ์ระบุ `source_commit` และ `source_evidence_mode: COMMITTED_GIT_BLOBS` ไม่ fetch ไม่ใช้ replacement object และไม่อ้างว่าได้ตรวจต้นฉบับที่ยังไม่ commit ตัว manifest/ทะเบียน/คำอธิบายที่ใช้จัดการ์ดยังอ่านจาก working tree จึงอย่าอ้างว่า `source_commit` รับรอง metadata ที่ยังไม่ commit ทั้งชุด

`check` ยังคงตรวจ raw working-tree ตามเดิม ไม่มีสวิตช์ให้ข้าม hash ล้มเหลว หากต้นฉบับเปลี่ยนจริง ให้ทบทวน fact, knowledge, locator และ supporting source ทั้งสายก่อนอัปเดต manifest ห้ามอัปเดต hash อย่างเดียวเพื่อซ่อนการเปลี่ยนความหมาย

## เพิ่มเรื่องหรือบ้านอื่น

โมดูลเป็นตัวเลือก: เรื่องที่ไม่มี `data/house_references.json` ทำงานเดิมได้ ใช้ [schema v1](../schemas/v1/house_references.schema.json) และตัวอย่างทดสอบจำลองใน [test_house_cards.py](../tests/test_house_cards.py) สร้าง metadata ในรากเรื่องของตนเอง ไม่อ้าง path ข้ามเรื่อง

- `houses` เป็นรหัสค้นหาที่คงที่; `design_target_ref` แยกแบบเป้าหมายจาก built state (ตัวอย่างนี้เป็น null)
- `sources` ผูก path/hash/status; `supporting_sources` ผูก snapshot กับต้นฉบับที่มันสรุป
- `facts` และ `knowledge` เป็นข้ออ้างที่ผู้จัดทำเลือกพร้อมจุดเปิดเผยและ citation แบบ `L540-L554` หรือ JSON Pointer
- `views` เลือก ID ที่ตรง house/scene/BEFORE หรือ AFTER เท่านั้น ไม่มี reducer แอบเติมค่าให้
- `owner_character_ref` ต้องเป็นตัวละครในเรื่อง; `location_refs` ต้องเป็นสถานที่ในเรื่อง รุ่นนี้ยังไม่มี group registry จึงรับ `owner_group_ref` ได้เฉพาะ null อย่าสร้างชื่อกลุ่มขึ้นเอง

ตัวตรวจยืนยันโครงสร้าง การอ้างอิง ขอบเขตการเปิดเผย และ byte identity **ไม่ได้อ่านเข้าใจว่าข้อความพิสูจน์ fact จริงหรือไม่** ผู้ดูแลยังต้องตรวจคำบรรยายกับต้นฉบับก่อนใช้หรือแก้ metadata

## ข้อจำกัดของรุ่นนี้

นี่คือ curated scene views เพื่อรักษาความต่อเนื่องการเขียน ไม่ใช่ world-state replay: ลำดับทะเบียนบทและฉากใช้กันการเปิดเผยอนาคตเท่านั้น `world_time` ยัง UNKNOWN ไม่คำนวณ flashback/เหตุการณ์พร้อมกัน ถ้าฉากย้อนเวลาไม่มี view ที่ตรวจแล้วให้ UNKNOWN ไม่ใช้สถานะปัจจุบันแทน

ยังไม่รวมการ์ดเข้ากับ context pack อัตโนมัติ ไม่ดึง delta จากร้อยแก้ว ไม่เพิ่มรูปทรงอาคาร ไม่แก้ dashboard และไม่ใช่ระบบอนุมัติ canon ผู้เขียนต้องเลือกการ์ดที่ตรงฉาก อ่านข้อจำกัดและหลักฐาน แล้วจึงเขียนหรือเสนอการเปลี่ยนแปลงผ่าน review เดิม

## แบบขยายที่ยังไม่ใช่สภาพบ้านในฉาก

[เป้าหมายบ้านตัวเอก 4×4 สองชั้น](../stories/last-island-active/design/proposals/protagonist-house-4x4-v1/WRITER_HANDOFF_TH.md) บันทึกคำสั่งออกแบบของผู้เขียนแยกจากการ์ด built state: กำแพงขอบนอก 4×4 หนึ่งแนว แล้วกำแพงบ้าน 2×2 เดิมอีกหนึ่งแนว รวมสองแนวเท่านั้น รายละเอียดด้านบนและเส้นทางยังไม่กำหนด เอกสาร target นี้ไม่ถูกโหลดเข้าการ์ดฉากหรือ context โดยอัตโนมัติ และไม่เป็นหลักฐานว่าขยายแล้ว
