# Engine E3/E4 — หลักฐาน review และ workflow ที่แยกต่อเรื่อง

milestone นี้เพิ่มเครื่องมือเตรียมหลักฐาน review และวินิจฉัยข้อมูลในเครื่อง พร้อมสัญญาการส่งต่องาน writer/reviewer/updater ที่ใช้ได้กับทุก story root ไม่เขียนเนื้อเรื่อง ไม่เรียกโมเดล และไม่อนุมัติ canon เอกสารนี้ระบุความสามารถและวิธีใช้; ผล tests, commit, Draft PR และ CI ต้องอ้างผลจริงของ commit สุดท้ายใน PR

อ่าน [AGENTS.md](AGENTS.md) และ [runbook บทบาท agent](docs/AGENT_RUNBOOK.md) ก่อนทำงาน ส่วน [ENGINE_E2.md](ENGINE_E2.md) กำหนด schema/replay และ [ENGINE_E1.md](ENGINE_E1.md) กำหนด story roots กับ compatibility ข้อมูลตัวอย่าง Last Island คงอยู่ใน root ของตัวเองโดยไม่แก้เนื้อหา

## ขอบเขตที่ทำได้และงานที่ยังเหลือ

| ส่วน | ความสามารถปัจจุบัน | ขอบเขตที่ยังไม่ทำ |
| --- | --- | --- |
| E1 | story roots แยกกัน, config แบบมีเวอร์ชัน, scaffold ว่าง, extension กลไกเกมเลือกใช้ได้ | ไม่แปลงข้อมูลเรื่องอื่นให้อัตโนมัติ |
| E2 | JSON Schema จริง, semantic checks, replay ก่อน target จากหลักฐานในเครื่องที่ครบ | ไม่สร้างประวัติย้อนหลังจากแผนหรือ snapshot ปัจจุบัน |
| E3 บางส่วน | รายงานปัญหา schema/อ้างอิง/ประวัติจากข้อมูลในเครื่องผ่าน `doctor` | schema migration และ diagnostics ขั้นสูงยังรอ milestone ถัดไป |
| E4 | `brief-review`, alias `propose`, templates และบทบาท human workflow แบบ generic | ไม่รัน writer/reviewer/updater อัตโนมัติหรือให้คะแนนแทนผู้ตรวจ |
| E5 | แสดงข้อจำกัดของ local approval ให้ชัด | ยังไม่ตรวจผู้อนุมัติ, merged PR และ provenance จาก GitHub จริง |
| E6 บางส่วน | `doctor` เป็นการวินิจฉัย local ขั้นต้น | rollup ยังไม่ทำ และไม่มีคำสั่งจำลองที่ทำเสมือนสำเร็จ |
| E7 | ใช้ synthetic metadata กับ regression tests ตามขอบเขตของแต่ละ PR | ยังไม่อ้างว่า workflow ประเมินครบทุกขั้นหรือจับ semantic prose ได้ทั้งหมด |

คำว่า APPROVED ในไฟล์หรือ fixture เป็นข้อมูลที่ผู้ใช้ประกาศในเครื่อง ไม่ใช่หลักฐานว่าบุคคลใน GitHub อนุมัติจริง การผ่าน `check` หรือ `doctor` ไม่ยืนยันคุณภาพ prose, สิทธิ์ repository, branch settings หรือการบังคับ CODEOWNERS

## เริ่ม story ใหม่และเลือกขอบเขต

ใช้ Python 3.11+ และ dependencies ที่ pin ไว้จาก official PyPI:

ส่วน review/Git diagnostics ต้องใช้ Git ที่รองรับ global option [`--no-lazy-fetch`](https://git-scm.com/docs/git) ด้วย หาก Git ไม่รองรับให้ review fail หรือรายงาน Git diagnostics เป็น UNKNOWN ไม่อ้างว่ารองรับ Git ทุกเวอร์ชัน คำสั่งอ่านเฉพาะ objects ในเครื่อง ไม่ fetch ส่วนที่หาย ไม่ติดตั้ง Git และไม่เปลี่ยน persistent settings

```bash
python -m pip install --index-url https://pypi.org/simple --only-binary=:all: -r requirements.txt
python scripts/storyctl.py new my-story --title "My story"
python scripts/storyctl.py --story my-story check
python scripts/storyctl.py --story my-story status
python scripts/storyctl.py --story my-story doctor --out .local/doctor.json
```

`new` สร้าง config, registries ว่าง, ledger ว่าง และคำแนะนำทั่วไป ไม่สร้างชื่อคน เหตุการณ์ หรือ prose scaffold ว่างยังไม่มี scene ให้ pack/review มนุษย์ต้องกรอก metadata ที่จำเป็นและไฟล์ที่อ้างอิงก่อน อย่าเพิ่มข้อมูลสมมติเพียงเพื่อให้คำสั่งผ่าน

ระบุ `--story <slug>` ทุกครั้งเมื่อทำหลายเรื่อง หากใช้ workspace อื่นให้ระบุ `--workspace <path>` ด้วย แล้วเก็บ output ใหม่ภายใต้ `<workspace>/.local/` ของ workspace นั้น คำสั่งเดิมยังใช้ default ใน `studio.json`; engine ห้าม fallback ไปอ่านอีกเรื่องเมื่อไฟล์หาย

## เตรียม review จาก working draft จริง

หลัง target มี metadata ที่ผ่าน validation และ draft อ่านได้:

```bash
python scripts/storyctl.py --story my-story brief SC-001
python scripts/storyctl.py --story my-story pack SC-001 --out context.md
python scripts/storyctl.py --story my-story replay SC-001
python scripts/storyctl.py --story my-story brief-review SC-001 --base HEAD --out .local/reviews/SC-001.json
```

`brief-review` เตรียม JSON สำหรับฉากเดียวจาก draft ปัจจุบัน, diff, target context และ commit anchors ที่อ่านจาก Git จริง พร้อม digest ของ draft ผู้ตรวจต้องใช้ story, target, resolved HEAD/base และ digest ชุดเดียวกัน Working draft อาจมีการเปลี่ยนแปลงที่ยังไม่ commit; การมี HEAD ใน bundle ไม่ได้แปลว่าข้อความตรงกับ HEAD หรือผ่าน review แล้ว `--base HEAD` ใช้เทียบกับ HEAD ปัจจุบัน ส่วน base อื่นต้องเป็น ref ที่ตั้งใจและ resolve ได้จริง

คำสั่งนี้ต้องใช้ local Git repository ที่อ่าน HEAD/base ได้จริง พร้อม manifest ของ inputs ภายใน story ที่ pack/validation ใช้ โดยเก็บ SHA-256 และขนาดเป็น bytes เพื่อตรวจว่าข้อมูลไม่เปลี่ยนระหว่างสร้าง bundle Manifest อธิบาย working-tree sources ไม่ได้รับรองตัว engine code หรือยืนยันว่า context ตรงกับ commit ใด หากไม่มี draft path ใน base จะระบุว่าเป็นไฟล์เพิ่ม ไม่สร้าง base text ที่ไม่มีจริง

แต่ละ source ที่อ่านจำกัด 1 MiB รวม draft, base blob, registries, style และ evidence ที่เกี่ยวข้อง ต้องเป็น UTF-8 text ที่ยอมรับได้ Draft/base เก็บ CRLF และการไม่มี newline ท้ายไฟล์ตาม bytes จริง; unified diff ระบุกรณีไม่มี final newline ไม่ตัดข้อความให้ผ่าน limit ส่วน context ใช้ cap เดิมของ pack (ค่าเริ่มต้น 25,000 ตัวอักษร) ถ้าเกินให้ fail และลดขอบเขตอย่างชัดเจน ไม่ตัด canon ทิ้งเงียบ ๆ

bundle เริ่มต้นเป็น unreviewed evidence ไม่มีคะแนนหรือคำตัดสินจาก reviewer ที่แต่งขึ้น ไม่ใช่ approval record และไม่แก้ ledger/state หาก draft หรือ context เปลี่ยน ให้สร้าง bundle ใหม่และบันทึก scope ใหม่ อย่านำผล review เก่ามารับรองข้อมูลคนละชุด

file output ของ `brief-review` และ `doctor` รับเฉพาะภายใน `.local/` ของ workspace ที่เลือก หรือเลือกไม่ระบุ `--out` เพื่อแสดง stdout การจำกัดนี้ใช้กับสองคำสั่งใหม่; ไม่เปลี่ยนรูปแบบ output ของ CLI เดิม Bundle อาจมี draft, context และ diff ที่ยังไม่เผยแพร่ จึงเก็บในเครื่องที่ ignore ไว้ ห้ามแนบ public PR, issue หรือส่งภายนอกโดยไม่มีคำอนุญาตจากผู้ใช้ การแสดง stdout ก็ต้องคำนึงถึงข้อความที่อาจถูกเก็บใน log

## Diagnostics และข้อเสนอ

```bash
python scripts/storyctl.py --story my-story doctor --target SC-001 --out .local/doctor.json
python scripts/storyctl.py --story my-story propose EP-001
python scripts/storyctl.py --story my-story proposal EP-001
```

`doctor` อ่านข้อมูลในเครื่องและรายงานผลที่สังเกตได้ เช่น validation และสถานะ history สำหรับ target ที่ระบุ ใช้โดยไม่ระบุ `--target` เพื่อตรวจ local workspace ได้ การเขียนไฟล์รายงานไม่เปลี่ยน story data ไม่แก้ปัญหาแทนมนุษย์ และไม่ติดต่อ GitHub เพื่อยืนยัน auth/settings สิ่งที่ไม่ได้ตรวจต้องเป็น UNKNOWN หรือระบุว่าไม่ได้ตรวจ ห้ามแปล report เป็นการรับรอง branch protection หรือ CODEOWNERS enforcement

เมื่อมี local errors คำสั่งคืน exit code 1; การไม่รู้ Git metadata หรือไม่ตรวจ online controls ไม่กลายเป็นหลักฐานว่า local data ผิดเอง ดู errors, warnings, local validation และ state availability แยกกัน อย่าตีความ exit code 0 ว่า history ครบหรือได้รับ human approval

`propose` เป็น alias ของ `proposal` เดิม สร้างข้อเสนอให้มนุษย์พิจารณา ไม่ apply deltas, ไม่เลื่อนสถานะเป็น CANON และไม่ทำ rollup การเสนอเพิ่มข้อมูลกับการอนุมัติจริงเป็นคนละขั้นตอน

## ขอบเขต replay และ approval ที่ต้องรักษา

ใช้ schema/replay ตาม E2: history ที่ระบุไว้ต้องครบตั้งแต่ baseline ถึงก่อน target เท่านั้น; future/unapproved evidence ไม่ถูก replay ช่องว่างเป็น UNKNOWN โดยไม่คืน partial state และ before-condition ที่ขัดกันต้อง fail ไม่เดา state จาก planned effects ไม่เติมประวัติให้ตัวอย่างเก่า หากไม่มี history file ให้ใช้ compatibility snapshot/UNKNOWN ที่ E2 อธิบายอย่างตรงไปตรงมา

Writer ส่งเฉพาะงานที่ได้รับอนุญาตและข้อเสนอ Reviewer ให้ findings ตามหลักฐานของ scope นั้น Updater แก้ approved history ได้เมื่อมีคำตัดสินจากมนุษย์ที่อนุญาตการเปลี่ยนนั้นแล้วเท่านั้น ผลของเครื่องมือทั้งสามบทบาทไม่ใช่ canon ดูรายการส่งต่อและเกณฑ์หยุดใน [AGENT_RUNBOOK.md](docs/AGENT_RUNBOOK.md)

## Verification และ milestone ถัดไป

ก่อนส่ง Draft PR ต้องรันคำสั่งจริงและรายงาน PASS / FAIL / NOT RUN แยกกัน:

```bash
python scripts/novelctl.py check
python scripts/story_engine.py check
python -m unittest discover -s tests -v
```

ต้องตรวจ compatibility ของคำสั่งเก่า, สอง story datasets ที่แยกกัน, CLI ใหม่กับ synthetic metadata, target/time/approval boundaries, working draft ที่ต่างจาก HEAD, output ภายนอก `.local/` ที่ต้องถูกปฏิเสธ และ byte preservation ของข้อมูลตัวอย่าง ไม่ใช้เอกสารนี้แทนผลทดสอบ ไม่สร้าง reviewer scores หรือ friction entries ที่ไม่มีเหตุการณ์จริง หลัง push ต้องตรวจ CI ของ exact head ก่อนรายงานว่าเสร็จ

งานถัดไปยังต้องมี acceptance criteria แยก PR: E3 ที่เหลือทดสอบ migration แบบ reversible และ diagnostics ของ edge cases; E5 ตรวจ provenance จากผู้อนุมัติและ merged PR จริงโดยไม่เชื่อ local labels; E6 ออกแบบ rollup/status/doctor ขั้นสมบูรณ์ที่ไม่เปลี่ยน canon เกินสิทธิ์; E7 ทดสอบ synthetic workflow สามฉากครบขั้น โดย critical planted canon, knowledge และ approval violations ต้องถูกจับทั้งหมดก่อนอ้างว่าผ่านการประเมิน ไม่สร้างเนื้อเรื่องจริงเพื่อทดสอบ งานเหล่านี้ยังไม่ใช่ความสามารถที่เสร็จแล้วใน E3/E4
