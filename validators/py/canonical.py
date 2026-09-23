#!/usr/bin/env python3
"""Handshake v0.1 — RFC 8785 JSON Canonicalization Scheme (JCS), zero dependencies.

THE shared primitive for Handshake v0.1: message_hash = sha256(canonical_bytes), hex.
Mirrors validators/js/canonical.js exactly; run-checks.sh proves byte equality.

Rules implemented from the RFC text (RFC 8785 §3):
  - §3.2.1: no insignificant whitespace.
  - §3.2.2.2: strings — \\" \\\\ \\b \\t \\n \\f \\r; other U+0000–U+001F as \\uhhhh
    with LOWERCASE hex; everything else raw. Lone surrogates are an error.
  - §3.2.2.3: numbers — ECMAScript Number→String (shortest round-trip);
    NaN/±Infinity are an error. Implemented by hand from repr() so Python
    never emits its own number syntax.
  - §3.2.3: object keys sorted by UTF-16 code units (NOT Python code points).
  - §3.2.4: output is a Unicode string; hash over its UTF-8 bytes.

Duplicate object member names in parsed input: rejected (I-JSON forbids them).
"""

import hashlib
import json
import math
import sys


# ---------------------------------------------------------------- internals

def _check_no_lone_surrogates(s, what="string"):
    for ch in s:
        o = ord(ch)
        if 0xD800 <= o <= 0xDFFF:
            raise ValueError("RFC 8785: lone surrogate in %s data" % what)


def _utf16_units(s):
    """Key for UTF-16 code-unit ordering (§3.2.3)."""
    units = []
    for ch in s:
        o = ord(ch)
        if o < 0x10000:
            units.append(o)
        else:
            o -= 0x10000
            units.append(0xD800 + (o >> 10))
            units.append(0xDC00 + (o & 0x3FF))
    return units


_SHORT_ESCAPES = {
    '"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f",
    "\n": "\\n", "\r": "\\r", "\t": "\\t",
}


def _ser_str(s):
    _check_no_lone_surrogates(s, "string")
    out = ['"']
    for ch in s:
        esc = _SHORT_ESCAPES.get(ch)
        if esc is not None:
            out.append(esc)
        elif ord(ch) < 0x20:
            out.append("\\u%04x" % ord(ch))  # lowercase hex, §3.2.2.2
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _ser_num(f):
    """ECMAScript Number→String (§3.2.2.3) built from the shortest round-trip
    digits of repr(). Raises on NaN/±Infinity."""
    if isinstance(f, bool):
        raise ValueError("RFC 8785: booleans are not numbers")
    f = float(f)
    if math.isnan(f) or math.isinf(f):
        raise ValueError("RFC 8785: non-finite numbers are not valid JSON")
    if f == 0:
        return "0"  # -0.0 included
    neg = math.copysign(1.0, f) < 0
    d = repr(abs(f))  # shortest round-trip, C-style exponent
    if "e" in d:
        mant, _, exp_s = d.partition("e")
        exp = int(exp_s)
    else:
        mant, exp = d, 0
    if "." in mant:
        ip, _, fp = mant.partition(".")
        digits = ip + fp
        e10 = exp - len(fp)
    else:
        digits = mant
        e10 = exp
    s = str(int(digits))          # strip leading zeros; nonzero guaranteed
    t = len(s) - len(s.rstrip("0"))
    s = s.rstrip("0")
    k = len(s)
    n = k + e10 + t              # value = s × 10^(n-k)
    if k <= n <= 21:
        out = s + "0" * (n - k)
    elif 0 < n <= 21:
        out = s[:n] + "." + s[n:]
    elif -6 < n <= 0:
        out = "0." + "0" * (-n) + s
    else:
        out = s[0]
        if k > 1:
            out += "." + s[1:]
        e = n - 1
        out += "e" + ("+" if e > 0 else "-") + str(abs(e))
    return ("-" if neg else "") + out


def _serialize(v):
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, str):
        return _ser_str(v)
    if isinstance(v, bool):
        raise ValueError("unreachable")
    if isinstance(v, int):
        try:
            return _ser_num(float(v))
        except OverflowError:
            raise ValueError("RFC 8785: number out of double range")
    if isinstance(v, float):
        return _ser_num(v)
    if isinstance(v, list):
        return "[" + ",".join(_serialize(x) for x in v) + "]"
    if isinstance(v, dict):
        for k in v:
            if not isinstance(k, str):
                raise ValueError("RFC 8785: object keys must be strings")
            _check_no_lone_surrogates(k, "property name")
        items = sorted(v.items(), key=lambda kv: _utf16_units(kv[0]))
        return "{" + ",".join(_ser_str(k) + ":" + _serialize(val)
                              for k, val in items) + "}"
    raise ValueError("RFC 8785: unsupported value of type %s" % type(v).__name__)


def _no_dupes(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise ValueError("duplicate object member: %r" % (k,))
        obj[k] = v
    return obj


# ---------------------------------------------------------------- public API

def canonicalize(value):
    """RFC 8785 canonical form of a parsed JSON value → str."""
    return _serialize(value)


def canonicalize_json(text):
    """RFC 8785 canonical form of JSON text → str (rejects duplicate keys)."""
    return canonicalize(json.loads(text, object_pairs_hook=_no_dupes))


def message_hash(value):
    """sha256 over the UTF-8 bytes of the canonical form → lowercase hex."""
    return hashlib.sha256(canonicalize(value).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- self-test

def selftest():
    """RFC 8785 vectors (§3.2.2, §3.2.3, Appendix B). Returns failure list."""
    failures = []

    def eq(name, got, want):
        if got != want:
            failures.append("%s: got %r, want %r" % (name, got, want))

    numbers = [
        ("0", "0"), ("-0", "0"),
        ("5e-324", "5e-324"), ("-5e-324", "-5e-324"),
        ("1.7976931348623157e+308", "1.7976931348623157e+308"),
        ("-1.7976931348623157e+308", "-1.7976931348623157e+308"),
        ("9007199254740992", "9007199254740992"),
        ("-9007199254740992", "-9007199254740992"),
        ("295147905179352830000", "295147905179352830000"),
        ("9.999999999999997e+22", "9.999999999999997e+22"),
        ("1e+23", "1e+23"),
        ("1.0000000000000001e+23", "1.0000000000000001e+23"),
        ("999999999999999700000", "999999999999999700000"),
        ("999999999999999900000", "999999999999999900000"),
        ("1e+21", "1e+21"),
        ("9.999999999999997e-7", "9.999999999999997e-7"),
        ("1e-6", "0.000001"),
        ("333333333.3333332", "333333333.3333332"),
        ("333333333.33333325", "333333333.33333325"),
        ("333333333.3333333", "333333333.3333333"),
        ("333333333.3333334", "333333333.3333334"),
        ("333333333.33333343", "333333333.33333343"),
        ("-0.0000033333333333333333", "-0.0000033333333333333333"),
        ("1424953923781206.25", "1424953923781206.2"),
        ("1E30", "1e+30"), ("4.50", "4.5"), ("2e-3", "0.002"),
        ("100.0", "100"),
    ]
    for src, want in numbers:
        eq("number " + src, canonicalize(json.loads(src)), want)

    # §3.2.2 full example
    ex_in = ('{"numbers":[333333333.33333329,1E30,4.50,2e-3,'
             '0.000000000000000000000000001],'
             '"string":"€$\\u000F\\u000aA\'\\u0042\\u0022\\u005c\\\\\\"\\/",'
             '"literals":[null,true,false]}')
    ex_want = ('{"literals":[null,true,false],'
               '"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],'
               '"string":"€$\\u000f\\nA\'B\\"\\\\\\\\\\"/"}')
    eq("§3.2.2 example", canonicalize(json.loads(ex_in)), ex_want)

    # String escapes: short forms + LOWERCASE \uhhhh
    eq("escapes", canonicalize("\x00\x1f\b\t\n\f\r\"\\"),
       '"\\u0000\\u001f\\b\\t\\n\\f\\r\\"\\\\"')
    eq("lowercase hex", canonicalize("\x0f"), '"\\u000f"')

    # §3.2.3 key sorting (UTF-16 code units): input deliberately scrambled
    sort_in = ('{"€":"Euro Sign","\\r":"Carriage Return",'
               '"דּ":"Hebrew Letter Dalet With Dagesh",'
               '"1":"One","😀":"Emoji: Grinning Face","\u0080":"Control",'
               '"ö":"Latin Small Letter O With Diaeresis"}')
    sort_want = ('{"\\r":"Carriage Return","1":"One","\u0080":"Control",'
                 '"ö":"Latin Small Letter O With Diaeresis",'
                 '"€":"Euro Sign","😀":"Emoji: Grinning Face",'
                 '"דּ":"Hebrew Letter Dalet With Dagesh"}')
    eq("§3.2.3 key order", canonicalize(json.loads(sort_in)), sort_want)

    # No whitespace; nested sorting; array order preserved
    eq("nesting", canonicalize({"b": 1, "a": {"d": 2, "c": 3}, "arr": [3, 2, 1]}),
       '{"a":{"c":3,"d":2},"arr":[3,2,1],"b":1}')

    # Errors
    for name, fn in [
        ("lone surrogate throws", lambda: canonicalize("\ud800")),
        ("NaN throws", lambda: canonicalize(float("nan"))),
        ("Infinity throws", lambda: canonicalize(float("inf"))),
        ("duplicate key throws",
         lambda: canonicalize_json('{"a":1,"a":2}')),
    ]:
        try:
            fn()
            failures.append(name + ": did not throw")
        except (ValueError, TypeError):
            pass
    return failures


def _cli():
    args = sys.argv[1:]
    if "--selftest" in args:
        failures = selftest()
        if failures:
            for f in failures:
                print("FAIL " + f, file=sys.stderr)
            sys.exit(1)
        print("RFC 8785 selftest: all vectors pass (python %s)"
              % ".".join(map(str, sys.version_info[:3])))
        return
    files = [a for a in args if not a.startswith("--")]
    if not files:
        print("usage: canonical.py <file.json> [--hash] [--selftest]",
              file=sys.stderr)
        sys.exit(2)
    try:
        with open(files[0], encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        print("cannot read %s: %s" % (files[0], e), file=sys.stderr)
        sys.exit(2)
    try:
        value = json.loads(text, object_pairs_hook=_no_dupes)
        print(message_hash(value) if "--hash" in args else canonicalize(value))
    except (ValueError, TypeError) as e:
        print("error: %s" % e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli()
