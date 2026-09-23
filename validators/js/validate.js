#!/usr/bin/env node
// Handshake v0.1 — reference validator (JS, zero dependencies).
// Implements SPEC-v0.1.md §3 (global envelope) and §4 (the 15 message types).
//
//   validate(message[, opts]) -> { ok: true }
//                              | { ok: false, errors: [{ path, reason }] }
//
// Errors accumulate: every violation is reported, in deterministic field
// order. `message` may be a parsed object or a JSON string.
// opts.knownIds (optional Set/Array of msg_id strings) enables the
// dangling-supersedes check; without history the validator only checks
// supersedes *format*.
//
// Uncertainty model (provisional, vina ruling pending — see
// schemas/handshake-0.1/README.md): any field EXCEPT msg_type and version
// may carry {"_unknown": true, "reason": "..."} or {"_na": true,
// "reason": "..."} instead of its typed value. A missing key is a
// validation error; an explicit unknown is data.

'use strict';

const VERSION = '0.1';

// The 16 wire values of msg_type (§4.7 covers two: resource-offer/request).
const TYPES = [
  'claim', 'verdict', 'benchmark-result', 'task-handoff', 'presence',
  'tool-call', 'resource-offer', 'resource-request', 'kill-signal',
  'approval-request', 'result-receipt', 'rights-status', 'placement-proof',
  'content-package', 'build-event', 'correction-slip',
];

const ENVELOPE_FIELDS = ['msg_id', 'msg_type', 'version', 'sender_urn', 'sent_at', 'anchor_ref', 'supersedes'];

const UUID4_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const ISO_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})$/;
const DATE_RE = /^(\d{4})-(\d{2})-(\d{2})$/;

function isUuid4(s) { return typeof s === 'string' && UUID4_RE.test(s); }
function isIso(s) {
  return typeof s === 'string' && ISO_RE.test(s) && !Number.isNaN(Date.parse(s));
}
function isDateOnly(s) {
  if (typeof s !== 'string') return false;
  const m = DATE_RE.exec(s);
  if (!m) return false;
  const y = +m[1], mo = +m[2], d = +m[3];
  if (mo < 1 || mo > 12 || d < 1 || d > 31) return false;
  const dt = new Date(Date.UTC(y, mo - 1, d));
  return dt.getUTCFullYear() === y && dt.getUTCMonth() === mo - 1 && dt.getUTCDate() === d;
}

// Tri-state uncertainty tag. Returns true (valid), or an error string.
function triTagError(v) {
  if (v === null || typeof v !== 'object' || Array.isArray(v)) return 'not-an-object';
  const keys = Object.keys(v);
  const hasU = v._unknown === true;
  const hasN = v._na === true;
  if (!hasU && !hasN) return 'not-a-tag';
  if (hasU && hasN) return 'both _unknown and _na are set; exactly one is allowed';
  for (const k of keys) {
    if (k !== '_unknown' && k !== '_na' && k !== 'reason') return `unexpected key "${k}"`;
  }
  if (!('reason' in v)) return '"reason" is required on an uncertainty tag';
  if (typeof v.reason !== 'string' || v.reason.length === 0) return '"reason" must be a non-empty string';
  return null;
}

// Field descriptor: { t, req, tri, enum, format, min, max, elem, shape, useBound }
//   t: 's' string | 'n' number | 'i' integer | 'b' boolean | 'a' array | 'o' object | 'sn' string|number
//   tri: false disables the uncertainty tag (only msg_type + version).
function checkField(obj, name, d, path, errors) {
  const p = path ? `${path}.${name}` : name;
  const present = Object.prototype.hasOwnProperty.call(obj, name);
  if (!present) {
    if (d.req) errors.push({ path: p, reason: 'required field is missing' });
    return;
  }
  const v = obj[name];
  if (d.tri !== false) {
    const tagErr = triTagError(v);
    if (tagErr === null) return; // explicit unknown is data, not an error
    if (tagErr !== 'not-an-object' && tagErr !== 'not-a-tag') {
      errors.push({ path: p, reason: `invalid uncertainty tag: ${tagErr}` });
      return;
    }
  }
  const badType = (want) => errors.push({ path: p, reason: `expected ${want}` });
  switch (d.t) {
    case 's':
      if (typeof v !== 'string') { badType('string'); return; }
      if (v.length === 0) { errors.push({ path: p, reason: 'string must not be empty' }); return; }
      break;
    case 'n':
      if (typeof v !== 'number' || Number.isNaN(v)) { badType('number'); return; }
      break;
    case 'i':
      if (!Number.isInteger(v)) { badType('integer'); return; }
      break;
    case 'b':
      if (typeof v !== 'boolean') { badType('boolean'); return; }
      break;
    case 'a':
      if (!Array.isArray(v)) { badType('array'); return; }
      break;
    case 'o':
      if (v === null || typeof v !== 'object' || Array.isArray(v)) { badType('object'); return; }
      break;
    case 'sn':
      if (typeof v !== 'string' && typeof v !== 'number') { badType('string or number'); return; }
      if (typeof v === 'string' && v.length === 0) { errors.push({ path: p, reason: 'string must not be empty' }); return; }
      if (typeof v === 'number' && Number.isNaN(v)) { badType('string or number'); return; }
      break;
    default:
      errors.push({ path: p, reason: `internal: unknown descriptor type "${d.t}"` });
      return;
  }
  if (d.format === 'uuid4' && !isUuid4(v)) errors.push({ path: p, reason: 'must be a UUID v4' });
  if (d.format === 'iso' && !isIso(v)) errors.push({ path: p, reason: 'must be an ISO-8601 timestamp' });
  if (d.format === 'date' && !isDateOnly(v)) errors.push({ path: p, reason: 'must be a date (YYYY-MM-DD)' });
  if (d.enum && !d.enum.includes(v)) errors.push({ path: p, reason: `must be one of: ${d.enum.join(', ')}` });
  if (d.const !== undefined && v !== d.const) {
    errors.push({ path: p, reason: `must be exactly ${JSON.stringify(d.const)} (no silent coercion)` });
  }
  if (typeof d.min === 'number' && typeof v === 'number' && v < d.min) errors.push({ path: p, reason: `must be >= ${d.min}` });
  if (typeof d.max === 'number' && typeof v === 'number' && v > d.max) errors.push({ path: p, reason: `must be <= ${d.max}` });
  if (d.t === 'a' && d.elem === 's') {
    v.forEach((e, i) => {
      if (typeof e !== 'string') errors.push({ path: `${p}[${i}]`, reason: 'array element must be a string' });
      else if (e.length === 0) errors.push({ path: `${p}[${i}]`, reason: 'array element must not be empty' });
    });
  }
  if (d.t === 'o' && d.shape) {
    for (const [k, kd] of Object.entries(d.shape)) checkField(v, k, kd, p, errors);
    for (const k of Object.keys(v)) {
      if (!Object.prototype.hasOwnProperty.call(d.shape, k)) {
        errors.push({ path: `${p}.${k}`, reason: 'unknown field (not in v0.1 schema)' });
      }
    }
  }
  if (d.useBound && !(v === 'single-use' || isIso(v))) {
    errors.push({ path: p, reason: 'must be "single-use" or an ISO-8601 expiry timestamp' });
  }
}

// Per-type payload field tables, SPEC §4. Deterministic order.
const FIELDS = {
  'claim': {
    statement: { t: 's', req: true }, source: { t: 's', req: true },
    date: { t: 's', req: true, format: 'date' },
    confidence: { t: 'n', req: true, min: 0, max: 1 },
    claim_kind: { t: 's', enum: ['coverage', 'candidate-vetting', 'observation', 'rights-line'] },
    // coverage (conditional)
    outlet: { t: 's' }, writer: { t: 's' }, url: { t: 's' },
    published_at: { t: 's', format: 'iso' },
    // candidate-vetting (conditional)
    vetting_status: { t: 's', enum: ['pass', 'fail', 'unverifiable'] },
    rights_red_flags: { t: 'a', elem: 's' },
    // observation (conditional)
    metric: { t: 's' }, value: { t: 'n' }, unit: { t: 's' },
    observed_at: { t: 's', format: 'iso' }, provenance: { t: 's' },
    verdict_class: { t: 's', enum: ['verified', 'estimate'] },
    // rights-line (conditional)
    status: { t: 's', enum: ['DOCUMENTED', 'PENDING'] },
    assertion_class: { t: 's', enum: ['independently-documented', 'self-reported'] },
  },
  'verdict': {
    verdict: { t: 's', req: true },
    evidence_refs: { t: 'a', req: true, elem: 's' }, // may be empty, must be present
    dissent: { t: 'a', req: true, elem: 's' },        // may be empty, must be present
  },
  'benchmark-result': {
    method: { t: 's', req: true },
    corpus: { t: 's' }, scan_id: { t: 's' }, // at least one required (cross-field)
    result: { t: 'sn', req: true }, repro_ref: { t: 's', req: true }, error_bars: { t: 's', req: true },
  },
  'task-handoff': {
    task_id: { t: 's', req: true }, from_urn: { t: 's', req: true }, to_urn: { t: 's', req: true },
    acceptance_criteria: { t: 's', req: true }, deadline: { t: 's', req: true, format: 'iso' },
    result: { t: 's', req: true }, mechanism: { t: 's', req: true }, verification: { t: 's', req: true },
    review_date: { t: 's', req: true, format: 'iso' }, kill_rule: { t: 's', req: true },
    run_context_ref: { t: 's', req: true },
  },
  'presence': {
    agent_urn: { t: 's', req: true }, current_task_id: { t: 's', req: true },
    // state enum is provisional (spec names no values) — see schemas README.
    state: { t: 's', req: true, enum: ['active', 'idle', 'offline'] },
  },
  'tool-call': {
    tool: { t: 's', req: true }, args_hash: { t: 's', req: true }, invoked_by: { t: 's', req: true },
    idempotency_key: { t: 's', req: true }, authority_grant: { t: 's', req: true },
    grant_ledger_ref: { t: 's', req: true }, use_bound: { t: 's', req: true, useBound: true },
  },
  'resource-offer': {
    resource_ref: { t: 's', req: true }, terms: { t: 's', req: true },
    offered_by: { t: 's', req: true }, expires_at: { t: 's', req: true, format: 'iso' },
  },
  'resource-request': {
    resource_ref: { t: 's', req: true }, constraints: { t: 's', req: true },
    requested_by: { t: 's', req: true }, expires_at: { t: 's', req: true, format: 'iso' },
  },
  'kill-signal': {
    initiative_id: { t: 's', req: true },
    // trigger carries the measured numbers (D1: notification-only in v0.1).
    trigger: {
      t: 'o', req: true,
      shape: {
        metric: { t: 's', req: true }, value: { t: 'n', req: true },
        observed_at: { t: 's', format: 'iso' },
      },
    },
    issued_by: { t: 's', req: true }, authority_ref: { t: 's', req: true }, kill_rule_ref: { t: 's', req: true },
  },
  'approval-request': {
    subject: { t: 's', req: true }, exact_content: { t: 's', req: true }, channel: { t: 's', req: true },
    requested_by: { t: 's', req: true },
    approval_status: { t: 's', req: true, enum: ['pending', 'approved', 'rejected'] },
    decision_ref: { t: 's' }, // cross-field rule below
    approver: { t: 's', req: true }, approval_hash: { t: 's' }, // D4: hop must be mandatory-resolvable
  },
  'result-receipt': {
    initiative_id: { t: 's', req: true }, result: { t: 'sn', req: true }, receipt: { t: 's', req: true },
    verified_by: { t: 's', req: true }, verified_at: { t: 's', req: true, format: 'iso' },
  },
  'rights-status': {
    item_id: { t: 's', req: true },
    status: { t: 's', req: true, enum: ['DOCUMENTED', 'PENDING'] }, // D3: binary ships in v0.1
    source_ref: { t: 's', req: true },
    assertion_class: { t: 's', req: true, enum: ['independently-documented', 'self-reported'] },
    changed_at: { t: 's', req: true, format: 'iso' }, changed_by: { t: 's', req: true },
  },
  'placement-proof': {
    playlist_id: { t: 's', req: true }, track_id: { t: 's', req: true },
    claim_status: { t: 's', req: true, enum: ['claimed', 'verified', 'retired'] }, // D2 provisional
    observed_at: { t: 's', req: true, format: 'iso' }, evidence_ref: { t: 's', req: true },
    follow_up_due: { t: 's', req: true, format: 'iso' }, follow_up_ref: { t: 's', req: true },
    confidence: { t: 'n', min: 0, max: 1 }, // D2 provisional orthogonal companion
  },
  'content-package': {
    day: { t: 's', req: true, format: 'date' }, id: { t: 's', req: true }, type: { t: 's', req: true },
    media_files: { t: 'a', req: true, elem: 's' }, caption: { t: 's', req: true },
    hashtags: { t: 'a', req: true, elem: 's' }, threads_text: { t: 's', req: true },
    post_order: { t: 'i', req: true }, platform_targets: { t: 'a', req: true, elem: 's' },
    approval_status: { t: 's', req: true, enum: ['pending', 'approved', 'rejected'] },
    asset_checksums: { t: 'a', req: true, elem: 's' },
    embargo_until: { t: 's', format: 'iso' }, // D7 provisional optional
  },
  'build-event': {
    project: { t: 's', req: true },
    stage: { t: 's', req: true, enum: ['discover', 'design', 'build', 'test', 'deploy', 'go-live', 'post-launch'] },
    artifact_ref: { t: 's', req: true },
    tests: {
      t: 'o', req: true,
      shape: { passed: { t: 'i', req: true, min: 0 }, total: { t: 'i', req: true, min: 0 } },
    },
    checkpoint_evidence: { t: 's', req: true },
    gate: { t: 's', req: true, enum: ['passed', 'failed', 'blocked'] },
  },
  'correction-slip': {
    supersedes: { t: 's', req: true, format: 'uuid4' }, // required here (SPEC §4.15); one-way (D8)
    corrected_claim: { t: 's', req: true }, reason: { t: 's', req: true },
    cited_by: { t: 'a', req: true, elem: 's' }, // mandatory list, may be empty
  },
};

// claim_kind -> additionally required fields (SPEC §4.1).
const CLAIM_KIND_REQ = {
  'coverage': ['outlet', 'writer', 'url', 'published_at'],
  'candidate-vetting': ['vetting_status', 'rights_red_flags'],
  'observation': ['metric', 'value', 'unit', 'observed_at', 'provenance', 'verdict_class'],
  'rights-line': ['status', 'assertion_class'],
};

function validateEnvelope(msg, errors) {
  // msg_type and version are dispatch-critical: the uncertainty tag is NOT
  // accepted for them (documented in schemas/handshake-0.1/README.md).
  const ENV = {
    msg_id: { t: 's', req: true, format: 'uuid4' },
    msg_type: { t: 's', req: true, tri: false, enum: TYPES },
    version: { t: 's', req: true, tri: false, const: VERSION },
    sender_urn: { t: 's', req: true },
    sent_at: { t: 's', req: true, format: 'iso' },
    anchor_ref: { t: 's', req: true },
    supersedes: { t: 's', format: 'uuid4' },
  };
  for (const [name, d] of Object.entries(ENV)) checkField(msg, name, d, '', errors);
}

function validate(message, opts) {
  opts = opts || {};
  const errors = [];
  let msg = message;
  if (typeof msg === 'string') {
    try { msg = JSON.parse(msg); }
    catch (e) { return { ok: false, errors: [{ path: '$', reason: `not valid JSON: ${e.message}` }] }; }
  }
  if (msg === null || typeof msg !== 'object' || Array.isArray(msg)) {
    return { ok: false, errors: [{ path: '$', reason: 'message must be a JSON object' }] };
  }
  validateEnvelope(msg, errors);
  const _mt = msg.msg_type;
  const spec = typeof _mt === 'string' ? FIELDS[_mt] : undefined;
  if (spec) {
    const allowed = new Set([...ENVELOPE_FIELDS, ...Object.keys(spec)]);
    for (const k of Object.keys(msg)) {
      if (!allowed.has(k)) errors.push({ path: k, reason: `unknown field (not in the v0.1 ${msg.msg_type} schema)` });
    }
    for (const [name, d] of Object.entries(spec)) checkField(msg, name, d, '', errors);

    // claim_kind sub-type conditionals (SPEC §4.1)
    if (msg.claim_kind !== undefined && CLAIM_KIND_REQ[msg.claim_kind] && triTagError(msg.claim_kind) !== null) {
      for (const f of CLAIM_KIND_REQ[msg.claim_kind]) {
        const d = Object.assign({}, FIELDS.claim[f], { req: true });
        checkField(msg, f, d, '', errors);
      }
    }
    // benchmark-result: corpus and/or scan_id (§4.3 "corpus/scan_id")
    if (msg.msg_type === 'benchmark-result' &&
        !Object.prototype.hasOwnProperty.call(msg, 'corpus') &&
        !Object.prototype.hasOwnProperty.call(msg, 'scan_id')) {
      errors.push({ path: 'corpus', reason: 'at least one of corpus, scan_id is required' });
    }
    // approval-request decision_ref lifecycle rule (§4.9)
    if (msg.msg_type === 'approval-request' && Object.prototype.hasOwnProperty.call(msg, 'approval_status')) {
      const st = msg.approval_status;
      const hasDecision = Object.prototype.hasOwnProperty.call(msg, 'decision_ref');
      if (st === 'pending') {
        if (hasDecision && msg.decision_ref !== 'pending' && triTagError(msg.decision_ref) !== null) {
          errors.push({ path: 'decision_ref', reason: 'must be absent (or "pending") while approval_status is pending' });
        }
      } else if (st === 'approved' || st === 'rejected') {
        if (!hasDecision) {
          errors.push({ path: 'decision_ref', reason: 'decision_ref (message id of the decision) is required once approved/rejected' });
        } else if (msg.decision_ref === 'pending' || triTagError(msg.decision_ref) === null) {
          errors.push({ path: 'decision_ref', reason: 'decision_ref must be a concrete message id once approved/rejected' });
        }
      }
    }
    // build-event: passed <= total
    if (msg.msg_type === 'build-event' && msg.tests && typeof msg.tests === 'object' &&
        Number.isInteger(msg.tests.passed) && Number.isInteger(msg.tests.total) &&
        msg.tests.passed > msg.tests.total) {
      errors.push({ path: 'tests.passed', reason: 'tests.passed must not exceed tests.total' });
    }
    // dangling supersedes (only decidable with history)
    if (opts.knownIds && Object.prototype.hasOwnProperty.call(msg, 'supersedes') &&
        triTagError(msg.supersedes) !== null && isUuid4(msg.supersedes)) {
      const known = opts.knownIds instanceof Set ? opts.knownIds : new Set(opts.knownIds);
      if (!known.has(msg.supersedes)) {
        errors.push({ path: 'supersedes', reason: `supersedes references unknown msg_id ${msg.supersedes}` });
      }
    }
  }
  return errors.length === 0 ? { ok: true } : { ok: false, errors };
}

module.exports = { validate, validateEnvelope, TYPES, VERSION, FIELDS, CLAIM_KIND_REQ };

// CLI: node validate.js <message.json> [known-ids.json]
if (require.main === module) {
  const fs = require('fs');
  const [,, msgFile, knownFile] = process.argv;
  if (!msgFile) { console.error('usage: node validate.js <message.json> [known-ids.json]'); process.exit(2); }
  let raw;
  try { raw = fs.readFileSync(msgFile, 'utf8'); }
  catch (e) { console.error(`cannot read ${msgFile}: ${e.message}`); process.exit(2); }
  let o = undefined;
  if (knownFile) {
    try { o = { knownIds: new Set(JSON.parse(fs.readFileSync(knownFile, 'utf8'))) }; }
    catch (e) { console.error(`cannot read ${knownFile}: ${e.message}`); process.exit(2); }
  }
  console.log(JSON.stringify(validate(raw, o)));
}
