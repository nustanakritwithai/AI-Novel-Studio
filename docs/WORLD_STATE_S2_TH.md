# คู่มือ S2: ดูสถานะโลกจากประวัติที่ระบุชัดเจน

S2 เพิ่มการอ่านประวัติการเปลี่ยนสถานะเพื่อสร้าง **ภาพเสนอ** ณ จุดเวลาโลกที่ระบุ ผู้ใช้ตรวจดูผลได้ แต่ระบบไม่แก้ canon, ไม่เขียนสถานะกลับ และไม่อนุมัติข้อมูลให้อัตโนมัติ ข้อมูล S1 ใน `data/world_model.json` ยังคงเป็นแบบจำลองที่ opt-in; `observations` เป็นข้อสังเกต ไม่ใช่ delta ที่ S2 นำมาเล่นซ้ำ

## ประวัติ S2 และแบบจำลอง S1

เมื่อ story เปิด `world_state.enabled` ไฟล์ `data/world_history.json` เป็นประวัติแบบเลือกใช้ เวอร์ชัน `schema_version: 1` ของไฟล์นี้เป็น namespace แยกจาก `state_history` ของ v1 หากปิด S1 หรือไม่มีไฟล์ประวัติ ระบบคงเส้นทางเดิมไว้ และ `world-preview` รายงาน `UNKNOWN` หากไฟล์ที่ประกาศว่ามีอยู่เสียหรือผิดโครงสร้าง ระบบจะไม่ถือว่าเป็นการไม่มีประวัติ

ประวัติต้องผูกกับ story และแบบจำลองที่เลือกอย่างชัดเจน: `story_slug` ต้องตรงกัน, `baseline_id` ต้องตรงกับ baseline ของ S1 และ `model_sha256` ต้องตรงกับ SHA-256 ของ **วัตถุ JSON หลัง parse แล้ว canonicalize** ด้วยกติกาเดียวกับ `world_state_reducer.digest`: UTF-8, `ensure_ascii=False`, เรียง key, ตัวคั่น `,` และ `:` แบบไม่มีช่องว่าง, และปฏิเสธค่า non-finite ตัวอย่างการสร้าง hash ของ model ที่ canonicalize แล้ว:

```bash
python -c "import hashlib,json; from pathlib import Path; m=json.loads(Path('stories/my-story/data/world_model.json').read_text(encoding='utf-8')); b=json.dumps(m,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8'); print(hashlib.sha256(b).hexdigest())"
```

ประวัติมี `coverage.through` เพื่อประกาศว่ารวบรวมประวัติไว้ถึง cursor ใด ไม่มีการอนุมานว่าช่วงที่ไม่มี event ใน array ว่างหรือครบถ้วนแล้ว การขอ preview หลังขอบเขต coverage จึงเป็น `UNKNOWN` นอกจากนี้ history object และ event/operation object เป็น closed schema: ใช้ได้เฉพาะฟิลด์ที่กำหนด

จุดสำคัญคือ `baseline_boundary` ใน history บอกว่าข้อมูล baseline แทนสถานะ **ก่อนหรือหลัง** จุด world-time ใน `baseline.anchor` ส่วน `baseline.anchor.boundary` และ `event.anchor.boundary` ระบุตำแหน่งเชิงการเล่าในฉากเท่านั้น ห้ามใช้ narrative boundary หรือลำดับฉาก/flashback มาแทนลำดับเวลาโลก

## เวลาโลกและจุดตัด

Cursor ระบุ `clock_id`, `tick`, `suborder` และ `boundary` (`BEFORE` หรือ `AFTER`) ทั้ง baseline, target และ coverage ต้องใช้ `clock_id` เดียวกัน เหตุการณ์เรียงด้วย `(tick, suborder)`; `BEFORE` อยู่ก่อนเหตุการณ์ที่พิกัดเดียวกัน และ `AFTER` อยู่หลังเหตุการณ์นั้น ดังนั้น target ที่ `BEFORE` ไม่รวม event ณ จุดเดียวกัน ส่วน target ที่ `AFTER` รวม event นั้นได้

`baseline_boundary` ใช้กติกาด้านเดียวกัน: baseline `BEFORE` เปิดให้ event ที่จุดเดียวกันอยู่หลัง baseline และนำมาพิจารณาได้; baseline `AFTER` ถือว่า event ณ จุดเดียวกันผ่านไปแล้ว จึงไม่นำมาพิจารณาซ้ำ เหตุการณ์ที่อยู่ก่อน baseline หรือเลย cutoff จะไม่เปลี่ยนสถานะ ณ จุดตัด หากเวลาโลกเป็น `UNKNOWN`, ใช้ clock คนละชุด หรือจัดลำดับไม่ได้ ระบบตอบ `UNKNOWN` โดยไม่ fallback ไปใช้ลำดับการเล่า หาก event คนละ ID ในช่วงที่ต้อง replay ใช้ world coordinate เดียวกัน จะเป็น `INVALID` เพราะจัดลำดับไม่ได้ แม้ narrative boundary จะต่างกัน

ตัวอย่างการขอ preview หลัง event ที่ tick 12:

```bash
python scripts/storyctl.py --workspace . --story my-story world-preview \
  --clock CLOCK-MAIN --tick 12 --suborder 0 --boundary AFTER
```

`--suborder` มีค่าเริ่มต้น `0`; `--boundary` มีค่าเริ่มต้น `BEFORE` หากใช้ `--out` ต้องบันทึกไว้ใต้ `.local/` ของ workspace เท่านั้น เช่น `--out .local/world-preview.json`; ไฟล์ต้นทางของ story อ่านอย่างเดียว

## Event ที่ S2 ใช้ได้

มีเพียง operation สองชนิด:

- `MOVE_CHARACTER` ต้องระบุ character, ตำแหน่งต้นทาง และตำแหน่งปลายทาง หาก baseline ไม่มีตำแหน่งที่ทราบแน่ หรือ location ปัจจุบันไม่ตรงกับต้นทางที่ระบุ ผลเป็น `UNKNOWN`; ระบบไม่อนุมานเส้นทางหรือความเป็นไปได้ของการเดินทาง
- `TRANSFER_ITEM` ต้องระบุ item, holder ต้นทาง/ปลายทางแบบ `CHARACTER` หรือ `LOCATION` และ quantity จำนวนเต็มบวก holder ต้องต่างกัน และ item ต้องมี policy ใน S1

สำหรับ `UNIQUE` ต้องมี holding ของ item เพียงหนึ่งแถวที่ทราบ holder ตรงกับต้นทางและ quantity เท่ากับ `1`; การโอนต้องเป็นหนึ่งชิ้น หากข้อมูลตั้งต้นขาดหรือไม่ตรง ผลเป็น `UNKNOWN` สำหรับ `STACK` ต้องมีแถวต้นทางและแถวปลายทางอยู่ใน baseline ทั้งคู่ พร้อมจำนวนที่ทราบแน่ และจำนวนต้นทางต้องเพียงพอ แถวปลายทางที่ไม่มีอยู่ **ไม่ใช่ศูนย์**; จะไม่สร้างแถวนั้นเอง แถวที่เหลือ quantity `0` ยังคงอยู่

missing row, `UNKNOWN`, `null`, หรือค่าที่ไม่ตรงเงื่อนไขไม่ถูกแปลงเป็นการไม่มีข้อมูลหรือศูนย์ ทุก operation อ้างอิง IDs ใน catalogs ของ story ที่เลือก ก่อนเปลี่ยน event ต้องผ่าน precondition ครบ; หาก operation หรือ event ใดล้มเหลว รายงานจะไม่มี `state` และ `applied_event_ids` ว่าง จึงไม่มีผลบางส่วน

event ID ซ้ำที่มี canonical payload เดิมทั้งก้อนจะถูกนับครั้งเดียวและแสดงใน `duplicate_event_ids`; ID เดิมที่มีฟิลด์หรือ payload เปลี่ยนแม้เพียงส่วนเดียวเป็น `INVALID` ระบบไม่เดาว่าเวอร์ชันใดใหม่กว่า

## Coverage, หลักฐาน และสถานะรายงาน

`local_status: APPROVED` เป็นเพียง eligibility ของ declaration ในเครื่องสำหรับ preview แบบ `PROPOSED` ไม่ใช่หลักฐานว่ามีมนุษย์อนุมัติจริง รายงานคง `human_editorial_approval: UNVERIFIED`, `approval_basis: LOCAL_DECLARATIONS_NOT_AUTHENTICATED`, `canon_change_authorized: false` และ `ledger_apply_authorized: false` เสมอ เมื่อ event ที่อยู่ในช่วง replay ยังเป็น `PROPOSED` จะเกิด history gap และผลเป็น `UNKNOWN` ไม่มีการข้าม event นั้นเงียบ ๆ

preview ผ่าน file API อ่าน/ตรวจหลักฐานของ baseline, coverage และ event ที่รวมอยู่ในช่วง replay และมี local status `APPROVED` เท่านั้น หลักฐานของ event ที่อยู่นอกช่วง—รวม event ในอนาคต—ไม่ถูกเปิดหรือ hash ใน preview; อย่างไรก็ดี ทุก event ยังต้องมีโครงสร้างและ world clock ที่ใช้จัดตำแหน่งได้ ส่วน `world_history.validate` ที่เรียกโดย `check` ตรวจ bytes ของ baseline, coverage และ **ทุก** event ที่ประกาศ `APPROVED` รวมถึง event นอกช่วง preview

`source.sha256` เป็น SHA-256 ของ bytes จริงในไฟล์: สูงสุด 1 MiB ต่อหลักฐาน, ต้องไม่ว่าง, path ต้องอยู่ภายใน story ที่เลือก และต้องไม่ชี้ไปที่ไฟล์ model/history หลักฐานเกินขนาด, หาย, stale, ออกนอก story หรืออ่านไม่ได้ทำให้ preview ไม่พร้อมใช้งาน ไม่พิมพ์เนื้อหาหลักฐานออกมา ส่วน JSON ของ model/history จำกัด 8 MiB ต่อไฟล์, ต้องเป็น UTF-8, ห้าม key ซ้ำ และห้ามค่า non-finite

การเรียก pure API `world_state_reducer.preview(..., evidence_check=...)` ใช้ callback ที่ผู้เรียกส่งมาเป็น trust boundary; ไม่มี callback จะได้ `UNKNOWN` เพราะหลักฐานยังไม่ถูกตรวจ callback ที่เขียนสำหรับ fixture เป็นเพียงตัวแทนการตรวจใน test ไม่ใช่การยืนยันการอนุมัติ ส่วน `world_history.preview(root, cutoff)` ใช้ตัวตรวจไฟล์จริงที่ตรวจ containment, ขนาด และ hash ตาม bytes

## อ่านผลและทดสอบ

รายงานมี `availability` เป็น `AVAILABLE`, `UNKNOWN` หรือ `INVALID`; มี `state` เฉพาะเมื่อ `AVAILABLE` เท่านั้น `world-preview` ออกด้วยรหัส `0` เมื่อ AVAILABLE, `2` เมื่อ UNKNOWN และ `1` เมื่อ INVALID/runtime input error ส่วน argparse syntax error ออก `2` เช่นกัน ให้ดู JSON report เพื่อแยก syntax error ออกจากผล UNKNOWN

ทดสอบชุด world-state ที่ใช้ข้อมูลสังเคราะห์ได้ด้วย:

```bash
cd AI-Novel-Studio
python -m unittest discover -s tests -p "test_world_*.py" -v
```

คำสั่งนี้เป็นวิธีรันทดสอบที่ทำซ้ำได้ ไม่ใช่การยืนยันว่ารันทดสอบแล้ว ตัวอย่างและหลักฐานใน fixture เป็น metadata สังเคราะห์; ป้าย `APPROVED` ในนั้นไม่ใช่การอนุมัติของมนุษย์

บน Windows ค่า `core.autocrlf` อาจทำให้ bytes ใน working tree ของ manuscript ต่างจาก bytes ของ Git blob และทำให้ test ตรวจ Git blob identity เดิมไม่ผ่าน ให้ยืนยันด้วย Git bytes ที่ canonical/อ้างอิง commit หรือ CI ที่ตรวจ object เดียวกัน อย่าปรับ Git setting แบบถาวร เปลี่ยน manuscript หรือแก้/ลด test เพื่อซ่อนความต่างนี้ Hash ของหลักฐาน S2 ยังคงอ้างถึง bytes จริงของไฟล์หลักฐานที่อ่านใน workspace

S2 ไม่อ่านความหมายจาก prose, ไม่ใช้ network หรือ LLM, ไม่อนุมัติหรือ apply ผล และยังไม่ครอบคลุม abilities, groups, vehicles หรือ crafting ส่วน S3 genre checks, S4 query/map, S5 context และ S6 extraction อยู่นอกขอบเขตนี้
