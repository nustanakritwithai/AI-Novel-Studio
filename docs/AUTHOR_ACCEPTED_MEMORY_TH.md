# ระยะที่ 1 — Author-Accepted Memory (ความจำจากต้นฉบับที่ผู้แต่งรับรอง)

**สถานะ:** ระบบอ่าน/ตรวจแบบ opt-in และใช้ source-bound recaps เพื่อให้ AI เขียนต่อได้โดยไม่สับสนกับประวัติที่ยังไม่รับรองด้วย GitHub Review

## ทำไมแยกสองช่องความจำ

AI Novel Studio มีสองระดับหลักฐานที่ต่างกันและ **ห้ามสับสน**:

1. `ledger/index.json` — **GitHub-review-approved ledger** เดิม เก็บสรุปจากบทที่มีหลักฐาน GitHub `APPROVE` review และ merge จริง ต้องมีผู้รีวิว/หมายเลข PR/merge SHA ห้ามแต่งย้อนหลัง
2. `author_memory/index.json` — **Author-accepted source memory** เก็บสรุปบทจากต้นฉบับที่ผู้แต่งอนุมัติผ่านแชตและบันทึกเป็น local GitHub decision แล้ว ระบุ `AUTHOR_ACCEPTED_IN_CHAT` อย่างตรงไปตรงมา ไม่ปลอมเป็น GitHub Review

ความจำอย่างที่สองช่วยให้ต่อเรื่องได้ **โดยไม่ทำลายหลักฐานของอย่างแรก** แต่หลักฐานแชตที่บันทึกไว้เป็น local declaration ไม่ได้พิสูจน์ตัวตนของเจ้าของบัญชี GitHub โดยอัตโนมัติ

## Last Island: หลักฐานที่ใช้

- เรื่องที่เลือก: `stories/last-island-active` (ไม่แตะ `stories/last-island` ตัวอย่าง E1 ที่ตรวจ bytes 54 ไฟล์)
- ผู้เขียนให้คำอนุมัติผ่านแชตวันที่ **2026-10-23**; Decision `DEC-004`
- ต้นฉบับที่รับรอง: `drafts/EP-001/CH-01-FULL-DRAFT.md` และ `drafts/EP-002/CH-02-FULL-DRAFT.md`
- ต้นทางการ Merge: [PR #13](https://github.com/nustanakritwithai/AI-Novel-Studio/pull/13); Git head `3d0b3117b2a4a4029fe815899e5c7a28e69eb56f`, merged commit `5d32a9ff95b3b64953a792be3bd7fef078343a1f`
- แหล่งคำอนุมัติใน Repo: `editorial/AUTHOR_APPROVAL_2026-10-23.json`, `data/decisions.json`, `data/episodes.json.author_decision`, `data/story_state.json.author_approval`
- GitHub `APPROVE` review สำหรับ PR #13: **NOT_OBSERVED**; อย่าแต่ง username หรือช่วงเวลาการอนุมัติ

## วิธีใช้

สั่งจาก repository root (Python 3.11+ และติดตั้ง dependencies ใน `requirements.txt`):

```bash
python scripts/storyctl.py --story last-island-active check
python scripts/storyctl.py --story last-island-active memory
python scripts/storyctl.py --story last-island-active memory --before EP-002
python scripts/storyctl.py --story last-island-active pack EP-002
```

- `memory` แสดงสรุป **ทั้งสองบทที่ผู้แต่งรับรองต้นฉบับ** สำหรับวางแผนบทถัดไป พร้อมสถานะหลักฐาน
- `memory --before EP-002` คืนเฉพาะ EP-001; **ไม่ฉีด EP-002 หรือข้อมูลอนาคตเข้าก่อนเริ่ม EP-002**
- `pack EP-002` รวมฉากที่เลือก Canon LOCKED, approved-history ตามเดิม และสรุป EP-001 ในช่อง Author-Accepted โดย **แยกหัวข้อและระดับหลักฐาน**
- `memory --before SC-018` ก็ตัดตาม Episode ของฉากนั้น ไม่เปิดเผยสรุป EP-002 ที่ยังเป็นอนาคตของฉาก
- `memory --recent 0` ไม่คืนสรุป
- ผลลัพธ์ที่ส่งไฟล์ด้วย `memory --out` ต้องอยู่ใน `.local/` เพื่อไม่ให้เขียนทับ source ของนิยาย

หากยังไม่เริ่มบทที่ 3 ให้ใช้ `memory` เพื่อทบทวนสองบทโดยตรง เมื่อผู้แต่งกำหนดบทที่ 3 และจดทะเบียน `EP-003` จริงแล้วจึงใช้ `pack EP-003` ตามลำดับเรื่อง ห้ามเพิ่มเนื้อหาบทที่ 3 ขึ้นมาเพียงเพราะระบบต้องการ target

## พฤติกรรมเมื่อข้อมูลไม่ตรงกัน (fail-closed)

โมดูล `scripts/author_memory.py` ตรวจอย่างน้อย:

- ลำดับ Episode ต้องไม่ข้ามตอน/ซ้ำ; scene IDs ต้องตรงกับทะเบียนที่เลือก
- ชื่อเรื่องที่เลือก, Decision ID, authority `USER`, สถานะ `APPROVED_BY_USER`, ช่อง `ChatGPT`, PR/head/merge SHA ต้องตรงกับแหล่งอนุมัติที่บันทึกไว้
- **Git blob SHA-1** ของต้นฉบับต้องตรงกับต้นฉบับที่เจ้าของเรื่องรับรอง
- สรุปต้องอยู่ใน `author_memory/episodes/` และ Git blob SHA-1 ตรงกับค่าที่ตรึงไว้ใน index
- ต้องจำกัด path ไม่ให้อ่านนอก story, ป้องกัน duplicate JSON keys, จำกัดขนาดไฟล์ และปฏิเสธข้อมูลที่ยังไม่อยู่ในคำอนุมัติ
- กรณีไม่ตรงต้องทำให้ `check`, `memory` และ `pack` ล้มเหลว ไม่เปิดทางให้ความจำที่ไม่ได้รับรองหลุดเข้า Context

> การตรวจ SHA ในเครื่องพิสูจน์ความตรงของ bytes กับ **คำประกาศต้นฉบับที่เก็บไว้** ไม่พิสูจน์ผู้อนุมัติจริงหรือการเชื่อมโยง GitHub Review แยกจากนั้น หากผู้มีสิทธิ์แก้ทุกไฟล์และข้อมูลอ้างอิงพร้อมกัน โปรแกรมไม่อาจรับรองความเป็นตัวตนจากไฟล์ล้วน ๆ ได้

## ความถูกต้องของสรุป

- บท EP-001: บ้านไม้ 2×2 ชั้นเดียว, กล่องเศษวัสดุริมถนน **หนึ่งกล่อง**, เอาชนะคนถือไม้เบสบอลอย่างเฉียดฉิว, จบบทในบ้านขั้นพื้นฐาน ไม่มีเตียงหรือโต๊ะคราฟต์
- บท EP-002: โต๊ะคราฟต์ กล่อง ที่นอน, ถูกมือธนูยิงตายและเกิดใหม่, คราฟต์ธนูกลับไปเอาของคืน, ยิงผู้เล่น 2 คนใกล้ฐาน 4×4, กลับอัปโครงสร้างหิน เพิ่มบันไดชั้นยิง และออฟไลน์
- ปริมาณไม้ หิน เศษวัสดุ ลูกธนู และ HP **UNKNOWN**; ไม่คิดเลขขึ้นเอง
- มือธนูที่พบใกล้บ้าน 4×4 เป็นเป้าหมายที่พระเอกสงสัยว่าเป็นผู้โจมตีก่อนหน้า แต่ยังไม่มีหลักฐานระบุตัวตนแน่ชัด
- สูตรคราฟต์/ที่นอนเกิดใหม่/การดรอปของ/หินป้องกันการโจมตี เป็นกติกาของ **นิยาย** เท่านั้น จนกว่าจะตรวจเกมจริงในโหมดที่ใช้อ้างอิง

**หมายเหตุด้านบรรณาธิการ:** ตัวเนื้อเรื่องที่เป็นต้นฉบับผ่านการยอมรับจากผู้เขียนในแชตแล้ว แต่สรุปสองบทในช่อง `author_memory` เป็นงาน **derived recap** จากต้นฉบับนั้น ยังไม่ได้รับการรีวิวแยกทีละถ้อยคำโดยเจ้าของเรื่อง จึงแสดง `RECAP_STATUS: DERIVED_FROM_ACCEPTED_SOURCE / NOT_SEPARATELY_REVIEWED` ไว้ชัดเจน

## แนวทางสำหรับเอเจนต์ถัดไป

ก่อนเขียนตอนถัดไป อ่าน `stories/last-island-active/HANDOFF.md` และสั่ง `memory` เพื่อทบทวนบทที่ 1–2 พร้อมเปิดต้นฉบับเต็มเมื่อต้องการพิสูจน์รายละเอียดที่สำคัญ **ห้ามเอา Candidate State ที่ไม่มีจำนวนแน่นอนมาใส่ตัวเลขจริง** และห้ามเอา `memory` ไปอ้างเป็นหลักฐาน GitHub Review
