# AI Novel Studio v0.1 — GitHub-first Story Continuity System

**โครงการตัวอย่าง:** LAST ISLAND: WORLD CHAMPIONSHIP — เริ่มเล่าเรื่องเมื่อพระเอกเล่นเกม Full-Dive VR แบบส่วนตัวในห้องของตน ไม่ใช่เปิดเวทีชิงแชมป์โลก

## จุดประสงค์

GitHub เป็น **source of truth** ไม่ใช่แชต AI: บันทึกเนื้อเรื่อง ตัวละคร ลำดับเหตุการณ์ ทรัพยากร รู้/ไม่รู้ของแต่ละคน แหล่งอ้างอิงเกมเพลย์ และประเด็นที่ยังไม่สรุป AI นักเขียนคนต่อไปอ่าน `AGENTS.md` และขอ `brief` เฉพาะฉากได้โดยไม่ต้องย้อนอ่านบทสนทนาหลายพันข้อความ

> **สถานะ:** Starter working kit. ตัวตรวจเชิงโครงสร้างทำงานแล้ว แต่ยังไม่ใช่ตัวพิสูจน์ความสมจริงของบทหรือเข้าใจนัยภาษาโดยอัตโนมัติ ฉากแรกทั้งหมดอยู่ขั้น OUTLINE; **ยังไม่ได้มีบทนิยายที่อนุมัติ**.

## เริ่มใช้ใน 1 นาที

```bash
python scripts/novelctl.py status
python scripts/novelctl.py check
python scripts/novelctl.py brief SC-001 --out my-brief.md
python scripts/novelctl.py research
python -m unittest discover -s tests -v
```

ไม่มี package ภายนอก; ใช้ Python 3.11+ และไลบรารีมาตรฐาน ใช้กับ GitHub Actions ได้

อ่านบันทึกข้อมูลผ่านเว็บ: จากโฟลเดอร์โครงการ เรียก `python -m http.server 8000` แล้วเปิด `http://localhost:8000/` เพื่อดู dashboard `index.html` (เปิดไฟล์ HTML ตรง ๆ อาจถูกเบราว์เซอร์บล็อกการอ่าน JSON)

## โครงสร้าง

```text
AGENTS.md                     กฎของ AI writer/editor ทุกตัว
PROJECT.md                    จุดประสงค์ ขอบเขต ความสำเร็จ
STATE.md                      สถานะมนุษย์อ่านได้ / สิ่งที่ไม่รู้
HANDOFF.md                    จุดเริ่มต้นรับช่วงต่อ
bible/                        Story Bible โลก กลไก ชุดตัวละคร ฉาก/สถานที่ น้ำเสียง
plot/                         ซีรีส์, ซีซัน, รายตอน
scenes/                       Scene Cards (หนึ่งไฟล์ต่อฉาก)
drafts/                       บทฉบับร่าง (ไม่มีฉากที่อนุมัติใน v0.1)
research/                     ทะเบียนหลักฐานคลิปและ gap จากเกมจริง
data/                         Machine-readable canon/characters/events/state/inventory/threads/etc.
scripts/novelctl.py           ตรวจอ้างอิง สร้าง context pack ส่งต่อ
index.html                    Dashboard อ่านข้อมูลแบบ responsive
.github/                      CI GitHub Actions + Issue/PR templates + Copilot instructions
tests/                        Regression tests
EXAMPLE_CONTEXT_PACK.md       ตัวอย่าง context สำหรับฉากต่อสู้ SC-006
```

## การออกแบบความจริง 3 ชั้น (สำคัญ)

1. **STORY LOCKED**: ข้อกำหนดของผู้แต่ง เช่น "เริ่มในห้องส่วนตัว", "บ้าน 2×2", "กล่องเศษวัสดุ 1 กล่อง", "ต่อสู้ไม้เบสบอล" เป็น canon *ของเรื่อง* แม้ยังต้องตรวจเกมจริง
2. **GAMEPLAY EVIDENCE**: กฎที่พบจากคลิปจริง บันทึก Source ID + URL + timestamp + ระดับหลักฐาน (`TRANSCRIPT_ONLY`, `VIDEO_REVIEWED`). อย่าข้ามจากคลิปเซิร์ฟเวอร์หนึ่งเป็นกฎทุกโหมด
3. **FICTIONAL WORLDBUILDING**: เทคโนโลยี Full-Dive VR, รายการแข่งขันผู้เล่น 100 คนในอนาคต เป็นของโลกนิยาย ไม่ใช่การอ้างว่ามีจริงหรือมีในเกมปัจจุบัน

`UNKNOWN ≠ PASS`. รายละเอียดที่ AI เคยเสนอ (พระเอกชื่อ "บอส", ค.ศ. 2045, รางวัล $100M) ถูกเก็บไว้เป็น `PROPOSED` เท่านั้น

## วงจรเขียนงานหนึ่งฉาก

1. เปิด Issue เขียนฉาก มี Scene ID (ตัวอย่าง SC-001)
2. AI อ่าน `AGENTS.md`, `STATE.md` แล้วรัน `brief SC-001`; **อย่าโหลดทุกไฟล์เข้าคอนเท็กซ์**
3. AI เขียนไฟล์ `drafts/EP-001/SC-001.md` บน **branch ใหม่** พร้อมบันทึก NEW_FACTS / changed items / locations / knowledge
4. อัปเดต `data/scenes.json` ให้เป็น `DRAFT` (ไม่เปลี่ยน canonical state)
5. เปิด Pull Request: Reviewer ตรวจความต่อเนื่อง ความถูกต้องจากเกมเพลย์ เสียงตัวละคร ขัดแย้งกับ LOCKED หรือไม่
6. GitHub Actions เรียก `python scripts/novelctl.py check` และ unit tests (ตรวจโครงสร้างเท่านั้น)
7. **มนุษย์อนุมัติ** แล้วค่อยเปลี่ยนสถานะจาก DRAFT → APPROVED/CANON พร้อมปรับ `data/events.json`, `data/story_state.json`, `STATE.md`, `HANDOFF.md` ใน PR เดียวกัน

### ห้ามทำ

- แต่งตัวละครใหม่แล้วอ้างว่าเคยปรากฏ
- ให้ตัวละครรู้ข้อมูลนอก POV/เวลาของตัวเอง
- สร้างกระสุน/ไอเทม/อุปกรณ์จำนวนไม่จำกัดโดยไม่มีเหตุการณ์ได้มา
- เปลี่ยนว่าเปิดเรื่องในเวทีแข่งขัน (ขัด FACT-002)
- ล็อกสูตรไม้เบสบอลว่าเป็นสูตรในเกมจริงจนกว่าจะมีหลักฐาน gameplay เฉพาะเวอร์ชัน
- ให้ AI auto-merge หรือ auto-approve สิ่งที่ต้องใช้การตัดสินใจเชิงเนื้อเรื่อง

## ขึ้น GitHub

จัดโครงการเป็น repository **แยกใหม่** เช่น `AI-Novel-Studio`; แนะนำ **Private** ตอนกำลังร่างนิยาย

กรณีสร้าง repo เปล่าจาก GitHub (อย่าให้ GitHub สร้าง README/.gitignore ไว้ก่อน):

```bash
git init
git add .
git commit -m "Initialize AI Novel Studio with Last Island continuity system"
git branch -M main
git remote add origin https://github.com/<YOUR_USERNAME>/AI-Novel-Studio.git
git push -u origin main
```

> **ความเป็นส่วนตัว**: GitHub Pages อาจเผยแพร่ข้อมูลให้บุคคลทั่วไปเข้าถึงได้ตามรูปแบบบัญชี/การตั้งค่า อย่าเปิด Pages จนกว่าจะตรวจสิทธิ์และยืนยันว่าไม่มีร่างที่ต้องเก็บเป็นส่วนตัว; Dashboard ใช้ผ่าน localhost ได้โดยไม่ต้องเปิด Pages

### ใช้ AI บน GitHub

มี `.github/copilot-instructions.md` และ `AGENTS.md` เป็นกฎกลางที่รองรับ AI agents; ความสามารถจริงขึ้นกับเครื่องมือ/แพ็กเกจที่เชื่อม ไม่ใช่การทำงานอัตโนมัติโดย repo เฉย ๆ. [GitHub custom instructions](https://docs.github.com/en/copilot/concepts/prompting-and-context/custom-instructions)

## เป้าหมาย v0.2

- จำแนกเหตุการณ์เวลาในเกม vs เวลาโลกจริงละเอียดขึ้น
- Inventory Ledger ที่ระบุจำนวนเมื่อมีหลักฐาน (ตอนนี้ไม่เดาจำนวน)
- ตรวจ POV knowledge กับเหตุการณ์ในร่าง prose แบบกึ่งอัตโนมัติ
- หน้าสร้าง Issue/Draft จากหน้าเว็บผ่านการยืนยันตัวตนที่ปลอดภัย
- ระบบ story arcs/relationships และ regression test ตามพล็อตใหญ่

## More continuity ledgers

- `data/inventory_ledger.json` บันทึกไอเทมที่ได้/ใช้/คราฟต์/ปล้น พร้อม Scene ID; จำนวนที่ไม่รู้เป็น `null` และห้ามบวกเลขเอง
- `data/threads.json` ติดตามปมเรื่องที่ยังเปิดอยู่และฉาก setup/payoff
- `data/relationships.json` เก็บความสัมพันธ์ที่ตรวจสอบย้อนกลับถึงฉาก (ยังไม่ล็อกใครเป็นเพื่อน/ศัตรูถาวร)
- `data/decisions.json` เป็นทะเบียนคำตัดสินของผู้เขียนที่มีอำนาจเหนือข้อเสนอของ AI
