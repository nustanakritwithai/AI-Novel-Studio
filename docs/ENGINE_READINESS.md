# Engine readiness — ตรวจรับตามหลักฐาน ไม่ใช่การอนุมัติเนื้อเรื่อง

เอกสารนี้แยกความพร้อมของเครื่องมือในเครื่องออกจากการอนุมัตินิยายและการควบคุม repository ผล unit tests, CI และ synthetic fixtures ไม่ได้พิสูจน์คุณภาพนิยายหรือ human editorial approval และไม่อนุญาตให้ promote canon หรือ merge โดยอัตโนมัติ

## ที่มาของเกณฑ์และเลข milestone

ใช้เลขปัจจุบันตามแผนผู้ใช้: E0 privacy/rulesets, E1 แยกเรื่อง, E2 schema/replay, E3 migration/diagnostics ที่เหลือ, E4 generic workflow, E5 ledger/provenance, E6 synthetic evaluation, E7 คู่มือไทย

เกณฑ์ที่ตรวจย้อนหลังได้อยู่ใน [E1](../ENGINE_E1.md), [E2](../ENGINE_E2.md), [E3/E4](../ENGINE_E3_E4.md), [E5](../ENGINE_E5.md), [runbook](AGENT_RUNBOOK.md) และ [Story Engine v0.2](../STORY_ENGINE_V02.md) ต้องอ่านข้อจำกัดควบคู่กับรายการความสามารถ

ประวัติ `ENGINE_E1.md` ณ commit `17edf50fda2296c5c2da292ddd4b68d7ee87f96a` ใช้เลข roadmap อีกแบบ: E2 รวม migration, E3 state, E4 provenance, E5 templates, E6 ledger/doctor, E7 evaluation เอกสารภายหลังแก้เลขให้ตรงแผนผู้ใช้และนำ replay มาทำใน E2 แล้ว การเปลี่ยนเลขไม่ได้ทำให้เกณฑ์ที่ยังขาดกลายเป็นงานที่เสร็จ

ไม่พบ checklist E0 ฉบับเต็มที่ versioned อยู่ใน repository ที่ตรวจครั้งนี้ จึงไม่แต่งข้อกำหนด E0 เพิ่มเอง รายการ privacy/rulesets ด้านล่างมาจากขอบเขตงานปัจจุบันและข้อกำหนด human review ใน `STORY_ENGINE_V02.md` สถานะของข้อกำหนด E0 อื่นที่ไม่มีหลักฐานคือ UNKNOWN

## ความหมายสถานะ

| สถานะ | ความหมาย |
| --- | --- |
| PASSED | มีผลตรวจที่ระบุ input/tree และขอบเขตจริง; ไม่ครอบคลุมสิ่งที่ไม่ได้ตรวจ |
| IMPLEMENTED_LOCAL | มีความสามารถใน CLI/โค้ดสำหรับข้อมูลในเครื่อง; ไม่แปลว่า GitHub หรือมนุษย์รับรอง |
| UNVERIFIED | ยังพิสูจน์ความจริง/สิทธิ์/ที่มาของคำอ้างนั้นไม่ได้ |
| BLOCKED | gate ที่ต้องมีหลักฐานหรือคำตัดสินเพิ่มเติมยังไม่ผ่าน; ห้ามอ้างว่าพร้อมในขอบเขตนั้น |
| NOT_RUN | ไม่ได้ดำเนินการตรวจนั้น; ไม่ใช่ผลผ่านหรือหลักฐานว่าถูกปฏิเสธ |
| DEFERRED | ยังไม่มี implementation หรือยังไม่ส่งตรวจใน milestone นี้ |

## Checklist E0–E7

| Gate | เกณฑ์รับงาน | สถานะและหลักฐานปัจจุบัน | ข้อจำกัด/สิ่งที่ยังขาด |
| --- | --- | --- | --- |
| E0.1 | ตรวจ/ตั้ง privacy, rulesets และสิทธิ์ branch ตามที่เจ้าของอนุญาต | NOT_RUN — งาน engine นี้ไม่อนุญาตให้เปลี่ยน settings; `doctor` คืน GitHub settings/security/CODEOWNERS enforcement เป็น UNKNOWN | ไม่มีการทดสอบ push เข้า main เพื่อให้เกิด denial; ไม่อ้างว่า branch protection หรือ CODEOWNERS ถูก enforce |
| E0.2 | gate ก่อนเผยแพร่/รวม approved narrative ต้องมีคำตัดสินมนุษย์ที่มีสิทธิ์ | BLOCKED / UNVERIFIED — ไม่มี actual editorial approval ใน synthetic workflow | merge account, บัญชีชนิด User, local APPROVED หรือ software PR ที่ merge ไม่ใช่หลักฐานการอนุมัตินิยาย |
| E1.1 | แยกข้อมูล กฎ style และ optional gameplay ต่อเรื่อง | IMPLEMENTED_LOCAL — `story_config`, `storyctl new`, story-root tests และ per-story rules/style | `new` สร้าง metadata ว่าง ไม่สร้างเรื่องหรือ canon; gameplay ปิดโดย default |
| E1.2 | สอง dataset ใช้ IDs ซ้ำได้โดยไม่รั่วข้อมูล; CLI เดิมยังใช้ได้ | PASSED ที่ baseline PR #7 — `test_story_roots.py`, `test_storyctl_contracts.py` และ tests เวลา/knowledge | ต้องระบุเรื่องให้ชัด; missing story ไม่ fallback ไปเรื่องอื่น |
| E1.3 | เก็บตัวอย่างเดิมโดย byte content ไม่เปลี่ยน | PASSED ที่ baseline PR #7 — `test_example_integrity.py` และ manifest 54 ไฟล์ | ไม่ถือว่าการย้ายไฟล์หรือ tests เป็นการอนุมัติ Last Island; milestone นี้ไม่เขียนเนื้อเรื่อง |
| E2.1 | ตรวจ registry แบบมี version, required/type/enum/reference และ malformed input | IMPLEMENTED_LOCAL — JSON Schema Draft 2020-12 จริง, offline resources, pinned dependencies และ `test_registry_schema.py` | ต้องติดตั้ง requirements ครบ; schema PASS ไม่พิสูจน์ semantic draft หรือ approval |
| E2.2 | replay deterministic ก่อน target, ไม่ใช้ future/planned/unapproved evidence, gap เป็น UNKNOWN | IMPLEMENTED_LOCAL — `state_replay.py`, `test_state_replay.py`, integration tests และ scene-time pack tests | ผล KNOWN มีขอบเขต local evidence; ไม่มี history ใช้ legacy snapshot/UNKNOWN ตามที่ระบุ ไม่สร้างประวัติเอง |
| E3.1 | version policy และ reversible migration พร้อมตรวจ bytes/ความหมายก่อน–หลัง | DEFERRED — ยังไม่มีคำสั่ง migration ครบวงจร | นี่เป็นเกณฑ์เดิมที่มีอยู่จริงใน E1 roadmap (เดิมอยู่ E2) จึงยังเป็น acceptance gap ของแผนเต็ม ไม่ใช่งานที่ลบออกเพราะเปลี่ยนเลข |
| E3.2 | diagnostics อธิบาย reference/state/provenance gaps โดยไม่แก้เงียบ | IMPLEMENTED_LOCAL บางส่วน — `doctor` ตรวจ schema, local refs, Git anchors และ availability ของ state แบบ read-only | advanced diagnostics และ authenticated remote provenance ใน doctor ยัง DEFERRED; UNKNOWN ต้องคงอยู่เมื่อไม่ได้ตรวจ |
| E4.1 | writer/reviewer/updater contracts และ templates แยกต่อเรื่อง | IMPLEMENTED_LOCAL — `docs/AGENT_RUNBOOK.md`, issue/PR templates, `brief-review`, `propose` alias | เป็น handoff ที่ต้องใช้คำตัดสินมนุษย์ ไม่มี writer/reviewer/updater automation หรือ prose-quality score |
| E4.2 | review bundle จับ exact working draft/diff/input hashes และ commit anchors | IMPLEMENTED_LOCAL — `review_bundle.py`, review/CLI regressions; status UNREVIEWED | draft อาจต่างจาก HEAD; anchors ของ engine ไม่ได้อ้างว่า working draft ถูก commit หรือ review แล้ว |
| E5.1 | PR/repo/head/merge/source identities ตรงกัน, stale/missing/inconsistent evidence fail closed | IMPLEMENTED_LOCAL และ PASSED live smoke ที่ baseline PR #7 — `provenance.py`, adversarial tests; software PR #2/#3 README metadata/hash | live proof ยืนยัน observed merged metadata และ bytes ที่อยู่ใน tree เท่านั้น ไม่พิสูจน์ว่า PR เปลี่ยนไฟล์นั้นหรือใครอนุมัติเนื้อหา |
| E5.2 | offline/fixture ไม่ยกระดับเป็น authenticated proof | IMPLEMENTED_LOCAL — `OFFLINE_UNVERIFIED`, `UNVERIFIED_LOCAL_DECLARATIONS` และ anti-spoof tests | fixture statuses, simulated local Git commit/merge และ reviewer agent ไม่ใช่ human editorial approval |
| E5.3 | rollup ใช้ eligible source recaps จริงและคง provenance โดยไม่แต่ง summary | IMPLEMENTED_LOCAL — deterministic exact recap concatenation, hashes, stable snapshots และ rollup regressions; status PROPOSED | ไม่ apply ledger/state/canon; ไม่มี LLM summary หรือ auto approval |
| E5.4 | approved-only ledger lifecycle หลัง actual human approval/merge | BLOCKED / DEFERRED — มี proposal CLI; ยังไม่มี postmerge workflow | ต้องกำหนด editorial identity/authority และตรวจ trusted revision/read permissions ก่อนเพิ่ม automation; ห้ามเอา synthetic local labels ปิด gate นี้ |
| E6.1 | reproducible synthetic 3-scene workflow ใช้ commands จริงครบเส้นทาง | PASSED สำหรับ command workflow ที่บันทึก — `python scripts/acceptance.py --out .local/e6-workflow-proof` จบ 17 ขั้นตอน exit 0, empty check PASS และ `source_preserved: true`; ดู [procedure](../ENGINE_E6.md) และ [ผลที่บันทึก](../evaluation/e6/RESULTS.md) | runner เองระบุ semantic evaluation NOT_RUN และ human editorial approval BLOCKED; ผล command acceptance ไม่ถูกยกระดับเป็น semantic/human approval; final full suite/CI ต้องรายงานแยกใน Draft PR |
| E6.2 | fresh blind reviewer จับ planted faults 5 ข้อครบ โดย critical canon/knowledge/inventory/approval ต้องไม่หลุด | PASSED เฉพาะ synthetic assertion case ที่บันทึก — [A94 raw findings](../evaluation/e6/raw/A94.json) จับ 5/5 ข้อตาม [adjudication](../evaluation/e6/adjudication.json), ไม่มี seeded miss; [manifest](../evaluation/e6/manifest.json) ผูก packet/key hashes และ [RESULTS](../evaluation/e6/RESULTS.md) บันทึกขั้นตอน | reviewer เป็น fresh native agent `fork_turns=none` รับ packet เดียว ไม่มี key/author reasoning; เป็น procedural blind บน shared filesystem ไม่ใช่ OS-enforced sealing; adjudicator เป็น implementation agent ไม่ใช่มนุษย์; ไม่ได้ทดสอบ literary prose หรือ general semantic quality |
| E6.3 | clean control วัด false positives และรายงาน misses จริง | PASSED เฉพาะ control ที่บันทึก — [B17 raw report](../evaluation/e6/raw/B17.json) คืน `findings: []`; adjudication บันทึก zero reported false positives และคง uncertainty เรื่อง actual human review history | ไม่มีคะแนน/เปอร์เซ็นต์ที่แต่งขึ้น; raw reviewer severity คงเดิม แม้ไม่ตรง priority ของ answer key; ผลจากหนึ่ง candidate/หนึ่ง control ไม่ใช่สถิติความสามารถทั่วไป |
| E7.1 | คู่มือไทยและ fillable premise/world rules/characters/style template ตาม schema/CLI จริง | IMPLEMENTED_LOCAL — [คู่มือ E7](../ENGINE_E7.md) ครอบคลุม dependencies, คำสั่ง, examples, recovery และ boundaries; [fillable input template](../templates/STORY_INPUT_TH.md) คง UNKNOWN/PENDING และอธิบาย registry mapping | เป็นคู่มือของความสามารถที่มี ไม่ได้ปิด gate ที่ยังขาด; template ไม่ใช่ auto-importer/approval record และไม่ pre-approve canon หรือสร้าง prose |
| E7.2 | fresh empty `new` ตรวจผ่านได้โดยไม่แก้ core; dependency/examples/recovery ชัดเจน | PASSED สำหรับ guide smoke 7 checks ที่บันทึกในคู่มือ — `new`, empty `check` (0 errors/0 warnings), `status`, `doctor` ผ่าน; duplicate `new`, empty-target `pack` และ missing-story `check` fail ตามคาด โดย source 21 ไฟล์ไม่เปลี่ยน | โครงว่างไม่มี target ให้ pack/review; missing source ต้อง fail/UNKNOWN ไม่สร้างข้อมูลแทน; smoke ใช้ dependencies ที่ติดตั้งแล้ว ไม่ใช่การพิสูจน์ installation ใหม่หรือ human signoff |

## หลักฐาน baseline และ final milestone

Baseline ที่ใช้เริ่ม E6/E7 คือ [Draft PR #7](https://github.com/nustanakritwithai/AI-Novel-Studio/pull/7), head `3d915241203aa762f2b3c8fc3d3c68170ba5189e`, tree `cd7d6fb0a241e0eb9c0e6c8ec18e353e601a0810` หลักฐานส่งมอบของ baseline ระบุ complete suite 215 passed / 0 failed / 0 skipped, validators 0 errors และ 4 existing UNVERIFIED gameplay warnings ต่อ validator, pack smoke และ byte-integrity manifest ผ่าน; [CI run 39763107748](https://github.com/nustanakritwithai/AI-Novel-Studio/actions/runs/39763107748) ผ่านบน exact head นั้น นี่เป็นผลของ baseline ไม่ใช่ผลล่วงหน้าของ final E6/E7 tree

Final E6/E7 ต้องบันทึกผล command workflow, tests/validators, blind review กับ clean control, guide smoke, published head และ exact-head CI ของตัวเองใน Draft PR พร้อม links ของ artifacts ส่วนที่ยังไม่มีผลต้องคง NOT_RUN/UNVERIFIED จนกว่าจะมีหลักฐานจริง

## ขอบเขตคำว่าพร้อม

เครื่องมือสำหรับตรวจ metadata, ประกอบ context/review evidence, replay local history และเสนอ rollup มีขอบเขตที่ทดสอบได้ การผ่าน synthetic acceptance จะอนุญาตให้กล่าวเฉพาะว่าเส้นทาง synthetic ที่ระบุผ่าน ไม่ใช่กล่าวว่า engine ทั้ง E0–E7 พร้อมใช้งานครบ หรือว่า narrative พร้อมเผยแพร่

ยังห้ามปิด gate เรื่อง privacy/rulesets, actual human editorial approval, approved ledger lifecycle/postmerge workflow และ reversible migration ด้วยผล tests หรือ fixture approval ไม่มีการ merge Draft PR นี้หรือเปลี่ยน canon/ข้อมูลจริงโดยอัตโนมัติ
