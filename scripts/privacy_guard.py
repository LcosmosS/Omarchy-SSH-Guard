#!/usr/bin/env python3
"""Fail closed for obvious private artifacts in Git-tracked text. Heuristic only.

Do not print the matching content. Does not claim full secret scanning.
"""
from __future__ import annotations

import ipaddress
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_HISTORY_OBJECTS = 8000
MAX_HISTORY_BYTES = 32 * 1024 * 1024

# Public, manually reviewed artwork is allowed only at this exact tracked
# location and with exactly these bytes. This does not permit arbitrary images,
# operational screenshots, or private artifacts. Git history checks can match
# the digest independently of the historical path.
APPROVED_PUBLIC_ARTWORK = {
    "assets/omarchy-ssh-guard-overview.webp": "814a3a854184d914cc0578d912317f5d33773426e7c8ae5653b0770ca4acaad6",
}


def approved_public_artwork(data: bytes, path: str | None = None) -> bool:
    if len(data) > MAX_FILE_BYTES or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return False
    signature = hashlib.sha256(data).hexdigest()
    if path is not None:
        return APPROVED_PUBLIC_ARTWORK.get(path) == signature
    return signature in APPROVED_PUBLIC_ARTWORK.values()
DOC_NETS = [
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("2001:db8::/32"),
]
IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
# Extract colon-delimited candidates and ask ipaddress to validate them.
IPV6 = re.compile(r"(?<![\w:])(?:[0-9a-fA-F:]{3,})(?![\w:])")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
ROOT_HOME = "/" + "root"  # Constructed to avoid a false match when scanning this source.
ABS_HOME = re.compile(r"(?<!\w)/(?:home|Users)/[A-Za-z0-9._-]+(?=$|[^A-Za-z0-9._-])"
                      + r"|(?<!\w)" + re.escape(ROOT_HOME) + r"(?=$|[^A-Za-z0-9._-])")
SECRETS = (
    ("private key header", re.compile(r"-----BEGIN\s+(?:OPENSSH|RSA|EC|DSA|ENCRYPTED)\s+PRIVATE\s+KEY-----")),
    ("GitHub access token", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("GitHub fine-grained token", re.compile(r"github_pat_[A-Za-z0-9_]{30,}")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("PEM private key block", re.compile(r"-----BEGIN\s+PRIVATE\s+KEY-----")),
)
# These are prohibited filenames, not references to filenames in instructions.
PRIVATE_NAMES = re.compile(
    r"^(?:\.env(?:\..+)?|authorized_keys|known_hosts|"
    r"id_(?:rsa|ed25519|ecdsa)(?:\.pub)?|ssh_host_[^/]+|"
    r"transaction(?:[_-][^/]*)?\.json|"
    r"(?:ssh_)?evidence(?:[_-][^/]*)?\.json|"
    r"ssh_authorized_sources\.json|"
    r"(?:ufw|firewall)[_-](?:backup|before)[^/]*|"
    r"[^/]*\.(?:pem|p12|pfx|key|log|sqlite|db|tar|tgz|zip))$",
    re.IGNORECASE,
)
PRIVATE_DIRS = {".ssh", ".aws", ".kube", "private-runtime", "backups"}
# Only these common bind/loopback addresses are permitted beyond TEST-NET.
SAFE_MISC = {
    ipaddress.ip_address("0.0.0.0"),
    ipaddress.ip_address("255.255.255.255"),
    ipaddress.ip_address("::"),
    ipaddress.ip_address("::1"),
}


def is_example_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return ip in SAFE_MISC or ip.is_loopback or any(ip in net for net in DOC_NETS)


def filename_findings(path: str) -> list[str]:
    segments = PurePosixPath(path).parts
    issues = []
    if any(segment in PRIVATE_DIRS for segment in segments[:-1]):
        issues.append("private runtime directory")
    if segments and PRIVATE_NAMES.fullmatch(segments[-1]):
        issues.append("private artifact filename")
    return issues


def content_findings(text: str) -> list[str]:
    found = set()
    for label, rx in SECRETS:
        if rx.search(text):
            found.add(label)
    if ABS_HOME.search(text):
        found.add("absolute home-directory reference")
    for match in EMAIL.finditer(text):
        domain = match.group().rsplit("@", 1)[-1].lower()
        if domain not in {"example.com", "example.org", "example.net", "users.noreply.github.com"}:
            found.add("possible personal email address")
    for match in IPV4.finditer(text):
        try:
            ip = ipaddress.ip_address(match.group())
        except ValueError:
            continue
        if not is_example_ip(ip):
            found.add("non-example IPv4 literal")
    for match in IPV6.finditer(text):
        candidate = match.group()
        if candidate.count(":") < 2:
            continue
        try:
            ip = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if not is_example_ip(ip):
            found.add("non-example IPv6 literal")
    return sorted(found)


def tracked_paths() -> list[str]:
    proc = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "--cached"],
                          check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return [item.decode("utf-8", "strict") for item in proc.stdout.split(b"\x00") if item]


def audit_paths(paths: list[str], root: Path = ROOT) -> dict[str, list[str]]:
    issues = {}
    for path in sorted(paths):
        errors = filename_findings(path)
        # Path text can also contain credentials, private endpoints or home-directory names.
        errors.extend(content_findings(path))
        file = root / path
        if file.is_symlink():
            errors.append("tracked symlink forbidden")
        elif not file.is_file():
            errors.append("tracked file missing")
        elif file.stat().st_size > MAX_FILE_BYTES:
            errors.append("file too large for privacy scan")
        else:
            try:
                data = file.read_bytes()
                if b"\x00" in data:
                    if not approved_public_artwork(data, path):
                        errors.append("unscannable binary data")
                else:
                    try:
                        errors.extend(content_findings(data.decode("utf-8")))
                    except UnicodeDecodeError:
                        if not approved_public_artwork(data, path):
                            errors.append("unreadable or non-UTF8 content")
            except OSError:
                errors.append("unreadable or non-UTF8 content")
        if errors:
            issues[path] = sorted(set(errors))
    return issues



def _git(root: Path, *args: str, input_data: bytes | None = None) -> bytes:
    """Run a bounded, read-only Git query without invoking a shell."""
    return subprocess.run(
        ["git", "-C", str(root), *args],
        input=input_data,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=True,
        timeout=35,
    ).stdout


def introduced_history_findings(base: str, head: str, root: Path = ROOT) -> dict[str, list[str]]:
    """Inspect all blobs and filenames introduced between two Git commits.

    Scans intermediate commit objects even when a later commit deletes a file.
    The object range MUST be supplied by a trusted workflow, not PR-controlled
    text. This is a heuristic: it does not erase already published secrets.
    """
    for value in (base, head):
        if not re.fullmatch(r"[0-9a-f]{40}", value):
            raise ValueError("Expected two valid Git SHA-1 revision IDs")
    _git(root, "merge-base", "--is-ancestor", base, head)
    revision_range = f"{base}..{head}"
    raw_ids = _git(root, "rev-list", "--objects", "--no-object-names", revision_range)
    object_ids = raw_ids.decode("ascii").splitlines()
    if len(object_ids) > MAX_HISTORY_OBJECTS or any(
        not re.fullmatch(r"[0-9a-f]{40}", oid) for oid in object_ids
    ):
        raise ValueError("Git history object count or identity invalid")

    findings: dict[str, list[str]] = {}
    # -z is required: filenames may include newlines and non-ASCII characters.
    name_data = _git(root, "log", "--format=", "--name-only", "-z", revision_range)
    for raw_name in name_data.split(b"\x00"):
        if not raw_name:
            continue
        name = raw_name.decode("utf-8").lstrip("\n")
        if not name:
            continue
        issues = filename_findings(name) + content_findings(name)
        if issues:
            digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:16]
            findings[f"historical_path_sha256_prefix={digest}"] = sorted(set(issues))

    if not object_ids:
        return findings
    metadata = _git(root, "cat-file", "--batch-check",
                    input_data=("\n".join(object_ids) + "\n").encode("ascii"))
    entries = metadata.decode("ascii").splitlines()
    if len(entries) != len(object_ids):
        raise ValueError("Git history object metadata mismatch")
    total_bytes = 0
    for expected, item in zip(object_ids, entries):
        fields = item.split()
        if len(fields) != 3 or fields[0] != expected:
            raise ValueError("Git history object metadata invalid")
        kind, size_text = fields[1], fields[2]
        if kind not in {"blob", "tree", "commit", "tag"} or not size_text.isdecimal():
            raise ValueError("Git history object type or size invalid")
        if kind != "blob":
            continue
        size = int(size_text)
        total_bytes += size
        key = f"historical_blob_sha256_prefix={hashlib.sha256(expected.encode()).hexdigest()[:16]}"
        if size > MAX_FILE_BYTES or total_bytes > MAX_HISTORY_BYTES:
            raise ValueError("Git history privacy scan size limit exceeded")
        content = _git(root, "cat-file", "blob", expected)
        if len(content) != size:
            raise ValueError("Git blob length mismatch")
        try:
            if b"\x00" in content:
                if not approved_public_artwork(content):
                    findings[key] = ["unscannable historical binary data"]
            else:
                issues = content_findings(content.decode("utf-8"))
                if issues:
                    findings[key] = issues
        except UnicodeDecodeError:
            if not approved_public_artwork(content):
                findings[key] = ["unreadable historical UTF-8 content"]
    return findings

def main() -> int:
    try:
        result = audit_paths(tracked_paths())
        base = os.environ.get("PRIVACY_BASE_SHA")
        head = os.environ.get("PRIVACY_HEAD_SHA")
        if base or head:
            if not base or not head:
                raise ValueError("Both history revisions must be provided")
            result.update(introduced_history_findings(base, head))
        elif os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("GITHUB_EVENT_NAME") in {"pull_request", "push"}:
            raise ValueError("Missing history revisions in CI")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, UnicodeError, ValueError) as exc:
        print(f"PRIVACY CHECK BLOCKED: cannot enumerate or inspect Git history ({type(exc).__name__})", file=sys.stderr)
        return 2
    if result:
        for path, findings in result.items():
            fingerprint = hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]
            print(f"PRIVACY CHECK: path_sha256_prefix={fingerprint}: {', '.join(findings)}", file=sys.stderr)
        print("PRIVACY CHECK FAILED: inspect files locally; do not print secrets in logs.", file=sys.stderr)
        return 1
    print("Privacy heuristic PASS: tracked files contain no covered forbidden patterns.")
    print("This is not a comprehensive secret scan or proof of confidentiality.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
