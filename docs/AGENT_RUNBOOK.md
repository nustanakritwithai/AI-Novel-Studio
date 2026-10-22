# Agent runbook — ส่งต่องานภายใน story เดียว

ใช้ร่วมกับ [AGENTS.md](../AGENTS.md), [ENGINE_E5.md](../ENGINE_E5.md), [ENGINE_E3_E4.md](../ENGINE_E3_E4.md) และสัญญา schema/replay ใน [ENGINE_E2.md](../ENGINE_E2.md) Runbook นี้กำหนด human workflow; CLI ไม่เรียกโมเดล ไม่ส่งงานภายนอก และไม่อนุมัติ canon เอง งาน engine-only ใช้ synthetic metadata เท่านั้น ไม่อนุญาตให้เขียน prose

## ข้อมูลร่วมของทุก handoff

บันทึก story slug/root, target scene/episode, รายการไฟล์ที่อนุญาต, ผลลัพธ์ที่ร้องขอ, base ref ที่ตั้งใจ, resolved base/HEAD commit SHA จริง และ digest ของ working draft ที่กำลังตรวจ อ่าน root instructions พร้อม `AGENTS.md`, `story.json`, rules/style/canon/state ของ story ที่เลือก ห้ามเติมข้อมูลจากอีก story หากหลักฐานหาย

การอ่าน local Git ต้องใช้เวอร์ชันที่รองรับ global `--no-lazy-fetch` หากไม่รองรับให้ review fail หรือ Git diagnostics เป็น UNKNOWN ไม่ fetch objects, ติดตั้ง Git หรือแก้ persistent settings เพื่อทำให้ข้อจำกัดหายไป

ใช้ `check` และ target context ก่อนส่งต่องาน:

```bash
python scripts/storyctl.py --story my-story check
python scripts/storyctl.py --story my-story brief-review SC-001 --base HEAD --out .local/reviews/SC-001.json
python scripts/storyctl.py --story my-story doctor --target SC-001 --out .local/doctor.json
```

คำสั่งเหล่านี้ต้องใช้ metadata/draft ที่มีอยู่จริง Scaffold ว่างยัง pack/review ฉากที่ไม่มีไม่ได้ อย่าสร้างเนื้อเรื่องหรือ approval เพื่อทำให้ตัวอย่างคำสั่งผ่าน เมื่อใช้ `--workspace` อื่น output ต้องอยู่ใน `.local/` ของ workspace นั้น

## Writer contract

รับเฉพาะขอบเขตที่มนุษย์อนุญาต อ่าน LOCKED facts และ context ของฉากนั้นก่อน ถ้างานอนุญาต prose จึงเขียนเฉพาะไฟล์/ฉากที่ระบุ ใช้ภาษาและ style ของ story เอง ไม่ยืมกฎเฉพาะของตัวอย่างอื่น POV ใช้ได้เฉพาะ knowledge ก่อน target ตามหลักฐาน ห้ามแต่งประวัติที่ไม่มี

ส่งรายการไฟล์ที่เปลี่ยน, proposed facts, proposed state/knowledge deltas, evidence และ UNKNOWNs ทุกข้อยังเป็นข้อเสนอ ไม่เขียนทับ LOCKED facts หรือแก้ approved ledger อัตโนมัติ หาก story เปิด extension กลไกเกมจึงใช้ข้อกำหนด mechanics/sources ของ story นั้น

## Reviewer contract

ตรวจ bundle ของ story/target/commit anchors/draft digest ชุดที่ได้รับจริง Bundle มี working draft ซึ่งอาจยังไม่ commit และเริ่มจากสถานะ unreviewed หาก input เปลี่ยนต้องขอหรือสร้างหลักฐานใหม่ ไม่อ้างว่า review commit SHA ครอบคลุมข้อความ working tree คนละชุด

ตรวจ manifest ของ selected-story inputs และ SHA-256/byte length ด้วย Context เป็น working tree ไม่ใช่ commit identity ของ engine จำกัด source แต่ละไฟล์ที่อ่านไว้ 1 MiB รวม registries/style/evidence และใช้ cap ของ pack โดยไม่ truncate ถ้าเกินหรือ inputs เปลี่ยนระหว่างสร้าง bundle ให้แก้ขอบเขตแล้วสร้างใหม่ ไม่รับรอง bundle ที่สร้างไม่สำเร็จ

รายงาน findings เป็นตำแหน่ง/ID, หลักฐาน, ผลกระทบ และแนวทางแก้ที่เสนอ แยก contradiction ที่พบจาก UNKNOWN ที่หลักฐานไม่พอ ตรวจ target chronology, POV knowledge, LOCKED canon และ approval boundary ไม่ให้ planned effects หรือ future/unapproved evidence กลายเป็นอดีตที่อนุมัติแล้ว การผ่าน schema ไม่รับรองความหมาย prose ไม่แต่ง reviewer score, approval provenance หรือ friction log

ผล reviewer เป็นคำแนะนำให้มนุษย์ตัดสิน ไม่มีสิทธิ์ mark CANON, เปลี่ยน approved history, merge หรือกล่าวว่ามนุษย์อนุมัติแทนบุคคลจริง

## Updater contract

ก่อนเปลี่ยน approved history ต้องมีคำตัดสินจากมนุษย์ที่อนุญาตการเปลี่ยนนั้นโดยชัดเจน ตรวจว่าคำตัดสินตรงกับ story, target และเนื้อหาชุดที่ตรวจ แล้วเสนอ patch ที่เล็กและตรวจย้อนกลับได้ บันทึกแหล่งหลักฐานที่มีจริง หากยังขาดคำอนุมัติหรือ provenance ให้รายงาน UNKNOWN และคงเป็น proposal

E5 ตรวจ merged metadata และ source hash ผ่านคำสั่ง live ที่ระบุชัดได้ แต่ human editorial approval ยังเป็น UNVERIFIED ห้ามอ้าง merged_by, ชนิดบัญชี, local APPROVED fields หรือ test fixtures ว่าเป็น authenticated human approval ไม่ใช้ชื่อ reviewer/PR ที่คาดเดา การเรียก `propose`/`proposal` หรือ `rollup` ไม่ apply patch; rollup เป็นข้อเสนอจาก recaps เดิมเท่านั้น

หลังแก้ข้อมูลที่ได้รับอนุญาต ให้ตรวจ story, replay boundary และ regression ที่เกี่ยวข้องอีกครั้ง รายงานผลจริงพร้อม exact commit และ CI เมื่อมีการ push ตามสิทธิ์ของงาน

## Provenance และ rollup proposal

เมื่อได้รับงานให้ตรวจ remote provenance ใช้ `verify-provenance` กับ repo/PR/head/merge ที่ตั้งใจจริง และ source path/hash เมื่อจำเป็น โดยใช้ `gh` authentication ที่มีอยู่แล้วเท่านั้น หากเข้าไม่ได้หรือข้อมูลไม่ตรงให้รายงาน error ไม่ login ใหม่ ไม่สร้าง credentials หรือเปลี่ยนสิทธิ์ Report live ยืนยันได้เฉพาะ merged metadata/source bytes ตามที่สังเกต ไม่ยืนยัน human editorial decision

หากใช้ `--evidence` ให้อ่าน cached/fixture JSON แบบ offline เท่านั้น ผลที่ตรงกันยังเป็น `OFFLINE_UNVERIFIED` (exit 2) ไม่ได้กลายเป็น live proof ส่วนผล live `OBSERVED_MERGED_METADATA` ใช้ exit 0 และ failures ใช้ exit 1 อย่าแก้ label ให้ดูผ่าน หรือใช้ software PR เป็นการอนุมัติเนื้อเรื่อง

`rollup EP-001 EP-002` สร้าง `PROPOSED` output ด้วยการต่อ recaps ที่มีอยู่จริงจาก eligible local approved ledger ไม่สรุปใหม่ด้วยโมเดล Default เป็น `UNVERIFIED_LOCAL_DECLARATIONS`; `--repo OWNER/REPO --verify-remote` จึงตรวจ repo/PR/head/merge/source hash ของแต่ละ record แบบ online ข้อมูลหายหรือ unapproved ต้องไม่ถูกนำมาสร้างข้อเสนอที่ดูครบ ห้าม apply proposal หรือเปลี่ยน canon/ledger/state โดยอัตโนมัติ และไม่มี post-merge automation ใน E5 ชุดนี้

## การเก็บหลักฐานและเกณฑ์หยุด

`brief-review`, `doctor`, `verify-provenance` และ `rollup` ส่งไฟล์ได้เฉพาะ workspace `.local/` ซึ่งถูก ignore หรือส่ง stdout Bundle อาจมี draft/context/diff ที่ไม่เปิดเผย; stdout อาจไปอยู่ใน log ได้เช่นกัน ห้ามแนบ public PR/issue หรือส่งให้บุคคล/บริการภายนอกโดยไม่มีคำอนุญาตจากผู้ใช้ ใช้สรุป metadata/ผลตรวจเท่าที่อนุญาตใน template

หยุดส่วนที่ต้องพึ่งข้อมูลเมื่อ story/target/commit scope ไม่ตรง, draft digest เปลี่ยน, หลักฐานขาด/ขัดกัน หรือมนุษย์ยังไม่อนุญาต canon change ระบุ action, target, เหตุผล และงานที่ทำแล้วให้ชัด ทำงานส่วนที่ไม่พึ่งข้อมูลนั้นต่อได้ ห้ามแก้ UNKNOWN ด้วยการแต่งข้อมูลหรือข้าม approval boundary

`doctor` ตรวจ local data เท่านั้น ไม่ยืนยัน GitHub auth, repository settings, branch protections หรือ CODEOWNERS enforcement อย่าทดสอบ push-denial กับ live main หรือเปลี่ยน settings เพื่อพิสูจน์ผล การจัดการสิทธิ์และ provenance ต้องอยู่ในงานที่ได้รับอนุญาตแยกต่างหาก
