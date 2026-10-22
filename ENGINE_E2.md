# Engine E2 — schema แบบมีเวอร์ชันและ replay สถานะตามฉาก

> คู่มือปัจจุบันสำหรับ local review, diagnostics และบทบาท agent อยู่ที่ [ENGINE_E3_E4.md](ENGINE_E3_E4.md) และ [docs/AGENT_RUNBOOK.md](docs/AGENT_RUNBOOK.md) เอกสาร E2 นี้ยังเป็นสัญญา schema/replay; การย้าย schema รุ่นเก่า, การยืนยัน approval จาก GitHub และ rollup ยังไม่เสร็จ ดูสถานะ roadmap ปัจจุบันในคู่มือ E3/E4

E2 ต่อจาก E1 โดยเพิ่มการตรวจรูปแบบ registry ด้วย JSON Schema จริง และการอ่านประวัติสถานะก่อนฉากที่ขอ งานนี้เป็น engine เท่านั้น ไม่เขียนนิยาย ไม่สร้างข้อเท็จจริง ไม่อนุมัติ canon และไม่ merge PR

เอกสารนี้ระบุสัญญาและเกณฑ์รับงาน ผล tests, commit, Draft PR และ CI ของ tree สุดท้ายต้องบันทึกตามผลจริงใน PR ไม่ถือว่ารายการข้างล่างเป็นหลักฐานว่าผ่านแล้ว

## ติดตั้งและขอบเขต schema

ใช้ Python 3.11 ขึ้นไปและ dependency ที่ระบุใน `requirements.txt`:

```bash
python -m pip install --index-url https://pypi.org/simple --only-binary=:all: -r requirements.txt
python scripts/storyctl.py --story last-island check
python -m unittest discover -s tests -v
```

E1 ใช้ standard library เท่านั้น แต่ E2 เพิ่ม `jsonschema==4.26.0` จาก [โครงการบน PyPI](https://pypi.org/project/jsonschema/4.26.0/) เพื่อใช้ [`Draft202012Validator`](https://python-jsonschema.readthedocs.io/en/stable/validate/) ไม่ได้เขียนตัวตรวจบางส่วนขึ้นเองแล้วเรียกว่า JSON Schema เต็มรูปแบบ การติดตั้ง dependency เป็นขั้นตอนที่ต้องทำก่อนเรียก engine ใน environment ใหม่; การติดตั้งไม่เกี่ยวข้องกับ LLM หรือบริการเสียเงิน

E2 เปิด `FormatChecker` และระบุ dependency ตัวช่วยตรวจ RFC 3339 ใน `requirements.txt` เพื่อให้ `format: date-time` ที่ประกาศใน schema ถูกตรวจจริง ไม่ใช่เพียงคำอธิบายของ field ให้ติดตั้งชุด requirements ทั้งหมด ไม่เลือกติดตั้งเฉพาะแพ็กเกจหลักแล้วอ้างว่าตรวจ formats ได้เท่ากัน

schemas อยู่ใต้ `schemas/v1/` และข้อมูลรุ่นนี้ใช้ `schema_version: 1` ครอบคลุม registry ที่ engine ใช้, approved ledger และไฟล์ประวัติสถานะที่เลือกเพิ่มได้ เวอร์ชันที่ไม่รองรับหรือค่าผิดชนิดต้อง fail พร้อมตำแหน่งข้อมูล ไม่เดารูปแบบและไม่ย้ายเวอร์ชันอัตโนมัติ ไฟล์ตัวอย่าง Last Island เดิมไม่ต้องถูกเขียนใหม่เพื่อผ่าน schema

ต้องแยกขอบเขตสองส่วน:

- JSON Schema ตรวจชนิดข้อมูล, required fields, enums, arrays และโครงสร้างย่อยตาม schema ที่ประกาศ ใช้ schema resources ภายใน repository; การตรวจข้อมูลไม่ควรไปโหลด `$ref` จากเครือข่าย
- ตัวตรวจเชิงความสัมพันธ์เดิมตรวจ ID อ้างอิง, ลำดับ episode/scene, causal flags, source evidence และขอบเขต approved ledger การผ่าน schema จึงไม่แปลว่า reference ถูกต้อง หรือประวัติสถานะ replay ได้ครบ

v1 ยอมให้มี editorial metadata เพิ่มในตำแหน่งที่ schema อนุญาตเพื่อรักษาข้อมูลเดิม แต่ known fields ยังต้องตรงชนิดและข้อกำหนด ไม่ควรตีความนโยบายนี้ว่า field ที่ engine ไม่รู้จักถูกตรวจความหมายแล้ว การตรวจรูปแบบไม่ได้รับรองคุณภาพ prose หรือความจริงของ gameplay

## ประวัติสถานะแบบเลือกใช้

ไฟล์ `data/state_history.json` อยู่ภายใน root ของเรื่องที่เลือกเท่านั้น ไม่มีการค้นหาประวัติจากเรื่องอื่นหรือจาก branch อื่น และไม่มีการสร้างประวัติย้อนหลังจาก planned effects

ไฟล์ว่างที่ยังไม่อ้างว่ามีประวัติอนุมัติแล้วมีรูปแบบดังนี้:

```json
{
  "schema_version": 1,
  "baseline": null,
  "deltas": []
}
```

`baseline` เมื่อมีข้อมูล ต้องระบุ `before_scene`, `status`, `evidence_path` และ `state` ที่เป็น object ข้อมูลนี้บอกสถานะที่ผู้ดูแลระบุไว้อย่างชัดเจนก่อนฉากนั้น ไม่ใช่สำเนา latest snapshot ที่ engine ย้อนเวลาให้เอง `evidence_path` ต้องอ่านได้และไม่ว่างภายในเรื่องที่เลือก

ประวัติไม่สามารถอ้างตัว `state_history.json` เองเป็น independent evidence ได้ ขอบเขตไฟล์ยังต้องปฏิเสธ traversal และ symlink ที่พาไปอ่านเรื่องอื่น

หลักฐาน baseline ต้องเป็นข้อมูลสถานะเริ่มต้นที่แยกอิสระ อยู่นอก `data/`, `scenes/`, `drafts/` และ `ledger/` เพื่อไม่ใช้ live snapshot, scene card หรือ ledger index เป็น baseline ก่อนหน้า และต้องไม่ resolve ไปยัง `draft_path` ของฉากใดไม่ว่าจะประกาศไฟล์ไว้ที่ใด หลักฐานจากฉากใช้ได้ผ่าน deltas ตาม chronology เท่านั้น เพื่อไม่ให้ prose ของฉากอนาคตหรือฉากที่ยังไม่ approved ย้อนกลับมาตั้ง baseline ก่อนหน้า หลักฐานอิสระอย่าง `bible/INITIAL_STATE.md` ใช้ได้ตามเวลาที่ระบุไว้ในข้อมูลท้องถิ่น แต่ยังเป็นเพียง local declaration ไม่ใช่การอนุมัติที่ GitHub ยืนยันแล้ว

แต่ละ delta ระบุ `id`, `scene_id`, `status` และ `changes` สถานะของ baseline/delta เป็น `APPROVED` หรือ `PROPOSED` ตามสัญญาของข้อมูลท้องถิ่น การใช้ delta ยังต้องตรวจว่า source scene เป็น `APPROVED`/`CANON` และมี draft ต้นทางที่อ่านได้ ไม่ว่าง และอยู่ใน `drafts/` ของเรื่องเดียวกัน

ตัวอย่างต่อไปนี้แสดงรูปแบบ operation ของ **synthetic metadata fixture เท่านั้น** ไม่ใช่เหตุการณ์นิยายหรือหลักฐานการอนุมัติจริง:

```json
{
  "path": ["flags", "fixture_flag"],
  "operation": "SET",
  "before_exists": true,
  "before": false,
  "value": true
}
```

`path` เป็นรายการ key ของ object ไม่ใช่ filesystem path ทุก operation ต้องตรวจเงื่อนไขก่อนเปลี่ยนค่า:

- `SET` ต้องระบุ `value` และทำได้เมื่อ `before_exists` กับ `before` ตรงกับสถานะที่ replay มา ถ้าระบุว่า leaf ยังไม่มีอยู่ ต้องไม่มี leaf นั้นจริง
- `REMOVE` ใช้กับ leaf ที่มีอยู่แล้วและค่าเดิมตรงกัน ไม่มีการลบ field ที่ไม่เคยมีหลักฐาน
- parent objects ต้องมีอยู่ในสถานะก่อนหน้า engine ไม่สร้าง parent หรือเติมค่าเริ่มต้นให้เพื่อทำให้ delta ผ่าน
- `changes: []` คือบันทึกชัดเจนว่าฉากนั้นไม่มีการเปลี่ยนสถานะ ไม่เท่ากับการข้ามฉากที่ไม่มี delta

delta ที่มี ID/scene ซ้ำ อ้างฉากที่ไม่มี หรือเรียงขัดกับ chronology ต้อง fail ไม่เลือกอันใดอันหนึ่งเงียบ ๆ

`check` ตรวจ schema, pointers, chronology และ source evidence ที่เข้าเกณฑ์ของทั้งไฟล์ ส่วนเงื่อนไขค่าก่อนเปลี่ยน (`before`) ตรวจขณะ replay เฉพาะช่วงที่ target ต้องใช้ ดังนั้น delta อนาคตไม่เปลี่ยนสถานะก่อน target แต่รูปแบบหรือ pointers ที่เสียในประวัติยังเป็น validation error ได้

## ขอบเขตเวลาและผล replay

ใช้ลำดับ episode ใน registry ตามด้วย `scene.order` ไม่ใช้การเรียงชื่อ ID สำหรับ target ฉากจะอ่านถึง **ก่อนเริ่มฉากนั้น**; target episode ใช้ขอบเขตก่อนฉากแรกของ episode

จาก `baseline.before_scene` ถึง target แบบไม่รวม target ทุกฉากที่ต้องข้ามต้องมี delta ที่เข้าเกณฑ์ approved พร้อม source evidence ฉากอนาคต, delta `PROPOSED` และ source scene ที่ยังไม่ approved ไม่ทำให้สถานะเปลี่ยน การข้ามข้อมูลที่ขาดแล้วนำ delta หลังช่องว่างมาใช้จะทำให้ดูเหมือนมีประวัติครบ จึงห้ามทำ

ตัวอย่าง chronology ของ fixture สามฉาก: ถ้า baseline อยู่ก่อน `SC-001` และ target เป็น `SC-003` ต้องมี delta ที่ใช้ได้ของ `SC-001` และ `SC-002`; delta ของ `SC-003` ยังไม่ถูกใช้ ถ้า delta ของ `SC-002` ยัง proposed ผลต้องเป็น `UNKNOWN` ไม่ส่งสถานะบางส่วนออกมาเหมือนเป็นสถานะก่อน `SC-003`

| สถานการณ์ | ผลที่ควรได้รับ |
| --- | --- |
| baseline และทุกช่วงก่อน target มีหลักฐานครบ | สถานะ `KNOWN` พร้อม `as_of_scene` และ payload `state` จากข้อมูลที่ replay จริง |
| ไม่มี baseline ที่เข้าเกณฑ์, target อยู่ก่อน baseline, หรือมีช่องว่าง/ฉากยังไม่ approved | `UNKNOWN` พร้อมเหตุผล โดยไม่มี payload บางส่วนที่อาจชวนให้เข้าใจผิด |
| ค่า `before` ขัดกับสถานะก่อนหน้า, operation ไม่สอดคล้อง หรือประวัติผิดโครงสร้าง/ลำดับ | error ที่ต้องแก้ข้อมูล ไม่คาดเดาว่าค่าใดถูก |
| ไม่มีไฟล์ `state_history.json` | ใช้ทาง compatibility เดิม: snapshot ที่อยู่ก่อน target หรือ `UNKNOWN`; ไม่สร้าง deltas ให้เอง |

`KNOWN` หมายถึงคำนวณได้ครบภายใต้ข้อมูลท้องถิ่นที่ผ่านเงื่อนไข ไม่ได้หมายความว่า GitHub ยืนยันว่าเป็นการอนุมัติจากมนุษย์จริง ผลใหม่ต้องแสดงขอบเขตนี้ เช่น `approval_basis: LOCAL_RECORDS_NOT_GITHUB_AUTHENTICATED` งานตรวจ source PR/review/merge commit จริงอยู่ใน E5

## ใช้ร่วมกับคำสั่งเดิม

การเลือกเรื่องและ direct root ของ E1 ยังคงใช้ได้:

```bash
python scripts/novelctl.py check
python scripts/story_engine.py check
python scripts/story_engine.py pack SC-001 --recent 7
python scripts/storyctl.py --story last-island pack SC-001
python scripts/storyctl.py --story last-island replay SC-001
python scripts/story_engine.py --root stories/last-island pack SC-001
```

เมื่อเรื่องมีไฟล์ประวัติที่ถูกต้อง `brief`/`pack` ต้องใช้สถานะตามขอบเขต target นั้น เมื่อไม่มีไฟล์ ประวัติเดิมยังไม่ถูกแต่งเติม การมีคำสั่งสร้าง proposal ไม่เป็นการอนุมัติสถานะหรือ promote canon

`storyctl replay TARGET` แสดงผลเป็น JSON เพื่ออ่านสถานะก่อน target โดยตรง ใช้ selector `--story`/`--workspace` เช่นเดียวกับคำสั่งอื่น และต้องรายงาน `UNKNOWN` เมื่อไม่มีประวัติที่ใช้ได้ ไม่ใช่เติมค่าหรือซ่อนช่องว่าง

เมื่อมี `state_history.json` ผล replay ใช้ envelope `availability`, `before_scene`, `as_of_scene` และ `approval_basis` พร้อม `state` เฉพาะผล `KNOWN` แต่เมื่อไม่มีไฟล์นี้ ทาง legacy จะคืนรูปแบบ snapshot เดิมหรือ object `UNKNOWN` เดิมเพื่อ compatibility; snapshot เดิมอาจไม่มี field `availability` และยังไม่ใช่หลักฐานการอนุมัติที่ GitHub รับรอง

ห้ามเพิ่ม history สมมติให้ Last Island เพื่อทำให้ demo ดูครบ การทดสอบประวัติใช้ fixture metadata ใน temporary roots และต้องระบุว่าเป็นข้อมูลทดสอบ สถานะ `APPROVED` ใน fixture ไม่ใช่ approval provenance จริงจาก GitHub

## เกณฑ์รับงานและหลักฐานจริง

- เก็บ regression tests เดิมทั้งหมด รวม coverage จาก E1 62 tests; ถ้าเปลี่ยน fixture ต้องระบุเหตุผลและไม่ลด assertion เพื่อซ่อนปัญหา
- ทดสอบ schema ที่ผิด required/type/enum/nested shape และเวอร์ชันไม่ตรง พร้อมตำแหน่ง error ที่ใช้งานได้ ทดสอบ schema documents เองด้วย validator ของ Draft 2020-12
- ทดสอบ replay ย้อนฉาก, ข้าม episode, target ก่อน baseline, explicit no-op, `SET`/`REMOVE`, เงื่อนไขค่าเดิม และประวัติขาดช่วง
- ทดสอบว่า future/unapproved delta ไม่รั่วเข้า state และไม่มีการใช้ planned effects แทนหลักฐาน
- ทดสอบสองเรื่องและ temporary branch roots ที่มี IDs เหมือนกัน แต่ state ต่างกัน ต้องไม่ใช้ cache หรือข้อมูลข้าม root
- ตรวจ legacy commands, optional gameplay, example-integrity manifest และ 54 source bytes เดิม
- รัน complete suite และ validation บน tree สุดท้าย แล้วตรวจ published head และ CI ของ head นั้น ระบุ passed/failed/skipped/not-run ตามจริงใน Draft PR

ยังไม่มีผลทดสอบของ E2 ถูกอ้างไว้ในเอกสารนี้โดยล่วงหน้า ไม่สร้าง reviewer scores, friction entries หรือสถิติที่ไม่ได้วัดจริง

## งาน E3–E7 ที่ยังเหลือ

E2 นำรากฐาน state replay ที่เคยอยู่ในแผน E3 มาทำร่วมกับ schema แล้ว ตารางนี้เป็น backlog ที่ต้องตรวจรับแยก ไม่ได้สรุปว่า engine เสร็จครบแล้ว:

| Milestone | งานต่อ | เกณฑ์รับงาน |
| --- | --- | --- |
| E3 — migration และ state diagnostics | นโยบายอัปเกรด schema, เครื่องมือ migration ที่ย้อนกลับได้, การวินิจฉัย state edge cases | migration ไม่แก้ canon เงียบ ๆ; ตรวจ byte/history หลังย้ายได้; รายงานช่องว่าง/ความขัดแย้งตามฉากชัดเจน และไม่แทน unknown ด้วยค่าเดา |
| E4 — generic review/templates | สัญญา input/output และเครื่องมือ `brief-review`/proposal ที่ไม่ผูกเรื่อง | ใช้ rules/style ของ root ที่เลือกเท่านั้น; แยก Proposed Facts และข้อขัดแย้ง; ไม่มีการ promote canon หรืออ้างว่าสถานะท้องถิ่นเป็นการอนุมัติจริง |
| E5 — authenticated approval provenance | ตรวจ repository, source PR, review และ merged commit จาก GitHub จริง | ปฏิเสธ PR ที่ยังไม่ merge, ผิด repo/SHA หรือไม่มีหลักฐานตามนโยบาย; fixture ต้องระบุว่าเป็นการจำลอง; local labels ไม่กลายเป็น verified human approval |
| E6 — ledger operations | `rollup`, `doctor` และ status diagnostics | rollup อ้างเฉพาะอดีตที่เข้าเกณฑ์พร้อม source; doctor รายงาน reference/provenance/state gaps โดยไม่แก้ข้อมูลเอง; ไม่ตัด LOCKED facts เพื่อให้ pack ผ่าน cap |
| E7 — evaluation workflow | workflow synthetic สามฉากและชุด planted violations | **critical canon, knowledge และ approval violations ที่วางไว้ต้องถูกจับทุกกรณี**; รายงานจาก assertions จริง รวมข้อจำกัดที่ยังจับไม่ได้ และห้ามประกาศพร้อมใช้งานเมื่อข้อวิกฤตยังหลุด |

E2 ไม่ใช้ paid APIs ไม่อ่าน secrets ไม่เปลี่ยน permissions/privacy/security/rulesets ไม่เขียน prose และไม่สื่อสารกับ reviewer ภายนอก การอนุมัติให้ merge PR #2/#3 ในอดีตไม่ใช่อำนาจ merge Draft PR ของ E1/E2
