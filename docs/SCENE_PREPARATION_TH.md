# เตรียมฉากด้วยแหล่งข้อมูลที่ระบุชัด

คำสั่งนี้ช่วยผู้เขียนเตรียม **ก่อนเริ่มฉากหนึ่งฉาก** โดยรวม context/style เดิม, ตัวละคร/สถานที่, หลักฐานความรู้ POV, รายการ inventory ก่อนหน้า, thread ที่มีจุดตั้งต้นก่อนหน้า และ house card เมื่อระบุบ้าน ไม่เขียนนิยาย ไม่เรียกโมเดล และไม่เปลี่ยน canon/ledger ผลทั้งหมดเป็น `PROPOSED` และ `human_editorial_approval: UNVERIFIED`

## ใช้งาน

ใช้ Python 3.11+, dependencies ที่ pin ใน `requirements.txt` และ Git ที่รองรับ `--no-lazy-fetch` สำหรับโหมด committed ไม่มีการติดตั้งหรือดึง object อัตโนมัติ

```bash
python scripts/storyctl.py --story last-island-active check --source-mode committed
python scripts/storyctl.py --story last-island-active prepare-scene SC-018 --house LOC-009 --source-mode committed --max-chars 100000 --out .local/SC-018-preparation.json
```

ไฟล์ผลลัพธ์อยู่ได้เฉพาะ `.local/` ที่ถูก ignore ภายใน workspace ของคำสั่งนี้ มี unpublished context จึงไม่ควรแนบใน public PR โดยไม่มีคำอนุญาต หากไม่ส่ง `--out` จะพิมพ์ JSON ทาง stdout คำสั่งไม่แก้ source หรือ registry

เรื่องทั่วไปใช้ได้โดยไม่ต้องมีบ้านหรือระบบเกม:

```bash
python scripts/storyctl.py new my-story --title "ชื่อเรื่อง"
python scripts/storyctl.py --story my-story check
# เติม metadata ฉากตามคู่มือ ENGINE_E7.md ก่อนใช้:
python scripts/storyctl.py --story my-story prepare-scene SC-001 --out .local/my-story-scene.json
```

scaffold ว่างผ่าน check แต่ยังไม่มี SC-001 คำสั่งเตรียมฉากจึงต้องปฏิเสธจนมีฉากจริง ไม่สร้างเรื่องหรือฉากให้เอง

## Source mode และ Windows

- `working-tree` เป็นค่าเดิม/ค่าเริ่มต้น: อ่าน bytes จริง ไม่แก้ CRLF/LF ไม่ถือว่า hash ต่างกันเป็นสิ่งเดียวกัน แหล่งที่ pin hash แล้วเปลี่ยนต้อง fail
- `committed` เป็นทางเลือกที่ต้องระบุ: อ่าน exact Git blobs จาก HEAD ที่ตรึงไว้ครั้งเดียว ตรวจ hash ที่ประกาศตามเดิม ไม่มี fallback ไปไฟล์ทำงานหรือ network ทั้ง hash ของ bytes ที่ใช้และ raw working-tree hash ถูกบันทึกใน `source_evidence`
- `raw_status: DIFFERENT` หมายถึงไฟล์ทำงานต่างจาก blob ที่ใช้จริง อาจเกิดจาก CRLF หรือจากการแก้ข้อความ คำสั่งไม่จำแนกว่าเป็นการเปลี่ยนที่ปลอดภัย ไม่ normalize และไม่อ้างว่าตรวจ draft ปัจจุบันผ่านแล้ว
- `MISSING`/`UNREADABLE` ไม่ใช่หลักฐานว่า raw source ตรงกัน โหมด committed อาจอ่าน blob ที่มีอยู่ได้ แต่ต้องแสดงสถานะ raw ตามจริง ส่วนโหมด raw ต้องอ่านได้จริง
- `commit: UNKNOWN` ในโหมด raw หมายถึงไม่มี Git anchor ที่อ่านได้ ยังมี raw hash แต่ไม่ใช่ committed evidence โหมด committed ต้องมี local Git ที่ใช้งานได้ มิฉะนั้น fail
- Registry/config/approval declarations ยังคงมาจาก working tree โดยแสดง `metadata_basis: WORKING_TREE_REGISTRIES` และ `metadata_evidence` แยกต่างหาก ไม่อ้างว่า bundle ทั้งหมดมาจาก commit เดียวกัน ตรวจ metadata และ raw source ซ้ำก่อนส่งผล หาก HEAD/source/metadata เปลี่ยนระหว่างทำงานให้หยุด

`storyctl check`, `memory`, `pack` และ `story_engine.py check/pack` รองรับ `--source-mode committed` เช่นกัน Default เดิมยังคง fail เมื่อ pinned raw bytes ไม่ตรง จึงไม่ได้ปกปิด raw source changes หรือทำให้ full Windows raw suite ผ่านโดยเปลี่ยน assertions/Git settings

## อ่าน bundle อย่างถูกต้อง

1. ตรวจ story/scene/POV และ `scene_cursor` ซึ่งเป็น `BEFORE` เท่านั้นในรุ่นนี้
2. `author_planning_context` มีเป้าหมาย/beat ของฉากที่ได้รับมอบหมายและ user directives เพื่อช่วยเขียน ไม่ใช่เหตุการณ์ที่เกิดแล้วหรือความรู้ตัวละคร โหมดนี้ไม่ดึงฉากข้างเคียง ไม่แสดงคำถามระดับ episode ที่ไม่มีเวลาระบุ และไม่แสดง target inventory operations เป็นของตั้งต้น `pack` เดิมยังคงขอบเขตเดิมเพื่อความเข้ากันได้
3. `pov_knowledge` ใช้เฉพาะรายการที่มี scene ก่อนหน้าและ local APPROVED/CANON พร้อม source ที่อ่านได้ Untimed traits และ unapproved knowledge ถูกกันไว้ Local label/hash ไม่พิสูจน์ human approval บน GitHub
4. Inventory เป็นรายการเหตุการณ์ก่อนหน้าที่มี local approval เท่านั้น ไม่คำนวณ balance/ศูนย์/จำนวนที่ไม่มีหลักฐาน `current_balance` จึงคง `UNKNOWN` Thread OPEN ปัจจุบันไม่พิสูจน์สถานะในอดีต
5. บ้านต้องส่ง `--house HOUSE-ID` ชัดเจน ไม่เดา owner/group หรือหยิบแบบใกล้เคียง ใช้ exact BEFORE view ของฉาก ถ้าไม่มี view ให้ UNKNOWN แบบที่เสนอหรือส่วนต่อเติมอนาคตไม่กลายเป็น built state ความรู้ POV ของบ้านยังแยกจาก facts จริงของบ้าน
6. Source reader ร่วมถูกใช้กับ author memory, house cards, approved source/recaps และ state/world evidence ตรวจ pin เดิม ไม่ข้าม validation เพื่อให้ pack ออก

ถ้าต้องการ world preview ต้องส่ง **ครบสี่ค่า**:

```bash
python scripts/storyctl.py --story my-story prepare-scene SC-002 --world-clock CLOCK-MAIN --world-tick 2 --world-suborder 0 --world-boundary BEFORE --out .local/SC-002-preparation.json
```

ค่าดังกล่าวเป็นตัวอย่าง syntax ต้องใช้ clock/tick ที่มีหลักฐานของเรื่องนั้นเอง ไม่มีการแปลง scene order เป็น world time, ไม่มีการเดา flashback mapping `world_preview` เป็นข้อมูลสำหรับผู้เขียนและยัง PROPOSED/UNVERIFIED ไม่ใช่สิ่งที่ POV รู้ หากไม่ได้เปิด S1/S2 หรือหลักฐานไม่ครบให้ UNKNOWN ไม่ใช่ PASS

`PREPARED_WITH_EXPLICIT_UNKNOWNS` หมายถึงประกอบเอกสารได้ ไม่ได้หมายถึงข้อเท็จจริงทุกช่องได้รับการยืนยัน Missing/stale pinned source, registry/schema ผิด หรือข้อมูลเปลี่ยนระหว่างอ่านต้องปฏิเสธการประกอบ ไม่มีการซ่อมข้อมูล/อนุมัติให้เอง

## ขอบเขตที่ยังเหลือ

- ไม่มี per-scene delta extraction หรือ automatic construction/damage/repair events
- ไม่มี semantic reviewer, writer execution, revision loop หรือ owner-signoff automation
- ไม่มีการ apply ledger/canon หรือรับรองบัญชีผู้อนุมัติ
- World chronology ต้องระบุเอง; ไม่ได้สร้าง mapping จาก narration order
- การตรวจ source hash/โครงสร้างไม่ใช่การเข้าใจความหมาย prose และไม่ยืนยัน gameplay/โครงสร้างอาคารจริง

ดู roadmap ใน [ENGINE_NEXT_BATCHES_TH.md](ENGINE_NEXT_BATCHES_TH.md) และ [postmerge contract](POSTMERGE_PROPOSALS.md)
