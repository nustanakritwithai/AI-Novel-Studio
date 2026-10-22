# E6 — synthetic acceptance และการตรวจแบบ blind

E6 ตรวจเส้นทางเครื่องมือด้วยข้อมูล synthetic สามฉากและตรวจข้อขัดแย้งด้วย reviewer ใหม่แยกจากผู้สร้างโจทย์ ไม่มีเนื้อเรื่องจริง ไม่มี paid API และไม่อนุมัติ canon ดูผลที่วัดจริงใน [evaluation/e6/RESULTS.md](evaluation/e6/RESULTS.md) และ gate ที่ยังไม่ผ่านใน [readiness checklist](docs/ENGINE_READINESS.md)

## รัน command workflow ซ้ำ

ใช้ Python 3.11+ และติดตั้ง pinned dependencies ตาม [README](README.md) ก่อน จาก root ของ repository รัน:

```bash
python scripts/acceptance.py --out .local/e6-acceptance
```

ใช้ output directory ใหม่ทุกครั้ง เช่น `.local/e6-acceptance-2` ห้ามใช้ story จริงเป็น output โปรแกรมไม่เขียนทับ run เดิม ไม่เปลี่ยน default story ไม่ติดต่อ network และไม่รันโมเดล สร้าง workspace แยกใต้ `.local/` พร้อม metadata fixtures เท่านั้น

runner ใช้ CLI จริงสำหรับ `new`, empty `check`, populated `check`, `pack`, `brief-review`, `propose`, `replay`, `rollup` และ `doctor` ดูคำสั่ง/exit codes/ผลตรวจในรายงานของ run นั้น Git commit ภายใน workspace เป็น synthetic local anchor เพื่อทดสอบ review bundle ไม่ใช่ GitHub PR, merge หรือ human editorial approval ทุก label APPROVED/LOCKED ใน fixture เป็นข้อมูลทดสอบที่ประกาศไว้เท่านั้น

fixture มีสามฉากตามลำดับ: SC-001 ใช้ token จากหนึ่งเหลือศูนย์, SC-002 มี delta ว่างที่ระบุชัดว่าไม่เปลี่ยน state, SC-003 จึงบันทึกการได้ความรู้ใหม่ การ replay ก่อนฉากต้องไม่ดึง delta ของฉากนั้นหรืออนาคตกลับมาใช้ การขาดหลักฐานหรือเปลี่ยนสถานะเป็น unapproved ต้องไม่ทำให้เกิดความรู้หรือ inventory ที่แต่งขึ้นเอง

การผ่าน runner และ unit tests เป็น **structural/command acceptance** ไม่ใช่ผล semantic review และไม่ยืนยันคุณภาพงานเขียน

## โปรโตคอล semantic review ที่แยก input

1. เก็บ context pack ของ SC-002 และ candidate assertions เป็น packet คงที่ ระบุ hash ของ packet และ context ใน [manifest](evaluation/e6/manifest.json) แทน absolute fixture path ด้วย `<SYNTHETIC_STORY_ROOT>` เท่านั้น
2. ผู้สร้างโจทย์บันทึกข้อผิดพลาดห้าข้อและ clean control ใน [answer key](evaluation/e6/answer_key.json) แล้วคำนวณ SHA-256 **ก่อน** ส่งงาน reviewer ห้ามแก้ key หรือ packet เพื่อให้เข้ากับผลภายหลัง
3. ส่ง reviewer แต่ละรายเป็น fresh native agent โดยใช้ `fork_turns=none` ให้คนละ packet เท่านั้น ห้ามให้ author reasoning, answer key, role ของ candidate หรือจำนวนข้อผิดพลาดที่คาดไว้ Reviewer ต้องแยก contradiction/unsupported claim/UNKNOWN และอ้าง claim ID กับหลักฐานใน packet ไม่มีคะแนนคุณภาพที่สมมติขึ้น
4. เก็บ raw report โดยไม่แก้คำตอบ แล้วเทียบผลจริงกับ key หลัง review จบ บันทึกทุก miss และ false positive ของ control ถ้า critical canon/knowledge/inventory/approval fault หลุด ต้อง BLOCK gate นั้น ไม่เปลี่ยนโจทย์หรือปิด miss เงียบ ๆ
5. Reviewer ไม่ใช่มนุษย์ผู้มีอำนาจอนุมัติ บัญชี agent, passing tests และ local Git commit ไม่อนุญาตให้ promote canon หรือ merge

นี่คือ **procedural blind review**: ประวัติของ reviewer แยกจากผู้สร้างและจำกัดไฟล์ด้วยคำสั่ง แต่ระบบไฟล์ของทีมยังใช้ร่วมกัน ไม่อ้างว่าเป็น OS sandbox หรือ cryptographic access control SHA-256 ช่วยตรวจว่า input/key เปลี่ยนหรือไม่ ไม่พิสูจน์การปิดบังข้อมูลด้วยตัวมันเอง

packet เป็น labeled metadata assertions ไม่มี novel prose จึงวัดเฉพาะการพบข้อขัดแย้งที่ระบุใน synthetic case นี้ ไม่ใช่ literary style, ความสามารถทุกภาษา, ความสม่ำเสมอหลายรอบ หรือผล review นิยายจริง

## รัน reviewer ซ้ำโดยไม่ทำเป็นผลอัตโนมัติ

ให้ผู้ประสานงานสร้าง reviewer ใหม่สองราย คนละ packet ใน `evaluation/e6/packets/` ห้ามส่ง key หรือรายงานเก่าไปพร้อม input ใช้สัญญา output ตาม raw report เดิมได้ แต่ไม่มี expected answer/count หากยังไม่มี reviewer จริง ให้บันทึก NOT_RUN ห้ามให้ runner สร้าง findings หรือ success stub แทน reviewer

ผลที่ versioned อยู่เป็นผลการทดลองที่บันทึกครั้งหนึ่ง CI ตรวจ integrity และคำสั่งซ้ำได้ แต่ CI ไม่ได้เรียก semantic reviewer ใหม่ การเปลี่ยน packet/key ต้องทำ evaluation ใหม่และเก็บผลเก่าอย่างชัดเจน

## ขั้นต่อไปก่อนใช้งานจริง

ใช้ [คู่มือ E7](ENGINE_E7.md) กับ [template รับข้อมูล](templates/STORY_INPUT_TH.md) เพื่อเริ่มเรื่องใหม่โดยไม่แก้ core ข้อกำหนด privacy/rulesets, authenticated human editorial approval, postmerge ledger workflow และ reversible schema migration ยังต้องตรวจรับแยกตาม [readiness checklist](docs/ENGINE_READINESS.md) ห้ามเรียก engine ทั้ง E0–E7 ว่าเสร็จครบเพราะ synthetic case ผ่าน
