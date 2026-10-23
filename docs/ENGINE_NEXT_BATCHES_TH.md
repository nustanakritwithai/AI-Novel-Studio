# งาน engine ต่อจากการรวม #27 และ #19

ทุกชุดใช้ synthetic fixtures สำหรับเหตุการณ์ใหม่ ไม่แก้ prose/canon จริง และเปิด Draft PR ให้ตรวจโดยไม่ merge อัตโนมัติ

| ลำดับ | งาน/ผลส่งมอบ | เกณฑ์ตรวจรับ | สถานะของชุดนี้ |
| --- | --- | --- | --- |
| 1a | แยก observed PR base SHA ออกจาก merge first parent ใน postmerge proposal | stale-base two-parent control ผ่าน; wrong repo/head/association/race ยังปฏิเสธ; สิทธิ์ read-only เดิม | MERGED #29; main CI 491 tests; runtime ใหม่ผ่าน live run 40023031352 และดาวน์โหลด artifact 12531955840 มาตรวจจริง ดู POSTMERGE_PROPOSALS.md |
| 1b | exact source reader ร่วม, explicit committed mode พร้อม raw differences | CRLF ไม่ถูก normalize; raw mismatch ยัง fail; ไม่มี fallback; อ่าน source ตาม story/commit ที่ระบุ | MERGED #31 เป็น b6542359; final integration CI 520 tests ผ่าน; full Windows raw aggregate ยังไม่ยืนยันผ่าน |
| 2 | prepare-scene ก่อนฉากหนึ่งฉาก รวม context/style/บ้าน/POV/inventory/thread และ optional world preview | ไม่เผยฉากข้างเคียง/อนาคต; cursor ไม่เดา; UNKNOWN แยก; private output; generic story ใช้ได้ | MERGED #31 ชุดเดียวกับ 1b; world/POV mapping ที่ไม่มีหลักฐานยัง UNKNOWN และ withhold temporal context |
| 3 | เสนอ candidate delta ต่อฉากพร้อมข้อความ/ตำแหน่ง รวม construction/damage/repair observations | source hash/locator ผูกแต่ละข้อ; proposed เท่านั้น; time/history/idempotency; ไม่มี event ที่เดาขึ้น | MERGED #32 เป็น ac611008; final integration CI 547 tests ผ่าน รวม guard episode-manuscript alias; ยังไม่ทำ automatic semantic extraction |
| 4 | reviewer อ่าน prose เทียบ source-bound context | แยก grounded contradiction/UNKNOWN/ข้อเสนอ; blind seeded faults และ clean control; รายงาน misses ตามจริง | Runtime MERGED #33 เป็น 5ddf03b3; integration CI 565 tests ผ่าน; native experiment พบ critical 5/5, miss 0, clean 0, หลัง revision 0 findings ดู raw/ข้อจำกัดใน evaluation/scene_workflow_v1 ไม่ใช่ general quality score |
| 5 | supervised Planner → Writer → Reviewer → revision → owner checkpoint | scope/draft hashes/real handoff; ไม่ข้าม owner; ไม่ต้องมี paid API/n8n/LINE | MERGED #33 + native handoffs จริงใน acceptance batch; หยุด owner BLOCKED/UNVERIFIED; standalone delta เป็นข้อเสนอแยก ไม่ใช่ผ่าน gate |
| 6 | synthetic workflow 3 ฉาก มี flashback และบ้านที่ยังสร้างไม่เสร็จ รวม generic new-story compatibility | ทำซ้ำได้; no future leakage; no auto canon; รายงาน model-dependent evaluation แยกจาก tests | PR #34 เก็บ runner/packet/key/raw findings + integrity tests; final exact-head CI อ้างอิง PR; human signoff BLOCKED/NOT_RUN ส่วน software postmerge ผ่าน live แยกตามข้อ 1a |

ข้อมูลและรูปแบบบ้านที่เสนอไม่ได้กลายเป็นสิ่งปลูกสร้างที่สร้างแล้วจากการ merge software/reference PR, และ merge metadata ไม่ใช่ human editorial approval Privacy/rulesets/credentials/paid services ไม่อยู่ในขอบเขตนี้
