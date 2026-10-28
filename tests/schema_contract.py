"""Mandatory independent schema check for CI; install requirements-schema.txt first."""
import copy
from jsonschema import Draft202012Validator, FormatChecker
from test_evidence import SCHEMA, challenge, report, bundle

Draft202012Validator.check_schema(SCHEMA)
checker = FormatChecker()
assert {"date-time", "uuid", "ipv4", "ipv6"} <= checker.checkers.keys(), "Required format checkers unavailable"
validator = Draft202012Validator(SCHEMA, format_checker=checker)
positives = [challenge(), challenge(6), report(), bundle()]
for value in positives:
    validator.validate(value)
negatives = []
for value in positives:
    negatives.append({**value, "unexpected": True})
    missing = copy.deepcopy(value); del missing["kind"]; negatives.append(missing)
for field in ["nonce", "policy_sha256", "client_id", "user", "issued_at", "run_id"]:
    for prefix, suffix in [("!", ""), ("", "!"), ("", "\n")]:
        value = challenge(); value[field] = prefix + value[field] + suffix; negatives.append(value)
for field, bad in [("issued_at", "2026-02-30T20:00:00Z"), ("issued_at", "2026-10-27T20:00:00"),
                   ("source", "hostname.example"), ("destination_port", True)]:
    value = challenge(); value[field] = bad; negatives.append(value)
for port in [True, "41000", -1, 0, 65536]:
    value = report(); value["source_port"] = port; negatives.append(value)
for value in negatives:
    assert not validator.is_valid(value), "Schema unexpectedly accepted a negative fixture"
print(f"Draft 2020-12: meta-schema + {len(positives)} positives + {len(negatives)} negatives passed (FormatChecker enabled)")
