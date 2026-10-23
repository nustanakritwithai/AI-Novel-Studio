# คู่มือ World State Model รุ่น S1

S1 เป็นแบบจำลองข้อมูลแบบเลือกเปิดใช้สำหรับบันทึกข้อสังเกตเรื่องตำแหน่งตัวละครและผู้ถือไอเท็ม โดยตรวจโครงสร้าง การอ้างอิง และแหล่งข้อมูลในเรื่องที่เลือกเท่านั้น เอกสารและโมเดลนี้ไม่ทำ world replay หรือ world-state query ไม่สร้างข้อเท็จจริงจากเรื่อง และไม่เปลี่ยนการทำงานของ v1 เมื่อยังไม่เปิดใช้

สถานะ `APPROVED` ในไฟล์เป็นเพียงป้ายกำกับในเครื่อง ไม่ยืนยันว่าใครอนุมัติเนื้อหา การตรวจผ่านยืนยันได้เพียงว่าไฟล์และการอ้างอิงสอดคล้องกับกฎ S1; ไม่ใช่การตรวจความจริงของเรื่องหรือ human approval ที่ยืนยันตัวตนแล้ว

## เปิดใช้กับ story

ถ้าต้องการเริ่ม story ใหม่ ให้สร้าง scaffold จากราก repository:

```bash
python scripts/storyctl.py new my-story --title "My story"
```

คำสั่ง `new` สร้าง metadata ว่าง ไม่สร้างฉากหรือข้อเท็จจริง เปิดไฟล์ `stories/my-story/story.json` แล้วเพิ่ม `world_state` ระดับบนสุด:

```json
{
  "schema_version": 1,
  "slug": "my-story",
  "title": "My story",
  "extensions": {"gameplay": false},
  "rules": [],
  "world_state": {"schema_version": 1, "enabled": true}
}
```

สำหรับ story ที่มีอยู่ ให้คงค่าฟิลด์เดิมและเพิ่มเฉพาะ `world_state` นี้ ห้ามย้ายหรือเปลี่ยน ID เดิมเพื่อเปิดใช้ S1 เมื่อไม่มี `world_state` หรือ `enabled` เป็น `false` ระบบจะคงพฤติกรรมเดิมและไม่อ่านไฟล์โมเดลที่อาจวางค้างไว้ เมื่อเปิดใช้แล้ว ระบบต้องพบไฟล์ที่ตำแหน่งตายตัว `stories/<slug>/data/world_model.json`; ไม่มีฟิลด์สำหรับเลือก path อื่น

เริ่มจากโมเดลว่างนี้ได้ ไฟล์นี้เป็นโมเดลว่างที่ถูกต้องตามโครงสร้าง S1 และไม่ได้ยืนยันว่ามีตัวละคร ไอเท็ม หรือสถานที่ใดอยู่จริง:

```json
{
  "schema_version": 1,
  "story_slug": "my-story",
  "baseline": null,
  "observations": [],
  "item_policies": []
}
```

บันทึกเป็น UTF-8 ที่ `stories/my-story/data/world_model.json` หลังจากนั้นตรวจ story ที่เลือกอย่างชัดเจน:

```bash
python scripts/storyctl.py --story my-story check
python scripts/storyctl.py --story my-story doctor
```

`check` ตรวจ story และ schema ที่ใช้อยู่ รวมถึงโมเดลเมื่อเปิดใช้ `doctor` สรุปผลตรวจในเครื่องและสถานะที่ยังไม่ได้ตรวจออนไลน์; รหัสออกสำเร็จหมายถึงไม่พบข้อผิดพลาดในสิ่งที่คำสั่งตรวจ ไม่ใช่การอนุมัติหรือการ query world state ถ้าใช้ workspace อื่น ให้ใส่ `--workspace <path>` ก่อนคำสั่ง เช่นเดียวกับ `--story` อย่าพึ่ง `default_story` เมื่อทำงานกับหลายเรื่อง

`doctor --target SC-001` (ถ้ามี target ที่ถูกต้อง) ใช้เส้นทางตรวจสถานะเดิมก่อนฉากของ v1 เท่านั้น ไม่อ่านโมเดลเพื่อ replay หรือ query ตำแหน่ง/ผู้ถือ และเวลาโลกในโมเดลไม่เปลี่ยนผลนั้น

## รูปแบบข้อสังเกตและหลักฐาน

`baseline` เป็น `null` ได้ ถ้าไม่ทราบข้อมูลตั้งต้นหรือยังไม่มีหลักฐาน; `observations` และ `item_policies` เป็น array ว่างได้ การไม่มี baseline และ observation ไม่สร้างเหตุการณ์ `CREATE`/`GAIN` และไม่แปลว่าไม่มีตัวละครหรือของในโลกเรื่อง

แต่ละ record ใน `baseline` หรือ `observations` เป็นข้อสังเกตอิสระที่มีแหล่งข้อมูล ไม่ใช่ delta หรือคำสั่งเปลี่ยนสถานะ ตัวอย่างฟิลด์หลัก:

```json
{
  "id": "OBS-001",
  "anchor": {
    "scene_id": "SC-001",
    "narration_suborder": 0,
    "boundary": "BEFORE",
    "world_time": {"status": "UNKNOWN"}
  },
  "source": {
    "path": "evidence/scene-001-notes.md",
    "sha256": "<64 ตัวอักษร hex ตัวพิมพ์เล็ก>"
  },
  "local_status": "PROPOSED",
  "positions": [
    {"character_id": "CHAR-A", "location": {"status": "KNOWN", "location_id": "LOC-ROOM"}},
    {"character_id": "CHAR-B", "location": {"status": "UNKNOWN"}}
  ],
  "holdings": [
    {"item_id": "ITEM-KEY", "holder": {"kind": "CHARACTER", "character_id": "CHAR-A"}, "quantity": 1}
  ]
}
```

ตัวอย่างนี้เป็นโครงสำหรับอธิบายเท่านั้น ต้องเปลี่ยน ID ให้ตรงกับ registry ของ story ที่เลือก และแทนค่า SHA256 ด้วย hash จริงก่อนใช้ ทุก `scene_id`, `character_id`, `location_id` และ `item_id` ที่ระบุในโมเดลต้องอ้างถึงข้อมูลใน catalogs ของ story เดียวกัน ระบบไม่ค้นจากเรื่องอื่นแทน หากต้องการให้ข้อสังเกตผูกกับไอเท็ม ต้องเพิ่ม policy ของ item นั้นใน `item_policies` เช่น:

```json
{"item_id": "ITEM-KEY", "tracking": "UNIQUE", "important": true}
```

ทุก record ต้องระบุ `source.path` แบบ relative ภายใน story ที่เลือกและ `source.sha256` แบบ lowercase 64-hex โดย validator อ่าน bytes ปัจจุบันและเทียบ SHA256; ไม่รับไฟล์ว่าง ไม่รับ path ที่ออกนอก story หรือให้โมเดลอ้างตัวเองเป็น source ถ้าหา source ไม่พบหรือ hash ไม่ตรง `check` จะรายงาน error และไม่ยอมรับข้อสังเกตนั้น อย่าข้าม error หรือเปลี่ยน hash เพื่อกลบการเปลี่ยนแปลงหลักฐาน ให้ตรวจไฟล์ที่ตั้งใจอ้างใน story ที่เลือกก่อน หากเป็นหลักฐานฉบับใหม่ ให้เก็บไฟล์ฉบับใหม่และผูก declaration ที่ตรวจทานแล้วกับ hash ของ bytes ฉบับนั้น

คำนวณ hash ด้วย Python standard library จากราก repository แล้วนำผลลัพธ์ไปใส่ใน `sha256`:

```bash
python -c "import hashlib; from pathlib import Path; p=Path('stories/my-story/evidence/scene-001-notes.md'); print(hashlib.sha256(p.read_bytes()).hexdigest())"
```

`check` อ่านโมเดล, catalogs และ source เท่านั้น ไม่แก้ไขไฟล์ใด ไม่สร้างหรือเติม baseline และไม่ปรับสถานะ `PROPOSED`/`APPROVED` ให้เอง ให้ถือ bytes ของหลักฐานที่ผูก hash แล้วเป็น immutable; หากเนื้อหาเปลี่ยน hash เดิมจะ stale และต้องตรวจทาน declaration ใหม่ การมี hash หรือ local label ไม่ได้ยืนยันอำนาจอนุมัติ

## ตำแหน่ง ผู้ถือ และ UNKNOWN

- ระบุได้หนึ่งตำแหน่งต่อ character ต่อ record: `{"status":"KNOWN","location_id":"LOC-ROOM"}` หรือ `{"status":"UNKNOWN"}` ห้องเป็น location ID ใน catalog เช่นเดียวกับ site/building
- การไม่ใส่ character ใน `positions` หรือไม่ใส่ item ใน `holdings` หมายถึงไม่มีข้อสังเกตใน record นั้น ไม่ได้หมายถึงไม่มีตัวละคร/ของ ไม่มีผู้ถือ หรืออยู่ที่เดียวกับ POV/cast/scene location ห้ามเติมข้อเท็จจริงจากความเงียบ
- `quantity: null` คือจำนวน `UNKNOWN`; `quantity: 0` คือทราบว่าจำนวนเป็นศูนย์ ทั้งคู่ไม่เหมือนกัน สำหรับไอเท็ม `UNIQUE` จำนวนที่ทราบต้องเป็น `1`; `1` หรือ `null` ผ่านกฎจำนวน แต่ในแต่ละ record มี holding ได้ไม่เกินหนึ่งแถวต่อ item
- `STACK` อนุญาตให้ item เดียวมีหลายแถวที่ผู้ถือแตกต่างกัน แต่ห้ามมีแถวซ้ำสำหรับคู่ item/holder เดียวกัน นี่เป็นการตรวจรูปแบบแถวเท่านั้น ไม่ได้คำนวณยอดรวม ย้ายของ อนุรักษ์จำนวน หรือจำลองคลัง
- `important` เป็นการจัดประเภทตามความสำคัญของ story ไม่ใช่กฎ genre สากล และไม่เปลี่ยนกฎ holder เอง ผู้เขียนต้องกำหนด `tracking` เป็น `UNIQUE` หรือ `STACK` ให้ชัด ความสำคัญไม่ทำให้ข้อมูลที่หายไปกลายเป็น known

ถ้าระบุ `hierarchy` จะตรวจ location references, node ซ้ำ และวงจร parent; ไม่จำเป็นต้องกำหนด root ครอบจักรวาล `parent` ใช้ `ROOT`, `UNKNOWN` หรือ `LOCATION` เพื่อบอก containment เท่านั้น การอยู่ใต้สถานที่หนึ่งไม่สร้าง adjacency, เส้นทาง, การเดินทาง หรือการถ่ายทอดตำแหน่งให้ตัวละครอัตโนมัติ

## ID, ภาษาไทย และเวลา

ID ที่ S1 อ้างอิงใหม่ต้องเป็น stable ASCII ID เช่น `CHAR-A`, `ITEM-KEY`, `LOC-ROOM`, `SC-001` และ `CLOCK-MAIN` โดยรักษาการสะกดเดิมทุกจุด ห้ามสร้างหรือเปลี่ยน ID อัตโนมัติจากชื่อ หรือนำชื่อภาษาไทยไปแทน ID ให้ใช้ฟิลด์แสดงผลใน catalog ที่มีอยู่ เช่น `name` และ `aliases` สำหรับชื่อภาษาไทย/ชื่อเรียก การแก้ label ย้อนกลับได้เพราะไม่เปลี่ยน ID หรือ reference; label ไม่ใช่กุญแจข้อมูลเดิมที่แปลกลับเป็น ID ได้เอง ID ภาษาอื่นที่มีอยู่ใน v1 และไม่ได้ถูกอ้างในโมเดลไม่ต้อง rewrite หรือ migrate เพื่อเปิด S1

`narration_suborder` และ `boundary` ระบุจุดในลำดับการเล่าเรื่อง; `boundary` เป็น `BEFORE` หรือ `AFTER` จุดนั้น `world_time` แยกอีกแกนหนึ่ง: `{ "status": "UNKNOWN" }` หรือ `{ "status": "KNOWN", "clock_id": "CLOCK-MAIN", "tick": 20, "suborder": 0 }` โดย `tick` เป็นจำนวนเต็ม และ `suborder` เป็นจำนวนเต็มไม่ติดลบ ห้ามอนุมานเวลาโลกจากลำดับฉาก หรืออนุมานลำดับเล่าเรื่องจาก tick

flashback จึงระบุได้ด้วยลำดับการเล่าที่มาทีหลังแต่มี world tick ก่อนหน้า; validator ไม่เรียง ไม่กรอง และไม่ replay เวลาโลก การใช้คนละ `clock_id` ไม่ได้แปลว่าเปรียบเทียบเวลาได้ จุด narrative เดียวกัน `(scene_id, narration_suborder, boundary)` ซ้ำกันเป็น error; จุด world-time ที่รู้ค่าและซ้ำกัน `(clock_id, tick, suborder, boundary)` ก็เป็น error ให้ระบุ suborder ที่ชัดเจนเมื่อเป็นจุดคนละจุด ระบบไม่แก้ collision ให้ ไม่ตัดสินลำดับเหตุการณ์พร้อมกัน และไม่สร้างนาฬิกาโลกให้อัตโนมัติ

## Fixture และขอบเขตของ S1

`tests/fixtures/world_state/synthetic_valid.json` เป็นชุดกรณีสังเคราะห์สำหรับการทดสอบ ไม่ใช่ข้อมูล story จริงหรือไฟล์ที่จะนำไปวางเป็น `world_model.json` โดยตรง กรณีเหล่านี้แสดงการอ้างอิงที่แยกตาม story, label ภาษาไทยกับ ID คงที่, holder/position ที่ไม่ทราบ, จำนวนศูนย์เทียบกับ `null`, item แบบ UNIQUE/STACK, hierarchy ของห้อง และ flashback ที่มี world chronology ย้อนก่อนหน้า

S1 ยังไม่ทำ reducer, replay, การ query ตำแหน่งหรือผู้ถือ, การดึงข้อเท็จจริงจาก prose, การย้าย/ถ่ายโอน, conservation/inventory arithmetic, map/routing หรือการบังคับ genre invariants ความสามารถด้าน abilities/resources, groups/vehicles, crafting/economy และการ migrate ข้อมูล story จริงก็อยู่นอกขอบเขตเช่นกัน
