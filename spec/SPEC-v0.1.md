# Handshake — Spec v0.1 (Draft)

**Status:** Phase 0 synthesis, 2026-09-20. Precedes Twenty Minds review and Black's two rulings (D1 kill authority, name).
**Positioning (Black, 2026-09-20):** in-house infrastructure. Customer = CWI's own agent traffic. Outside agents engage as testers via the CWI Tester Network kit. No public marketing site, no pricing page.
**Name note:** "Handshake" is Black's chosen name and the internal codename. Trademark screen: HIGH risk (live USPTO HANDSHAKE marks in Classes 9/42; Stryder Corp. joinhandshake.com expanding into AI; HNS protocol owns "Handshake protocol" with blockchain devs). Recommended fallback: **Accord**. Black's call pending — the protocol design is name-independent.

## 1. What Handshake is

A typed message dialect for CWI's agents: a fixed set of versioned message shapes, machine-validated before they land anywhere, encoded as typed-JSON, with message batches hash-anchored so any agent (and any outside tester) can verify integrity and provenance. Malformed messages are rejected at the door — they never enter memory, never trigger actions.

**The one-sentence thesis:** agents garble each other because messages are loose; Handshake makes looseness a validation error.

## 2. Design principles (each earned by the Phase 0 precedent sweep)

1. **Strict envelope, prose inside the task.** The interface contract (fields, types, required-ness) is rigid; the claim's statement content may be prose. (Confirmed by the Aug-2026 multi-agent survey: structure the interface contract, allow natural-language task specification.)
2. **Beat terse English + JSON Schema or don't ship.** A constructed symbolic surface can *lose* to the incumbent (Tokenese: 1.30–1.31× larger than terse English, zero adopters, archived 2026-07). Every encoding decision is measured, not asserted.
3. **Ride the envelope, don't rebuild it.** Every surviving protocol owns discovery/transport/tool-call; every death tried to be the whole stack. Handshake payloads travel as A2A DataParts / MCP content blocks on the tester surface. (Prior-languages lesson 2.)
4. **The dogfood metric is the forcing function.** KQML died of interop indifference ("no benefit to research groups in focusing on interop" — Finin). Handshake's ≥80% internal traffic in 14 days is the adoption forcing function KQML never had. No tester-surface launch before it's green internally.
5. **Self-describing at the byte level.** MCP's host-dependence caution: schema-bearing side channels get dropped in transit. Every message carries its own schema identity (`msg_type` + `version`) and explicit field presence. No reliance on host-preserved headers.
6. **Handoff ≠ tool-call.** A handoff is a *control transfer* (run ownership moves; message carries run continuity). A tool-call is a *bounded capability grant* (caller retains control; message carries the authority-grant chain). Different authority transitions, different semantics — never collapsed into one "do this." (OpenAI Agents SDK precedent, 2026.)
7. **Uncertainty is explicit and distinct from absence.** Required fields are always present; epistemically uncertain values use tagged states (`value | unknown | not_applicable`) with reason/evidence. A *missing key* is a validation error; an *explicit unknown* is data. (Converging 2026 precedent: "nullable + always required keeps the FSM total"; A2A's explicit TASK_STATE_AUTH_REQUIRED; MCP's isError correction loop. Vina's ruling on type-system vs envelope placement is pending — provisional: type-system tri-state.)
8. **Anchoring is the differentiator.** A2A v1.0 signs only the Agent Card — messages, parts, and artifacts are unsigned and carry no authority attribution. Handshake's hash-chained per-batch anchoring fills exactly that gap: verification of *what was said* and *under whose authority*.

## 3. Global envelope (all message types)

Every message carries:

| Field | Required | Meaning |
|---|---|---|
| `msg_id` | yes | Unique message identifier (UUID v4) |
| `msg_type` | yes | One of the 16 wire types below |
| `version` | yes | Spec version the message conforms to (`"0.1"`) |
| `sender_urn` | yes | Sender agent URN (e.g. `agent:MUSE_CWI`) |
| `sent_at` | yes | ISO-8601 timestamp of sending |
| `anchor_ref` | yes | Batch attestation reference (populated at batch seal; `pending` before) |
| `supersedes` | no | `msg_id` of the message this replaces (append-only history; nothing is edited) |

## 4. Message types (16 wire types)

> §4.7 defines **two** wire types (`resource-offer`, `resource-request`); the remaining sections define one each, for 16 total. This was a spec-draft counting error (the draft said 15), corrected at build integration 2026-09-20 — no wire change, the validator already treated them as distinct types.

### 4.1 claim
General assertion. `claim_kind` sub-types carry kind-specific required fields (the tight-dialect answer to type explosion).
- Base required: `statement`, `source`, `date`, `confidence`
- `claim_kind=coverage`: + `outlet`, `writer`, `url`, `published_at`
- `claim_kind=candidate-vetting`: + `vetting_status` (pass/fail/unverifiable), `rights_red_flags[]`
- `claim_kind=observation`: + `metric`, `value`, `unit`, `observed_at`, `provenance`, `verdict_class` (verified/estimate)
- `claim_kind=rights-line`: + `status` {DOCUMENTED,PENDING}, `assertion_class` (independently-documented/self-reported)

### 4.2 verdict
A decision with its evidence and its dissent. Required: `verdict`, `evidence_refs[]`, `dissent[]` (may be empty, must be present).

### 4.3 benchmark-result
A measurement with its method and repro. Required: `method`, `corpus`/`scan_id`, `result`, `repro_ref`, `error_bars`. (A benchmark without repro instructions is an anecdote.)

### 4.4 task-handoff — CONTROL TRANSFER
Run ownership moves from one agent to another. Carries run continuity. Required: `task_id`, `from_urn`, `to_urn`, `acceptance_criteria`, `deadline`, `result`, `mechanism`, `verification`, `review_date`, `kill_rule`, `run_context_ref` (continuity pointer — what the new owner needs to proceed).

### 4.5 presence
Liveness. Required: `agent_urn`, `current_task_id`, `state`. Semantics: preserve-not-wipe (a heartbeat never destroys state it didn't read — the 2026-09-17 incident, encoded). Anchoring: deltas only, not every tick (D5 — ~1,584 msgs/day is anchoring tax on expiring data; Results to price overhead before Phase 1).

### 4.6 tool-call — BOUNDED CAPABILITY GRANT
One agent invokes a capability. Caller retains control. Required: `tool`, `args_hash`, `invoked_by`, `idempotency_key`, `authority_grant` (the capability-scoped grant, reproduced fact), `grant_ledger_ref` (position in the hash-chained ledger — replay detection), `use_bound` (expiry or single-use). Open: oracle-vs-carried-claims (pj-qx reply pending) — provisional: carried claims + chain position, with the oracle question revisited before the tester-surface launch.

### 4.7 resource-offer / resource-request (two wire types)
Capability/material advertisement and requests. Required: `resource_ref`, `terms`/`constraints`, `offered_by`/`requested_by`, `expires_at`. `resource-offer` carries `offered_by`; `resource-request` carries `requested_by`.

### 4.8 kill-signal — PROVISIONAL: notification-only
Declares a kill. Required: `initiative_id`, `trigger` (measured numbers), `issued_by`, `authority_ref`, `kill_rule_ref`. **D1 unresolved:** Results + departments say kills are issued only by initiative owner/KingCode/Black (programmatic kill only from pre-registered kill_rules); ATHENA says pre-registered numeric rules should fire autonomously. **v0.1 ships notification-only** — the signal announces intent with its measured trigger; execution stays human until Black rules.

### 4.9 approval-request
The company's central control plane (exact-copy approval gate). Required: `subject`, `exact_content`, `channel`, `requested_by`, `approval_status` (pending/approved/rejected), `decision_ref` (message id of the decision), `approver`. Publishing lanes may carry `approval_hash` referencing the approved request, with the hop mandatory-resolvable (D4 — ATHENA's "resolve or reject").

### 4.10 result-receipt
The anti-fraud primitive ("verified or it didn't happen" as a schema constraint). Required: `initiative_id`, `result`, `receipt` (ledger event id / URL / hash / confirmation), `verified_by`, `verified_at`. The only message type that can close a task-handoff.

### 4.11 rights-status
The Sync↔Affairs DOCUMENTED/PENDING gate, machine-enforced. Required: `item_id`, `status` {DOCUMENTED,PENDING}, `source_ref`, `assertion_class`, `changed_at`, `changed_by`. Append-only: superseded by new messages, never edited. **D3 unresolved:** Affairs refuses any third state; Sync wants "in-process." Escalated to Black — v0.1 ships the binary.

### 4.12 placement-proof
Placement claims with the follow-up clock. Required: `playlist_id`, `track_id`, `claim_status` {claimed,verified,retired}, `observed_at`, `evidence_ref`, `follow_up_due`, `follow_up_ref`. (The 2026-09-20 follow-up doctrine, typed. D2 unresolved: Data wants confidence × lifecycle as orthogonal fields; Radio wants the single three-state field. Design session before Phase 1 — provisional: the three-state field ships, with `confidence` as a separate optional field so Data's scoreboard can compute the orthogonal view.)

### 4.13 content-package
The standing content.json contract as a message. Required: `day`, `id`, `type`, `media_files[]`, `caption`, `hashtags[]`, `threads_text`, `post_order`, `platform_targets[]`, `approval_status`, `asset_checksums[]` (Studio's non-optional checksum — Black approves exact media; exactness needs a hash). `embargo_until` optional (D7 — Press's embargo logic accepted as optional field; Marketing's scope concern noted).

### 4.14 build-event
Stage-gate evidence for the 6-stage lifecycle playbook. Required: `project`, `stage` (discover/design/build/test/deploy/go-live/post-launch), `artifact_ref`, `tests` (passed/total), `checkpoint_evidence`, `gate` (passed/failed/blocked).

### 4.15 correction-slip
Corrections chase their citations. Required: `supersedes` (message id), `corrected_claim`, `reason`, `cited_by[]` (propagation list — mandatory). Open (D8): one-way delivery vs two-way acknowledgment. Provisional: one-way delivery with the ack question revisited if forked-reality incidents occur.

## 5. Wire format: typed-JSON

**The binary lane was killed by its own kill rule** (measured 2026-09-20, 40-message corpus, median of 2000 passes): only Protobuf cleared the ≥30% size bar (−33.0%); nothing reached ≥2× validation speed in Node.js (protobuf-static 1.36× best case; V8's JSON.parse is within ~15% of the fastest binary decode). The one allowed rework was spent inside the analysis. Per standing law the rule fires: **v0.1 ships typed-JSON.**

- JSON Schema per message type, versioned with the spec (`schemas/handshake-0.1/`).
- Reference validators: JS zero-dep + Python (the bench scripts already contain working validators).
- Canonicalization: RFC 8785 JSON Canonicalization for hashing/signing (same primitive A2A uses for its JWS Agent Cards).
- The `.proto` schema (research/synapse.proto → renamed `handshake.v1` in Phase 1) is retained as the canonical field structure and the documented binary stretch: if a future Node decoder clears the bar, the binary question reopens without a redesign.

## 6. Anchoring

- **Primary:** EAS off-chain attestations (house L1, $0, live since 2026-09-18). Batch schema: `batchRoot` (Merkle root over the batch's messages), `batchId`, `firstMsgTime`, `lastMsgTime`, `msgCount`, `batchCid`. `refUID` chains batch→batch. Bodies stay in CWI storage; anchors carry roots, counts, CIDs only.
- **Extension:** daily OpenTimestamps stamp of the chain-head (Bitcoin-finality timestamps at $0; closes the sidecar's self-asserted-time weakness; additive — the EAS chain is unaffected if calendars go dark).
- **Identity:** ERC-8004 agent-identity binding (owner-gated: registration is gas + identity action → Black's call). Maps each attester address to its agent NFT; roots provenance in the 2026 agent-identity standard.
- **Open (diviner reply pending):** the batch-boundary problem — a perfectly chained attestation of an incomplete batch verifies perfectly. Do not finalize batching policy until answered; provisional: batcher attests `msgCount` and per-message inclusion proofs ship with the batch.

## 7. Transport (in-house)

Internal: the existing CWI runtime surfaces (memory pool, task logs, gear ledger) carry Handshake messages; the validator gates writes. Tester surface (CWI Tester Network kit): Handshake payloads exposed as A2A DataParts and MCP content blocks so outside agents can speak the dialect without adopting the stack. Nostr/XMTP evaluated as external transports only — not anchors.

## 8. Versioning

- Spec versions are semver (`0.1`, `0.2` …). `version` is required on every message.
- Additive changes (new optional fields, new message types) bump minor. Any change to a required field or the envelope bumps major. Validators reject messages whose `version` they don't implement — no silent coercion.
- The 16-type list is guarded by D9: sub-typing (`claim_kind`) is how dialects grow barnacles. New types require a Twenty Minds review.

## 9. Kill rules (restated, standing)

- **Discovery (FIRED-clean):** existing protocol ≥80% → extend, don't build. Highest was A2A at ~40–45%. Gate passes.
- **Binary lane (FIRED):** ≥30% smaller AND ≥2× faster — missed; rework spent; binary lane killed, typed-JSON ships.
- **Build/Test:** full test suite green (target: every message type round-trips; interop test: two agents exchange all 16 types; validator rejects every malformed fixture).
- **Deploy:** ≥80% of CWI inter-agent message traffic on Handshake within 14 days of internal launch — miss, rework adoption once, then kill.
- **Overall:** v0.1 shippable (spec + tested reference implementation + tester kit) within 14 days of Phase 1 start — miss, rework scope, not the deadline.
- Intervention checkpoints at 50% and 75% of every phase window.

## 10. Open items (explicit, owned)

| # | Item | Owner | Blocks |
|---|---|---|---|
| D1 | Kill-signal authority: autonomous numeric kills vs owner-issued only | Black | Autonomous execution (v0.1 ships notification-only) |
| D2 | Verification-state cardinality: orthogonal fields vs single three-state | Design session | placement-proof final shape |
| D3 | Rights binary vs third "in-process" state | Black | rights-status final shape (v0.1 ships binary) |
| D8 | Correction-slip: one-way delivery vs two-way ack | Revisit on incident | Nothing in v0.1 |
| Name | "Handshake" (HIGH trademark risk) vs "Accord" | Black | Public/tester-surface branding only |
| vina | Tri-state placement: type-system vs envelope | Reply pending (re-check 2026-09-21) | Schema-shape finalization |
| diviner | Batch-boundary / completeness construction | Reply pending (re-check 2026-09-21) | Batching policy finalization |
| pj-qx | Oracle vs carried claims for tool-call auth | Reply pending (re-check 2026-09-21) | tool-call auth finalization |
