# อ่านฉาก ตรวจหลักฐาน และส่งงานระหว่าง agent ภายใต้ owner

ชุดนี้เป็นเครื่องมือช่วยงานเขียนนิยาย ไม่ใช่ตัวจำลองโลกหรือระบบอนุมัติเรื่องอัตโนมัติ ใช้โมเดล/agent ที่ผู้ใช้เลือกในแอปด้วย handoff ที่ชัดเจน CLI ไม่เรียกโมเดล ไม่ต้องมี API key, paid API, LINE หรือ n8n

## Packet สำหรับ reviewer

```bash
python scripts/storyctl.py --story my-story review-packet SC-001 --out .local/run1/packet-v1.json
python scripts/storyctl.py --story my-story review-check --packet .local/run1/packet-v1.json --report .local/run1/reviewer-v1.json --out .local/run1/checked-v1.json
```

`review-packet` จับ **raw working draft จริงเสมอ** พร้อม SHA-256/byte length และ scene-only context จาก `prepare-scene` ตัวเลือก `--source-mode committed` ใช้กับหลักฐาน context เท่านั้น ไม่แทน draft ที่ reviewer ต้องอ่านด้วย blob เก่า มี local Git HEAD/base diff เมื่ออ่านได้ ถ้าไม่มี Git ให้แสดง UNKNOWN ไม่ติดตั้งหรือ fetch เพิ่ม

ส่ง packet ให้ reviewer ใหม่ที่ไม่ได้รับเหตุผลของ writer หรือ answer key ให้ตรวจ canon, POV knowledge, inventory, ลำดับเวลา, สภาพ/เส้นทางของบ้านและ approval boundary แยก `CONTRADICTION` ที่มีหลักฐานจาก `UNKNOWN` ที่ข้อมูลไม่พอ ห้ามใช้ schema/hash เป็นหลักฐานว่าการตีความถูก

Reviewer ส่ง JSON ตาม `schemas/v1/grounded_review_report.schema.json`: packet ID, draft hash, coverage, limitations และ findings แต่ละข้อมี quote/เลขบรรทัดใน draft กับ JSON Pointer/quote ใน `scene_preparation.content` ตัวตรวจยืนยันตำแหน่งและตัวตน input เท่านั้น ผลเป็น `BOUND_ADVISORY_NOT_APPROVAL` แม้ไม่พบ findings ก็ไม่ใช่ semantic PASS หรือการรับรองความครบถ้วน

## Flashback และเวลาที่ไม่ผูกกัน

```bash
python scripts/storyctl.py --story my-story review-packet SC-002 --world-clock CLOCK-MAIN --world-tick 5 --world-suborder 0 --world-boundary BEFORE --out .local/run2/flashback.json
```

ต้องระบุ world cursor ทั้งสี่ค่าเอง ไม่มีการแปลง scene order เป็น world time เมื่อยังไม่มี mapping ที่ตรวจได้ รุ่นนี้จงใจไม่ให้ความรู้/ยอดของ/ประวัติ thread/house state ที่กรองด้วย narrative order เข้า writer context ของ world cursor นั้น เก็บ style และแผนฉากที่ระบุชัดว่าเป็น author input; world preview แยกสำหรับผู้เขียนและยัง PROPOSED สิ่งที่ไม่รู้ยัง UNKNOWN การไม่พบข้อมูลบันไดไม่ได้พิสูจน์ว่าไม่มีบันได

นี่เป็นขอบเขตที่ปลอดภัยสำหรับ flashback ไม่ใช่ระบบย้อนเวลา POV อัตโนมัติหรือการพิสูจน์ mapping การเล่ากับโลก การจัด mapping/knowledge ที่ละเอียดกว่านี้ยังไม่ได้ทำ

## Supervised handoff ที่บันทึกได้จริง

`scene-flow` ไม่ dispatch agent เอง Coordinator ส่งงานให้ native agent ตามสิทธิ์ที่ผู้ใช้ให้ แล้วเก็บคำตอบดิบ/ไฟล์ไว้ใน `.local/` ทุก handoff ใช้ packet/draft hash ที่ agent ได้อ่านจริง ห้ามใส่ชื่อ reviewer/คะแนน/คำอนุมัติที่ไม่ได้เกิดขึ้น

1. **Planner** รับ context ของฉากเดียว ระบุข้อกำหนด/ข้อเสนอ/UNKNOWN ไม่เพิ่มข้อเท็จจริงจากฉากอนาคต
2. **Writer** รับแผนและ context ที่ผูก hash หากงานเขียนได้รับอนุญาตจึงแก้เฉพาะ draft ฉากที่ระบุ งาน engine ใช้เฉพาะ synthetic assertion fixtures ไม่สร้างเนื้อเรื่องจริง
3. **Reviewer** เป็นคนละ agent อ่าน draft และ packet จริง ไม่รับ answer key หรือเหตุผล writer ส่ง grounded report ตาม schema
4. **Revision** แก้ตาม finding IDs ภายใน scope เก็บ draft เก่าและคำตอบดิบไว้ สร้าง packet ใหม่และให้ reviewer อ่านใหม่เสมอ ผลที่ผูก hash เก่าใช้กับ draft ใหม่ไม่ได้
5. **Owner checkpoint** มนุษย์อ่านฉบับล่าสุดกับผลตรวจจริง local note เป็นเพียงบันทึกที่ยัง UNVERIFIED ไม่ยืนยันตัวตนหรือการอนุมัติแทนเจ้าของ
6. **Delta proposal แยกต่างหาก** ส่ง claims ที่ผูก draft ล่าสุดเข้า `propose-deltas` เก็บเป็นข้อเสนอที่ยังไม่อนุมัติ ไม่ใช่การผ่าน owner gate หรือการแก้ canon/ledger/state

ตัวอย่างบันทึกแต่ละ stage:

```bash
python scripts/storyctl.py --story my-story scene-flow PLANNER --packet .local/run1/packet-v1.json --artifact .local/run1/planner-note.json --out .local/run1/flow-01.json
python scripts/storyctl.py --story my-story scene-flow WRITER --packet .local/run1/packet-v2.json --artifact .local/run1/writer-note.json --previous .local/run1/flow-01.json --out .local/run1/flow-02.json
python scripts/storyctl.py --story my-story scene-flow REVIEWER --packet .local/run1/packet-v2.json --artifact .local/run1/reviewer-note.json --previous .local/run1/flow-02.json --out .local/run1/flow-03.json
python scripts/storyctl.py --story my-story scene-flow VERIFY --previous .local/run1/flow-03.json --packet .local/run1/packet-v2.json
```

ไฟล์ note มี `packet_id`, `draft_sha256`, `notes` ซึ่งต้องตรงกับ packet จริง สำหรับ REVIEWER เพิ่ม `report` เป็น report JSON ทั้งฉบับ Stage อื่นไม่รับ field เพิ่ม ตัวอย่างนี้ใช้ชื่อไฟล์สมมติ ต้องสร้าง artifact จากงานจริงก่อน ไม่ใช่ success stub

คำสั่งปฏิเสธ stage ผิดลำดับ, input เก่า/คนละ story, output นอก `.local/`, การเขียนทับ, known contradictions ที่ยังไม่ผ่าน revision/review ใหม่ และ revision ที่ draft ไม่เปลี่ยน เก็บ chain จำกัด 32 stages การ VERIFY เช็กความต่อเนื่องและ digest ของข้อมูลที่ให้มา ไม่ดึง source/review ประวัติจาก remote และไม่พิสูจน์ว่าคนที่อ้างชื่อเป็นเจ้าของจริง หากส่ง `--packet` จะตรวจเทียบ current draft/context อีกครั้งด้วย

`OWNER_CHECKPOINT` ยังแสดง `owner_gate: BLOCKED_AUTHENTICATED_SIGNOFF_NOT_ESTABLISHED` เสมอ และ workflow หยุดที่จุดนี้ ไม่อนุญาตบันทึก stage ต่อไปโดยใช้ local note แทนคำอนุมัติจริง ไม่มี `approve`/`apply`/`merge` command ข้อเสนอจาก `propose-deltas` เป็น artifact แยกที่ยังไม่อนุมัติ ไม่ใช่การปลด gate การทดลอง synthetic จึงรายงาน human signoff เป็น BLOCKED/NOT_RUN ไม่ปลอมขั้นตอนคนจริงเพื่อให้ workflow ดูครบ

## การพิสูจน์และข้อจำกัด

`scene_workflow_acceptance.py` แยกจาก acceptance เดิม ใช้ scaffold ใหม่ สามฉากจำลองที่มี world order ต่างจาก narration และส่วนบ้านที่ยังไม่เสร็จ รัน CLI จริงและตรวจ source/approval boundaries การทดสอบ deterministic ไม่ใช่ semantic review ส่วนผล native blind reviewer และ clean control ต้องเก็บคำตอบดิบพร้อม hash และรายงาน hit/miss/false positive จริงแยกต่างหาก

```bash
python scripts/scene_workflow_acceptance.py --out .local/scene-workflow-run-01
```

ใช้ directory ใหม่ทุกครั้ง ถ้ารันไม่ผ่านให้เก็บ report/inputs ไว้แล้ววิเคราะห์ ห้ามล้าง directory อื่นเพื่อทำให้ผ่าน `PASS` ของ runner หมายถึงคำสั่ง/ขอบเขตข้อมูลเท่านั้น ผล semantic เป็น NOT_RUN และ owner เป็น BLOCKED เสมอ ผล native ที่รันแยกแล้วอยู่ใน [หลักฐานการทดลอง](../evaluation/scene_workflow_v1/README.md) และไม่ถูกรันโมเดลซ้ำโดย CI

อ้างอิง [source modes](SCENE_PREPARATION_TH.md), [delta proposals](SCENE_DELTAS_TH.md), [agent runbook](AGENT_RUNBOOK.md) และ [roadmap](ENGINE_NEXT_BATCHES_TH.md) Windows raw pinned-source checks ยังคงเข้มตาม bytes จริง ไม่อ้าง full Windows pass จาก Linux CI และไม่เปลี่ยน CRLF/settings เพื่อซ่อนปัญหา
