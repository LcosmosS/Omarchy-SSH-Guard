"""Offline-only R2 design contract. No VM, network, disk mutation or host calls."""
import json
import re
from pathlib import Path

SCHEMA = "ssh-guard-r2-design-plan-v0.1"
CLASSIFICATION = "R2_DESIGN_ONLY"
REFERENCE = "docs/RECOVERY_VM_VALIDATION.md"
ROOT_KEYS = frozenset({"schema", "classification", "reference", "vm_executed", "deployment_authorized", "cases"})
ROW_KEYS = frozenset({"id", "initial_state", "fault", "expected_recovery", "required_observation", "pass_fail_rule", "status"})
ID_PATTERN = re.compile(r"V(?:0[1-9]|1[0-9]|2[0-8])\Z")


class ContractError(ValueError):
    """No assurance may be inferred from invalid or incomplete plan data."""


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("Duplicate JSON key")
        result[key] = value
    return result


def parse_plan(raw):
    if not isinstance(raw, (str, bytes)):
        raise ContractError("Plan must be JSON text")
    try:
        document = json.loads(raw, object_pairs_hook=unique_pairs,
                              parse_constant=lambda _: (_ for _ in ()).throw(ContractError("Nonfinite JSON value")))
    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ContractError("Invalid JSON design plan") from exc
    validate_plan(document)
    return document


def validate_plan(document):
    if type(document) is not dict or set(document) != ROOT_KEYS:
        raise ContractError("Unexpected or missing plan root fields")
    if (document["schema"] != SCHEMA or document["classification"] != CLASSIFICATION
            or document["reference"] != REFERENCE
            or document["vm_executed"] is not False
            or document["deployment_authorized"] is not False):
        raise ContractError("Design-only classification and no-deployment boundary are mandatory")
    rows = document["cases"]
    if type(rows) is not list or len(rows) != 28:
        raise ContractError("Exactly 28 R1 VM cases required")
    for position, row in enumerate(rows, start=1):
        if type(row) is not dict or set(row) != ROW_KEYS:
            raise ContractError("Case fields changed")
        expected_id = "V%02d" % position
        if row.get("id") != expected_id or not ID_PATTERN.fullmatch(str(row.get("id"))):
            raise ContractError("Missing, duplicate or reordered VM case")
        if row.get("status") != "NOT_RUN":
            raise ContractError("Public design plan cannot claim executed or passed VM tests")
        for field in ROW_KEYS - {"id", "status"}:
            value = row[field]
            if type(value) is not str or not value or len(value) > 2000:
                raise ContractError("Missing or invalid R1 case contract text")
    return True


def r1_rows(source):
    """Read only the six-column canonical R1 Markdown table."""
    result = []
    for line in source.splitlines():
        if not re.match(r"^\| V(?:0[1-9]|1[0-9]|2[0-8]) \|", line):
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) != 6:
            raise ContractError("R1 source row has an altered column count")
        result.append(dict(zip(
            ("id", "initial_state", "fault", "expected_recovery", "required_observation", "pass_fail_rule"), parts
        )))
    if len(result) != 28:
        raise ContractError("Canonical R1 matrix does not contain exactly 28 rows")
    if [r["id"] for r in result] != ["V%02d" % i for i in range(1, 29)]:
        raise ContractError("R1 matrix IDs changed")
    return result


def validate_against_r1(document, source):
    validate_plan(document)
    for current, locked in zip(document["cases"], r1_rows(source)):
        if {k: v for k, v in current.items() if k != "status"} != locked:
            raise ContractError("Design plan differs from canonical R1 VM protocol")
    return {"classification": CLASSIFICATION, "vm_cases": 28,
            "not_run": 28, "vm_verified": False, "deployment_authorized": False}


def check_repository(root):
    """Safe file-reading convenience function; does not execute any test or command."""
    root = Path(root)
    plan = parse_plan((root / "r2/validation_plan.json").read_text(encoding="utf-8"))
    r1 = (root / REFERENCE).read_text(encoding="utf-8")
    return validate_against_r1(plan, r1)
