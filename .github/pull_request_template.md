## Change summary

Describe the change and its trust-boundary implications.

## Security and privacy review

- [ ] Changes contain no real SSH keys, fingerprints, host identities, client allowlists, firewall backups, journal exports, receipts or deployment evidence.
- [ ] Synthetic addresses and fixtures only; no private credentials, authentication tokens or personal contact details.
- [ ] No changes to live SSH, UFW, Docker, DNS or systemd services.
- [ ] User-writable plugin/CLI code is not executed as root.
- [ ] New external dependencies and GitHub Actions permissions are justified.
- [ ] A new privileged action (if proposed) is reviewed separately; it must not be silently enabled in this PR.
- [ ] CODEOWNERS changes (if any) are recorded in `docs/CODEOWNERS_LOG.md`.

## Validation

Provide reproducible tests and their results. Explicitly list skipped, unknown, and host-only validations.

- [ ] Unit tests / CI
- [ ] Privacy guard
- [ ] CodeQL results reviewed
- [ ] Live Omarchy widget validation (if QML changed)
- [ ] Independent security review (if trust boundary changed)

## Non-claims

Do not describe offline success as proven external network isolation, verified rollback, or a secure workstation. Do not attach host-specific proof to this public PR.
