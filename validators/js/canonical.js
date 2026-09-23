#!/usr/bin/env node
// Handshake v0.1 — RFC 8785 JSON Canonicalization Scheme (JCS), zero dependencies.
//
// THE shared primitive for Handshake v0.1: message_hash = sha256(canonical_bytes), hex.
// Build B (anchoring) and Build C (tests) consume this definition.
//
// Rules implemented from the RFC text (RFC 8785 §3):
//  - §3.2.1: no insignificant whitespace.
//  - §3.2.2.2: strings — \" \\ \b \t \n \f \r; other U+0000–U+001F as \uhhhh
//    with LOWERCASE hex; everything else raw. Lone surrogates are an error.
//  - §3.2.2.3: numbers — ECMAScript Number→String (shortest round-trip);
//    NaN/±Infinity are an error.
//  - §3.2.3: object keys sorted by UTF-16 code units (JS default sort order).
//  - §3.2.4: output is a Unicode string; hash over its UTF-8 bytes.
//
// Note: duplicate object member names cannot exist in a parsed JS value
// (I-JSON forbids them at the producer); JSON.parse keeps the last one.

'use strict';

const crypto = require('crypto');

function assertNoLoneSurrogates(s, what) {
  for (const ch of s) {
    const cp = ch.codePointAt(0);
    if (cp >= 0xD800 && cp <= 0xDFFF) {
      throw new Error(`RFC 8785: lone surrogate in ${what || 'string'} data`);
    }
  }
}

function serNumber(n) {
  if (typeof n !== 'number' || !Number.isFinite(n)) {
    throw new Error('RFC 8785: non-finite numbers are not valid JSON');
  }
  return String(n); // ECMAScript Number→String; String(-0) === "0"
}

function serialize(v) {
  if (v === null) return 'null';
  if (v === true) return 'true';
  if (v === false) return 'false';
  if (typeof v === 'string') {
    assertNoLoneSurrogates(v, 'string');
    return JSON.stringify(v); // escaping matches §3.2.2.2 exactly (lowercase \uhhhh)
  }
  if (typeof v === 'number') return serNumber(v);
  if (Array.isArray(v)) return '[' + v.map(serialize).join(',') + ']';
  if (typeof v === 'object') {
    const keys = Object.keys(v).sort(); // UTF-16 code unit order (§3.2.3)
    return '{' + keys.map((k) => {
      assertNoLoneSurrogates(k, 'property name');
      return JSON.stringify(k) + ':' + serialize(v[k]);
    }).join(',') + '}';
  }
  throw new Error(`RFC 8785: unsupported value of type ${typeof v}`);
}

function canonicalize(value) { return serialize(value); }

function canonicalizeJson(text) { return canonicalize(JSON.parse(text)); }

function messageHash(value) {
  return crypto.createHash('sha256').update(canonicalize(value), 'utf8').digest('hex');
}

// --- RFC 8785 self-test vectors (§3.2.2, §3.2.3, Appendix B) ---
function selftest() {
  const failures = [];
  const eq = (name, got, want) => {
    if (got !== want) failures.push(`${name}: got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`);
  };
  // Appendix B number serialization samples: [input JSON, expected output]
  const NUMBERS = [
    ['0', '0'], ['-0', '0'],
    ['5e-324', '5e-324'], ['-5e-324', '-5e-324'],
    ['1.7976931348623157e+308', '1.7976931348623157e+308'],
    ['-1.7976931348623157e+308', '-1.7976931348623157e+308'],
    ['9007199254740992', '9007199254740992'],
    ['-9007199254740992', '-9007199254740992'],
    ['295147905179352830000', '295147905179352830000'],
    ['9.999999999999997e+22', '9.999999999999997e+22'],
    ['1e+23', '1e+23'],
    ['1.0000000000000001e+23', '1.0000000000000001e+23'],
    ['999999999999999700000', '999999999999999700000'],
    ['999999999999999900000', '999999999999999900000'],
    ['1e+21', '1e+21'],
    ['9.999999999999997e-7', '9.999999999999997e-7'],
    ['1e-6', '0.000001'],
    ['333333333.3333332', '333333333.3333332'],
    ['333333333.33333325', '333333333.33333325'],
    ['333333333.3333333', '333333333.3333333'],
    ['333333333.3333334', '333333333.3333334'],
    ['333333333.33333343', '333333333.33333343'],
    ['-0.0000033333333333333333', '-0.0000033333333333333333'],
    ['1424953923781206.25', '1424953923781206.2'],
    ['1E30', '1e+30'], ['4.50', '4.5'], ['2e-3', '0.002'], ['100.0', '100'],
  ];
  for (const [input, want] of NUMBERS) eq(`number ${input}`, canonicalize(JSON.parse(input)), want);

  // §3.2.2 full example
  const exIn = '{"numbers":[333333333.33333329,1E30,4.50,2e-3,0.000000000000000000000000001],' +
    '"string":"€$\\u000F\\u000aA\'\\u0042\\u0022\\u005c\\\\\\"\\/","literals":[null,true,false]}';
  const exWant = '{"literals":[null,true,false],"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],' +
    '"string":"€$\\u000f\\nA\'B\\"\\\\\\\\\\"/"}';
  eq('§3.2.2 example', canonicalize(JSON.parse(exIn)), exWant);

  // String escapes: short forms + LOWERCASE \uhhhh
  eq('escapes', canonicalize('\u0000\u001f\b\t\n\f\r"\\'), '"\\u0000\\u001f\\b\\t\\n\\f\\r\\"\\\\"');
  eq('lowercase hex', canonicalize('\u000f'), '"\\u000f"');

  // §3.2.3 key sorting (UTF-16 code units): input deliberately scrambled
  const sortIn = '{"\u20ac":"Euro Sign","\\r":"Carriage Return","\ufb33":"Hebrew Letter Dalet With Dagesh",' +
    '"1":"One","\ud83d\ude00":"Emoji: Grinning Face","\u0080":"Control","\u00f6":"Latin Small Letter O With Diaeresis"}';
  const sortWant = '{"\\r":"Carriage Return","1":"One","\u0080":"Control","\u00f6":"Latin Small Letter O With Diaeresis",' +
    '"\u20ac":"Euro Sign","\ud83d\ude00":"Emoji: Grinning Face","\ufb33":"Hebrew Letter Dalet With Dagesh"}';
  eq('§3.2.3 key order', canonicalize(JSON.parse(sortIn)), sortWant);

  // No whitespace; nested sorting; array order preserved
  eq('nesting', canonicalize({ b: 1, a: { d: 2, c: 3 }, arr: [3, 2, 1] }),
    '{"a":{"c":3,"d":2},"arr":[3,2,1],"b":1}');

  // Errors
  for (const [name, fn] of [
    ['lone surrogate throws', () => canonicalize('\ud800')],
    ['NaN throws', () => canonicalize(NaN)],
    ['Infinity throws', () => canonicalize(Infinity)],
    ['undefined throws', () => canonicalize(undefined)],
  ]) {
    try { fn(); failures.push(`${name}: did not throw`); } catch (e) { /* expected */ }
  }
  return failures;
}

module.exports = { canonicalize, canonicalizeJson, messageHash, selftest };

// CLI: node canonical.js <file.json> [--hash] | node canonical.js --selftest
if (require.main === module) {
  const fs = require('fs');
  const args = process.argv.slice(2);
  if (args.includes('--selftest')) {
    const failures = selftest();
    if (failures.length) {
      for (const f of failures) console.error('FAIL ' + f);
      process.exit(1);
    }
    console.log(`RFC 8785 selftest: all vectors pass (${process.version})`);
    process.exit(0);
  }
  const file = args.find((a) => !a.startsWith('--'));
  if (!file) { console.error('usage: node canonical.js <file.json> [--hash] [--selftest]'); process.exit(2); }
  let text;
  try { text = fs.readFileSync(file, 'utf8'); }
  catch (e) { console.error(`cannot read ${file}: ${e.message}`); process.exit(2); }
  try {
    const value = JSON.parse(text);
    console.log(args.includes('--hash') ? messageHash(value) : canonicalize(value));
  } catch (e) { console.error(`error: ${e.message}`); process.exit(1); }
}
