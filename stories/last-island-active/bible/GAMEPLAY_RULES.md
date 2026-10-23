# Gameplay contract — verify, never assume

ใช้ `data/mechanics.json` เป็นทะเบียนสถานะกลไกแยกจากคำสั่งของผู้แต่ง

| Mechanic | Evidence | Story role | Note |
| --- | --- | --- | --- |
| เก็บไม้/คราฟต์ | TRANSCRIPT_SUPPORTED SRC-001 | LOCKED | พบในคลิปสตรีมเมอร์หนึ่งโหมด |
| ไม้เบสบอลคราฟต์จากไม้ | UNVERIFIED | LOCKED scene | ผู้แต่งกำหนด; ต้องหาหลักฐานสูตรเกม |
| กล่องเศษวัสดุริมถนน | UNVERIFIED | LOCKED scene | กล่องหนึ่งใบในตอนแรก |
| ของผู้แพ้ตกไว้ | UNVERIFIED | LOCKED scene | เก็บหิน/เศษวัสดุตามพล็อต แต่ยังไม่ยืนยัน mechanic |
| เตียง/จุดเกิด | UNVERIFIED | LOCKED tutorial | อย่าอ้างการทำงานของ respawn ถ้าไม่มีหลักฐาน |
| การ์ดห้อง เขียว/ฟ้า/ม่วง | TRANSCRIPT_SUPPORTED SRC-001 | OPTIONAL | จำกัดบริบทตัวอย่าง |
| ชิงแชมป์โลก 100 คน | FICTIONAL_TOURNAMENT | FUTURE LOCKED | ไม่เท่ากับจำนวนผู้เล่นของโหมดจริง |

## Rule of evidence

- `VISUALLY_VERIFIED`: ผู้ตรวจดูเฟรม/วิดีโอจริงและให้ timestamp
- `TRANSCRIPT_SUPPORTED`: อาศัยคำบรรยาย/ transcript ที่อาจสะกดผิด
- `TITLE_ONLY`: รู้แต่หัวข้อ/คำอธิบาย ยังไม่เห็นสิ่งที่เกิดขึ้นจริง
- `UNVERIFIED`: ยังไม่พบหลักฐาน หรือสูตร/โหมดไม่ชัด
- `FICTIONAL_TOURNAMENT`: กติกานิยายล้วน

อย่าเปลี่ยนเป็น `VISUALLY_VERIFIED` จากความทรงจำ/ชื่อคลิป. กฎเรื่องที่ผู้แต่งสั่งไว้เขียนตามได้ โดยติด research gap ไว้หากขัดหรือยังพิสูจน์ไม่ได้.

## EP-003 additions — fictional rulebook, not real-game verification

| Mechanic | Evidence | Story requirement | Restriction |
| --- | --- | --- | --- |
| Road oil crate random availability (`MECH-013`) | UNVERIFIED | USER_PLOT_DIRECTIVE | Unopened dark crate is NOT identified as an oil crate |
| Furnace-oil-iron-ammunition upgrade chain (`MECH-014`) | UNVERIFIED | USER_PLOT_DIRECTIVE | No new furnace or metal or hero bullets obtained in EP-003 |
| Enemy uses pistol during bow duel (`MECH-015`) | UNVERIFIED | USER_PLOT_DIRECTIVE | Exact 6 fired shots in this encounter; not a universal gun-capacity rule |
| Meat, hide and fat from animals / fat→oil (`MECH-016`) | UNVERIFIED | USER_PLOT_DIRECTIVE | First actual hunt begins only after EP-003; yield and recipe quantity UNKNOWN |

All new mechanics have `source_ids: []` because no selected-mode evidence was verified. The narrator may use author-specified fictional rules while claims about actual Last Island remain unverified.

## EP-005 — two return encounters (all real-game mechanics UNVERIFIED)

| In-story rule | Reference | Editorial constraint |
|---|---|---|
| Hammer and handgun at 2×2 stone base entrance | MECH-022 | Threatened/battered doorway but no quantified destruction in EP005 |
| Bow fight using preexisting upper cover | MECH-023 | Two opponents defeated across the first clash, then both return alive for a later warning |
| Pistol reload window and bow/pistol tactical contrast | MECH-024 | Exact pistol fight cartridge expenditure UNKNOWN |
| Respawning opponents returning after defeat | MECH-025 | No fixed time-to-respawn or arsenal inferred |
| One warning shot causes a standoff and retreat | MECH-026 | Character choice, not a universal fear mechanic |

User-accepted story loot: **two pistols total and 100 rounds observed on looting**. A later one-round warning is separate; final ammunition stock remains UNKNOWN because earlier use and loaded magazines are unspecified.

No new layered fortifications, completed furnace iron/gunpowder, or permanent horse stable appear in EP005. Story scene acceptance in chat is distinct from authenticated GitHub reviewer approval and independent gameplay verification.

## EP-006 fictional oil refinery rules (all unverified in real game)

| Rule in prose | Mechanic | Restriction |
|---|---|---|
| Zombie NPCs are melee attackers in refinery | MECH-027 | No universal zombie AI/HP/spawn conclusion |
| Green card opens special locked room | MECH-028 | One card acquired but unused in EP006 |
| Crude barrel enters time-gated refinery | MECH-029 | No output collected before hero escapes; no formula/timer specified |
| Three motorcycles with armed riders; hero's horse killed | MECH-030 | Mount loss author-directed; unknown which individual fired |

Possession of firearms cannot establish superiority over all players; group sizes, weapon levels and location matter to character decisions. Vehicle/fuel supply and 'territory control' are only the protagonist's inference. No physical-world petroleum processing instructions are implied by this fictional game mechanic.
