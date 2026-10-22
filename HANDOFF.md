# HANDOFF — START HERE

คุณคือ AI Writer/Continuity Editor ที่รับงานต่อของ LAST ISLAND

**ลำดับอ่าน:** `AGENTS.md` → `STATE.md` → `PROJECT.md` → `python scripts/novelctl.py status` → `python scripts/novelctl.py brief SC-001`.

## Current focus

เขียน **EP-001 / SC-001** ซึ่งเริ่มจากพระเอกเล่นเกมส่วนตัวในห้อง ก่อนเข้าสู่เซิร์ฟเวอร์ธรรมดา ไม่มีเวทีชิงแชมป์โลกในตอนแรก

## Next task

1. สร้าง branch `draft/EP-001-SC-001`
2. สร้าง `drafts/EP-001/SC-001.md` จาก scene card และ context pack
3. เขียนรายละเอียดให้เห็นภาพ แต่บันทึกชื่อ อาชีพ ปีที่เกิดเหตุ สีผนังห้อง/รุ่นเครื่องเป็น `PROPOSED` หากมีผลต่อเรื่องระยะยาว
4. เปิด PR พร้อมตาราง state delta และรายการ source verification
5. Reviewer ต้องตรวจความสอดคล้องก่อน APPROVED

## QA commands

```bash
python scripts/novelctl.py check
python -m unittest discover -s tests -v
```

## Never invent retroactively

ใช้ `UNKNOWN` เมื่อไม่ทราบข้อมูล, แยก GAMEPLAY_EVIDENCE ออกจาก STORY_CANON, และห้ามย้ายเหตุการณ์การแข่งขันระดับโลกกลับมาใน opening
