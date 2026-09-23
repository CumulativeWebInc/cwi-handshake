# Handshake v0.1 — typed agent message protocol

Every conversation starts with one. **16 wire types** (claim, approval-request, presence,
placement-proof, kill-signal, resource-offer, …), strict typed JSON, RFC 8785
canonicalization byte-identical across JavaScript and Python zero-dependency validators.

- **Live docs:** https://cumulativewebinc.github.io/cwi-handshake/
- **Spec:** [spec/SPEC-v0.1.md](spec/SPEC-v0.1.md)

## Quick start

```bash
git clone https://github.com/CumulativeWebInc/cwi-handshake.git
cd cwi-handshake
# JavaScript
node --input-type=module -e "
import { validate } from './validators/js/validate.js';
import { readFileSync } from 'node:fs';
console.log(validate(JSON.parse(readFileSync('examples/claim.json','utf8'))))"   # {"ok":true}
# Python
cd validators/py && python3 -c "
from validate import validate
import json
print(validate(json.load(open('../../examples/claim.json'))))"   # {'ok': True}
```

## Layout

| Path | What |
|---|---|
| `schemas/` | 17 JSON Schemas: envelope + 16 message types |
| `validators/js/` | Zero-dep JS validator + RFC 8785 canonicalization |
| `validators/py/` | Zero-dep Python validator + canonicalization |
| `examples/` | 16 worked messages, validator-pinned |
| `spec/` | SPEC-v0.1.md, trade-offs, recorded dissent |
| `COST-CEILING.md` | Measured cost ceiling: 0.0087 ms/msg (Node), 0.0268 ms (Python) |

## Test receipts (full build, 2026-09-20)

- Validators: 215/215 · Anchoring: 15/15 (seal → attest → verify; tamper drill red-as-required) · Full suite: 546/546

## Honest limits

v0.1 ships the protocol + validators. The external tester kit is deliberately **held** until the
internal dogfood gate closes (≥80% of CWI agent traffic on Handshake within 14 days). Strict dialect:
unknown fields are rejected, not ignored. Validators are normative over schemas.

Built by Cumulative Web Inc. · Contact: hp@cumulativeweb.com · © 2026 Cumulative Web Inc.
Free to use with attribution; commercial licensing via hp@cumulativeweb.com.
