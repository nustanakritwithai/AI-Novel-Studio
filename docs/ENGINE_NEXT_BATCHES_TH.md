# งาน engine ต่อจากการรวม #27 และ #19

ทุกชุดใช้ synthetic fixtures สำหรับเหตุการณ์ใหม่ ไม่แก้ prose/canon จริง และเปิด Draft PR ให้ตรวจโดยไม่ merge อัตโนมัติ

| ลำดับ | งาน/ผลส่งมอบ | เกณฑ์ตรวจรับ | สถานะของชุดนี้ |
| --- | --- | --- | --- |
| 1a | แยก observed PR base SHA ออกจาก merge first parent ใน postmerge proposal | stale-base two-parent control ผ่าน; wrong repo/head/association/race ยังปฏิเสธ; สิทธิ์ read-only เดิม | Draft #29; หลักฐาน test/CI ของ head ล่าสุดอยู่ใน PR; runtime ใหม่ live NOT_RUN |
| 1b | exact source reader ร่วม, explicit committed mode พร้อม raw differences | CRLF ไม่ถูก normalize; raw mismatch ยัง fail; ไม่มี fallback; อ่าน source ตาม story/commit ที่ระบุ | Draft #31 head eb439b73; CI 516 tests ผ่าน; Windows raw aggregate ยังมีข้อจำกัด |
| 2 | prepare-scene ก่อนฉากหนึ่งฉาก รวม context/style/บ้าน/POV/inventory/thread และ optional world preview | ไม่เผยฉากข้างเคียง/อนาคต; cursor ไม่เดา; UNKNOWN แยก; private output; generic story ใช้ได้ | Draft #31 ชุดเดียวกับ 1b; ยังไม่ merge |
| 3 | เสนอ candidate delta ต่อฉากพร้อมข้อความ/ตำแหน่ง รวม construction/damage/repair observations | source hash/locator ผูกแต่ละข้อ; proposed เท่านั้น; time/history/idempotency; ไม่มี event ที่เดาขึ้น | ชุดนี้เพิ่ม propose-deltas/schema/tests; ดูผล exact-head CI ใน Draft PR และคู่มือ SCENE_DELTAS_TH.md; ยังไม่ทำ automatic semantic extraction |
| 4 | reviewer อ่าน prose เทียบ source-bound context | แยก grounded contradiction/UNKNOWN/ข้อเสนอ; blind seeded faults และ clean control; รายงาน misses ตามจริง | ยังไม่ส่งมอบ; deterministic checks ไม่ใช่ semantic reviewer |
| 5 | supervised Planner → Writer → Reviewer → revision → owner approval → proposed continuity | scope/draft hashes/real handoff; ไม่ข้าม owner; ไม่ต้องมี paid API/n8n/LINE | ยังไม่ส่งมอบ; prompts/scaffold อย่างเดียวไม่นับว่าจบ |
| 6 | synthetic workflow 3 ฉาก มี flashback และบ้านที่ยังสร้างไม่เสร็จ รวม generic new-story compatibility | ทำซ้ำได้; no future leakage; no auto canon; รายงาน model-dependent evaluation แยกจาก tests | ยังไม่ส่งมอบชุดใหม่ |

ข้อมูลและรูปแบบบ้านที่เสนอไม่ได้กลายเป็นสิ่งปลูกสร้างที่สร้างแล้วจากการ merge software/reference PR, และ merge metadata ไม่ใช่ human editorial approval Privacy/rulesets/credentials/paid services ไม่อยู่ในขอบเขตนี้
