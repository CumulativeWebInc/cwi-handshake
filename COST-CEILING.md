# Handshake v0.1 — Cost Ceiling (the Devil's accountant's condition)

**Date:** 2026-09-20 (re-measured 12:18 UTC) · **Lane:** BUILD C · **Status:** measured on this VM, $0 spent.
**Rule it satisfies:** Twenty Minds gating item 2 — "a per-1,000-message cost ceiling in the Phase-1 plan."
**Feeds:** Results' D5 presence-pricing lane.
**Measured against:** Build A `validators/js|py/validate.js` + Build B `anchor/lib/batch.js`
batch construction (canonicalize + SHA-256 leaves + binary Merkle tree + batchCid).

## 1. What was measured (this VM, zero dependencies)

Bench: `instrumentation/bench-cost.js` (Node) + `instrumentation/bench_cost.py` (Python).
OTS: live calibration stamps from the public calendars (`instrumentation/ots-calibration.json`).

| Input | Node | Python (conservative lane) |
|---|---|---|
| validator CPU per message | 0.0087 ms | 0.0268 ms |
| seal per batch (10 / 50 / 200 msgs) | 0.33 / 1.44 / 4.45 ms | 1.34 / 6.38 / 25.39 ms |
| seal amortized per message | 0.022 – 0.033 ms | 0.127 – 0.134 ms |
| batch attestation core bytes (10 / 50 / 200) | 722 / 2,282 / 8,133 B | 671 / 2,271 / 8,272 B |
| sealed batch file w/ inclusion proofs (Build B seal.js, 8 msgs) | 4,534 B (~567 B/msg) | — |
| average message bytes (worked examples) | 544 B | 570 B |
| validator p50 / p99 (meter, live traffic shape) | 0.020 / 0.84 ms | — |

OTS stamp: pending commitments measured live — alice 137 B, bob 205 B.
A completed (Bitcoin-attested) single-digest proof is dominated by the 80-byte
block header + merkle path + ops: **≈1.1–2.0 KB** (format-based estimate, labeled as such).

Note: the "batch attestation core" is the meter-style record (batchId, batchRoot,
batchCid, msgCount, messageIds, times) — what gets anchored. The "sealed batch file"
is Build B's full `seal.js` output including per-message leaf hashes and Merkle
inclusion proofs — what gets stored for verification. Both are measured; the
ceilings below cover each.

## 2. Per-1,000-message cost model (conservative lane, batch size 50)

| Cost | Per 1,000 messages | Per 1M messages |
|---|---|---|
| validate CPU | 27 ms | 27 s |
| seal CPU (amortized) | 128 ms | 128 s |
| **total CPU** | **≈155 ms** | **≈155 s (≈2.6 CPU-min)** |
| message storage | 570 KB | 570 MB |
| sealed-batch storage w/ proofs (20 batches × ~28 KB) | 567 KB | 567 MB |
| **total storage** | **≈1.1 MB** | **≈1.1 GB** |
| OTS stamps (1/day, fixed) | +2 KB/day | +2 KB/day |

At the projected internal scale (~10k agent messages/day, the dogfood fleet):
**~1.6 CPU-seconds/day, ~11 MB/day storage, one 2 KB stamp/day.**

## 3. Converted to dollars

- **Licenses / services: $0.** Validator (Build A) and batch construction (Build B)
  are zero-dependency code we own; EAS off-chain attestations are $0 (house L1, no gas);
  OTS stamps are $0 (public calendars). Stated plainly: there is no per-message
  vendor meter anywhere in v0.1.
- **Compute:** 2.6 CPU-minutes per 1M messages. On this existing VM the marginal cost
  is $0. On commodity cloud ($0.02/vCPU-hour) it would be ≈$0.0009 per 1M messages —
  four orders of magnitude below any pricing conversation.
- **Storage:** ~1.1 GB per 1M messages ≈ $0.025/month on commodity object storage.
  Effectively $0 at our scale.
- **Maintainer time (the honest cost):** the dominant line item. Validator upkeep
  (schema changes, new message types), the OTS calendar watch (if calendars go dark,
  stamps degrade gracefully — the EAS chain is unaffected), and the inspector that
  recomputes roots. Estimated at **a few hours per quarter** once the schemas freeze;
  higher during Phase 1 while the three peer replies (vina/diviner/pj-qx) may move
  wire shapes. This is the cost the ceiling really guards: **complexity, not compute.**

## 4. The ceiling proposal (v0.1 must stay under these, or the lane reworks)

Set at ≈5× the measured medians, rounded up — headroom for slower hosts, none for bloat:

| Ceiling | Value | Measured basis |
|---|---|---|
| validate p99 per message | **≤ 1.0 ms** | median 0.0087–0.0268 ms |
| seal p99 per 50-msg batch | **≤ 35 ms** | median 1.44 ms (node) / 6.38 ms (py) |
| sealed batch file | **≤ 1 KB / message** | ~567 B/msg (Build B seal.js, 8-msg batch) |
| storage per 1,000 messages | **≤ 1.5 MB** | ~1.1 MB (messages + proofs) |
| daily OTS stamp | **≤ 4 KB** | 137–205 B commitment, ≤2 KB completed proof |
| validator reject-rate alert | **> 5% sustained** pages the lane | protocol misuse or a bad schema push |

**Kill-adjacent rule:** if any ceiling is breached on two consecutive weekly measurements,
the batching or schema design reworks — the cost model is a design constraint, not a report.

## 5. What this means for D5 (presence pricing)

Presence is the highest-frequency type (~1,584 msgs/day projected). At 570 B/message,
presence alone costs ≈0.9 MB/day storage and ≈0.35 CPU-seconds/day — negligible.
The D5 question was never about bytes; it was about **anchoring tax on expiring data**.
Recommendation carried to Results: presence heartbeats anchor **deltas only** (SPEC §4.5),
and the meter's `per_type` counters will show the exact presence share of traffic from day one.
