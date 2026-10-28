"""Synthetic negative tests for the privacy heuristic."""
import importlib.util
import subprocess
import hashlib
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("privacy_guard", ROOT / "scripts/privacy_guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class PrivacyGuardTests(unittest.TestCase):
    def test_documentation_address_allowed(self):
        self.assertEqual(guard.content_findings("198.51.100.25 2001:db8::1"), [])

    def test_loopback_bindings_allowed(self):
        self.assertEqual(guard.content_findings("127.0.0.1:5432 0.0.0.0:22 [::1]:631"), [])

    def test_private_ipv4_detected(self):
        ip = "192" + ".168.77.5"
        self.assertIn("non-example IPv4 literal", guard.content_findings(ip))

    def test_private_ipv6_detected(self):
        ip = "fd12" + ":" * 2 + "ab" + ":" + "12"
        self.assertIn("non-example IPv6 literal", guard.content_findings(ip))

    def test_global_ipv4_detected(self):
        ip = "8" + ".8.8.8"
        self.assertIn("non-example IPv4 literal", guard.content_findings(ip))

    def test_private_key_marker_detected(self):
        header = "-----BEGIN " + "OPENSSH PRIVATE KEY-----"
        self.assertIn("private key header", guard.content_findings(header))

    def test_access_token_detected(self):
        token = "gh" + "p_" + "x" * 38
        self.assertIn("GitHub access token", guard.content_findings(token))

    def test_nonexample_email_detected(self):
        address = "somebody" + "@" + "corp.test"
        self.assertIn("possible personal email address", guard.content_findings(address))

    def test_safe_email_allowed(self):
        self.assertEqual(guard.content_findings("security@example.org"), [])

    def test_home_path_detected(self):
        reference = "/" + "home/alice/" + "secret"
        self.assertIn("absolute home-directory reference", guard.content_findings(reference))

    def test_markdown_home_path_detected(self):
        # Construct the path to avoid embedding a real home-path literal in a tracked file.
        path = "/" + "home/alice"
        reference = "See " + "`" + path + "`" + " for details."
        self.assertIn("absolute home-directory reference", guard.content_findings(reference))
        self.assertIn("absolute home-directory reference", guard.content_findings(path + " "))
        self.assertIn("absolute home-directory reference", guard.content_findings(path + "/file"))

    def test_tracked_filename_token_is_scanned(self):
        token = "gh" + "p_" + "x" * 38
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = token + ".txt"
            (root / path).write_text("harmless fixture", encoding="utf-8")
            findings = guard.audit_paths([path], root)
            self.assertIn("GitHub access token", findings[path])

    def test_tracked_filename_personal_data_is_scanned(self):
        path = "private" + "@" + "example.invalid" + ".txt"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / path).write_text("harmless fixture", encoding="utf-8")
            findings = guard.audit_paths([path], root)
            self.assertIn("possible personal email address", findings[path])

    def test_root_home_path_detected(self):
        path = "/" + "root" + "/runtime/state"
        self.assertIn("absolute home-directory reference", guard.content_findings(path))
        self.assertIn("absolute home-directory reference", guard.content_findings("\`" + path + "\`"))
        self.assertEqual(guard.content_findings("/" + "rootless/service"), [])

    def test_deleted_sensitive_blob_detected_in_pr_history(self):
        """A later deletion must not hide a token in an earlier PR commit."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            def git(*args):
                return subprocess.run(
                    ["git", "-C", str(root), *args],
                    check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                ).stdout.decode().strip()
            git("init", "-q")
            git("config", "user.name", "Synthetic Test")
            git("config", "user.email", "tests@example.org")
            git("commit", "--allow-empty", "-qm", "base")
            base = git("rev-parse", "HEAD")
            token = "gh" + "p_" + "Z" * 38
            (root / "transient.txt").write_text(token, encoding="utf-8")
            git("add", "transient.txt")
            git("commit", "-qm", "add synthetic sensitive blob")
            git("rm", "-q", "transient.txt")
            git("commit", "-qm", "remove synthetic sensitive blob")
            self.assertEqual(guard.audit_paths([], root), {})
            findings = guard.introduced_history_findings(base, git("rev-parse", "HEAD"), root)
            self.assertTrue(any("GitHub access token" in details for details in findings.values()))
            self.assertTrue(all(token not in key for key in findings))

    def test_deleted_sensitive_filename_detected_in_pr_history(self):
        """The history scan checks deleted path names, not just blob content."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            def git(*args):
                return subprocess.run(
                    ["git", "-C", str(root), *args],
                    check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                ).stdout.decode().strip()
            git("init", "-q")
            git("config", "user.name", "Synthetic Test")
            git("config", "user.email", "tests@example.org")
            git("commit", "--allow-empty", "-qm", "base")
            base = git("rev-parse", "HEAD")
            name = "gh" + "p_" + "Y" * 38 + ".txt"
            (root / name).write_text("safe", encoding="utf-8")
            git("add", name)
            git("commit", "-qm", "add sensitive filename")
            git("rm", "-q", name)
            git("commit", "-qm", "remove sensitive filename")
            findings = guard.introduced_history_findings(base, git("rev-parse", "HEAD"), root)
            self.assertTrue(any("GitHub access token" in details for details in findings.values()))
            self.assertTrue(all(name not in key for key in findings))

    def test_history_rejects_invalid_or_unrelated_revisions(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                guard.introduced_history_findings("0" * 39, "1" * 40, Path(td))

    def test_private_filename_detected(self):
        self.assertIn("private artifact filename", guard.filename_findings("state/" + "authorized_keys"))
        self.assertIn("private artifact filename", guard.filename_findings("output/" + "evidence.json"))

    def test_normal_file_allowed(self):
        self.assertEqual(guard.filename_findings("docs/RULESET_REVIEW.md"), [])

    def test_pinned_branding_artwork_is_allowed(self):
        path = "assets/omarchy-ssh-guard-overview.webp"
        data = (ROOT / path).read_bytes()
        self.assertEqual(
            hashlib.sha256(data).hexdigest(), guard.APPROVED_PUBLIC_ARTWORK[path]
        )
        self.assertTrue(guard.approved_public_artwork(data, path))
        self.assertEqual(guard.audit_paths([path], ROOT), {})

    def test_changed_artwork_is_not_exempt(self):
        path = "assets/omarchy-ssh-guard-overview.webp"
        data = bytearray((ROOT / path).read_bytes())
        data[-1] ^= 1
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "assets").mkdir()
            (root / path).write_bytes(data)
            self.assertIn("unscannable binary data", guard.audit_paths([path], root)[path])

    def test_branding_artwork_at_wrong_path_is_not_exempt(self):
        data = (ROOT / "assets/omarchy-ssh-guard-overview.webp").read_bytes()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "unreviewed.webp").write_bytes(data)
            self.assertIn("unscannable binary data",
                          guard.audit_paths(["unreviewed.webp"], root)["unreviewed.webp"])

    def test_historical_public_artwork_accepted_by_digest(self):
        data = (ROOT / "assets/omarchy-ssh-guard-overview.webp").read_bytes()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            def git(*args):
                return subprocess.run(
                    ["git", "-C", str(root), *args],
                    check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                ).stdout.decode().strip()
            git("init", "-q")
            git("config", "user.name", "Synthetic Test")
            git("config", "user.email", "tests@example.org")
            git("commit", "--allow-empty", "-qm", "baseline")
            base = git("rev-parse", "HEAD")
            (root / "assets").mkdir()
            (root / "assets/omarchy-ssh-guard-overview.webp").write_bytes(data)
            git("add", "assets/omarchy-ssh-guard-overview.webp")
            git("commit", "-qm", "reviewed public artwork")
            self.assertEqual(guard.introduced_history_findings(base, git("rev-parse", "HEAD"), root), {})

    def test_unknown_binary_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "payload.bin").write_bytes(b"\x00\x01")
            findings = guard.audit_paths(["payload.bin"], root)
            self.assertIn("unscannable binary data", findings["payload.bin"])

    def test_symlink_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "target").write_text("test")
            (root / "link").symlink_to(root / "target")
            findings = guard.audit_paths(["link"], root)
            self.assertIn("tracked symlink forbidden", findings["link"])


if __name__ == "__main__":
    unittest.main()
