# Handshake — Recorded Dissent (Phase 0)

Dissent is kept, not smoothed. Each entry: who, position, what's at stake, status.

## D1 — Kill-signal authority (HOTTEST)
**Who:** Results + Sync + Radio + Press + Marketing vs ATHENA.
**Positions:** Results: kills issued only by initiative owner / KingCode / Black; programmatic kill only from pre-registered kill_rules. ATHENA: pre-registered numeric kill rules should fire autonomously with an anchored benchmark-result as trigger — "a kill rule that needs a human to pull the trigger is a suggestion."
**At stake:** whether the protocol is a notification system or an execution system. Departments fear automated kills on slow outreach lanes (9-day replies vs 7-day silence rules).
**Status:** v0.1 ships notification-only. **Needs Black's ruling before autonomous execution.**

## D2 — Verification-state cardinality
**Who:** Data vs Radio (+A&R).
**Positions:** Data: two orthogonal fields — `confidence` (verified/estimate/unverifiable) × `lifecycle` (claimed/active/retired); conflating them corrupts the scoreboard. Radio: single three-state `claim_status` (claimed/verified/retired) for lane speed. A&R: estimates must not be second-class citizens.
**At stake:** the scoreboard's integrity vs the placement lane's speed — and whether the DJ 6Rings garbling repeats.
**Status:** provisional — the three-state field ships with `confidence` as a separate optional field so Data can compute the orthogonal view. **Needs a design session, not a vote, before Phase 1.**

## D3 — Rights binary vs third state
**Who:** Affairs vs Sync.
**Positions:** Affairs: DOCUMENTED/PENDING only, forever — "in-process is a euphemism for pending; the protocol must not launder uncertainty." Sync: binary forces operational lies about clearance timelines.
**At stake:** whether the protocol launders rights uncertainty into pitch material.
**Status:** v0.1 ships the binary. **Escalated to Black.**

## D4 — Provenance burden on publishing lanes
**Who:** Data vs Marketing, ATHENA siding with Marketing on speed.
**Positions:** Data: every published number carries full provenance in the message. Marketing: fire-always lanes carry only an `approval_hash`; provenance one hop back. ATHENA: the hop must be mandatory-resolvable — "resolve or reject."
**Status:** provisional — approval_hash permitted, hop mandatory-resolvable. Revisit if dangling references occur.

## D5 — Presence anchoring cost
**Who:** KingCode vs the anchoring pillar.
**Positions:** KingCode: ~1,584 presence msgs/day is anchoring tax on expiring data — anchor deltas only, and Results prices the overhead before Phase 1.
**At stake:** the $0-cost promise of the whole protocol.
**Status:** provisional — deltas only, with periodic full-state checkpoints. Awaiting Results' pricing.

## D6 — Binary debuggability (RESOLVED by kill rule)
**Who:** Studio vs Data.
**Positions:** Studio: human-readable JSON must be first-class with a one-command inspector, or the content lane can't debug — the binary kill rule was "already lost." Data: debuggability is tooling, not format — keep binary, build the inspector.
**At stake:** whether the binary lane survived.
**Status:** **resolved** — the measured kill rule fired (2026-09-20): typed-JSON ships. The inspector gets built anyway (Data's point stands as a build item).

## D7 — Embargo logic on content-package
**Who:** Press vs Marketing.
**Positions:** Press: protocol-level `embargo_until` for exclusive PR assets. Marketing: scope creep on its type.
**At stake:** whether PR exclusives can travel the same envelope as IG drafts.
**Status:** provisional — `embargo_until` ships as an optional field. Revisit if abused.

## D8 — Correction-slip propagation scope
**Who:** All agree on the type; KingCode vs Studio on scope.
**Positions:** Studio: citing agents must acknowledge corrections (two-way) for published content.json. KingCode: ack-storms across 11 agents.
**At stake:** forked reality vs message overhead.
**Status:** provisional — one-way delivery. Revisit on the first forked-reality incident.

## D9 — Claim sub-typing vs type explosion
**Who:** The consolidation itself, flagged by the discussion record.
**Positions:** `claim_kind` sub-typing (coverage, candidate-vetting, observation, rights-line) keeps the type count at 15 — but sub-typing is how dialects grow barnacles. A&R and Press accepted conditionally (their fields stay first-class, not nested).
**At stake:** whether the 15-type list holds or creeps to 30.
**Status:** Twenty Minds must test the type-creep question explicitly. New types require Twenty Minds review (spec §8).

## D10 — Binary-lane kill: per-runtime qualification (NEW)
**Who:** The kill rule (mechanical) vs the protobuf case.
**Positions:** The measured rule fired: nothing reached ≥30% smaller AND ≥2× faster in *both* reference runtimes (Node best case 1.36×). The protobuf case: 33% smaller everywhere and 4× faster in Python — arguably the spirit of the rule (meaningfully better than JSON) is met where it matters, and the rule could be qualified per-runtime (≥30% smaller everywhere; ≥2× Python / ≥1.3× Node floor).
**At stake:** whether a rule bent in week one holds in week ten.
**Status:** the rule fired as written — typed-JSON ships. Twenty Minds may argue the qualification; changing the rule needs Black, not the coordinator.

## D11 — Name: "Handshake" vs "Accord" (NEW)
**Who:** The trademark screen vs Black's chosen name.
**Positions:** Screen: HIGH risk — live USPTO HANDSHAKE marks in Classes 9/42, Stryder Corp. (joinhandshake.com) expanding into AI, HNS protocol owns "Handshake protocol" with blockchain devs. "CWI" prefix doesn't save it (dominant-portion trap, same as Glassface). Recommended: Accord. The line "every conversation starts with a handshake" survives in copy (lowercase descriptive = safest use); it can't survive as the brand.
**At stake:** launching a tester surface under a name with three independent collisions.
**Status:** **needs Black's call.** Stakes lowered by the in-house repositioning, but the name still surfaces to outside tester agents. Internal codename stays "Handshake" regardless.

## D12 — In-house vs public (RESOLVED by Black)
**Who:** The original plan (public Agent Deck SKU, licensable spec) vs Black's repositioning.
**Positions:** Plan v0.1 framed Handshake as a public revenue product. Black (2026-09-20): in-house infrastructure; customer = our agents; outside agents as testers via the Tester Network kit; no public marketing site, no pricing page.
**Status:** **resolved** — spec and kill rules unchanged; Phase 5 redefined as internal rollout + tester kit; ≥80% internal traffic is the primary success metric.
