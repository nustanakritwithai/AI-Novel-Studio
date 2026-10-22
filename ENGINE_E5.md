# Engine E5 — provenance ที่ตรวจย้อนกลับได้และ rollup proposal

E5 ชุดนี้เพิ่มการตรวจ merged metadata/source bytes จาก GitHub แบบอ่านอย่างเดียว และสร้าง rollup proposal จาก recaps ที่มีอยู่แล้ว งานนี้ไม่เขียนเนื้อเรื่อง ไม่เรียก LLM ไม่อนุมัติ canon ไม่แก้ approved ledger/state และไม่ merge PR ผล live ที่ตรงกันยังไม่พิสูจน์ **human editorial approval**

ใช้ร่วมกับ [AGENTS.md](AGENTS.md), [agent runbook](docs/AGENT_RUNBOOK.md), [E3/E4 local review](ENGINE_E3_E4.md) และ [E2 schema/replay](ENGINE_E2.md) เลข roadmap ปัจจุบันตรงตามแผนผู้ใช้คือ **E5 ledger/provenance, E6 synthetic evaluation, E7 คู่มือไทย** ตารางเก่าที่จัด rollup ไว้ E6 และ evaluation ไว้ E7 เป็นเลขที่แก้ไขแล้ว E3 migration ขั้นสูงยังไม่เสร็จ

## ความสามารถและขอบเขตของคำว่า verified

| หลักฐาน | ผลที่บอกได้ | สิ่งที่บอกไม่ได้ |
| --- | --- | --- |
| live GitHub GET ที่ repo/PR/head/merge ตรงกัน | observed merged metadata จาก GitHub ตามเวลาที่ตรวจ | ผู้ merge เป็นมนุษย์ผู้มีสิทธิ์อนุมัติเนื้อหา หรือได้ตัดสินใจทางบรรณาธิการ |
| source path + SHA-256 ที่ตรงกับ immutable commit/tree/blob | bytes ณ commit ที่ระบุตรงกับ digest ที่คาดไว้ | เนื้อหานั้นจริง/เหมาะสม/เป็น canon โดยอัตโนมัติ |
| cached JSON หรือ fixture ผ่านเงื่อนไขภายใน | ข้อมูล offline สอดคล้องกับคำประกาศที่รับเข้า | เคยอ่านข้อมูลนั้นจาก GitHub จริงหรือเป็นหลักฐาน live ล่าสุด |
| local APPROVED/CANON, approved_by, merged_by หรือบัญชีชนิด User | ค่าข้อมูลที่พบในขอบเขตนั้น | authenticated human editorial approval |
| rollup proposal | recaps จาก local records ที่เข้าเกณฑ์ถูกนำมาต่อเป็นข้อเสนอ | ledger ใหม่ที่อนุมัติแล้ว หรือสิทธิ์ให้แก้ canon |

ห้ามใช้การ merge ของ software PR เป็นหลักฐานอนุมัติเนื้อเรื่อง ห้ามแต่งชื่อ reviewer, คะแนน, approval provenance หรือ friction entries เพื่อให้รายงานดูครบ `human_editorial_approval` ยังคง UNVERIFIED แม้ live merged metadata/source hash จะผ่าน

## Prerequisites และการเก็บ output

ติดตั้ง Python 3.11+ และ pinned dependencies ตาม README หากใช้ live verifier ต้องมี `gh` ที่ติดตั้งและ authenticated ไว้แล้วจากสภาพแวดล้อมที่ผู้ใช้อนุญาต คำสั่งใช้ GitHub API GET ผ่าน authentication เดิม ไม่ login/setup ใหม่ ไม่สร้าง credentials ไม่แสดง secrets และไม่เปลี่ยน repo visibility, permissions, settings หรือ branch protections หากเข้าไม่ได้ให้รายงาน error และหยุดส่วนที่ต้องใช้ remote

new file output อยู่ได้เฉพาะ `<workspace>/.local/` ที่ ignore ไว้ หรือไม่ระบุ `--out` เพื่อแสดง stdout เช่นเดียวกับ brief-review/doctor ข้อมูล source paths, hashes และ recaps อาจยังไม่เปิดเผย ห้ามแนบ public PR/issue หรือส่งภายนอกโดยไม่มีคำอนุญาตจากผู้ใช้ stdout ก็อาจถูกเก็บใน log ได้

## ตรวจ provenance แบบ live

ตัวอย่างต่อไปนี้เป็นรูปแบบคำสั่ง ให้แทน placeholders ด้วยข้อมูลที่ตั้งใจตรวจจริง ไม่ใช่หลักฐาน approval ตัวอย่างที่สร้างขึ้น:

```bash
python scripts/storyctl.py verify-provenance --repo OWNER/REPO --pr PR_NUMBER --head HEAD_SHA --merge MERGE_SHA --out .local/provenance.json
python scripts/storyctl.py verify-provenance --repo OWNER/REPO --pr PR_NUMBER --head HEAD_SHA --merge MERGE_SHA --source REPO_PATH --sha256 SHA256 --out .local/source-provenance.json
```

`--repository` เป็น alias ของ `--repo` ใช้ repository path สำหรับ `--source` ไม่ใช่ path ที่เดาจาก story อื่น ระบุ source กับ SHA-256 เป็นคู่เมื่อต้องตรวจ bytes ใช้ commit SHA เต็มที่ได้จากหลักฐานจริง ไม่ใช้ชื่อ branch ที่เคลื่อนต่อได้แทนค่าที่คาดไว้

`verify-provenance` ตรวจ scope จาก repo/PR/path ที่ระบุโดยตรง จึงไม่รับ global `--story` แทนการเงียบแล้วละเลย selector ต่างจาก rollup ซึ่งต้องเลือก story และผูก source path เต็มเข้ากับ recap ใน story นั้น

เมื่อไม่ระบุ `--evidence` คำสั่งนี้เป็นการขออ่าน GitHub แบบ live อย่างชัดเจน ตรวจ repo, PR number, merged state, head SHA และ merge SHA กับค่าที่คาดไว้ ถ้ามี source ให้ตรวจผ่าน immutable Git commit/tree/blob พร้อมตรวจชนิดของ object และ hash ไม่ใช้ Contents API ที่อาจตีความ symlink คลุมเครือ Inaccessible, missing หรือ inconsistent evidence ต้อง fail closed ไม่ลดระดับเป็นคำเตือนแล้วอ้างว่า verified

ผลสำเร็จ live ใช้ `OBSERVED_MERGED_METADATA` เป็นข้อเท็จจริงระดับ merge/source ที่สังเกตได้ ไม่ใช่การรับรองผู้อนุมัติทางบรรณาธิการ คำสั่งไม่แก้ label ใน story หรือบันทึก approval ลง ledger แทนมนุษย์

การพบ path/hash ณ merge commit พิสูจน์เพียงว่า bytes นั้นอยู่ใน tree ที่ตรวจ ไม่ได้พิสูจน์ว่า PR ที่ระบุเป็นผู้เปลี่ยนไฟล์นั้น หรือว่ามนุษย์ review/อนุมัติ narrative content นั้นแล้ว E5 นี้ยังไม่ตรวจ diff attribution ของแต่ละไฟล์กับ PR และไม่เปลี่ยนขอบเขต human editorial approval จาก UNVERIFIED

## ตรวจข้อมูล offline และอ่าน exit codes

```bash
python scripts/storyctl.py verify-provenance --repo OWNER/REPO --pr PR_NUMBER --head HEAD_SHA --merge MERGE_SHA --evidence .local/cached-pr.json --out .local/offline-provenance.json
```

`--evidence` ใช้ local cached/fixture JSON แบบ offline ไม่มีการยกระดับ fixture เป็น GitHub live verification แม้ fields และ digest จะตรงกันภายในไฟล์ก็ตาม เก็บที่มาของ cache ตามจริง; อย่าใส่ชื่อคนหรือ PR ที่แต่งขึ้นใน ledger เพื่อให้ตัวอย่างนี้ผ่าน

รูปแบบ cache ใช้ข้อมูล REST/Git objects จริงตามขอบเขตที่ตรวจ ไม่ใช่เพียงบันทึก report ที่มีคำว่า verified:

| Top-level key | ข้อมูลที่ต้องมี |
| --- | --- |
| `pull_request` และ `pull_request_after` | PR snapshots ก่อน/หลังสำหรับตรวจความคงที่; ต้องตรง number, `base.repo.full_name`, `head.sha`, `merge_commit_sha`, merged/closed และ timestamp ตามเงื่อนไข |
| `merge_commit` | Git commit object ที่ SHA ตรง merge ที่คาด และมี `tree.sha`; ต้องมีแม้ตรวจ metadata โดยไม่ระบุ source |
| `trees` | เมื่อระบุ source: map จาก tree SHA ไปยัง Git tree object ที่ไม่ truncated พร้อม entries ของ path components, mode/type/SHA และขนาด blob ตามที่ใช้ |
| `blobs` | เมื่อระบุ source: map จาก blob SHA ไปยัง object ที่มี SHA, size, encoding base64 และ content ที่ตรวจ hash ได้ |

ถ้าไม่ขอ source ใช้สาม keys แรกของ metadata คือ PR snapshots สองรายการกับ merge commit; ไม่ได้ตรวจ source bytes จึงใช้แทน source binding ที่ rollup ต้องการไม่ได้ การใส่ top-level status/transport/verified ที่กล่าวอ้างเองไม่ทำให้ cache เป็น live proof ไม่ใส่ fabricated payload เพื่อทำให้ demo ผ่าน

ไฟล์ cache รับได้ไม่เกิน 8 MiB และต้องเป็น strict JSON ค่าที่บันทึกไว้กับ hash เป็นหลักฐาน offline เท่านั้น ไม่ใช่ authentication ห้ามใช้ `--out` ทับไฟล์ `--evidence` ของคำสั่งเดียวกัน Failure report อาจถูกเขียนลง `.local/` ได้พร้อม nonzero exit code จึงต้องอ่าน status/errors และ exit code ร่วมกัน ไม่ถือว่าการมี output file แปลว่าตรวจผ่าน

verifier จำกัด source blob 1 MiB, live API response ต่อ object 2 MiB, path ไม่เกิน 32 components/1,024 ตัวอักษร และ tree listing ไม่เกิน 10,000 entries ข้อมูลเกิน limit หรือ object mode/type ไม่ตรงต้อง fail ไม่ตัด content หรือข้าม component ให้ผ่าน

| Exit code ของ verify-provenance | ความหมาย |
| --- | --- |
| 0 | live `OBSERVED_MERGED_METADATA` เท่านั้น; human editorial approval ยัง UNVERIFIED |
| 2 | offline evidence สอดคล้อง แต่ผลเป็น `OFFLINE_UNVERIFIED`; ไม่ใช่ live success |
| 1 | input, access, missing evidence หรือค่าที่ไม่ตรงทำให้ตรวจไม่ผ่าน |

อย่าเปลี่ยน exit 2 หรือ status ของ offline report เป็น verified เพื่อทำให้ CI ดูเขียว หากขั้นตอนต้องการ live proof ต้องตรวจ live ด้วยสิทธิ์ที่มีจริงตาม scope ที่อนุญาต

## สร้าง rollup proposal จาก recaps เดิม

หลัง story มี episode/scene metadata, approved source evidence และ ledger records ที่ผ่าน checks จริงแล้ว:

```bash
python scripts/storyctl.py --story my-story rollup EP-001 EP-002 --out .local/rollup.json
python scripts/storyctl.py --story my-story rollup EP-001 EP-002 --repo OWNER/REPO --verify-remote --out .local/remote-rollup.json
```

scaffold ใหม่ยังไม่มี recaps หรือ approved records ให้ rollup มนุษย์ต้องสร้างข้อมูลและอนุมัติตามกระบวนการก่อน ไม่สร้างเนื้อเรื่องหรือประวัติอนุมัติให้ตัวอย่างว่างเพื่อให้คำสั่งผ่าน ระบุ episode IDs ที่ต้องการในลำดับเรื่อง และอ่านผล validation ถ้าขาด record/source หรือมี unapproved evidence ให้หยุด ไม่สรุปจากแผนหรือ draft ที่ยังไม่เข้าเกณฑ์

rollup เป็นการนำ recap text เดิมมาต่ออย่าง deterministic เพื่อเสนอให้มนุษย์ตรวจ ไม่มี LLM summary ไม่มีข้อเท็จจริงใหม่ Default ทำงาน offline และติดขอบเขต `UNVERIFIED_LOCAL_DECLARATIONS`; local eligibility ไม่ใช่ human approval ที่ GitHub รับรอง หากใช้ `--verify-remote` ต้องมี repo และข้อมูลอ้างอิงของแต่ละ record ให้ตรวจ PR/head/merge/source hash ได้จริง รายการใดไม่ผ่านต้องไม่ถูกนำเสนอเป็น rollup ที่ remote verified แล้ว

IDs ต้องไม่ซ้ำและต่อเนื่องตามลำดับ series; offline rollup ไม่ต้องมี Git repository แต่ live verification ต้องอ่าน Git root จริงเพื่อผูก path แบบ repository-relative ของ recap ที่เลือก แต่ละ recap/source ที่อ่านจำกัด 1 MiB และ assembly รวมจำกัด 8 MiB หากเกินให้เลือก episodes น้อยลง ข้อความเดิมเก็บ UTF-8/CRLF ตาม source แล้วต่อด้วย separator `\n\n` พร้อม hash ของ sources, assembly และ input manifest ไม่มี silent truncation

`record.provenance` เป็น optional object ที่ต้องครบหก fields เมื่อใช้: `repository`, `pr_number`, `head_commit`, `merge_commit`, `source_path`, `source_sha256` ไม่เปลี่ยน schema version หรือบังคับเติม provenance ให้ข้อมูลตัวอย่างเดิม หากมีคำประกาศ source hash แต่ไม่ตรงกับ recap bytes ปัจจุบันต้อง fail แม้ offline ส่วน `--verify-remote` ต้องมี object นี้และผูก repository/path/hash ตรงกับ selected story จริง ค่าที่ผู้ใช้กรอกเองยังไม่กลายเป็น human approval

เมื่อ record มีทั้ง `approval` และ `provenance` ค่า `pr_number` และ `merge_commit` ต้องตรงกันด้วย การเทียบ SHA ไม่ขึ้นกับตัวพิมพ์ใหญ่/เล็ก ข้อขัดแย้งที่รู้แล้วต้อง fail ทั้ง offline และ live; สถานะ UNVERIFIED ไม่ใช่ข้อยกเว้นให้ identity/hash ที่ขัดกันผ่าน

output มีสถานะ `PROPOSED` แม้ remote checks ผ่าน การจบคำสั่งด้วย exit 0 ของ rollup จึงหมายถึงสร้าง proposal สำเร็จเท่านั้น ไม่ใช่อนุมัติหรือ apply proposal คำสั่งไม่เขียน recap กลับ, ไม่เพิ่ม chapter/book ledger, ไม่เปลี่ยน story_state และไม่เลื่อน canon

## Human decision และ automation ที่ยังไม่ทำ

writer/reviewer/updater ยังคงใช้ [runbook](docs/AGENT_RUNBOOK.md) ตาม story/target/commit/digest ที่ตรงกัน ก่อนแก้ approved history ต้องมีคำตัดสินจากมนุษย์ที่อนุญาตการเปลี่ยนนั้นจริง Hash และ merged metadata ช่วยผูก bytes กับ commit แต่ไม่แทนคำตัดสินนั้น `merged_by.type == User` หรือชื่อผู้ merge ไม่พิสูจน์ว่าเป็น human editor ผู้ได้รับอนุญาต

E5 bounded PR นี้เป็น CLI เท่านั้น ไม่มี post-merge workflow อัตโนมัติ การเพิ่ม automation ภายหลังต้องทบทวนแหล่งข้อมูล, trusted revision, permissions และการรัน untrusted PR content แยกต่างหาก ไม่เพิ่ม workflow ที่เข้าถึง secrets หรือเปลี่ยน settings เพื่อทำให้ข้อจำกัดนี้หายไป `doctor` ยังคงเป็น local report และไม่แอบเรียก live verifier

## Validation และหลักฐานที่ต้องรายงานจริง

คง regression coverage เดิม 157 tests จาก E3/E4 และ byte-integrity manifest ของตัวอย่างเดิมทั้ง 54 ไฟล์ เพิ่มเฉพาะ synthetic metadata/cache fixtures ที่ระบุว่า offline ไม่แตะตัวอย่าง Last Island หรือสร้าง approval ให้มัน รัน complete suite และ validators บน tree สุดท้าย:

```bash
python scripts/novelctl.py check
python scripts/story_engine.py check
python -m unittest discover -s tests -v
```

บันทึก compatibility จาก live checks: เมื่อ pin API `2026-03-10` ข้อมูล PR #2/#3 มี `merged: true` แต่ `merge_commit_sha: null` verifier จึง fail closed ตามเงื่อนไข ไม่มี authentication denial จากนั้นเลือก pin `2022-11-28` ซึ่งยังรองรับถึง 10 มีนาคม 2028 ตาม [GitHub REST API versions](https://docs.github.com/en/rest/about-the-rest-api/api-versions) เพื่อให้ contract ของ merge SHA ใช้งานได้ โดยไม่เปลี่ยน authentication/credentials/settings และไม่ผ่อนการตรวจ repo/SHA/hash

ผล verifier live หลังเปลี่ยน version ผ่านทั้งสอง software PR โดยแต่ละครั้งเป็น `OBSERVED_MERGED_METADATA`, errors ว่าง และ GitHub API GET 5 ครั้ง:

| Software PR | Merge commit ที่ตรวจ |
| --- | --- |
| [#2](https://github.com/nustanakritwithai/AI-Novel-Studio/pull/2) | `54e5b6eb60016a8a6241ac17b4afe30640d9010e` |
| [#3](https://github.com/nustanakritwithai/AI-Novel-Studio/pull/3) | `e2f82d2971526bd77ac82999f37f24fe5b7a8816` |

ทั้งสองตรวจ `README.md` ขนาด 11,830 bytes ได้ Git blob `d5dafbb735affd5c7efebbbb2062fba55e075722` และ SHA-256 `e6b5830e8249e02194b18baa12d5a61da25f35ec078747d73ca13853746ef5f7` ตรงตามที่คาด โดย PR #2 ผูกกับ head `3c0710c8a680b07efeb0bbd34030dfec121e8333` ผลยืนยัน merged metadata กับ source presence/hash เท่านั้น ไม่พิสูจน์ว่า PR เปลี่ยนไฟล์หรือมนุษย์ review/อนุมัติเนื้อหา; `human_editorial_approval` ยัง UNVERIFIED ทั้งคู่

ผล negative cases, rollup tests, exact final head และ CI ต้องอ้างผลจริงใน Draft PR ไม่ถือว่า live source check ของ software PR เป็น novel approval หรือผลทดสอบ final tree ทั้งหมด

ต้องมี tests สำหรับ PR ไม่ merge, repo/head/merge/hash ที่ไม่ตรง, inaccessible/missing source, object type ที่ไม่ยอมรับ, offline evidence ที่ห้ามถูกยกระดับ, rollup ที่ขาด/unapproved record และการไม่เปลี่ยน canon/ledger/state รายงาน PASS / FAIL / SKIPPED / NOT RUN ตามจริง ไม่ลด assertion เดิมเพื่อทำให้ผ่าน

## Roadmap ที่ยังต้องตรวจรับแยก

| Milestone | สิ่งที่ยังเหลือ | เกณฑ์รับงาน |
| --- | --- | --- |
| E3 ส่วนที่เหลือ | schema migration แบบ reversible และ diagnostics ขั้นสูง | ไม่แก้ canon เงียบ ๆ; ตรวจข้อมูลก่อน/หลังและ gaps ได้ |
| E5 ledger/provenance | นโยบายและหลักฐาน human editorial approval ที่พิสูจน์ได้จริง; lifecycle ของ ledger ที่เกิน proposal | ไม่เชื่อ local labels/merge account แทนคำตัดสิน; ไม่มีการ apply เกินสิทธิ์ |
| E6 synthetic evaluation | workflow สามฉากและ adversarial planted violations ครบขั้น | critical canon, knowledge และ approval violations ต้องถูกจับทุกกรณีก่อนอ้างว่าผ่าน; รายงานข้อที่ยังไม่ครอบคลุม |
| E7 คู่มือไทย | onboarding และ runbook ครบตาม engine ที่ตรวจรับจริง | ตัวอย่างทดสอบได้, ขั้นตัดสินใจชัด, อธิบาย UNKNOWN/UNVERIFIED และ recovery ได้ |

คู่มือ E5 และ runbook ที่เพิ่มเป็นความคืบหน้าของ E7 ด้วย แต่ยังไม่หมายความว่าคู่มือหรือ engine เสร็จครบทั้งแผน ไม่มี paid API, credentials ใหม่, settings/security changes, narrative writing หรือ automatic canon approval ใน milestone นี้
