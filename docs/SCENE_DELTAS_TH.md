# เสนอความเปลี่ยนแปลงจากฉาก โดยยังไม่แก้ประวัติเรื่อง

`propose-deltas` ตรวจ candidate ที่ผู้ใช้หรือ agent อ่านแล้วเสนอมา ไม่ได้สกัดความหมายของนิยายเอง ใช้กับฉากเดียวและ source ที่ระบุชัดเจน ผลทั้งหมดเป็น `PROPOSED`, `human_editorial_approval: UNVERIFIED` และไม่มีสิทธิ์เขียน canon/ledger/world history

## ขั้นตอนใช้งาน

1. เลือก story และ scene ให้ตรงกับงาน อ่าน draft จริงและทำรายการข้อความที่เสนอเป็นความเปลี่ยนแปลง แยกสิ่งที่ไม่รู้ไว้เป็น `UNKNOWN`
2. สร้าง claims JSON ใน `.local/` ตาม `schemas/v1/scene_delta_claims.schema.json` โดยใช้ `draft_path` ของฉากและ SHA-256 ของ **bytes ที่เลือกจริง** ไม่ normalize LF/CRLF ระบุ quote กับเลขบรรทัดเริ่ม/จบตรง source
3. รันคำสั่งนี้โดยใช้ชื่อ output ใหม่เสมอ:

```bash
python scripts/storyctl.py --story my-story propose-deltas SC-001 --claims .local/claims-v1.json --out .local/deltas/SC-001-v1.json
# เมื่อแก้ draft/claims: เก็บไฟล์ก่อนหน้า แล้วสร้าง revision ใหม่
python scripts/storyctl.py --story my-story propose-deltas SC-001 --claims .local/claims-v2.json --previous .local/deltas/SC-001-v1.json --out .local/deltas/SC-001-v2.json
```

output ต้องอยู่ใน `.local/` ของ workspace; คำสั่งปฏิเสธการเขียนทับไฟล์ที่มีอยู่ stdout ใช้ดูผลได้แต่ต้องระวัง unpublished context ใน log ไม่มีการเผยแพร่ artifact อัตโนมัติ

`--source-mode committed` เป็นทางเลือกสำหรับ exact local HEAD blob โดยรายงาน raw source ที่ต่าง/หาย/อ่านไม่ได้แยกจาก bytes ที่เลือก ไม่ใช้เพื่ออ้างว่า working draft ล่าสุดผ่านแล้ว ไม่ fetch Git objects หรือเปลี่ยน Git settings

ตัวอย่าง claims นี้ใช้กับ synthetic source บรรทัด `SYNTHETIC: floor frame remains unfinished.` เท่านั้น ค่า hash ต้องคำนวณจากไฟล์จริง:

```json
{
  "schema_version": 1,
  "scene_id": "SC-001",
  "draft_path": "drafts/EP-001/SC-001.md",
  "source_sha256": "<64 lowercase hex characters from the selected exact bytes>",
  "observations": [{
    "id": "OBS-001", "category": "CONSTRUCTION",
    "claim": "Frame is unfinished; completion time is UNKNOWN.",
    "locator": {"start_line": 1, "end_line": 1,
      "quote": "SYNTHETIC: floor frame remains unfinished."},
    "subject": {"kind": "LOCATION", "id": "LOC-001"},
    "candidate": {"target_kind": "LOCATION", "target_id": "LOC-001",
      "component_id": "PART-FRAME", "aspect": "unfinished frame"}
  }]
}
```

นี่เป็นตัวอย่างรูปแบบ ไม่ใช่ claims ที่รันได้โดยไม่ใส่ hash/source/catalog ให้ตรง และไม่ใช่เหตุการณ์ของ Last Island หรือเรื่องจริงใด

## อ่านผลอย่างไม่เกินหลักฐาน

- `EXACT_QUOTE_AT_LINES` ยืนยันเพียง quote อยู่ที่บรรทัดนั้นใน source hash ที่เลือก ไม่ได้ยืนยันว่า quote รองรับ claim การตีความยังเป็น `semantic_assessment: NOT_EVALUATED` ต้องให้ reviewer อ่านบริบทจริง รวมถึงการปฏิเสธ/สมมติ/แผน/ผู้เล่าที่ไม่น่าเชื่อถือ
- MOVE/TRANSFER เป็น candidate ที่ตรวจรูปแบบและ ID กับ catalog ของเรื่องนั้น ไม่ได้เรียก S2 reducer และไม่พิสูจน์ precondition, จำนวนคงเหลือ หรือเหตุการณ์เกิดขึ้นจริง
- CONSTRUCTION/DAMAGE/REPAIR เป็นข้อสังเกตที่เสนอเกี่ยวกับส่วนประกอบ ไม่ใช่ operation ใหม่ใน engine และไม่เปลี่ยน built/usable/damaged/repaired state อัตโนมัติ claim ต้องแยกการสร้างเสร็จจากใช้งานได้ และแผนก่อสร้างจากสภาพที่สร้างแล้ว
- ไม่มี world time จากลำดับการเล่า หากรู้จริง candidate ใส่ `world_time` ที่มี `status: KNOWN`, `clock_id`, `tick`, `suborder`, `boundary` ครบชุดได้ แต่ยังเป็นคำประกาศที่ต้องตรวจหลักฐาน ไม่ได้พิสูจน์ mapping ด้วย schema
- ไม่รู้จำนวนให้ใช้ `UNKNOWN` ไม่ใช่ 0 ไม่รู้ผู้ถือ/ตำแหน่งให้คง UNKNOWN ห้ามสร้าง baseline CREATE ย้อนหลัง
- Source ที่ใช้ร่วมหลายฉาก/ทั้งบทถูกปฏิเสธในรุ่นนี้ เพราะไม่มี scene-span ที่ยืนยันแล้ว ป้องกันหยิบเหตุการณ์อนาคตจากไฟล์บทเดียวกัน ห้ามแยก/แก้ prose จริงเพื่อทำให้คำสั่งผ่าน ให้รายงานข้อจำกัด
- `proposal_identity` คงเดิมต่อ story/scene/path; `revision_id` และ chain hashes ช่วยตรวจการเปลี่ยนข้อมูลและความต่อเนื่องในไฟล์ที่ให้มา ไม่ใช่ลายเซ็นหรือ authenticated approval ต้องเก็บไฟล์ revision เก่าไว้เอง จำกัดประวัติ 64 รายการ ไม่มีบริการจัดเก็บถาวรหรือการตรวจ source เก่าจาก remote

## ส่งต่อ reviewer และ owner

ส่ง story/scene, exact draft hash, claims/proposal revision และ source context เดียวกันให้ reviewer แยก contradiction ที่มีหลักฐานออกจาก UNKNOWN ข้อความที่อ้างถูกตำแหน่งแต่ตีความผิดยังต้องถูกแก้ เมื่อ draft เปลี่ยนต้องสร้าง proposal/review ใหม่ ห้ามใช้ผลของ hash เก่าแทนฉบับใหม่

Owner signoff สำหรับเนื้อเรื่องยังต้องมีจริงและผูกกับ revision ที่ตรวจ การ merge software PR, local APPROVED หรือ hash ตรงไม่ใช่การอนุมัติเนื้อเรื่อง คำสั่งนี้ไม่มี apply/approve/merge ไม่มี AI API และไม่มี narrative generation

ดู [scene preparation](SCENE_PREPARATION_TH.md), [agent runbook](AGENT_RUNBOOK.md) และ [roadmap](ENGINE_NEXT_BATCHES_TH.md) สำหรับ reviewer/supervised workflow/การทดลองสามฉากที่ต้องตรวจแยกจากตัว assembler
