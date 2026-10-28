"""Synthetic, offline fixtures only. No client identities, keys or network calls."""
import copy
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader("evidence_lint", str(ROOT / "bin/omarchy-guard-evidence"))
spec = importlib.util.spec_from_loader(loader.name, loader)
lint = importlib.util.module_from_spec(spec)
loader.exec_module(lint)
SCHEMA = lint.read_json(ROOT / "schemas/ssh-evidence-v2.schema.json")
NOW = lint.utc("2026-10-27T20:00:00Z")


def challenge(family=4):
    return {"schema_version": 2, "milestone": "SSH-HARDEN-01b", "kind": "challenge", "stage": "baseline",
            "run_id": "00000000-0000-4000-8000-000000000001", "challenge_id": "00000000-0000-4000-8000-000000000002",
            "nonce": "0" * 64, "issued_at": "2026-10-27T19:59:00Z", "expires_at": "2026-10-27T20:14:00Z",
            "policy_sha256": "0" * 64, "client_id": "example-client", "role": "unauthorized", "family": family,
            "source": "198.51.100.30" if family == 4 else "2001:db8::30",
            "destination": "203.0.113.20" if family == 4 else "2001:db8::20", "destination_port": 22,
            "user": "", "network_path": "Synthetic example path", "baseline_challenge_id": None}


def report():
    c = challenge()
    return {"schema_version": 2, "milestone": "SSH-HARDEN-01b", "kind": "report", "challenge": c,
            "started_at": "2026-10-27T19:59:30Z", "completed_at": "2026-10-27T19:59:32Z",
            "observed_source": c["source"], "observed_destination": c["destination"], "source_port": 41000,
            "tcp_connected": False, "result": "timeout", "reachability_before": True, "reachability_after": True,
            "authenticated": False, "fresh_connection": False, "method": "none", "verified_at": None,
            "banner_sha256": None, "signature": "0" * 64}


def bundle():
    return {"schema_version": 2, "milestone": "SSH-HARDEN-01b", "kind": "bundle", "stage": "baseline",
            "run_id": challenge()["run_id"], "baseline_run_id": None, "policy_sha256": "0" * 64,
            "created_at": "2026-10-27T19:58:00Z", "operator_attestation": False,
            "authorized": [], "unauthorized": []}


class EvidenceTests(unittest.TestCase):
    def test_all_three_shapes_and_both_address_families(self):
        for value in [challenge(), challenge(6), report(), bundle()]:
            self.assertEqual(lint.inspect(value, SCHEMA, NOW)["structure"], "VALID")

    def test_fabricated_signature_and_self_report_never_attest(self):
        for signature in ["0" * 64, "f" * 64]:
            value = report(); value["signature"] = signature
            result = lint.inspect(value, SCHEMA, NOW)
            self.assertEqual(result["signature"], "NOT_CHECKED")
            self.assertEqual(result["external_reachability"], "NOT_VERIFIED")
            self.assertFalse(result["deployment_authorized"])
            self.assertEqual(result["verdict"], "NOT_VERIFIED")

    def test_empty_or_attested_bundle_never_authorizes(self):
        for attested in [False, True]:
            value = bundle(); value["operator_attestation"] = attested
            result = lint.inspect(value, SCHEMA, NOW)
            self.assertEqual(result["run_binding"], "NOT_CHECKED")
            self.assertFalse(result["deployment_authorized"])

    def test_unknown_and_missing_fields_at_each_level(self):
        for value in [challenge(), report(), bundle()]:
            with self.assertRaises(ValueError): lint.inspect({**value, "unexpected": True}, SCHEMA, NOW)
            value.pop("kind")
            with self.assertRaises(ValueError): lint.inspect(value, SCHEMA, NOW)

    def test_exact_patterns_reject_prefix_suffix_and_newline(self):
        for field in ["nonce", "policy_sha256", "client_id", "user", "issued_at", "run_id"]:
            for transform in [lambda s: "!" + s, lambda s: s + "!", lambda s: s + "\n"]:
                value = challenge(); value[field] = transform(value[field])
                with self.assertRaises(ValueError): lint.inspect(value, SCHEMA, NOW)

    def test_ports_reject_bool_string_float_and_out_of_range(self):
        for port in [True, "41000", 41000.0, -1, 0, 65536]:
            value = report(); value["source_port"] = port
            with self.assertRaises(ValueError): lint.inspect(value, SCHEMA, NOW)

    def test_explicit_utc_calendar_and_canonical_addresses(self):
        for timestamp in [None, "2026-10-27T20:00:00", "2026-10-27T21:00:00+01:00", "2026-02-30T20:00:00Z"]:
            value = challenge(); value["issued_at"] = timestamp
            with self.assertRaises(ValueError): lint.inspect(value, SCHEMA, NOW)
        for address in ["host.example", "198.051.100.30", "2001:DB8::30", "2001:db8::1%eth0"]:
            value = challenge(); value["source"] = address
            with self.assertRaises(ValueError): lint.inspect(value, SCHEMA, NOW)

    def test_timestamp_lint_is_diagnostic_only(self):
        for delta, expected in [(0, "CURRENT"), (1000, "STALE_OR_FUTURE"), (-1000, "STALE_OR_FUTURE")]:
            result = lint.inspect(report(), SCHEMA, NOW + delta)
            self.assertEqual(result["local_time_window"], expected)
            self.assertEqual(result["verdict"], "NOT_VERIFIED")
        for start, end in [("2026-10-27T19:59:40Z", "2026-10-27T19:59:30Z"),
                           ("2026-10-27T19:59:00Z", "2026-10-27T20:00:00Z")]:
            value = report(); value.update(started_at=start, completed_at=end)
            self.assertEqual(lint.inspect(value, SCHEMA, NOW)["local_time_window"], "STALE_OR_FUTURE")

    def test_schema_extension_is_not_silently_ignored(self):
        schema = copy.deepcopy(SCHEMA); schema["unevaluatedProperties"] = False
        with self.assertRaises(ValueError): lint.inspect(challenge(), schema, NOW)

    def test_duplicate_nonfinite_encoding_and_deep_json_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            for data in [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'\xff', b'[' * 40 + b']' * 40]:
                path.write_bytes(data)
                with self.assertRaises(ValueError): lint.read_json(path)

    def test_large_regular_file_and_fifo_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"; path.write_bytes(b" " * (lint.MAX_BYTES + 1))
            with self.assertRaises(ValueError): lint.read_json(path)
            fifo = Path(directory) / "fifo"; os.mkfifo(fifo)
            with self.assertRaises(ValueError): lint.read_json(fifo)

    def test_leaf_and_parent_symlinks_and_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); real = base / "real"; real.mkdir()
            path = real / "input.json"; path.write_text("{}")
            leaf = base / "leaf"; leaf.symlink_to(path)
            parent = base / "parent"; parent.symlink_to(real, target_is_directory=True)
            for value in [leaf, parent / "input.json", real / ".." / "real" / "input.json"]:
                with self.assertRaises((OSError, ValueError)): lint.read_json(value)

    def test_parent_rename_does_not_redirect_pinned_descriptor(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); real = base / "real"; real.mkdir()
            (real / "input.json").write_text('{"pinned":true}')
            other = base / "other"; other.mkdir(); (other / "input.json").write_text('{"pinned":false}')
            original = lint.os.open
            triggered = []
            def opening(path, *args, **kwargs):
                fd = original(path, *args, **kwargs)
                if path == "real":
                    triggered.append(True)
                    real.rename(base / "moved")
                    real.symlink_to(other, target_is_directory=True)
                return fd
            with patch.object(lint.os, "open", side_effect=opening):
                self.assertEqual(lint.read_json(real / "input.json"), {"pinned": True})
            # The test must fail if implementation changes bypass the simulated race.
            self.assertEqual(triggered, [True], "Race injection was never exercised")
            self.assertTrue(real.is_symlink(), "Replacement symlink not installed")
            self.assertTrue((base / "moved").is_dir(), "Original directory was not moved")

    def test_output_omits_private_values_and_failure_details(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            value = challenge(); value["network_path"] = "SYNTHETIC_PRIVATE_MARKER"
            path.write_text(json.dumps(value))
            result = subprocess.run([sys.executable, "-B", str(ROOT / "bin/omarchy-guard-evidence"), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertNotIn(value["source"], result.stdout)
            self.assertNotIn(value["network_path"], result.stdout)
            self.assertNotIn(str(path), result.stdout)
            path.write_text('{"broken": "SYNTHETIC_PRIVATE_MARKER"')
            result = subprocess.run([sys.executable, "-B", str(ROOT / "bin/omarchy-guard-evidence"), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("SYNTHETIC_PRIVATE_MARKER", result.stdout + result.stderr)

    def test_root_execution_is_refused(self):
        with patch.object(lint.os, "geteuid", return_value=0), patch.object(sys, "argv", ["linter", "unused"]), patch.object(sys, "stderr", io.StringIO()):
            with self.assertRaises(SystemExit) as caught: lint.cli()
            self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
