#!/usr/bin/env python3
"""Handshake v0.1 — reference validator (Python, stdlib only).

Implements SPEC-v0.1.md section 3 (global envelope) and section 4 (the 15
message types). Mirrors validators/js/validate.js field-for-field.

    validate(message, opts=None) -> {"ok": True}
                                 | {"ok": False, "errors": [{"path","reason"}]}

Errors accumulate: every violation is reported, in deterministic field
order. `message` may be a parsed dict or a JSON string.
opts={"knownIds": [...]} enables the dangling-supersedes check.

Uncertainty model (provisional, vina ruling pending): any field EXCEPT
msg_type and version may carry {"_unknown": True, "reason": "..."} or
{"_na": True, "reason": "..."} instead of its typed value.
"""

import json
import re
import sys
from datetime import datetime, timezone

VERSION = "0.1"

# The 16 wire values of msg_type (section 4.7 covers two: resource-offer/request).
TYPES = [
    "claim", "verdict", "benchmark-result", "task-handoff", "presence",
    "tool-call", "resource-offer", "resource-request", "kill-signal",
    "approval-request", "result-receipt", "rights-status", "placement-proof",
    "content-package", "build-event", "correction-slip",
]

ENVELOPE_FIELDS = ["msg_id", "msg_type", "version", "sender_urn", "sent_at",
                   "anchor_ref", "supersedes"]

UUID4_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-"
                      r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
                    r"(\.\d+)?(Z|[+-]\d{2}:?\d{2})$")
DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def is_uuid4(s):
    return isinstance(s, str) and bool(UUID4_RE.match(s))


def is_iso(s):
    if not isinstance(s, str) or not ISO_RE.match(s):
        return False
    try:
        datetime.fromisoformat(s.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def is_date_only(s):
    if not isinstance(s, str):
        return False
    m = DATE_RE.match(s)
    if not m:
        return False
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        datetime(y, mo, d)
        return True
    except ValueError:
        return False


def tri_tag_error(v):
    """None if v is a valid uncertainty tag; 'not-a-tag' if it isn't a tag
    object at all; otherwise a human-readable problem string."""
    if not isinstance(v, dict):
        return "not-a-tag"
    keys = list(v.keys())
    has_u = v.get("_unknown") is True
    has_n = v.get("_na") is True
    if not has_u and not has_n:
        return "not-a-tag"
    if has_u and has_n:
        return "both _unknown and _na are set; exactly one is allowed"
    for k in keys:
        if k not in ("_unknown", "_na", "reason"):
            return 'unexpected key "%s"' % k
    if "reason" not in v:
        return '"reason" is required on an uncertainty tag'
    if not isinstance(v["reason"], str) or not v["reason"]:
        return '"reason" must be a non-empty string'
    return None


def _check_field(obj, name, d, path, errors):
    p = "%s.%s" % (path, name) if path else name
    if name not in obj:
        if d.get("req"):
            errors.append({"path": p, "reason": "required field is missing"})
        return
    v = obj[name]
    if d.get("tri", True):
        tag_err = tri_tag_error(v)
        if tag_err is None:
            return  # explicit unknown is data, not an error
        if tag_err not in ("not-a-tag",):
            # 'not-a-tag' can't happen here (dict check above returns None
            # only for dicts); any other string is a malformed tag.
            errors.append({"path": p,
                           "reason": "invalid uncertainty tag: %s" % tag_err})
            return
    t = d["t"]

    def bad(want):
        errors.append({"path": p, "reason": "expected %s" % want})

    if t == "s":
        if not isinstance(v, str):
            bad("string"); return
        if not v:
            errors.append({"path": p, "reason": "string must not be empty"}); return
    elif t == "n":
        if not isinstance(v, (int, float)) or isinstance(v, bool) or v != v:
            bad("number"); return
    elif t == "i":
        if not isinstance(v, int) or isinstance(v, bool):
            bad("integer"); return
    elif t == "b":
        if not isinstance(v, bool):
            bad("boolean"); return
    elif t == "a":
        if not isinstance(v, list):
            bad("array"); return
    elif t == "o":
        if not isinstance(v, dict):
            bad("object"); return
    elif t == "sn":
        if isinstance(v, bool) or not isinstance(v, (str, int, float)) or v != v:
            bad("string or number"); return
        if isinstance(v, str) and not v:
            errors.append({"path": p, "reason": "string must not be empty"}); return
    else:
        errors.append({"path": p, "reason": 'internal: unknown descriptor "%s"' % t})
        return

    if d.get("format") == "uuid4" and not is_uuid4(v):
        errors.append({"path": p, "reason": "must be a UUID v4"})
    if d.get("format") == "iso" and not is_iso(v):
        errors.append({"path": p, "reason": "must be an ISO-8601 timestamp"})
    if d.get("format") == "date" and not is_date_only(v):
        errors.append({"path": p, "reason": "must be a date (YYYY-MM-DD)"})
    if "enum" in d and v not in d["enum"]:
        errors.append({"path": p, "reason": "must be one of: %s" % ", ".join(d["enum"])})
    if "const" in d and v != d["const"]:
        errors.append({"path": p,
                       "reason": "must be exactly %s (no silent coercion)"
                                 % json.dumps(d["const"])})
    if isinstance(d.get("min"), (int, float)) and isinstance(v, (int, float)) \
            and not isinstance(v, bool) and v < d["min"]:
        errors.append({"path": p, "reason": "must be >= %s" % d["min"]})
    if isinstance(d.get("max"), (int, float)) and isinstance(v, (int, float)) \
            and not isinstance(v, bool) and v > d["max"]:
        errors.append({"path": p, "reason": "must be <= %s" % d["max"]})
    if t == "a" and d.get("elem") == "s":
        for i, e in enumerate(v):
            if not isinstance(e, str):
                errors.append({"path": "%s[%d]" % (p, i),
                               "reason": "array element must be a string"})
            elif not e:
                errors.append({"path": "%s[%d]" % (p, i),
                               "reason": "array element must not be empty"})
    if t == "o" and "shape" in d:
        for k, kd in d["shape"].items():
            _check_field(v, k, kd, p, errors)
        for k in v.keys():
            if k not in d["shape"]:
                errors.append({"path": "%s.%s" % (p, k),
                               "reason": "unknown field (not in v0.1 schema)"})
    if d.get("useBound") and not (v == "single-use" or is_iso(v)):
        errors.append({"path": p,
                       "reason": 'must be "single-use" or an ISO-8601 expiry timestamp'})


# Per-type payload field tables, SPEC section 4. Deterministic order.
FIELDS = {
    "claim": {
        "statement": {"t": "s", "req": True}, "source": {"t": "s", "req": True},
        "date": {"t": "s", "req": True, "format": "date"},
        "confidence": {"t": "n", "req": True, "min": 0, "max": 1},
        "claim_kind": {"t": "s", "enum": ["coverage", "candidate-vetting",
                                          "observation", "rights-line"]},
        "outlet": {"t": "s"}, "writer": {"t": "s"}, "url": {"t": "s"},
        "published_at": {"t": "s", "format": "iso"},
        "vetting_status": {"t": "s", "enum": ["pass", "fail", "unverifiable"]},
        "rights_red_flags": {"t": "a", "elem": "s"},
        "metric": {"t": "s"}, "value": {"t": "n"}, "unit": {"t": "s"},
        "observed_at": {"t": "s", "format": "iso"}, "provenance": {"t": "s"},
        "verdict_class": {"t": "s", "enum": ["verified", "estimate"]},
        "status": {"t": "s", "enum": ["DOCUMENTED", "PENDING"]},
        "assertion_class": {"t": "s", "enum": ["independently-documented",
                                              "self-reported"]},
    },
    "verdict": {
        "verdict": {"t": "s", "req": True},
        "evidence_refs": {"t": "a", "req": True, "elem": "s"},
        "dissent": {"t": "a", "req": True, "elem": "s"},
    },
    "benchmark-result": {
        "method": {"t": "s", "req": True},
        "corpus": {"t": "s"}, "scan_id": {"t": "s"},
        "result": {"t": "sn", "req": True}, "repro_ref": {"t": "s", "req": True},
        "error_bars": {"t": "s", "req": True},
    },
    "task-handoff": {
        "task_id": {"t": "s", "req": True}, "from_urn": {"t": "s", "req": True},
        "to_urn": {"t": "s", "req": True},
        "acceptance_criteria": {"t": "s", "req": True},
        "deadline": {"t": "s", "req": True, "format": "iso"},
        "result": {"t": "s", "req": True}, "mechanism": {"t": "s", "req": True},
        "verification": {"t": "s", "req": True},
        "review_date": {"t": "s", "req": True, "format": "iso"},
        "kill_rule": {"t": "s", "req": True},
        "run_context_ref": {"t": "s", "req": True},
    },
    "presence": {
        "agent_urn": {"t": "s", "req": True},
        "current_task_id": {"t": "s", "req": True},
        # state enum is provisional (spec names no values) — see schemas README.
        "state": {"t": "s", "req": True, "enum": ["active", "idle", "offline"]},
    },
    "tool-call": {
        "tool": {"t": "s", "req": True}, "args_hash": {"t": "s", "req": True},
        "invoked_by": {"t": "s", "req": True},
        "idempotency_key": {"t": "s", "req": True},
        "authority_grant": {"t": "s", "req": True},
        "grant_ledger_ref": {"t": "s", "req": True},
        "use_bound": {"t": "s", "req": True, "useBound": True},
    },
    "resource-offer": {
        "resource_ref": {"t": "s", "req": True}, "terms": {"t": "s", "req": True},
        "offered_by": {"t": "s", "req": True},
        "expires_at": {"t": "s", "req": True, "format": "iso"},
    },
    "resource-request": {
        "resource_ref": {"t": "s", "req": True},
        "constraints": {"t": "s", "req": True},
        "requested_by": {"t": "s", "req": True},
        "expires_at": {"t": "s", "req": True, "format": "iso"},
    },
    "kill-signal": {
        "initiative_id": {"t": "s", "req": True},
        # trigger carries the measured numbers (D1: notification-only in v0.1).
        "trigger": {"t": "o", "req": True, "shape": {
            "metric": {"t": "s", "req": True}, "value": {"t": "n", "req": True},
            "observed_at": {"t": "s", "format": "iso"},
        }},
        "issued_by": {"t": "s", "req": True},
        "authority_ref": {"t": "s", "req": True},
        "kill_rule_ref": {"t": "s", "req": True},
    },
    "approval-request": {
        "subject": {"t": "s", "req": True},
        "exact_content": {"t": "s", "req": True},
        "channel": {"t": "s", "req": True},
        "requested_by": {"t": "s", "req": True},
        "approval_status": {"t": "s", "req": True,
                            "enum": ["pending", "approved", "rejected"]},
        "decision_ref": {"t": "s"},
        "approver": {"t": "s", "req": True},
        "approval_hash": {"t": "s"},  # D4: hop must be mandatory-resolvable
    },
    "result-receipt": {
        "initiative_id": {"t": "s", "req": True},
        "result": {"t": "sn", "req": True}, "receipt": {"t": "s", "req": True},
        "verified_by": {"t": "s", "req": True},
        "verified_at": {"t": "s", "req": True, "format": "iso"},
    },
    "rights-status": {
        "item_id": {"t": "s", "req": True},
        "status": {"t": "s", "req": True, "enum": ["DOCUMENTED", "PENDING"]},
        "source_ref": {"t": "s", "req": True},
        "assertion_class": {"t": "s", "req": True,
                            "enum": ["independently-documented", "self-reported"]},
        "changed_at": {"t": "s", "req": True, "format": "iso"},
        "changed_by": {"t": "s", "req": True},
    },
    "placement-proof": {
        "playlist_id": {"t": "s", "req": True},
        "track_id": {"t": "s", "req": True},
        "claim_status": {"t": "s", "req": True,
                         "enum": ["claimed", "verified", "retired"]},
        "observed_at": {"t": "s", "req": True, "format": "iso"},
        "evidence_ref": {"t": "s", "req": True},
        "follow_up_due": {"t": "s", "req": True, "format": "iso"},
        "follow_up_ref": {"t": "s", "req": True},
        "confidence": {"t": "n", "min": 0, "max": 1},
    },
    "content-package": {
        "day": {"t": "s", "req": True, "format": "date"},
        "id": {"t": "s", "req": True}, "type": {"t": "s", "req": True},
        "media_files": {"t": "a", "req": True, "elem": "s"},
        "caption": {"t": "s", "req": True},
        "hashtags": {"t": "a", "req": True, "elem": "s"},
        "threads_text": {"t": "s", "req": True},
        "post_order": {"t": "i", "req": True},
        "platform_targets": {"t": "a", "req": True, "elem": "s"},
        "approval_status": {"t": "s", "req": True,
                            "enum": ["pending", "approved", "rejected"]},
        "asset_checksums": {"t": "a", "req": True, "elem": "s"},
        "embargo_until": {"t": "s", "format": "iso"},  # D7 provisional optional
    },
    "build-event": {
        "project": {"t": "s", "req": True},
        "stage": {"t": "s", "req": True,
                  "enum": ["discover", "design", "build", "test", "deploy",
                           "go-live", "post-launch"]},
        "artifact_ref": {"t": "s", "req": True},
        "tests": {"t": "o", "req": True, "shape": {
            "passed": {"t": "i", "req": True, "min": 0},
            "total": {"t": "i", "req": True, "min": 0},
        }},
        "checkpoint_evidence": {"t": "s", "req": True},
        "gate": {"t": "s", "req": True, "enum": ["passed", "failed", "blocked"]},
    },
    "correction-slip": {
        "supersedes": {"t": "s", "req": True, "format": "uuid4"},
        "corrected_claim": {"t": "s", "req": True},
        "reason": {"t": "s", "req": True},
        "cited_by": {"t": "a", "req": True, "elem": "s"},
    },
}

# claim_kind -> additionally required fields (SPEC section 4.1).
CLAIM_KIND_REQ = {
    "coverage": ["outlet", "writer", "url", "published_at"],
    "candidate-vetting": ["vetting_status", "rights_red_flags"],
    "observation": ["metric", "value", "unit", "observed_at", "provenance",
                    "verdict_class"],
    "rights-line": ["status", "assertion_class"],
}


def validate_envelope(msg, errors):
    # msg_type and version are dispatch-critical: the uncertainty tag is NOT
    # accepted for them (documented in schemas/handshake-0.1/README.md).
    env = {
        "msg_id": {"t": "s", "req": True, "format": "uuid4"},
        "msg_type": {"t": "s", "req": True, "tri": False, "enum": TYPES},
        "version": {"t": "s", "req": True, "tri": False, "const": VERSION},
        "sender_urn": {"t": "s", "req": True},
        "sent_at": {"t": "s", "req": True, "format": "iso"},
        "anchor_ref": {"t": "s", "req": True},
        "supersedes": {"t": "s", "format": "uuid4"},
    }
    for name, d in env.items():
        _check_field(msg, name, d, "", errors)


def validate(message, opts=None):
    """Validate a Handshake v0.1 message. See module docstring."""
    opts = opts or {}
    errors = []
    msg = message
    if isinstance(msg, str):
        try:
            msg = json.loads(msg)
        except json.JSONDecodeError as e:
            return {"ok": False, "errors": [{"path": "$",
                                             "reason": "not valid JSON: %s" % e}]}
    if not isinstance(msg, dict):
        return {"ok": False,
                "errors": [{"path": "$",
                            "reason": "message must be a JSON object"}]}
    validate_envelope(msg, errors)
    _mt = msg.get("msg_type")
    spec = FIELDS.get(_mt) if isinstance(_mt, str) else None
    if spec is not None:
        allowed = set(ENVELOPE_FIELDS) | set(spec.keys())
        for k in msg.keys():
            if k not in allowed:
                errors.append({"path": k,
                               "reason": "unknown field (not in the v0.1 %s schema)"
                                         % msg["msg_type"]})
        for name, d in spec.items():
            _check_field(msg, name, d, "", errors)

        kind = msg.get("claim_kind")
        if kind in CLAIM_KIND_REQ and tri_tag_error(kind) is not None:
            for f in CLAIM_KIND_REQ[kind]:
                d = dict(FIELDS["claim"][f]); d["req"] = True
                _check_field(msg, f, d, "", errors)

        if msg.get("msg_type") == "benchmark-result" \
                and "corpus" not in msg and "scan_id" not in msg:
            errors.append({"path": "corpus",
                           "reason": "at least one of corpus, scan_id is required"})

        if msg.get("msg_type") == "approval-request" and "approval_status" in msg:
            st = msg["approval_status"]
            has_decision = "decision_ref" in msg
            if st == "pending":
                if has_decision and msg["decision_ref"] != "pending" \
                        and tri_tag_error(msg["decision_ref"]) is not None:
                    errors.append({"path": "decision_ref",
                                   "reason": 'must be absent (or "pending") while '
                                             "approval_status is pending"})
            elif st in ("approved", "rejected"):
                if not has_decision:
                    errors.append({"path": "decision_ref",
                                   "reason": "decision_ref (message id of the decision) "
                                             "is required once approved/rejected"})
                elif msg["decision_ref"] == "pending" \
                        or tri_tag_error(msg["decision_ref"]) is None:
                    errors.append({"path": "decision_ref",
                                   "reason": "decision_ref must be a concrete message id "
                                             "once approved/rejected"})

        if msg.get("msg_type") == "build-event":
            t = msg.get("tests")
            if isinstance(t, dict) and isinstance(t.get("passed"), int) \
                    and not isinstance(t.get("passed"), bool) \
                    and isinstance(t.get("total"), int) \
                    and not isinstance(t.get("total"), bool) \
                    and t["passed"] > t["total"]:
                errors.append({"path": "tests.passed",
                               "reason": "tests.passed must not exceed tests.total"})

        if opts.get("knownIds") is not None and "supersedes" in msg \
                and tri_tag_error(msg["supersedes"]) is not None \
                and is_uuid4(msg["supersedes"]):
            known = opts["knownIds"]
            known = set(known) if not isinstance(known, set) else known
            if msg["supersedes"] not in known:
                errors.append({"path": "supersedes",
                               "reason": "supersedes references unknown msg_id %s"
                                         % msg["supersedes"]})

    return {"ok": True} if not errors else {"ok": False, "errors": errors}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python3 validate.py <message.json> [known-ids.json]",
              file=sys.stderr)
        sys.exit(2)
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            raw = f.read()
    except OSError as e:
        print("cannot read %s: %s" % (sys.argv[1], e), file=sys.stderr)
        sys.exit(2)
    o = {}
    if len(sys.argv) > 2:
        try:
            with open(sys.argv[2], encoding="utf-8") as f:
                o = {"knownIds": set(json.load(f))}
        except (OSError, ValueError) as e:
            print("cannot read %s: %s" % (sys.argv[2], e), file=sys.stderr)
            sys.exit(2)
    print(json.dumps(validate(raw, o)))
