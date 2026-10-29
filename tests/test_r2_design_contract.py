"""Synthetic R2 plan checks; all 28 VM rows remain NOT RUN."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from support.r2_contract import (
    ContractError, check_repository, parse_plan, validate_against_r1,
    validate_plan,
)

ROOT = Path(__file__).resolve().parents[1]


class R2DesignContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "r2/validation_plan.json").read_text(encoding="utf-8"))
        cls.r1 = (ROOT / "docs/RECOVERY_VM_VALIDATION.md").read_text(encoding="utf-8")

    def test_all_28_unexecuted_and_no_authority(self):
        result = validate_against_r1(self.data, self.r1)
        self.assertEqual(result["vm_cases"], 28)
        self.assertEqual(result["not_run"], 28)
        self.assertIs(result["vm_verified"], False)
        self.assertIs(result["deployment_authorized"], False)

    def test_can_read_repository_plan_without_executing(self):
        self.assertEqual(check_repository(ROOT)["classification"], "R2_DESIGN_ONLY")

    def test_duplicate_json_fields_fail_closed(self):
        raw = json.dumps(self.data)
        raw = raw.replace('"schema":', '"schema":"malicious", "schema":', 1)
        with self.assertRaises(ContractError):
            parse_plan(raw)

    def test_fabricated_success_cannot_pass(self):
        for field, value in (("status", "PASS"), ("status", "PASS_CANDIDATE"),
                             ("status", "INDEPENDENTLY_REVIEWED_PASS"), ("status", "BLOCKED")):
            with self.subTest(value=value):
                altered = deepcopy(self.data)
                altered["cases"][0][field] = value
                with self.assertRaises(ContractError):
                    validate_plan(altered)

    def test_missing_duplicate_or_reordered_rows_are_rejected(self):
        for tamper in ("missing", "duplicate", "reorder"):
            with self.subTest(tamper=tamper):
                altered = deepcopy(self.data)
                if tamper == "missing":
                    altered["cases"].pop()
                elif tamper == "duplicate":
                    altered["cases"][1] = deepcopy(altered["cases"][0])
                else:
                    altered["cases"][0], altered["cases"][1] = altered["cases"][1], altered["cases"][0]
                with self.assertRaises(ContractError):
                    validate_plan(altered)

    def test_tampering_locked_r1_rule_fails(self):
        altered = deepcopy(self.data)
        altered["cases"][25]["pass_fail_rule"] = "PASS without checkpoint evidence"
        self.assertTrue(validate_plan(altered))
        with self.assertRaises(ContractError):
            validate_against_r1(altered, self.r1)

    def test_incorrect_booleans_or_scope_fail(self):
        for field, value in (("vm_executed", True), ("deployment_authorized", True),
                             ("deployment_authorized", 0), ("classification", "VERIFIED")):
            with self.subTest(field=field, value=value):
                altered = deepcopy(self.data)
                altered[field] = value
                with self.assertRaises(ContractError):
                    validate_plan(altered)

    def test_missing_source_row_fails(self):
        with self.assertRaises(ContractError):
            validate_against_r1(self.data, self.r1.replace("| V28 |", "| VXX |"))

    def test_nonfinite_values_rejected(self):
        raw = json.dumps(self.data).replace('"vm_executed": false', '"vm_executed": NaN')
        with self.assertRaises(ContractError):
            parse_plan(raw)

    def test_public_design_does_not_mutate_reference(self):
        before = json.dumps(self.data, sort_keys=True)
        validate_against_r1(self.data, self.r1)
        self.assertEqual(before, json.dumps(self.data, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
