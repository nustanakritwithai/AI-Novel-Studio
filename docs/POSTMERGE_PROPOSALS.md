# Postmerge proposal artifact — ข้อเสนอจาก metadata เท่านั้น

Workflow นี้เพิ่มหลักฐานให้คนตรวจหลัง software PR ถูก merge โดยสร้างไฟล์ข้อเสนอจาก GitHub metadata ที่ตรวจตรงกัน ไม่อ่านหรือสรุปเนื้อเรื่อง ไม่เขียน canon/state/ledger ไม่สร้าง branch/PR และไม่อนุมัติหรือ merge งานอื่น ผลยังเป็น `PROPOSED` และ `human_editorial_approval: UNVERIFIED`

ดู [workflow](../.github/workflows/postmerge-proposal.yml), [E5](../ENGINE_E5.md) และ [readiness checklist](ENGINE_READINESS.md) ประกอบกัน การมีไฟล์ workflow ใน stacked Draft PR ยังไม่ติดตั้งมันบน `main` และไม่ถือว่า live trigger เคยทำงานแล้ว

## เหตุการณ์และ code ที่เชื่อถือ

Trigger คือ `workflow_run` เมื่อ `Novel continuity checks` จบสำเร็จจาก event `push` ไป `main` ใน repository เดียวกัน ไม่ใช้ `pull_request_target` และไม่ใช้ผลของ PR CI เป็นคำอนุมัติ

GitHub ใช้ workflow definition จาก default branch สำหรับ `workflow_run` ตัว logic เป็น Python stdlib ที่ฝังอยู่ใน definition นั้นและรันด้วย `python3 -I -S` ไม่มี repository checkout, import จาก repository, dependency installation, cache หรือ upstream-artifact download จึงไม่รัน code จาก PR หรือ merged source tree Workflow บันทึก revision ของ definition แยกจาก merge/head ที่กำลังตรวจ

ขอบเขต trust คือ **workflow definition ที่เจ้าของติดตั้งบน default branch** การแก้ definition ต้องได้รับการตรวจจากเจ้าของงาน เอกสารนี้ไม่รับรองว่า rulesets/CODEOWNERS หรือสิทธิ์ repository ถูกบังคับใช้แล้ว; E0 ยังไม่ได้ตรวจรับ Workflow ไม่ป้องกันกรณีผู้มีอำนาจแก้ trusted definition เอง

ไฟล์ `.yml` ใช้ JSON syntax ที่เป็น YAML ได้ เพื่อให้ tests อ่าน definition และ inline code ชุดเดียวกับที่ GitHub ใช้ด้วย stdlib JSON parser ไม่ได้มี Python module อีกชุดที่อ้างว่าแทน workflow จริง

## สิทธิ์และ network

| สิทธิ์ของ job token | ใช้อ่าน |
| --- | --- |
| `contents: read` | current main ref และ immutable commit/tree identities |
| `pull-requests: read` | PR ที่สัมพันธ์กับ commit และ metadata ของ PR ที่ merge |
| `actions: read` | workflow/run identity, head และ run attempt |

ไม่มี repository write scope และไม่ใช้ persistent credentials หรือ custom repository secrets ขั้นตรวจรับ token ชั่วคราวของ GitHub ผ่าน `GH_TOKEN` โดยไม่พิมพ์หรือบันทึกลง artifact การ upload artifact ของ job ใช้กลไก artifact runtime ของ GitHub ไม่ต้องเพิ่ม `actions: write`

การอ่าน API เป็น HTTPS GET ไป `api.github.com` ตาม endpoint ที่อนุญาตเท่านั้น ใช้ API version `2022-11-28` ปฏิเสธ redirect และไม่ใช้ proxy จาก environment ตรวจ JSON อย่างเข้มงวด และไม่ส่ง raw payload, token หรือ exception ที่อาจมีข้อมูลอ่อนไหวไป log ไม่มี PR title/body/source text หรือ account identity ในข้อเสนอ

ขอบเขตของ verifier คือ event ไม่เกิน 8 MiB, API response ไม่เกิน 2 MiB ต่อครั้ง, timeout 20 วินาทีต่อ GET, PR associations ต้องน้อยกว่า 100 รายการ และ proposal ไม่เกิน 64 KiB เกิน limit ต้อง fail ไม่ truncate หลักฐานให้ผ่าน

## หลักฐานที่ต้องตรงกันก่อนสร้างไฟล์

- Event ต้องอยู่ใน repository, branch, workflow และสถานะที่คาดไว้ พร้อม full commit SHA และ run/attempt identity ที่ถูกต้อง
- Remote workflow/run ต้องตรงกับ event จริง รวมถึง workflow path/ID และ run attempt; ชื่อ workflow อย่างเดียวไม่เพียงพอ
- Current `main` ต้องตรงกับ merge head ที่กำลังตรวจทั้งก่อนและหลังการอ่าน หาก `main` เดินหน้าแล้ว จะไม่สร้างข้อเสนอจาก event เก่า
- Git commit identity และ tree ต้องตรง มี parent หนึ่งหรือสองรายการ โดย `source.base_commit` มาจาก first parent ของ merge Git object ที่ตรวจแล้ว ส่วน PR API `base.sha` เก็บแยกเป็น `source.observed_pr_base_sha`: ค่านี้อาจค้างเมื่อ main เดินหน้าก่อน merge จึงไม่ใช่หลักฐาน premerge parent สำหรับ merge ที่มีสอง parents ต้องมี PR head เป็น second parent และต้องผูกกับ PR ที่ merge จริงเพียงรายการเดียวใน repository/main ที่คาดไว้ ประวัติแบบ parent เดียวยังคงเงื่อนไขอนุรักษนิยมว่า observed PR base ต้องตรง first parent; ถ้าไม่ตรงให้ปฏิเสธ ไม่เดา ancestry ตรวจ workflow/run/association/PR/ref ซ้ำ รวมทั้ง observed base เพื่อปฏิเสธข้อมูลที่เปลี่ยนระหว่างขั้นตอน
- ไม่มี token, evidence ขาด, PR ยังไม่ merge, wrong repository, ambiguity, stale event, API/network error หรือข้อมูลขัดกัน ต้องหยุดโดยไม่สร้าง valid proposal ห้ามลดเป็น warning แล้ว upload ผลว่าใช้ได้

การตรวจ metadata ไม่พิสูจน์ว่า PR เปลี่ยนเนื้อเรื่องใดหรือมีผู้มีอำนาจอนุมัติการตัดสินใจเชิงบรรณาธิการ แม้ merged metadata จะตรงทั้งหมดก็ยังนำไป apply ledger ไม่ได้

## Artifact ที่คนต้องตรวจต่อ

Workflow upload เฉพาะ `proposal.json` ที่สร้างใหม่ใน runner temp directory เท่านั้น ใช้ official `actions/upload-artifact` ที่ pin commit `ea165f8d65b6e75b540449e92b4886f43607fa02`, เก็บเจ็ดวัน, ปฏิเสธกรณีไม่มีไฟล์, ไม่ overwrite และไม่รวม hidden files ไม่ upload workspace, event payload, source prose หรือ raw API logs

ข้อเสนอชนิด `POSTMERGE_METADATA_PROPOSAL` ผูก repository/PR/head/merge/base/tree และแยก observed PR base SHA, upstream run/attempt, workflow definition ref/revision, canonical event digest และ raw event digest เข้าด้วยกัน ไม่บันทึก raw event มี `source_scope: MERGED_METADATA_ONLY_NO_RECAP_ASSEMBLY`, `canon_change_authorized: false` และ `ledger_apply_authorized: false` ข้อมูลเป็น metadata เพื่อให้ตามตรวจแหล่งที่มาได้ ไม่ใช่ recap assembly และไม่ใช่ approval record ของเรื่อง

หลังติดตั้งและมี run จริงที่เข้าเกณฑ์ ให้เปิด run ของ postmerge workflow ใน GitHub Actions แล้วตรวจ artifact ให้ตรงกับ PR, SHA และ upstream run ที่ต้องการก่อนส่งต่อให้คนพิจารณา story/target/draft digest ตาม [agent runbook](AGENT_RUNBOOK.md) ห้ามแก้สถานะเป็น CANON/APPROVED จากการพบ artifact หรือคำว่า success ของ workflow

## Failure และ recovery

| เหตุการณ์ | การตอบสนองที่คงขอบเขต |
| --- | --- |
| ไม่ใช่ completed successful push-to-main หรือข้อมูล event ขาด | job ที่ไม่เข้าเงื่อนไขอาจไม่เริ่ม; verifier ปฏิเสธ input ที่ไม่ถูกต้อง ไม่มีข้อเสนอที่ใช้ได้ |
| `main` เดินหน้า หรือ run attempt/head เปลี่ยน | event เก่าถูกปฏิเสธโดยตั้งใจ ใช้หลักฐานของ run ล่าสุดที่เข้าเกณฑ์ ไม่ reset branch เพื่อทำให้ event เก่าผ่าน |
| ไม่มี/มีหลาย merged PR ที่ผูกได้แน่นอน, second parent ไม่ตรง PR head หรือ single-parent base ไม่ตรง | หยุดให้เจ้าของตรวจประวัติ ไม่เดา PR หรือยกเว้น identity checks เพื่อสร้าง artifact |
| Token/API/network ใช้ไม่ได้ | ตรวจ read access และสถานะบริการที่มีอยู่; ไม่สร้าง PAT, ไม่ login หรือขยาย repository permissions อัตโนมัติ Retry ได้เฉพาะเมื่อหลักฐาน/SHAs ยังตรงและเจ้าของสั่งดำเนินการ |
| ขั้นตรวจล้มเหลวหรือไม่มีไฟล์ | ไม่ upload valid proposal; `if-no-files-found: error` ป้องกันการอ้างสำเร็จโดยไม่มี artifact |
| ประวัติ rebase/merge ที่ไม่ผ่าน parent/base contract | ปฏิเสธอย่างปลอดภัย ไม่อ้างว่ารองรับ merge history ทุกแบบ |

เงื่อนไข current-main equality เป็นข้อจำกัดแบบอนุรักษ์นิยม: delayed event และ rerun เก่าอาจไม่สร้าง artifact หลังมี merge ใหม่ จึงไม่รับรองว่าจะออกข้อเสนอครบทุก historical merge

## สถานะการทดสอบและ gate ที่ยังไม่ปิด

Tests จำลอง event/API และตรวจ workflow definition ได้ด้วย:

```bash
python -m unittest discover -s tests -p test_postmerge_proposal.py -v
python -m unittest discover -s tests -v
```

ก่อน owner อนุญาตติดตั้ง สถานะ live เป็น NOT_RUN; fixture/mock ไม่ใช่หลักฐาน live หลัง owner อนุญาต merge #29 เมื่อ 2026-10-23 ตรวจ runtime รุ่นแก้ไขจริงแล้ว: merge `64fb4fed15d44ea37bb81825a288959d0a56dbf8`, [main CI 491 tests](https://github.com/nustanakritwithai/AI-Novel-Studio/actions/runs/40022859423) และ [postmerge run](https://github.com/nustanakritwithai/AI-Novel-Studio/actions/runs/40023031352) ผ่าน ดาวน์โหลด artifact `12531955840` มาตรวจจริงแล้ว ZIP มีเฉพาะ `proposal.json`, SHA-256 `ec598807d035c749c66daaa95fc043bb8e76fc6b96ec92b2cf647d90ae6a2b21` และ PR/head/merge/first-parent/tree/upstream run/workflow-definition identities ตรงกัน

ผลนี้เป็น PASSED_LIVE สำหรับเหตุการณ์ที่บันทึกเท่านั้น observed PR base ของกรณี live นี้ตรง first parent; stale-base edge case ยังคงเป็น regression จำลอง ไม่อ้างว่ารัน event เก่าซ้ำหรือซ่อม failure เก่าย้อนหลัง ค่า event digests ตรวจรูปแบบได้ แต่ไม่ได้ดึง raw event มา recompute อย่างอิสระ Artifact เก็บเจ็ดวันตาม retention เดิม; ไม่มีการเปลี่ยน settings หรือสิทธิ์ token

Technical proposal-artifact workflow มี implementation แยกจาก approved-ledger lifecycle: **human editorial approval ยัง BLOCKED/UNVERIFIED และไม่มี automatic ledger application** E0 privacy/rulesets, reversible migration และ advanced diagnostics ที่ยังไม่ผ่านยังคงตาม [readiness checklist](ENGINE_READINESS.md) ไม่เรียก engine ทั้ง E0–E7 ว่าเสร็จครบจาก workflow นี้

## เอกสารอ้างอิง

- [GitHub: workflow_run และ default-branch workflow](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run)
- [GitHub: secure use และ least privilege](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub: workflow identity contexts](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#github-context)
- [Pinned official upload action](https://github.com/actions/upload-artifact/blob/ea165f8d65b6e75b540449e92b4886f43607fa02/action.yml)

## กรณี PR base snapshot ค้าง

PR API อาจเก็บ base SHA ก่อนที่ PR อื่นจะเข้า main แม้ merge Git object จะมี first parent เป็น main รุ่นใหม่ กรณี PR #26 มี observed base `905d7c3` แต่ merge `6e1d8bda` มี first parent `8a3addec` และ second parent ตรง PR head จึงเป็นรูปร่างข้อมูลที่ verifier เดิมปฏิเสธ Tests จำลองรูปร่างนี้กับ runtime ใน workflow โดยตรง และเก็บทั้ง first parent ที่ยืนยันแล้วกับค่า API ที่สังเกตได้ โดยไม่ทำให้ค่า API กลายเป็นหลักฐาน ancestry

[Run เดิม](https://github.com/nustanakritwithai/AI-Novel-Studio/actions/runs/39954851241) มีเพียง error รวมที่ปิดรายละเอียด จึงยังพิสูจน์ตำแหน่ง exception ในเหตุการณ์เดิมไม่ได้ การแก้นี้อ้างอิงข้อขัดแย้งที่ตรวจซ้ำจาก metadata และ regression จำลอง ไม่อ้างว่าดึง event เดิมมาทดสอบหรือว่า run เดิมถูกซ่อมย้อนหลัง

ยังคง read-only permissions, trusted inline stdlib runtime, current-main equality, merged PR/repository/ref/head identity, repeated-read race checks, fixed artifact path และ PROPOSED/UNVERIFIED ไม่มีการข้าม gate, เปลี่ยน settings, เพิ่ม credentials หรืออนุมัติ canon CI ของ Draft PR เป็นการทดสอบจำลอง ส่วนหลักฐาน live หลัง owner อนุญาต merge บันทึกแยกข้างต้น
