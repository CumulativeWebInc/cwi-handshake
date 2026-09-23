# Handshake — Consolidated Trade-off Tables (Phase 0)

All rows follow the standing shape: option / evidence / cost / risk / time-to-result / fallback.

## T1. Adopt vs build the protocol

| Option | Evidence | Cost | Risk | Time-to-result | Fallback |
|---|---|---|---|---|---|
| **Extend Google A2A** (highest-coverage existing) | A2A v1.0 (2026-03-12, Agentic AI Foundation, 150+ orgs): Agent Cards + Task/Message/Artifact, JWS-signed cards, RFC 8785 canonicalization. Covers ~40–45% of Handshake's four pillars (typed validated messages · binary efficiency · anchored integrity · tool/resource exchange). JSON-only; no claim/verdict/benchmark types; messages unsigned; no batch anchoring. | $0 license (Apache 2.0); high adaptation cost — we'd bolt on everything that makes Handshake Handshake | Building on a 40%-fit foundation means the 60% custom layer dwarfs the adopted core; version drift with the A2A spec | Weeks to a fork that is Handshake in all but name | Ship the A2A Agent Card bridge for edge interop regardless |
| **Adopt MCP as the message layer** | MCP is the dominant tool standard (stable 2025-11-25, Streamable HTTP RC 2026-07-28). Covers ~30–35%: the tool/resource half natively. But agent→tool, not agent→agent; no claim/verdict/benchmark/placement types; schema channels are host-dependent (servers must dual-serialize to text). | $0; moderate | Category error — MCP never models agent-to-agent commitments, receipts, or kill authority | Days to a prototype that answers the wrong question | Carry MCP-shaped payloads inside Handshake messages |
| **Revive FIPA ACL lineage** (agentlex et al.) | FIPA died 2005 (Swiss org dissolved; IEEE last met 2011): unverifiable mentalistic semantics, ontology-agreement overhead, formal semantics ignored in production, web stack ate its transport. ~20–25% coverage, design patterns only. | $0; high credibility cost — building on a lineage the field buried | Zero 2026 adoption; recruiting testers to a dead lineage | Months to rediscover why it died | Steal the performative-taxonomy discipline (our 15 types *are* performatives by another name) |
| **Build Handshake (RECOMMENDED)** | No existing protocol reaches the 80% discovery kill threshold. The defensible gap (Aug-2026 landscape survey): nobody delivers typed meaning graph + observable semantics + canonical hashable bytes + deterministic human rendering + transport independence together. Each element measurable. | $0; build cost is agent time, ~14 days to v0.1 shippable | Fighting A2A/MCP network effects; the "yet another protocol" graveyard (Tokenese: 1.3× larger than terse English, zero adopters) | 14 days to v0.1 (spec + tested reference impl + tester kit) | Edge bridges from day one: A2A Agent Card, MCP content-block carriage, Nostr out-of-band, ERC-8004 identity |

**Decision:** BUILD. Discovery kill rule not triggered.

## T2. Wire encoding

| Option | Evidence | Cost | Risk | Time-to-result | Fallback |
|---|---|---|---|---|---|
| **Protocol Buffers** | Measured 2026-09-20 (40-msg corpus, median of 2000 passes): −33.0% size vs JSON — the ONLY format clearing the 30% bar. Validate pipeline: 4.00× JSON in Python, **1.36× in Node.js** (V8's JSON.parse within ~15% of fastest binary decode). proto3 can't distinguish absent from default (`passed:false` drops off the wire) — needs `optional`/wrappers. | $0; codegen dependency (protoc or protobufjs) — violates the zero-dep preference for the reference impl | The AND kill rule failed on Node speed; shipping it needs Black to qualify the bar per-runtime — a rule bent in week one is a rule that won't hold in week ten | Days (schema exists as research/synapse.proto) | Keep as documented stretch |
| **CBOR** | −11.7% size; 1.31× Python, 0.89× Node. Fails both bars. | $0 | Ships a "binary" label with JSON-beating on neither axis | — | No |
| **MessagePack** | −12.2% size; 2.16× Python, 0.58× Node (SLOWER than JSON in V8). Fails both bars. Schemaless forever. | $0 | Worst of both: smaller nowhere that matters, slower where it counts | — | No |
| **FlatBuffers** | +2.2% size (BIGGER than JSON on this corpus); 0.15× validate in Python/JS. Zero-copy advantage exists only in native code. | $0 | Negative value in the reference runtimes | — | No |
| **Typed-JSON (RECOMMENDED — kill rule fired)** | Baseline: zero-dep both runtimes, fastest in Node, human-debuggable (Studio's non-negotiable), validators already written in the bench scripts. Costs 33% wire size vs protobuf — on ~300 msgs/day of a few hundred bytes, the absolute cost is noise. | $0 | Forgoes the size win; if traffic ever grows 100×, revisit | Immediate | Protobuf reopens the question if a future Node decoder clears the bar |

**Decision:** kill-rule fired mechanically — binary lane killed, typed-JSON ships. Recorded dissent: Data holds that debuggability is tooling not format (noted; the inspector gets built anyway).

## T3. Anchoring

| Option | Evidence | Cost | Risk | Time-to-result | Fallback |
|---|---|---|---|---|---|
| **EAS off-chain primary (RECOMMENDED)** | Live since 2026-09-18: anchor → verify ANCHORED-OK → tamper drill PASS. $0 measured. refUID hash-chaining already implemented; public mirror + iOS PWA verifier exist. Anyone recomputes the EIP-712 digest and walks the chain. | $0 / 1,000 batches; hours to adapt the batch schema | Self-asserted timestamps; trust concentrated in signing key + repo host | Days | Records are plain EIP-712 signatures — verifiable with any ECDSA library if EAS-the-standard dies |
| **+ OpenTimestamps root stamp (RECOMMENDED extension)** | Measured working Aug 2026: 665-byte proof, 2 s, 4 redundant calendars, $0. Stamp-the-root pattern documented in live 2026 specs. | $0; 1–2 days (`ots` CLI, one cron tick on the chain-head) | 1–6 h to full Bitcoin confirmation (pending proof immediate — the chain *upgrades*, never unverifiable) | 1–2 days | If calendars go dark, the EAS chain is unaffected — additive, never structural |
| **+ ERC-8004 identity binding (RECOMMENDED, owner-gated)** | ERC-8004 mainnet 2026-01-29: Identity/Reputation/Validation registries. Roots attester provenance in the 2026 agent-identity standard; plugs into the house trust_verdict vocabulary. | One-time registration gas + identity action — **queues to Black** | Draft spec; registration counts disputed across sources | When Black approves | Throwaway-key attestations keep working meanwhile |
| EAS on-chain (Base) per batch | ~$1.00 / 1,000 batches by measured gas × min-base-fee math; 2 s finality; easscan indexed | Trivial dollars — but **doctrine cost**: mainnet anchoring needs Black's per-batch signature; no hot wallet, no exceptions | Adopting as primary *reduces* autonomy while adding ~nothing in trust over EAS+OTS | Parked | Keep implemented as optional L2 |
| Sigstore | $0 public good; strongest key-management story (keyless, 10-min certs) | $0 | **Identity model mismatch:** headless agents have no interactive OIDC identity | — | Right tool for release artifacts, not agent loops |
| Nostr / XMTP as anchor | $0, signed, real-time | $0 | **No consensus timestamp** — proves authorship, not when; answers the wrong half | — | Evaluate as *transport* for the tester surface |

**Decision:** EAS off-chain primary + OTS root stamps + ERC-8004 binding (owner-gated). On-chain stays parked.

## T4. Message-type count: 8 vs 15

| Option | Evidence | Cost | Risk | Time-to-result | Fallback |
|---|---|---|---|---|---|
| **8-type sketch** | The original PLAN.md sketch. Clean, tight. | Smallest build surface | **Fails the company's central control plane outright:** no approval-request (needed by 6 of 11 departments), no result-receipt (anti-fraud primitive), no rights-status (Sync↔Affairs gate), no placement-proof (follow-up doctrine). The protocol couldn't run CWI. | — | No |
| **15 types (RECOMMENDED)** | All-agent discussion record 2026-09-20: every department's needs grounded in its charter; 4 merges accepted (asset-manifest, coverage-record, candidate-record, observation → folded with conditions); correction-slip unanimous. | Larger schema surface; 15 JSON Schemas + validators | D9: sub-typing is how dialects grow barnacles — `claim_kind` needs the Twenty Minds type-creep test | Same 14-day window | New types require Twenty Minds review (spec §8) |

**Decision:** 15 types. The 8-type sketch is falsified by the discussion record.

## T5. Presence anchoring: every tick vs deltas

| Option | Evidence | Cost | Risk | Time-to-result | Fallback |
|---|---|---|---|---|---|
| Anchor every heartbeat | Uniform policy, simplest reasoning | ~1,584 presence msgs/day anchored — anchoring tax on data that expires in minutes; threatens the $0 promise (D5) | Cost/complexity with zero evidentiary value | — | No |
| **Anchor deltas only (RECOMMENDED)** | KingCode's dissent: liveness ticks are not evidence; state *changes* are. Results to price overhead before Phase 1. | Small | A missed delta = a gap in the liveness record (mitigated: periodic full-state checkpoints) | Phase 1 | Revisit if the overhead prices out trivial |

## T6. Kill-signal authority (D1 — Black's ruling pending)

| Option | Evidence | Cost | Risk | Time-to-result | Fallback |
|---|---|---|---|---|---|
| **Notification-only v0.1 (PROVISIONAL)** | Results + departments: kills issued only by initiative owner/KingCode/Black; departments fear automated kills on slow outreach lanes (9-day replies vs 7-day rules) | $0; keeps the protocol a notification system in v0.1 | Slower kills; human latency on every trigger | Immediate | — |
| Autonomous numeric kills | ATHENA: pre-registered kill_rule + anchored benchmark-result trigger = the measurement fires the kill; "a kill rule that needs a human is a suggestion" | $0 | A 7-day silence rule kills a 9-day reply lane — the business | Needs Black's ruling | Provisional stands until he rules |
