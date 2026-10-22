# Engine E1 — แยกแกนระบบออกจากข้อมูลรายเรื่อง

> สถานะเอกสาร: E1 อธิบายการแยก story roots และ compatibility เดิม; schema/replay ดู [ENGINE_E2.md](ENGINE_E2.md), local review ดู [ENGINE_E3_E4.md](ENGINE_E3_E4.md), และ bounded provenance/ledger proposals กับ roadmap ปัจจุบันดู [ENGINE_E5.md](ENGINE_E5.md) เลขที่แก้ให้ตรงแผนผู้ใช้คือ E5 ledger/provenance, E6 synthetic evaluation, E7 คู่มือไทย เอกสาร E1 ไม่ได้อ้างว่าความสามารถภายหลังมีอยู่แล้วตอนทำ E1

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

## งานต่อจาก E1 และเลข roadmap ปัจจุบัน

ตารางนี้แก้เลข milestone ให้ตรงแผนผู้ใช้แล้ว ดูสถานะและข้อจำกัดปัจจุบันใน [ENGINE_E5.md](ENGINE_E5.md) ไม่ใช่คำกล่าวว่า E2–E7 เสร็จทั้งหมดจาก E1:

| Milestone | งาน | เกณฑ์รับงาน |
| --- | --- | --- |
| E2 — schema และ replay พื้นฐาน | versioned registries และ per-scene state deltas | ตรวจ required/type/enum/version และ replay ตามลำดับฉาก; future/planned/unapproved evidence ไม่กลายเป็นอดีต; gaps เป็น UNKNOWN |
| E3 — migration และ diagnostics ขั้นสูง | นโยบายย้าย schema ที่ย้อนกลับได้และวิเคราะห์ state edge cases | ไม่แก้ canon เงียบ ๆ; ตรวจ bytes/ความหมายก่อนและหลัง; migration ขั้นสูงยังไม่เสร็จ |
| E4 — generic workflow/templates | สัญญา input/output และ local brief-review/proposal ที่ไม่ผูกเรื่อง | ใช้กฎ/style ของ root ที่เลือก; แยก Proposed Facts/ข้อขัดแย้ง; ไม่ promote canon จากผลเครื่องมือ |
| E5 — ledger/provenance | ตรวจ merged metadata/source hash และสร้าง rollup proposals | ปฏิเสธ unmerged, ผิด repo/SHA/hash หรือหลักฐานไม่ครบ; offline เป็น UNVERIFIED; การต่อ recap ไม่ apply ledger และไม่พิสูจน์ human editorial approval |
| E6 — synthetic evaluation | workflow สามฉากและ planted violations ครบขั้น | **critical canon, knowledge และ approval violations ต้องถูกจับทุกข้อ**; รายงาน assertions จริงและข้อจำกัด ห้ามประกาศผ่านเมื่อข้อวิกฤตยังหลุด |
| E7 — คู่มือไทย | onboarding/runbook ตามเครื่องมือที่ตรวจรับจริง | ตัวอย่างทดสอบได้ แยก UNKNOWN/UNVERIFIED/proposal/human decision ชัดเจน คู่มือราย milestone ยังไม่ใช่คู่มือครบทั้งแผน |

E1 ในขณะส่งมอบยังไม่มี historical snapshots, authenticated GitHub approval verification, full registry schemas หรือการประเมิน semantic prose ครบวงจร ขอบเขตภายหลังดูคู่มือ milestone ที่เกี่ยวข้อง ไม่มี paid API, agent automation หรือการเปลี่ยน privacy/settings/ruleset ใน E1 การอนุมัติเนื้อหาและการ merge ยังคงต้องมีคำสั่งจากมนุษย์ตามขอบเขตงานนั้น
