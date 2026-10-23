# แผนพัฒนาโมดูลสิ่งปลูกสร้างเข้า engine — PROPOSED

สถานะ: **DEVELOPMENT PLAN / PROPOSED — ยังไม่ใช่ runtime หรือ canon**

**เป้าหมายหลักคือช่วยเขียนนิยายให้ต่อเนื่อง ไม่ใช่สร้างเกมหรือ CAD:** เริ่มที่ [คู่มือเอเจนต์นักเขียน](../stories/last-island-active/design/proposals/house-atlas-v1/WRITER_AGENT_RUNBOOK_TH.md) เลือกบ้าน/กลุ่มที่มีหลักฐาน เลือกรุ่นและสภาพที่สร้าง ณ ฉากนั้น ตรวจทางเดิน/บันได และจำกัดรายละเอียดตามความรู้ POV แผนทางเทคนิคด้านล่างเป็นส่วนรองที่จะทยอยทำเมื่อจำเป็นต่อการดึงข้อมูลและตรวจความต่อเนื่อง

บันทึกตามคำขอผู้ใช้ 2026-10-23 ให้พัฒนาระบบสิ่งปลูกสร้างต่อจากฐาน engine โดยเริ่มจากแบบสังเคราะห์ ไม่เปลี่ยนเนื้อเรื่อง ข้อมูล approved หรือ ledger การเปิด Draft PR แผนนี้ไม่ใช่การอนุมัติให้เขียน runtime ทุกเฟสหรือ merge อัตโนมัติ

## ขอบเขตและฐานที่ใช้จริง

- ฐาน main ที่ตรวจ: `49bd4ac796a143d31dd40c02900bdefbeb8d7a44` มี S1 declarations, S2 proposed replay และ author-accepted memory แยกจาก approved ledger
- S3 diagnostics อยู่ใน Draft PR #19 แยกต่างหาก ไม่ถูกนำเข้ามาใน branch แผนนี้ และยังต้องตรวจรับก่อนใช้เป็น dependency ที่ merge แล้ว
- แบบบ้าน 8 กลุ่มและตัวอย่างบ้านช่าง 2×2 ใน [แพ็กเกจข้อเสนอ](../stories/last-island-active/design/proposals/house-atlas-v1/DESIGN_BRIEF_TH.md) เป็น **PROPOSED** ไม่มีเจ้าของ ผู้เล่น กลุ่ม ฉาก หรือเหตุการณ์จริงที่ถูกผูกไว้
- งานรอบนี้ส่งเอกสาร สัญญาข้อมูลตัวอย่าง และภาพต้นฉบับพร้อม QA ของแบบสาธิตเท่านั้น ไม่เพิ่ม geometry runtime, CLI สิ่งปลูกสร้าง หรือการนำผังเข้า context/canon
- บ้านทั้ง 8 กลุ่มเป็น **unplaced schematic programs** ไม่อ้างว่าผ่าน geometry; เฉพาะ pilot บ้านช่างที่วางพิกัดสาธิตเท่านั้นที่ผ่าน bounded static QA ตาม convention ของภาพ
- ไม่ทำแบบจำลองต้นทุน/ทรัพยากร ค่า HP ความทนต่อการบุก หรือสมรรถนะโครงสร้าง การอนุมัติแผนนี้ไม่อนุญาตให้ผูกตัวละคร/สถานที่จริงหรือเปลี่ยน canon/ledger โดยอัตโนมัติ

## สถาปัตยกรรมที่เสนอ

แยกโมดูล `building` แบบ optional ของ engine ออกจากกฎรายเรื่อง: engine รู้จัก template, instance, version, topology, พิกัดที่ประกาศชัด และที่มาของข้อมูล ส่วน Last Island เปิดกฎ square/triangle และเสาหลักหนึ่งต้นต่อ **ทั้งหลัง** ใน config ของเรื่องเอง เรื่องอื่นไม่ถูกบังคับให้มีเสา รูปสามเหลี่ยม หรือกฎรับน้ำหนักแบบเดียวกัน

| ชั้นข้อมูล | หน้าที่และขอบเขต |
| --- | --- |
| Template | แบบนำกลับใช้ได้ มีช่องกำหนดรูปทรง/หน้าที่ที่ยังไม่ผูกเจ้าของหรือสถานที่จริง การแก้ template ไม่เปลี่ยนบ้านที่สร้างไว้แล้ว |
| House instance | identity ของบ้านหนึ่งหลังและการอ้าง version ปัจจุบัน อาจยังไม่ทราบ owner/occupant/location; UNKNOWN ไม่ใช่บ้านไร้เจ้าของหรือห้องว่าง |
| House version | snapshot ที่ไม่เขียนทับประวัติ มี parent version, ชุด tile/room/door/level/roof/connector และหลักฐานของ revision |
| Topology | ขอบร่วมของโมดูลเป็นคนละเรื่องกับประตู การที่ footprint ต่อกันไม่ได้ยืนยันว่าทุกห้องเดินถึงกัน |
| Geometry convention | ประกาศชนิดสามเหลี่ยม ขนาด หน่วย ระบบพิกัด และ tolerance/เลข exact ก่อนใช้ validator หากยังไม่ทราบ ให้เก็บแบบ unplaced และไม่รายงานว่า geometry ผ่าน |
| Vertical program | แยก floor index, symbolic elevation, local room height และมิติจริง หน่วย H/U ในภาพตัวอย่างไม่มี conversion เป็นเมตร |
| Rooms/voids/roof | ห้องมีขอบเขต XY และช่วงแนวดิ่ง; ช่องโล่งเปิดถึงด้านล่างไม่ใช่พื้น; หลังคาคลุมไม่เท่ากับระเบียงที่คนเดินใช้งานได้ |
| Navigation | ประตู/ช่องผ่านในชั้นเดียวและบันได/connector ข้ามระดับ พร้อม landing/opening ทั้งสองปลาย การผ่านเชิงกราฟไม่ยืนยัน pitch, clearance, support หรือกลไกเดินจริง |
| Pillar | identity ระดับอาคารหนึ่งรายการสำหรับ Last Island ไม่สร้างเสาใหม่ตามจำนวนชั้น ความสูง รัศมีอิทธิพล การย้าย และนิยามกลางบ้านยังต้องตัดสิน |
| Ownership/occupancy | แยกผู้ถือกรรมสิทธิ์ ผู้ใช้ห้อง ผู้พัก และสิทธิ์เข้าพื้นที่ การเปลี่ยนผู้พักไม่ใช่การเปลี่ยนเจ้าของโดยปริยาย |
| Provenance/knowledge | source path/hash, สถานะ proposal/approval, world time และ narrative/knowledge time แยกกัน แปลนจริงไม่ได้ทำให้ตัวละครหรือผู้อ่านรู้ทุกห้อง |

## Roadmap ที่เสนอ — ยังไม่ใช่คำสั่งให้ implement ทุกเฟส

| เฟส | Dependency | สิ่งส่งมอบที่เสนอ | เกณฑ์ทดสอบ/รับงาน |
| --- | --- | --- | --- |
| B0 ข้อตกลงที่ยังขาด | ผู้แต่งเลือก convention | decision record เรื่องรูปสามเหลี่ยม/หน่วย/ความสูง/เสา/พื้นและ support; แยก UNKNOWN กับข้อเสนอ | ไม่อ้างค่า default เป็นกฎเกม; รูปที่ยังไม่เลือกไม่ผ่าน geometry gate |
| B1 โมเดล optional | B0 และ S1 conventions | versioned schema สำหรับ template/instance/version/level/room/tile/door/void/roof/pillar/connector; per-story extension config | missing/disabled config รักษา v1; wrong version/ref/story ปฏิเสธ; fixture สองเรื่องไม่รั่วกัน |
| B2 Topology และ geometry | B1, convention ชัด | loader/validator read-only, edge IDs, พิกัดหรือสถานะ unplaced; รายงานขอบร่วม/overlap | polygon ไม่ซ้อน interior; ขอบที่อ้างตรงกัน; corner contact ไม่แทนขอบร่วม; footprint connected แยกจาก door-reachable |
| B3 ระดับและทางขึ้นลง | B2 | floor/elevation/local-height model, vertical connectors, ช่องบันไดและ landing, void/roof semantics, plan+section views | endpoints/landings อยู่ระดับถูกต้อง; opening ทั้งสองปลาย; พื้นไม่ปิด void; ห้องใช้งานเข้าถึงได้; clearance ที่ไม่มีมิติจริงเป็น UNKNOWN ไม่ใช่ PASS |
| B4 ประวัติและ state preview | B1–B3, S2, S3 เมื่อ merge แล้ว | immutable versions และ deltas เช่น ADD/RETIRE_MODULE, ADD/REMOVE_DOOR, CHANGE_ROOM_USE, ADD/ALTER_CONNECTOR, EXPAND/REPAIR, REASSIGN_OWNER/OCCUPANT; deterministic proposed preview | source/version hash และ preconditions ตรง; revision เก่าไม่ถูกเขียนทับ; replay ตาม world time ไม่ใช่ลำดับเล่า; event ซ้ำ idempotent; fail ไม่มี state บางส่วน; local APPROVED ไม่ใช่ human approval |
| B5 ความรู้และมุมมอง | B3–B4 และข้อกำหนด S5 ในอนาคต | query/visibility contract แยก actual geometry, explored/remembered layout และข้อมูลผู้อ่าน; projection แบบเลือกขอบเขต | แปลนลับ/ชั้นบนที่ยังไม่รู้ไม่เข้าบทตัวละคร; เสียง/แนวสายตาเป็น UNKNOWN หากกฎ/มิติยังขาด; ไม่มี inference จากการมีไฟล์ผัง |
| B6 Synthetic acceptance | B1–B5 | บ้านช่าง 2×2 หลายชั้น/หลาย version, valid controls และ planted violations, audit report | จับ overlap, unmatched edge, unreachable room, stairs ขาด opening, floor-vs-void, เสาซ้ำ, ผูกคนข้ามเรื่อง, stale version/source, future/unapproved delta; UNKNOWN ไม่ผ่าน; ไม่มี fake reviewer score |
| B7 เปิดใช้รายเรื่อง | ทุกเฟสที่เกี่ยวข้องผ่านและผู้ใช้อนุมัติ | คู่มือไทย, reversible import/proposal, migration receipt และการผูกบ้านกับตัวละคร/สถานที่ที่เจ้าของเรื่องเลือก | bytes และ IDs เดิมไม่หาย; ไม่ overwrite ประวัติ; ต้อง review ก่อนเปลี่ยน canon/ledger; engine เดิมยังผ่าน full regression และ 54-file manifest |

การแบ่งเฟสนี้ตั้งใจให้แต่ละ PR เล็กและตรวจรับได้ อาจเริ่ม B1 เฉพาะ schema/topology โดยยังไม่รับรอง geometry ที่ B0 ยังไม่เลือก ห้ามทำ success stub ให้ phase ที่ยังไม่มี implementation

## กติกา version/delta และ trust boundary

1. เก็บ `house_id` คงที่และ `version_id` ใหม่ทุก revision; tile/room/connector ID ที่ยังอยู่ต้องไม่ถูกนำไปแทนคนละสิ่ง การรื้อ/ยกเลิกต้องมี retirement ชัด ไม่ลบอดีต
2. Deltas อ้าง expected parent/version/source hashes, world clock และ boundary/suborder เมื่อไม่รู้ลำดับต้อง UNKNOWN/INVALID ไม่เรียงตามชื่อไฟล์หรือฉาก
3. การต่อเติม ซ่อม ย้ายบันได เปลี่ยนหน้าที่ห้อง หรือโอนสิทธิ์เป็นข้อเสนอจนผ่าน human gate; ไม่อนุมานจากภาพผังหรือสรุป AI ว่าเกิดจริงแล้ว
4. S1 เก็บ declarations/references; S2 เป็นแนวทาง replay ที่ไม่อนุมาน facts; S3 รายงาน known contradiction แยก UNKNOWN ใช้ร่วมกันผ่าน adapter ที่ประกาศ scope ไม่ให้ geometry กลายเป็น approved state โดยอัตโนมัติ
5. Actual geometry, ownership และ POV knowledge ต้องมี evidence/time boundary ของตนเอง local status/hash/CI ไม่ยืนยันตัวผู้อนุมัติ และระบบไม่เขียน canon หรือ ledger เอง

## Pilot บ้านช่าง 2×2 หลายระดับ

### ลำดับก่อสร้างและการรับงานอนาคต

แยก target blueprint ออกจาก as-built snapshot ตาม world time/scene ส่วนย่อยมี PROPOSED/NOT_BUILT/IN_PROGRESS/COMPLETED และ usability แยกกัน ห้อง/บันไดที่สร้างเสร็จอาจยังไม่เปิดใช้ แบบวาดครบไม่ทำให้บ้านในอดีตสร้างครบ ความเสียหาย/ซ่อมมีได้เมื่อบันทึกชัด ไม่อนุมานความสมบูรณ์หรือความเสียหาย ระยะเริ่ม/เสร็จ วัสดุ ขนาด ค่าใช้จ่าย และกลไกที่ไม่รู้คง UNKNOWN; ชื่อ stage ไม่ใช่เลเวลเกม

- B1: บัตรอ้างอิงเก็บ part status/usability, damage/repair, world time, narrative reveal และ POV แยกกัน; กลุ่ม/ฉากจริงที่ยังไม่ผูกคง UNKNOWN
- B4: event ระบุ part ID, เวลา/boundary, prerequisites และผลต่อห้อง/ทางเดิน/หลังคา; replay ใช้เฉพาะหลักฐานที่เข้าเกณฑ์ ไม่เรียงจากเลขบท ไม่รู้ลำดับหรือ prerequisite ต้อง UNKNOWN/INVALID โดยไม่แก้สถานะบางส่วน
- B4/B6: snapshot ก่อน/หลังเสร็จและก่อน/หลังเปิดใช้, event ซ้ำต้อง idempotent, stale parent/source และข้อมูลข้ามเรื่องถูกปฏิเสธ; ต่อเติมอนาคตห้ามรั่วเข้าฉากก่อนหน้า และย้อนอ่านบ้านก่อนต่อเติมได้เหมือนเดิม
- B6: ทดสอบ flashback, failed prerequisite, partial roof, completed-but-closed stair, UNKNOWN completion และ repair ที่ไร้หลักฐาน โดยไม่ใช้ผล structural tests แทน human approval

[construction_stages.json](../stories/last-island-active/design/proposals/house-atlas-v1/construction_stages.json) บันทึก event และสี่ snapshot สังเคราะห์ด้วยมือ ตั้งแต่โครง 2×2 จนถึงส่วนต่อชั้นบน ไม่ใช่ผล reducer หรือประวัติเรื่องจริง การตรวจแพ็กเกจตรวจ reference/ขอบเขตตัวอย่างเท่านั้น ไม่อ้างว่า engine มี construction replay แล้ว

ใช้ ID สังเคราะห์ `HOUSE-PROP-WORKSHOP-001` ไม่มี player/group/location canon binding รุ่น V01 เป็น low core, V02 เสนอพื้นที่ช่างสูงกับชั้นลอยวางแผนที่เงียบกว่า, V03 เสนอ annex แบบจับคู่และ gallery ด้านบน แต่ละรุ่นมี tile/door/stair/room IDs และ lineage ชัดเจน เสาหลักใช้ identity เดียวต่อทั้งบ้าน การเลือกคง XY ในภาพเป็นการเลือกแบบ ไม่ใช่กฎห้ามย้ายเสา

หากวางพิกัด จะทดสอบ non-overlap, matched edge, connected footprint และ reachable occupied rooms **ภายใต้ convention ของภาพเท่านั้น**; จุดบันไดและช่องเปิดต้องตรงกัน แต่ support/headroom/ความเป็นไปได้ในเกมยัง UNKNOWN หากเป็นแผน unplaced จะตรวจได้เฉพาะ references/graph และต้องไม่เรียกว่า geometry-valid ภาพผัง รูปตัด และ silhouette ต้องสะท้อนข้อมูลชุดเดียวกัน

## การตัดสินใจที่ยังเปิด

### ส่วนอ้างอิงชั้นป้องกันในเกมสมมุติ

เพิ่มแบบบันทึกเพื่อความต่อเนื่องของนิยาย: แยกบ้านชั้นใน ชั้นป้องกันแต่ละด้าน/ด้านบน และประตูต่อเนื่องเป็นราย ID พร้อมระดับ/วัสดุ สถานะก่อสร้าง/เปิดใช้/เสียหาย และ world time/scene bounds ดู [คู่มือ](../stories/last-island-active/design/proposals/house-atlas-v1/DEFENSIVE_ENVELOPE_WRITER_TH.md) และ [ข้อมูลตัวอย่าง](../stories/last-island-active/design/proposals/house-atlas-v1/defensive_envelope_reference.json) จำนวนชั้นอาจเพิ่มเมื่อมีหลักฐาน ไม่กำหนดตาราง progression หรือให้ความเสียหายชั้นนอกลบชั้นในโดยอัตโนมัติ

ผู้ใช้ชี้แจงว่าคู่เทียบวัสดุหมายถึง **ระดับความแข็งแกร่งเชิงเกม** ไม่ใช่ความหนาจริง จึงแยก material, geometric thickness, layer count และ symbolic strength tier; ค่าตัวเลข/HP ยัง UNKNOWN ไม่บวกความแข็งแกร่งข้ามชั้นและไม่สร้างสูตรต้านแรงระเบิด คู่เทียบประตูเหล็กกับประตูหินเก็บคำเดิมพร้อม pending clarification ว่าตัวเปรียบเทียบตั้งใจเป็นสิ่งใด การรอค่านี้ไม่ขัดขวางการใช้บัตรที่ระบุ UNKNOWN

ขอบเขต B1 คือช่องอ้างอิงทางเลือกในบัตรนักเขียน; B4/B6 ในอนาคตจึงตรวจ snapshot ตามเวลา การเปลี่ยนเฉพาะ part ที่มีหลักฐาน การเปิดประตูทีละจุด และการไม่รั่วชั้นต่อเติมอนาคต รอบนี้มีเพียงข้อมูล/คำแนะนำและ static consistency tests ไม่มี runtime ป้องกัน ความเสียหาย หรือเส้นทางเจาะ

| เรื่อง | สถานะ/สิ่งที่ต้องเลือกก่อน runtime |
| --- | --- |
| รูปสามเหลี่ยม/ขนาด | มุม ความยาวด้าน อัตราส่วน square/triangle และหน่วยจริง UNKNOWN; รูปสาธิตไม่ใช่กฎเกม |
| ความสูง | ความสูงห้อง/ครึ่งชั้น/ชั้นลอย จำนวนชั้นสูงสุด หน่วยจริงและข้อจำกัด headroom UNKNOWN |
| เสาหลัก | ยืนยันเพียงหนึ่งต้นกลางทั้งหลัง; metric centrality, การย้าย/รื้อ, ความสูง/รัศมีอิทธิพล/ผลต่อชั้นบน UNKNOWN |
| พื้นและ support | การรองรับส่วนยื่น ช่องโล่ง พื้นชั้นบน หลังคาที่เดินได้ น้ำหนัก และเงื่อนไขพัง UNKNOWN; graph validation ไม่ใช่วิศวกรรมโครงสร้าง |
| การเคลื่อนที่/สิทธิ์ | ชนิดบันได กฎการเดินจริง การปิดประตู/ล็อก และสิทธิ์เข้าออกต้องได้ข้อมูลเพิ่ม ไม่ใช้ furniture-jump หรือ bunker technique จาก Rust |
| ความรู้/เสียง/มองเห็น | ขอบเขตการสำรวจ เสียงข้ามผนัง/ชั้น และ occlusion ยังไม่ยืนยัน ต้องไม่บอกว่าตัวละครรู้ทั้งบ้านจากแปลน |

## หลักฐานและการตรวจรับของแพ็กเกจรอบนี้

งานวิจัยอ้าง catalogue/title/description และ secondary transcripts ตามระดับหลักฐานใน [source audit](../stories/last-island-active/design/proposals/house-atlas-v1/research/SOURCE_AUDIT_TH.md) ไม่ยืนยัน Rust เป็น Last Island และไม่คัดลอก assets หรือแปลนต้นฉบับ สถานะผลตรวจจริง รายชื่อไฟล์ exact commit และ CI จะบันทึกใน Draft PR แพ็กเกจนี้ ไม่เติมผลทดสอบที่ยังไม่ได้รันลงเป็น PASS
