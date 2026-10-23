# S3: ตรวจเงื่อนไขสถานะโลกโดยไม่แก้ข้อมูล

S3 เพิ่ม `lintstate` เพื่ออธิบายความขัดแย้งที่ตรวจได้จากข้อมูลตำแหน่งและผู้ถือไอเทมของ S1/S2 เท่านั้น ใช้เส้นทาง reducer เดียวกับ S2 ไม่สร้างเครื่อง replay อีกชุด และไม่เปลี่ยนผล `world-preview` เดิม รายงานเป็นข้อเสนอให้คนตรวจ ไม่ใช่การอนุมัติเรื่องหรือการเขียน canon/ledger

## สิ่งที่มีอยู่แล้วและสิ่งที่เพิ่ม

| ชั้น | ตรวจอะไร |
| --- | --- |
| S1 | JSON Schema, references รายเรื่อง, hierarchy/cycles, ตำแหน่งหรือผู้ถือซ้ำ และข้อกำหนด UNIQUE ในแต่ละ record |
| S2 | model/history binding, baseline/coverage, เวลาโลกและ boundary, event identity, หลักฐานและ local eligibility, MOVE/TRANSFER และการไม่คืน state บางส่วนเมื่อทำไม่สำเร็จ |
| S3 | อธิบาย precondition ที่ S2 ตรวจอยู่แล้วเป็น `PASS`, `CONTRADICTION` หรือ `UNKNOWN` พร้อม event/scene, ค่าก่อน, เงื่อนไขที่ขอ, ค่าหลัง และ references ของหลักฐาน |

S2 ยังคงตอบ `UNKNOWN` เมื่อ precondition ทำให้ replay ไม่สำเร็จ S3 แยกเพิ่มเติมว่ามีค่าที่รู้ชัดขัดกัน หรือข้อมูลยังไม่พอ โดยไม่เปลี่ยนข้อสรุปและ output ของ S2

## เปิดใช้แยกรายเรื่อง

เพิ่มไฟล์ **ใหม่ของเรื่องที่ต้องการเปิดใช้เอง** ที่ `stories/<slug>/data/world_rules.json` ตัวอย่างนี้เป็น metadata สังเคราะห์:

```json
{
  "schema_version": 1,
  "story_slug": "my-story",
  "enabled": true,
  "rules": ["MOVE_ORIGIN", "UNIQUE_CUSTODY", "STACK_BALANCE"]
}
```

ไม่ต้องแก้ `story.json` เพื่อเปิด S3 แต่ต้องมี S1/S2 ที่เปิดใช้งานและมี baseline/history/coverage ที่ตรวจหลักฐานได้ จึงจะประเมิน operation ได้ อ่านการเตรียมข้อมูลใน [S1](WORLD_STATE_S1_TH.md) และ [S2](WORLD_STATE_S2_TH.md)

ถ้าไม่มีไฟล์ ปิด `enabled` หรือเลือก rules ว่าง จะเป็น `DISABLED` ไม่ใช่ `PASS` กฎที่ไม่อยู่ในรายการไม่ทำงานโดยปริยาย ชื่อกฎหรือเวอร์ชันที่ไม่รองรับและฟิลด์เกิน schema เป็น `INVALID` ไม่มี genre rule ที่เปิดให้อัตโนมัติ และไม่มี success stub สำหรับกฎในอนาคต `story_slug` ต้องตรงกับ root ที่เลือกเสมอ

ไฟล์ config ใช้ real Draft 2020-12 schema ของ engine เท่านั้น ไม่โหลด schema จากเรื่องหรือเครือข่าย อ่าน JSON แบบ UTF-8 มีขนาดสูงสุด 8 MiB ปฏิเสธ key ซ้ำและ non-finite numbers เช่นเดียวกับ loader S2 เส้นทางต้องอยู่ในเรื่องที่เลือก dangling symlink และไฟล์ที่ไม่ใช่ regular file ไม่ถือเป็น config ที่หายไป

## กฎสามข้อที่รองรับ

| กฎ | CONTRADICTION เมื่อรู้ชัด | UNKNOWN เมื่อข้อมูลไม่พอ |
| --- | --- | --- |
| `MOVE_ORIGIN` | ตำแหน่งปัจจุบัน KNOWN ต่างจาก `from_location_id` | ไม่มีแถวตำแหน่ง หรือ location เป็น UNKNOWN |
| `UNIQUE_CUSTODY` | ผู้ถือ KNOWN เพียงรายเดียวต่างจากผู้โอน หรือขอโอนจำนวนที่ไม่ใช่ 1 สำหรับ UNIQUE | ขาด holding, ผู้ถือ UNKNOWN หรือ quantity ไม่ทราบ |
| `STACK_BALANCE` | ยอดต้นทางที่รู้ชัดน้อยกว่าจำนวนที่ขอโอน | ไม่รู้ยอดต้นทาง/ปลายทาง หรือไม่มีแถวที่ต้องใช้และยังไม่มีหลักฐานยืนยันความเป็นไปไม่ได้ |

ถ้ายอด STACK ต้นทางเป็น 2 แต่ขอโอน 3 นั่นเป็นความขัดแย้งที่รู้ชัด แม้แถวปลายทางจะหายไปด้วย แต่ถ้าต้นทางมีพอและปลายทางหายไป ผลยังเป็น UNKNOWN เพราะไม่อนุมานยอดปลายทางเป็นศูนย์ แถวปลายทางที่ระบุยอดศูนย์ไว้ชัดเจนใช้ได้

กฎเหล่านี้ไม่เพิ่ม CREATE event ให้ของที่อยู่ใน baseline ไม่เดาว่าของตกอยู่ที่ใด และไม่เดินทางตาม location hierarchy โดยอัตโนมัติ S1 ตรวจข้อผิดพลาดเชิงโครงสร้าง เช่น UNIQUE หลายผู้ถือ อยู่แล้ว; S3 ไม่พยายาม replay ข้อมูลที่ไม่ผ่านชั้นนั้น

## คำสั่งและผลลัพธ์

ต้องใช้ Python 3.11+ และ dependencies ที่ pin ใน `requirements.txt` เหมือน engine เดิม ไม่มี dependency ใหม่ใน S3

```bash
python scripts/storyctl.py --workspace . --story my-story lintstate \
  --clock CLOCK-MAIN --tick 2 --suborder 0 --boundary AFTER
```

`--suborder` มีค่าเริ่มต้น 0 และ `--boundary` มีค่าเริ่มต้น BEFORE ถ้าต้องการบันทึกรายงาน:

```bash
python scripts/storyctl.py --workspace . --story my-story lintstate \
  --clock CLOCK-MAIN --tick 2 --boundary AFTER --out .local/world-diagnostics.json
```

ใช้ `--out` ได้เฉพาะใต้ `.local/` ของ workspace ระบบใช้ helper เดิมที่เขียน artifact แบบแทน directory entry เพื่อรักษา source ที่อาจถูก hardlink ไว้ รายงานอาจมีข้อมูลของเรื่อง จึงควรเก็บเป็น local และไม่เผยแพร่ draft หรือ context โดยไม่มีอนุญาต

| status | ความหมาย | exit code |
| --- | --- | --- |
| PASS | มี operation ของกฎที่เลือกและทุกข้อที่ประเมินผ่าน พร้อม replay ที่ AVAILABLE | 0 |
| CONTRADICTION | พบค่าหรือคำขอที่ขัดกับข้อเท็จจริงที่รู้ชัดใน operation ที่ประเมิน | 1 |
| INVALID | config/cursor/schema/reference/identity หรือ ordering ที่ผิดตาม S1/S2 | 1 |
| UNKNOWN | หลักฐาน เวลา local eligibility หรือข้อเท็จจริงที่จำเป็นไม่พอ รวมกรณี replay หยุดจากกฎที่ไม่ได้เลือก | 2 |
| DISABLED | ไม่มี config, ปิดไว้ หรือไม่ได้เลือกกฎ | 2 |
| NO_CHECKS | replay มีข้อมูลพร้อม แต่ไม่มี operation ของกฎที่เลือกให้ประเมิน | 2 |

argparse syntax error ใช้ exit 2 ตามเดิม ให้ดู JSON status แยกจาก stderr ของ syntax error ไม่ใช้ exit 0 เป็นหลักฐานว่าเรื่องทั้งหมดถูกต้อง

PASS หมายถึง **preconditions ของ operation ที่เลือกและตรวจได้เท่านั้น** ตำแหน่งหรือจำนวนอื่นที่ไม่ได้ถูกอ้างยังเป็น UNKNOWN ได้ ไม่ได้รับรองว่าโลกทั้งหมดครบถ้วนหรือผ่านการอนุมัติของมนุษย์ คำสั่ง `check`/pack เดิมไม่ได้เรียก lintstate อัตโนมัติ เพราะต้องเลือก world cursor อย่างชัดเจน

## หลักฐาน เวลา และการไม่คืนผลบางส่วน

รายงานมี `WORLD_STATE_DIAGNOSTICS`, story/cutoff และ canonical hashes ของ model/history/rules แต่ไม่คัดลอก source prose แต่ละ diagnostic ระบุ `rule_id`, `event_id`, `scene_id`, `operation_index` เริ่มที่ 0, `world_time`, `entity_id`, `before`, `expected`, `after`, `source`, `baseline_source`, `coverage_source` และเหตุผล

`before` เป็นค่าที่เส้นทาง S2 ใช้ตรวจ `expected` เป็นเงื่อนไข/คำขอของ operation; `after` มีเฉพาะผลที่เกิดจาก operation ที่ผ่าน ถ้าทำไม่สำเร็จ after เป็น null ไม่แสดงปลายทางที่ขอว่าเป็นสถานะที่เกิดขึ้นจริง Diagnostics เป็นคำอธิบายราย entity ไม่ใช่ snapshot ที่นำไปใช้ต่อได้ รายงานคง `usable_world_state: false` และ `state: null` เสมอ

S2 ตรวจ baseline, coverage และหลักฐานของทุก event ที่อยู่ในช่วงก่อนเริ่มประเมิน operations ถ้าไม่ผ่าน gate นี้ S3 ไม่ออกผลตรวจ operation ที่ชวนให้เข้าใจว่ามีหลักฐานครบ Sources เป็น path/hash ที่ตรวจ bytes จริง ไม่ใช่หลักฐานยืนยันตัวคนอนุมัติ ไฟล์ model/history/rules ไม่ใช้เป็น source ของตัวเองได้

เวลาใช้ clock/tick/suborder/boundary เดียวกับ S2 เรียงตามเวลาโลก ไม่ใช่ลำดับ array หรือการเล่าเรื่อง จึงรองรับ flashback โดยไม่ทำให้ตัวละครย้อนถือของตามลำดับการเล่า Distinct events ที่ world coordinate เดียวกันยังเป็น INVALID ไม่มีการเดาว่าเหตุการณ์ไหนเกิดก่อน หลักฐานของ event อนาคตที่อยู่นอกช่วงไม่ถูกเปิดหรือ hash แต่โครงสร้างและ clock ของ history ยังต้องผ่าน S2

เมื่อ operation ล้มเหลว engine หยุดที่จุดนั้น ไม่ประเมิน operation ถัดไปโดยแต่ง state ให้เอง Diagnostics ก่อนหน้าที่ PASS ไม่ทำให้รายงานรวม PASS เมื่อ replay ยังไม่ AVAILABLE; `complete` เป็น false และ state ไม่ถูกคืน รายงานทุกสถานะยังเป็น `PROPOSED`, `human_editorial_approval: UNVERIFIED`, `canon_change_authorized: false`, `ledger_apply_authorized: false`

## ทดสอบและข้อจำกัด

```bash
python -m unittest discover -s tests -p "test_world_consistency.py" -v
python -m unittest discover -s tests -v
python scripts/novelctl.py check
python scripts/story_engine.py check
```

Tests ใช้ข้อมูลสังเคราะห์: seeded violations และ valid controls, UNKNOWN/หลักฐานขาด, flashback/boundaries/collisions, config/path/story isolation, immutable inputs, output ส่วนตัว และ regression ของ S2/v1 ไม่ใช่การทดสอบความหมายของ prose ด้วย AI คำสั่งเหล่านี้เป็นวิธีทำซ้ำ ให้ดูผลรันจริงและ exact-head CI ใน PR ของ milestone นี้

บน Windows ที่เปิด `core.autocrlf` การตรวจ Git-blob identity ของ manuscript เดิมอาจต่างจาก bytes ใน checkout การทดสอบรวมของ milestone ต้องระบุชัดว่าใช้ canonical Git-object bytes หรือ checkout แบบใด ไม่เปลี่ยน settings, source bytes หรือ assertions เพื่อซ่อน failure ใช้ hash manifest เดิมทั้ง 54 ไฟล์เป็นหลักฐานการคงข้อมูล

ยังไม่มี death/no-action, ability resources, travel duration, destroyed-location entry, groups/vehicles/crafting และไม่เปรียบเทียบ S1 observations กับ snapshot เพราะ narrative boundary ไม่ได้กำหนดด้านของ world-time observation ไว้ ห้ามอนุมานข้อเท็จจริงเหล่านี้จาก metadata อิสระ งาน S4 query/map, S5 context integration และ S6 extraction ยังอยู่นอก S3
