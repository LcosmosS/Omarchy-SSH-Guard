# Security Policy

**Release v0.1.0 is a prototype, not an audited host-hardening product.**

## Responsible disclosure

If GitHub private vulnerability reporting is enabled, use the repository's **Security → Report a vulnerability** feature. Otherwise, request a private reporting channel without disclosing exploit details in public issues. Never attach real private keys, internal hostnames, access logs, credentials, SSH client allowlists, firewall backups or deployment receipts.

## Security properties

- No privileged apply operation, automatic remediation, SSH edits, daemon restarts, systemd changes, network calls or uploads.
- The Omarchy QML widget is static and does not launch programs, read files or request elevation.
- The Python CLI uses only read-only commands, with `shell=False`; unprivileged execution only.
- Reports contain booleans and aggregate counts, never raw inventories or real addresses.
- Unreadable state is marked unknown and the verdict is always `NOT_VERIFIED`.

## Boundaries and non-goals

Omarchy plugins execute within the user's unsandboxed desktop process. A trusted code review is required before installation. No claim is made for compromised local users, malicious administrators, kernel vulnerabilities, bad package provenance, malicious Docker sockets, upstream firewall/NAT rules, stolen SSH credentials, or internet reachability. A user in the `docker` group can generally obtain powerful privileges.

Do not run a file from `~/.local/bin` as root, modify broad SSH rules while remotely connected without local recovery, or cancel automatic rollback on unverified evidence.

## Private test fixtures

Synthetic `198.51.100.0/24` / `2001:db8::/32` documentation addresses are acceptable. Real network endpoints and logs are not. If sensitive material is accidentally committed, make the repository private immediately, rotate any exposed credentials and consult GitHub's sensitive-data removal guidance; deleting a line in a later commit does not remove it from history.
