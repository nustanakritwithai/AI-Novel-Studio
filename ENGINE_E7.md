# E7 — คู่มือเริ่มเรื่องใหม่ด้วย continuity engine

คู่มือนี้ครอบคลุมเครื่องมือที่มีจริงในรุ่นปัจจุบัน ตั้งแต่สร้างทะเบียนเปล่าจนถึงเตรียมหลักฐานให้คนตรวจ โดยไม่เขียนนิยายหรืออนุมัติ canon ให้อัตโนมัติ ใช้กับเรื่องใหม่ได้โดยไม่แก้โค้ด engine และไม่ต้องใช้กฎหรือตัวละครจาก Last Island

อ่าน [ขอบเขตความพร้อมและ gates ที่ยังไม่ผ่าน](docs/ENGINE_READINESS.md), [E6 วิธีทดสอบ synthetic](ENGINE_E6.md), [ผล blind review ที่บันทึกจริง](evaluation/e6/RESULTS.md), [ข้อกำหนด agent](AGENTS.md) และ [runbook](docs/AGENT_RUNBOOK.md) ประกอบกัน การมีคู่มือหรือผ่าน structural tests ไม่ได้แปลว่าทุก gate ของ engine เสร็จแล้ว

## 1. เตรียมเครื่องมือ

รันตัวอย่างจาก repository root ใช้ Python **3.11 ขึ้นไป** และติดตั้ง dependencies ทั้งชุดที่ pin ใน `requirements.txt` จาก official PyPI เมื่อ environment ยังไม่มี:

```bash
python --version
python -m pip install --index-url https://pypi.org/simple --only-binary=:all: -r requirements.txt
```

เลือก virtual environment ของงานก่อนติดตั้งถ้าต้องการแยกแพ็กเกจ คำสั่ง engine ใช้ `python` ตัวเดียวกับที่ติดตั้ง requirements อย่าแก้ schema version หรือลบการตรวจ format เพื่อข้าม dependency ที่ขาด JSON Schema ใช้ตัวตรวจ Draft 2020-12 จริงและอ่าน schema ของ engine ในเครื่อง ไม่มีการโหลด schema URL ที่ story เสนอขึ้นมา

`new` และ `check` ไม่ต้องมี GitHub หรือ LLM ส่วน `brief-review` ต้องมี local Git repository, commit/base ที่อ่านได้ และ Git ที่รองรับ global option `--no-lazy-fetch` ตรวจความสามารถได้ใน repository ที่ใช้อยู่:

```bash
git --no-lazy-fetch rev-parse --is-inside-work-tree
```

ถ้า Git ไม่รองรับ ให้รายงานข้อจำกัดหรือเลือก environment ที่รองรับโดยผู้ใช้จัดเตรียมเอง อย่า fetch objects, สร้าง commit ปลอม, เปลี่ยน persistent Git settings หรือสร้าง credentials เพื่อทำให้ review ดูผ่าน `doctor` อาจรายงาน Git เป็น UNKNOWN ได้ โดยไม่ทำให้ข้อมูลเรื่องที่ถูกต้องกลายเป็นข้อมูลผิด

`verify-provenance` แบบ live ต้องมี `gh` ที่ติดตั้งและ authenticated อยู่แล้ว รวมถึงสิทธิ์อ่านข้อมูลที่ระบุ นี่เป็น network opt-in แยกจาก workflow ในเครื่อง คู่มือนี้ไม่สั่ง login, สร้าง token หรือแก้สิทธิ์ repository

## 2. สร้างเรื่องเปล่าใน workspace ใหม่

ตัวอย่างนี้เก็บงานทดลองไว้ใต้ `.local/` ที่ repository ignore อยู่แล้ว สร้าง workspace ใหม่เพียงครั้งเดียว ถ้าชื่อนี้มีอยู่ให้เลือกชื่อใหม่หรือใช้ workspace เดิมอย่างตั้งใจ ไม่ลบหรือเขียนทับข้อมูลเพื่อรันตัวอย่างซ้ำ:

```bash
python -c "from pathlib import Path; Path('.local/onboarding-workspace').mkdir(parents=True, exist_ok=False)"
python scripts/storyctl.py --workspace .local/onboarding-workspace new my-story --title "My story"
python scripts/storyctl.py --workspace .local/onboarding-workspace --story my-story check
python scripts/storyctl.py --workspace .local/onboarding-workspace --story my-story status
python scripts/storyctl.py --workspace .local/onboarding-workspace --story my-story doctor --out .local/onboarding-workspace/.local/doctor.json
```

ผลที่คาดจาก `check` ของ scaffold เปล่าคือ `PASS | 0 errors; 0 warnings` ชื่อ `my-story` เป็นเพียง slug ของโครงเปล่า ไม่มี premise หรือเนื้อเรื่องตัวอย่าง `new` สร้าง `stories/my-story/` พร้อม config, registries และ ledger เปล่า ไม่เปลี่ยน `default_story` ของ workspace และไม่เขียนทับเรื่องเดิม

`--workspace` และ `--story` เป็น global options จึงอยู่ **ก่อนชื่อคำสั่ง** `new` รับ slug โดยตรงและไม่รับ `--story` ส่วนการทำงานกับเรื่องที่มีอยู่ควรระบุ `--story` ทุกครั้ง โดยเฉพาะเมื่อมีหลายเรื่อง เครื่องมือไม่ fallback ไปเรื่องอื่นเมื่อหาเรื่องหรือหลักฐานที่เลือกไม่พบ Slug ใช้อักษรอังกฤษตัวเล็ก/ตัวเลขคั่นด้วยขีด เริ่มด้วยตัวอักษร ยาวไม่เกิน 63 ตัว และไม่ใช้ชื่ออุปกรณ์สงวนของ Windows

โครงหลักที่ได้:

```text
stories/my-story/
  story.json                 schema_version, slug, title, extensions, rules
  AGENTS.md                  ข้อตกลงเฉพาะเรื่อง
  bible/STYLE_GUIDE.md        ข้อกำหนดสำนวนที่ยังรอคนกำหนด
  data/*.json                ทะเบียนข้อเท็จจริง ตัวละคร ฉาก เหตุการณ์ และ state
  scenes/                    scene cards
  drafts/                    draft/source evidence เมื่อมีงานที่ได้รับอนุญาต
  ledger/index.json          ทะเบียน recap ที่ยังว่าง
  ledger/episodes/           recap ที่มีหลักฐานและผ่านขั้นตอนอนุมัติจริงในภายหลัง
```

workspace ตัวอย่างอยู่ใต้ `.local/` ทั้งหมด ถ้าเลือก workspace ที่อื่น ต้องจัดการ Git ignore และสิทธิ์เก็บข้อมูลส่วนตัวให้เหมาะสมเองก่อนใช้ ไม่มีคำสั่งใดรับรองว่า repository เป็น Private หรือบังคับ rulesets แล้ว

## 3. กรอกข้อมูลตั้งต้นโดยยังไม่สร้าง canon ปลอม

คัดลอก [แบบรับข้อมูลเรื่อง](templates/STORY_INPUT_TH.md) ไปใช้เป็นเอกสารทำงาน เช่นเก็บไว้ใน story root ของตน กรอก premise, กฎโลก, ตัวละคร, knowledge boundaries และ style ด้วยข้อมูลที่เจ้าของเรื่องให้จริง ปล่อย UNKNOWN/คำถามไว้เมื่อยังไม่มีคำตอบ เอกสารนี้ไม่ถูก import เข้า registry อัตโนมัติ

| ข้อมูลที่คนตัดสินใจ | ไฟล์ปลายทางเมื่อผ่านการพิจารณา | ขอบเขต |
| --- | --- | --- |
| ชื่อเรื่องและส่วนขยายที่ใช้ | `story.json` | schema version ปัจจุบันคือ 1; ไม่เพิ่ม keys นอก config schema |
| ข้อเท็จจริง/ข้อห้ามของโลก | `data/canon.json`, `story.json.rules` | canon มี status `PROPOSED`, `UNKNOWN`, `DISPUTED`, `LOCKED`; ใช้ LOCKED หลังมีการตัดสินใจจริง |
| ตัวละคร ความรู้และสิ่งที่ยังไม่รู้ | `data/characters.json` | knowledge อ้าง `after_scene` ที่มีอยู่; สิ่งที่จะรู้ในฉากหน้าไม่ใช่ความรู้ก่อนฉากนี้ |
| สถานที่ สิ่งของ และการเปลี่ยนจำนวน | `data/locations.json`, `data/items.json`, `data/inventory_ledger.json` | จำนวนไม่ทราบใช้ `null` ตาม schema ไม่เดาว่าเป็น 0; ตรวจหลักฐานตามลำดับฉาก |
| ตอน/ฉากและลำดับเหตุการณ์ | `data/episodes.json`, `data/scenes.json`, `data/events.json`, `scenes/<id>.md` | ตอนเริ่ม `OUTLINE`; ฉากเริ่ม `PLANNED`/สถานะงานจริง ไม่ใส่ APPROVED เพื่อข้ามขั้นตอน |
| state และประวัติก่อนฉาก | `data/story_state.json`, optional `data/state_history.json` | ไม่สร้างอดีตจาก planned effects; flags รับ boolean จริงเท่านั้น |
| สำนวนและข้อห้ามการเขียน | `bible/STYLE_GUIDE.md` | ใช้ style ของเรื่องนี้เท่านั้น; pack โหลดไฟล์นี้อยู่แล้ว |

ใช้ [schemas/v1/](schemas/v1/) เป็นสัญญาของทะเบียนจริง และ [schemas/story.schema.json](schemas/story.schema.json) สำหรับ config ตัวอย่าง scene schema มี fields เช่น `episode_id`, `order`, `pov`, `location_id`, `character_ids`, `item_ids`, `canon_refs`, `goal`, `conflict`, `outcome`, `beats`, `requires_flags`, `effects_flags`, `draft_path`; ทุก reference ต้องมีเป้าหมายจริง `check` จะรายงานตำแหน่งที่ผิด อย่าคัดลอกแถว UNKNOWN ของแบบฟอร์มไปทำเป็น ID หรือ knowledge record ที่ไม่มีหลักฐาน

Gameplay ปิดไว้โดยค่าเริ่มต้น (`extensions.gameplay: false`) เรื่องทั่วไปไม่ต้องมีทะเบียน mechanics/sources ถ้าเรื่องต้องใช้ส่วนขยายนี้จริง ให้จัดหาข้อมูลและหลักฐานตาม [E1](ENGINE_E1.md)/[E2](ENGINE_E2.md) ก่อนเปิด ไม่ใช้รายละเอียดเกมของเรื่องตัวอย่างแทนโลกใหม่

หลังคนเพิ่ม metadata แต่ละครั้ง ให้รัน `check` ใหม่ การผ่าน check ยืนยันเฉพาะเงื่อนไขที่โค้ดตรวจได้ ไม่ใช่ human editorial approval หรือการรับรองคุณภาพเนื้อหา

## 4. ใช้คำสั่งตามวงจรงานจริง

Scaffold เปล่ายังไม่มี `SC-001` จึงต้องปฏิเสธ `pack SC-001` ให้กรอกตอน/ฉากและ scene card ที่ถูกต้องก่อน บางคำสั่งต้องมี draft ที่อ่านได้หรือ approved evidence ด้วย ห้ามแต่งข้อมูลขึ้นมาเพียงเพื่อทำให้คำสั่งผ่าน

เมื่อ **มี target และ source ที่ถูกต้องแล้ว** คำสั่งต่อไปนี้ใช้ workspace/slug เดียวกัน เปลี่ยน IDs ตามเรื่องจริง:

```bash
python scripts/storyctl.py --workspace .local/onboarding-workspace --story my-story check
python scripts/storyctl.py --workspace .local/onboarding-workspace --story my-story pack SC-001 --out .local/onboarding-workspace/.local/SC-001-context.md
python scripts/storyctl.py --workspace .local/onboarding-workspace --story my-story replay SC-001 --out .local/onboarding-workspace/.local/SC-001-state.json
python scripts/storyctl.py --workspace .local/onboarding-workspace --story my-story brief-review SC-001 --base HEAD --out .local/onboarding-workspace/.local/SC-001-review.json
python scripts/storyctl.py --workspace .local/onboarding-workspace --story my-story propose EP-001 --out .local/onboarding-workspace/.local/EP-001-proposal.md
python scripts/storyctl.py --workspace .local/onboarding-workspace --story my-story doctor --target SC-001 --out .local/onboarding-workspace/.local/doctor.json
```

`pack`/`brief` ประกอบ context ของ target; `replay` อ่าน state **ก่อน** target จากหลักฐานที่เข้าเกณฑ์; `brief-review` ใส่ draft/diff/hash กับ HEAD/base ที่อ่านจาก Git จริง Working draft อาจต่างจาก HEAD จึงต้องตรวจ digest ของ draft ที่ส่ง ไม่อ้างว่า HEAD อนุมัติข้อความใน working tree แล้ว `propose` เป็น alias ของ `proposal` ที่เตรียมข้อเสนอโดยไม่ apply state/ledger/canon

`brief-review` ต้องใช้ Git anchor ที่มีอยู่จริงใน repository ซึ่งครอบคลุมแหล่งข้อมูลนั้น หากกำลังใช้ workspace เปล่าที่ไม่ได้อยู่ใน Git ให้คง gate นี้ NOT_RUN จนมี local history ที่เจ้าของงานจัดเตรียมจริง อย่าคิดว่า `new` สร้าง commit หรือ remote repository ให้แล้ว

เมื่อมี recap ที่ผ่านกระบวนการอนุมัติและ ledger อ้างหลักฐานครบจริง จึงใช้:

```bash
python scripts/storyctl.py --workspace .local/onboarding-workspace --story my-story rollup EP-001 EP-002 --out .local/onboarding-workspace/.local/rollup-proposal.json
```

IDs ต้องไม่ซ้ำและต่อเนื่องตาม series order `rollup` ต่อ recap เดิมแบบ deterministic พร้อม hashes ไม่สรุปด้วย LLM ไม่เขียน chapter/book ledger และ output คง `PROPOSED` ค่าเริ่มต้นคือ `UNVERIFIED_LOCAL_DECLARATIONS` ถ้าต้องอ่าน metadata/source จาก GitHub ใช้ explicit `verify-provenance` หรือ `rollup --repo OWNER/REPO --verify-remote` ตาม [E5](ENGINE_E5.md) การพบ bytes ใน merge commit ไม่พิสูจน์ว่า PR นั้นแก้ไฟล์หรือมนุษย์อนุมัติเนื้อหา

## 5. รักษาข้อมูลส่วนตัวและขอบเขตการอนุมัติ

ไฟล์ output ของ `brief-review`, `doctor`, `verify-provenance`, `rollup` ต้องอยู่ใต้ `<workspace>/.local/` ถ้าใช้ workspace อื่น path หลัง `--out` ต้องเปลี่ยนตามด้วย `pack`, `replay`, `propose` ยังใช้ output path แบบ compatibility เดิม จึงเลือก `.local/` เองเสมอเพื่อไม่เขียนทับ source ถ้าไม่ระบุ `--out` จะส่ง stdout ซึ่งอาจถูกเก็บใน log ได้

Review bundle มี draft/context เต็มส่วนที่เกี่ยวข้อง รวมถึงสิ่งที่ยังไม่เผยแพร่ ไม่แนบ public PR/issue หรือส่งคน/agent ภายนอกโดยไม่มีคำสั่งอนุญาตเฉพาะจากผู้ใช้ การเก็บใต้ `.local/` ไม่ได้เปลี่ยน privacy ของ GitHub หรือรับรอง repository permissions

| ค่า/เหตุการณ์ | ความหมายที่ใช้ได้ |
| --- | --- |
| `UNKNOWN` | หลักฐานไม่พอ; ไม่เติมค่าจากการคาดเดา |
| `OFFLINE_UNVERIFIED` | cache/fixture/local declarations ไม่ใช่ live GitHub verification |
| `OBSERVED_MERGED_METADATA` | live metadata/source ที่ตรวจตรงกัน; human editorial approval ยัง UNVERIFIED |
| `PROPOSED` | ข้อเสนอที่คนต้องพิจารณา; ยังไม่ถูก apply |
| local APPROVED/CANON หรือ local Git commit | คำประกาศ/anchor ในเครื่อง; ไม่ใช่หลักฐานยืนยันตัวบุคคลบน GitHub |
| คนอนุมัติเนื้อหา | ต้องมีคำตัดสินจริงต่อ story/target/digest ที่ตรงกัน; เครื่องมือไม่สร้างคำตัดสินแทน |

Workflow ของ writer/reviewer/updater อยู่ใน [runbook](docs/AGENT_RUNBOOK.md) การ review กับการตัดสินใจอนุมัติเป็นคนละขั้นตอน ไม่มีคำสั่งในชุดนี้ autoapprove หรือ merge

## 6. แก้ปัญหาโดยไม่ข้ามหลักฐาน

| อาการ | สิ่งที่ตรวจและแนวทางกลับมาทำงาน |
| --- | --- |
| `No story selected` / หา slug ไม่พบ | ตรวจ `--workspace`, `--story`, path `stories/<slug>/story.json`; ไม่ fallback ไปเรื่องตัวอย่าง |
| สร้างเรื่องซ้ำไม่ได้ | เป็นการป้องกัน overwrite; ใช้เรื่องเดิมโดยตั้งใจหรือเลือก slug ใหม่ ไม่ลบข้อมูลเพื่อบังคับผ่าน |
| import `jsonschema`/format dependency ไม่ได้ | ตรวจ Python/virtual environment และติดตั้ง requirements ทั้งชุดจากแหล่งที่กำหนด; ไม่ลด schema assertions |
| schema/version/reference ผิด | ใช้ error path และ schemas รุ่นปัจจุบันแก้ข้อมูลที่มีหลักฐาน; migration อัตโนมัติยังไม่มี |
| target ไม่พบ/scene card หาย | ตรวจ ID และ relative path ใต้ story root; empty scaffold ต้อง fail; ไม่สร้างฉากขึ้นมาแทน |
| approved source/recap หายหรืออ่านไม่ได้ | หยุด pack/rollup ที่อ้างมัน กู้ source จริงหรือแก้สถานะตามคำตัดสินเจ้าของงาน; warning ไม่ใช่ valid evidence |
| replay เป็น UNKNOWN | ตรวจ independent baseline และ deltas ที่เข้าเกณฑ์ครบถึงก่อน target; ไม่ใช้ future/unapproved records และไม่อนุมาน history จากแผน |
| before-condition ใน delta ขัดกัน | ตรวจ source/history ของช่วงนั้น หยุดแล้วเสนอแก้โดยมีหลักฐาน ไม่เลือกค่าที่ทำให้ผ่านเอง |
| source เกิน 1 MiB / pack เกิน cap | ลดขอบเขตด้วยวิธีที่ตรวจได้; ไม่ตัด canon หรือหลักฐานเงียบ ๆ เอกสาร E3/E4 ระบุ limits |
| input/draft/HEAD เปลี่ยนระหว่างสร้าง bundle | สร้างใหม่จาก snapshot ที่นิ่ง แล้วให้ reviewer ตรวจชุด/digest ใหม่ |
| `--out` ถูกปฏิเสธ | ใช้ `<workspace>/.local/...`; ไม่เขียนทับ source/cache และไม่ใช้ symlink/junction เพื่อออกนอกขอบเขต |
| Git อ่าน anchor ไม่ได้/option ไม่รองรับ | ให้ผู้ใช้จัดเตรียม local commit/ref และ Git ที่รองรับ; ไม่ fetch หรือสร้างประวัติให้ดูเหมือนอนุมัติ |
| live provenance error / exit 2 | exit 2 คือ offline UNVERIFIED; exit 1 คือ input/access/evidence fail; อย่าแปลงเป็น verified หรือสร้าง credentials เพื่อแก้เอง |
| `doctor` exit 0 แต่ GitHub fields UNKNOWN | แปลว่าไม่มี local error ที่ตรวจพบ ไม่ได้ตรวจ privacy/ruleset/CODEOWNERS/approval ให้แล้ว |

## 7. ทำซ้ำ acceptance โดยไม่แตะเรื่องจริง

หลังมี dependencies และ Git ที่รองรับแล้ว ใช้ runner ของ E6 จาก repository root โดยเลือก directory output ที่ยังไม่มี:

```bash
python scripts/acceptance.py --out .local/e6-acceptance
```

runner สร้าง workspace แยกใต้ output มี empty control และ synthetic three-scene metadata พร้อม local Git anchor สำหรับทดสอบคำสั่งเท่านั้น ไม่ copy/แก้ Last Island หรือเรื่องของผู้ใช้ และไม่ถือว่าการจำลอง PR/merge/APPROVED เป็น GitHub human approval ดู `report.json` และ artifacts ที่สร้างจริง ผล semantic blind review แยกอยู่ใน [RESULTS.md](evaluation/e6/RESULTS.md); runner ไม่เรียก reviewer หรือแสร้งให้คะแนน semantic เอง

หาก output เดิมมีอยู่ ให้ใช้ชื่อใหม่ การรันซ้ำไม่ควร overwrite งานเก่า คำสั่งใน acceptance ไม่แทนการอนุมัติให้เขียนนิยายจริง

## 8. หลักฐานการทดสอบคู่มือและสิ่งที่ยังเป็น gate

คำสั่ง setup ของ guide ถูกลองใน workspace ใหม่ที่ ignore อยู่ ด้วย Python 3.12.14 และ pinned dependencies ที่มีอยู่แล้ว: `new`, empty `check` (0 errors/0 warnings), `status`, `doctor` ผ่าน ส่วน duplicate `new`, `pack SC-001` บนเรื่องว่าง และ missing-story `check` ต้อง fail โดยไม่เปลี่ยน source files ไม่ติดตั้ง dependencies ซ้ำ ไม่ใช้ network และไม่สร้าง approval ในการ smoke นี้

proof run ของ E6 ใช้ `python scripts/acceptance.py --out .local/e6-workflow-proof` ผ่านทั้ง 17 ขั้นตอนและยืนยัน `source_preserved: true` โดย target ของ pack/review/doctor คือ `SC-002`, replay ตรวจ `SC-001` ถึง `SC-003`, proposal ใช้ `EP-003`, rollup ใช้ recaps `EP-001 EP-002` ใน fixture ที่แยกไว้ runner ยังระบุ semantic evaluation เป็น NOT_RUN และ human approval เป็น BLOCKED ตามขอบเขตของมัน ผล blind review เป็นหลักฐานอีกชุดหนึ่ง ไม่ได้ถูกสร้างจากคำว่า PASS ของ runner

นี่เป็นหลักฐาน onboarding/command smoke ไม่ใช่ผล complete suite หรือ semantic evaluation ของ final commit ให้ใช้ [readiness report](docs/ENGINE_READINESS.md), [ผล E6](evaluation/e6/RESULTS.md) และ exact-head CI ที่บันทึกใน Draft PR ของ milestone สำหรับผลรับงานจริง

สิ่งที่ต้องตัดสินใจหรือทำแยกยังรวมถึง E0 privacy/rulesets/permissions ที่ไม่ได้รับอนุญาตให้เปลี่ยน, authenticated human editorial approval, postmerge proposal workflow, การ apply ledger โดยมี human signoff และ migration/advanced diagnostics ที่อยู่นอกขอบเขตนี้ ทุก gate ที่ต้องมี human signoff แต่ยังไม่มีต้องเป็น BLOCKED/NOT_RUN ไม่ใช่ PASS การมีคู่มือนี้ไม่ประกาศว่า engine เสร็จครบทุก E0–E7 gate
