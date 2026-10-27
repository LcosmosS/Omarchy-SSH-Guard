# Contributing

This is a security-sensitive, currently **read-only** Omarchy plugin. Please use issues to propose changes before adding a privileged helper.

- No real IP addresses, hostnames, device IDs, public/private keys, access logs, SSH fingerprints, tokens, docker inspect dumps, or firewall archives.
- Use reserved example networks (`198.51.100.0/24`, `203.0.113.0/24`, `2001:db8::/32`).
- Every parser change needs deterministic tests and negative/unknown-state cases.
- Never make an audit claim `SECURE` or equivalent solely from local observations.
- Changes to the root/user privilege boundary require separate threat-model review.
- Run `./scripts/check.sh` and validate QML using `omarchy plugin validate .` on Omarchy.
- Keep network tests opt-in and controlled by the operator; never probe third-party addresses.
- Public security disclosures must not contain exploitable credentials or private network evidence.

License: MIT; contributions are submitted under the repository license.
