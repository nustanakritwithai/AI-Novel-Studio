# Engine E1 — แยกแกนระบบออกจากข้อมูลรายเรื่อง

> สถานะเอกสาร: E1 อธิบายการแยก story roots และ compatibility เดิม สำหรับ dependency, schema/replay และลำดับงานที่อัปเดตให้ใช้ [ENGINE_E2.md](ENGINE_E2.md) เป็นคู่มือปัจจุบัน E2 นำรากฐาน replay มารวมกับ schema แล้ว; roadmap เดิมท้ายเอกสารนี้เก็บเป็นบริบทของ E1 ไม่ใช่เลข milestone ปัจจุบัน โดยการตรวจ approval provenance จาก GitHub จริงอยู่ใน E5

E1 เป็น milestone แรกสำหรับ engine ที่ใช้ซ้ำได้หลายเรื่อง งานนี้ไม่เขียนนิยาย ไม่สร้าง canon ใหม่ และไม่ถือว่า engine ทั้งแผนเสร็จแล้ว ผลตรวจจริงและ CI ของ commit สุดท้ายต้องบันทึกใน Draft PR; รายการตรวจด้านล่างเป็นเกณฑ์รับงาน ไม่ใช่คำกล่าวว่าผ่านแล้ว

## โครงสร้างและขอบเขต

```text
scripts/                     แกนตรวจข้อมูลและสร้าง context
studio.json                  schema_version + default_story ของ workspace
schemas/story.schema.json    รูปแบบ config รายเรื่อง
stories/<slug>/
  story.json                 ชื่อเรื่อง กฎ และส่วนขยายที่เปิดใช้
  data/                      canon, scenes, episodes, events, state และทะเบียนอื่น
  bible/STYLE_GUIDE.md        ข้อตกลงสไตล์ของเรื่องนี้
  scenes/                    scene cards
  drafts/                    แหล่งข้อความที่อาจอ้างเป็นหลักฐานหลังอนุมัติ
  ledger/                    index และสรุปที่ผ่านการอนุมัติ
```

ข้อมูล Last Island เก็บใน `stories/last-island/` ด้วยการย้ายไฟล์เดิมโดยคง bytes และประวัติ Git ไม่แก้เนื้อหา และไม่ promote สถานะใดเป็น approved จากการย้ายนี้ เอกสารเดิมภายในตัวอย่างอาจมีคำสั่งหรือเส้นทางแบบเดิม; ใช้คำสั่งจาก repository root ตามคู่มือนี้เมื่อต้องการเลือกเรื่องอย่างชัดเจน

เลือก `story.json` แทน YAML เพื่อให้ E1 ยังใช้ Python standard library โดยไม่เพิ่ม parser ภายนอก ตัวอย่าง config ของโครงว่าง:

```json
{
  "schema_version": 1,
  "slug": "sample",
  "title": "โครงว่าง",
  "extensions": {"gameplay": false},
  "rules": []
}
```

`slug` เป็นชื่อโฟลเดอร์ที่ระบบตรวจความปลอดภัยแล้ว ไม่ใช่ path อิสระ `rules` และ style guide อยู่ใน root ของเรื่องที่เลือก แกนระบบไม่เติมกฎโลก ตัวละคร หรือข้อจำกัดของ Last Island ให้เรื่องอื่น

`extensions.gameplay: false` ไม่บังคับให้มี `data/mechanics.json` หรือ `data/sources.json` เรื่องทั่วไปจึงตรวจและสร้าง pack ได้โดยไม่เพิ่มข้อมูลเกม เมื่อเปิดส่วนขยาย ระบบต้องตรวจหลักฐานและระดับ verification ตามเดิม; การปิดส่วนขยายไม่ใช่ช่องทางทำให้ reference ที่ไม่มีหลักฐานผ่านตรวจได้

## เริ่มจากโครงว่าง

รันจาก repository root ด้วย Python 3.11 ขึ้นไป:

```bash
python scripts/storyctl.py new sample --title "โครงว่าง"
python scripts/storyctl.py --workspace . --story sample check
python scripts/storyctl.py --workspace . --story sample status
```

`new` สร้างทะเบียน metadata ว่าง, config, ledger และข้อตกลงสไตล์พื้นฐาน ไม่สร้างนิยาย scene beats หรือข้อเท็จจริงที่อ้างว่าอนุมัติแล้ว และไม่เขียนทับ root ที่มีอยู่ การสร้างเรื่องไม่เปลี่ยน `default_story` ของ workspace โดยอัตโนมัติ

ก่อนใช้ `brief` หรือ `pack` ต้องมี episode/scene metadata และ scene card ของเป้าหมายใน root นั้นก่อน โครงว่างไม่มี `SC-001` ให้ระบบเดาหรือแต่งแทน:

```bash
python scripts/storyctl.py --workspace . --story sample brief SC-001
python scripts/storyctl.py --workspace . --story sample pack SC-001
```

E1 มี `new`, `check`, `pack`, `brief`, `status` และทางเข้า `proposal` ที่ใช้ความสามารถเดิม การตรวจและสร้างเอกสารไม่อนุมัติ canon ไม่ merge PR และไม่เรียก LLM

## ใช้คำสั่งเดิมและเลือก root

`studio.json` ระบุ `schema_version: 1` และ `default_story` เพื่อให้คำสั่งเดิมเลือกตัวอย่างที่ย้ายมาได้:

```bash
python scripts/novelctl.py check
python scripts/novelctl.py status
python scripts/novelctl.py brief SC-001
python scripts/story_engine.py check
python scripts/story_engine.py pack SC-001 --recent 7
python scripts/story_engine.py proposal EP-001
```

เลือก root โดยตรงได้เช่นกัน:

```bash
python scripts/novelctl.py --root stories/last-island check
python scripts/story_engine.py --root stories/last-island pack SC-001
```

fixture หรือโครงการเดิมที่ส่ง `--root` ไปยัง root ซึ่งมี `data/` แบบเก่ายังใช้ได้ตาม compatibility path ส่วน `--story` ต้องเลือก root ภายใต้ `stories/` ของ workspace ที่กำหนด ห้าม fallback ไปโหลดเรื่องอื่นเมื่อหาเรื่องที่ขอไม่พบ

## เกณฑ์รับงาน E1 และหลักฐานที่ต้องแนบ

| เกณฑ์ | หลักฐานรับงาน |
| --- | --- |
| แยกข้อมูลและกฎรายเรื่อง | แกน context/check ไม่มีข้อกำหนด Last Island ฝังอยู่; pack อ่านกฎและ style จาก root ที่เลือก |
| คงตัวอย่างเดิม | เทียบ bytes ของไฟล์ Last Island ก่อน/หลังย้าย พร้อมรายการ mapping และ Git diff ที่ตรวจย้อนหลังได้ |
| ใช้กับเรื่องทั่วไป | generic scaffold ตรวจได้โดยไม่มี mechanics/sources; config ไม่ถูกต้องหรือ version ไม่รองรับต้อง fail ชัดเจน |
| แยกสองชุดข้อมูล | synthetic fixtures สองเรื่องใช้ IDs ซ้ำกันได้ แต่ check/brief/pack ต้องไม่มี sentinel, style, rules, canon หรือ state ของอีกเรื่อง |
| รักษาความน่าเชื่อถือเดิม | คง 43 regression tests เดิมโดยเปลี่ยน fixture path เท่าที่จำเป็น หรือระบุ mapping ที่เทียบเท่า; ทดสอบ boolean flags, scene-start knowledge และ approved-source checks ต่อไป |
| คงการใช้งานเดิม | ทดสอบ CLI เดิม, default workspace, direct root, explicit story, และการปฏิเสธ path traversal/การเขียนทับ |
| พร้อมให้ตรวจ | รัน complete suite และ validation บน final tree; ระบุ commit, Draft PR และ CI ของ head นั้นจริง ไม่ใช้ผลจากคนละ tree |

คำสั่งหลักสำหรับบันทึกผลจริง:

```bash
python -m unittest discover -s tests -v
python scripts/novelctl.py check
python scripts/story_engine.py check
python scripts/story_engine.py pack SC-001 --recent 7
python scripts/story_engine.py proposal EP-001
```

ผล `PASS` ของ validator หมายถึงผ่านเงื่อนไขที่โค้ดตรวจได้เท่านั้น ไม่ยืนยันคุณภาพวรรณกรรมหรือพิสูจน์ว่า reviewer เป็นมนุษย์จริง ห้ามนำค่า approval ใน fixture ไปอ้างเป็น GitHub approval จริง ห้ามกรอกคะแนน reviewer, จำนวน friction หรือสถิติความสำเร็จที่ไม่ได้วัด

## งานที่ยังเหลือหลัง E1

E2–E7 ต่อไปนี้เป็น backlog พร้อมเกณฑ์รับงาน ต้องแบ่งเป็นงานที่ตรวจได้ก่อนเริ่มแต่ละ milestone ไม่รวมเข้า E1 โดยปริยาย

| Milestone | งาน | เกณฑ์รับงาน |
| --- | --- | --- |
| E2 — schema และ migration | schema ครบทุก registry, version policy และข้อมูลผิดรูปแบบ | ตรวจ required fields, type, enum, reference และ version ครบ; ข้อมูลเสีย fail พร้อมตำแหน่งที่แก้ได้; migration ต้องย้อนกลับและตรวจ bytes/ความหมายได้ |
| E3 — state ตามฉาก | per-scene state deltas และการอ่านสถานะย้อนหลัง | replay ตามลำดับฉากให้ผล deterministic; ทดสอบย้อนฉากและข้าม episode; ห้ามข้อมูลอนาคตหรือ planned effects กลายเป็น approved state; ขาดประวัติต้องเป็น `UNKNOWN` |
| E4 — provenance จริง | ตรวจ source PR, review และ merge commit จาก GitHub | อ้าง PR ที่ merge จริงและตรงเนื้อหา/SHA; ปฏิเสธ unmerged, ผิด repo, ผิด commit และหลักฐานไม่ครบ; offline fixture ต้องระบุว่าเป็นการจำลอง ไม่อ้างเป็นการอนุมัติจริง |
| E5 — prompt/template ทั่วไป | สัญญา input/output ที่ไม่ผูกเรื่อง รวม `brief-review` และข้อเสนอเปลี่ยนแปลง | ใช้กฎ/style ของเรื่องที่เลือก; ส่งออก Proposed Facts และข้อขัดแย้งโดยไม่ promote canon; ไม่มีชื่อโลกหรือข้อบังคับเกมของตัวอย่างหลุดไปเรื่องอื่น |
| E6 — เครื่องมือดูแล ledger | `rollup`, `doctor` และ status ที่อธิบายปัญหาครบ | rollup ใช้เฉพาะอดีตที่ approved และมี source; doctor รายงาน reference/provenance/state gaps โดยไม่แก้เงียบ; ไม่ทิ้ง LOCKED facts เพื่อให้ pack ผ่านขนาด |
| E7 — evaluation workflow | synthetic workflow 3 ฉากและชุด planted violations | ทดสอบเส้นทางตั้งแต่ metadata ถึง proposal/approved ledger ด้วย fixture ที่ประกาศชัด; **critical canon, knowledge และ approval violations ที่วางไว้ต้องถูกจับทุกข้อ**; รายงานผลจาก assertions จริง รวมสิ่งที่ยังจับไม่ได้ และ block การประกาศพร้อมใช้เมื่อข้อวิกฤตหลุด |

E1 ยังไม่มี historical snapshots, authenticated GitHub approval verification, full registry schemas หรือการประเมิน semantic prose ครบวงจร ไม่มี paid API, agent automation หรือการเปลี่ยน privacy/settings/ruleset ใน milestone นี้ การอนุมัติเนื้อหาและการ merge ยังคงต้องมีคำสั่งจากมนุษย์ตามขอบเขตงานนั้น
