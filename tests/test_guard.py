import importlib.machinery
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "bin/omarchy-guard"
loader = importlib.machinery.SourceFileLoader("omarchy_guard", str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
guard = importlib.util.module_from_spec(spec)
loader.exec_module(guard)


class GuardTests(unittest.TestCase):
    def test_global_ipv4_ipv6_and_source_rule(self):
        rules = """[ 1] 22/tcp LIMIT IN Anywhere
[ 2] 22/tcp LIMIT IN 198.51.100.25
[ 3] 22/tcp (v6) LIMIT IN Anywhere (v6)
"""
        result = guard.ssh_rule_classification(rules)
        self.assertTrue(result["global_ipv4_allow"])
        self.assertTrue(result["global_ipv6_allow"])
        self.assertEqual(result["source_specific_rule_count"], 1)

    def test_not_outbound_or_other_ports(self):
        result = guard.ssh_rule_classification(
            "22/tcp ALLOW OUT Anywhere\n2222/tcp ALLOW IN Anywhere")
        self.assertFalse(result["global_ipv4_allow"])
        self.assertFalse(result["global_ipv6_allow"])

    def test_docker_expose_is_not_published(self):
        text = ('{"Ports":"127.0.0.1:5432->5432/tcp, 33060/tcp"}\n'
                '{"Ports":"0.0.0.0:8080->80/tcp, :::8080->80/tcp"}')
        r = guard.loopback_publications(text)
        self.assertEqual(r["containers_observed"], 2)
        self.assertEqual(r["loopback_published"], 1)
        self.assertEqual(r["nonloopback_published"], 2)

    def test_docker_unclassified_not_silent(self):
        result = guard.loopback_publications('garbled\n{"Ports":"192.0.2.44:22->22/tcp"}')
        self.assertEqual(result["unclassified_published"], 2)

    def test_listener_not_reachability(self):
        self.assertTrue(guard.ssh_wildcard_listening(
            "LISTEN 0 128 0.0.0.0:22 0.0.0.0:*"))
        self.assertFalse(guard.ssh_wildcard_listening(
            "LISTEN 0 128 127.0.0.1:22 0.0.0.0:*"))

    def test_only_single_host_source(self):
        self.assertEqual(guard.plan_source("198.51.100.25/32"), "198.51.100.25/32")
        self.assertEqual(guard.plan_source("2001:db8::1/128"), "2001:db8::1/128")
        for bad in ["0.0.0.0/0", "198.51.100.0/24", "2001:db8::/64", "invalid"]:
            with self.assertRaises(Exception):
                guard.plan_source(bad)

    def test_audit_not_optimistic(self):
        with patch.object(guard, "run", return_value=(False, "")):
            report = guard.audit()
        self.assertEqual(report["verdict"], "NOT_VERIFIED")
        self.assertFalse(report["checks"]["ufw"]["observed"])
        self.assertFalse(report["checks"]["external_reachability"]["observed"])

    def test_no_mutation_commands_in_audit(self):
        called = []
        def fake_run(argv, timeout=8):
            called.append(argv)
            return False, ""
        with patch.object(guard, "run", side_effect=fake_run):
            guard.audit()
        self.assertEqual([c[1] for c in called], ["status", "-ltn", "ps"])
        self.assertTrue(all(c[0] in ["/usr/bin/ufw", "/usr/bin/ss", "/usr/bin/docker"] for c in called))


if __name__ == "__main__":
    unittest.main()
