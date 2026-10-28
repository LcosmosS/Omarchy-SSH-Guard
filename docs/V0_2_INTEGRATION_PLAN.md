# Proposed v0.2 integration plan

Decision: accept a read-only evidence-format experiment for review; reject the
candidate executor and operational collector for integration at this time.
Branch: `review/v0.2-evidence-only`. No deployment, merge, push or release is
authorized by this patch. Version metadata deliberately remains v0.1.0.

## Concrete proposed patch

- Add `schemas/ssh-evidence-v2.schema.json`, derived only from the reviewed generic
  schema, with explicit complete-string patterns and an honest structure-only scope.
- Add `bin/omarchy-guard-evidence`, an optional source-checkout offline linter.
  It never loads signing keys, executes clients, reads journals, writes evidence,
  requests privilege or changes a firewall/service. All verdicts remain
  `NOT_VERIFIED` and deployment authorization is always false.
- Add synthetic parser, privacy, symlink/race, malformed-input, freshness and
  non-attestation tests, and mandatory independent Draft 2020-12 instance checks
  in CI. Runtime stays stdlib-only; validator packages are development-only.
- Add architecture/threat model, prioritized review, complete supplied-test
  inventory and test report. Strengthen private-runtime ignore rules.
- Preserve audit, plan, QML, plugin activation and user-level installation behavior.

The root shell/Python executor, root collector, original tests/policy, deployment
plan/diff and all operational artifacts are excluded. No installation command,
sudoers rule, systemd template or automatic finalization hook is added.

## Local review of this proposal

```bash
python3 -B -m unittest discover -s tests -v
python3 -B tests/schema_contract.py  # requires requirements-schema.txt in a dev environment
python3 -B bin/omarchy-guard-evidence /private/local/example.json
```

The last command reads an operator-selected file without printing its contents.
Exit 0 means structurally valid JSON, not authenticated, complete, safe or approved
evidence. It accepts incomplete bundle shapes and does not decide semantic policy.
Run as the ordinary user. Keep any real input outside the checkout. These are
review commands, not a deployment runbook. The existing `scripts/check.sh` remains
available; its optional Omarchy validation depends on a live installed runtime.

## Human review gates before merging this limited patch

Review findings F01–F10, the narrow linter authority, schema canonicalization
differences, dependency pins, privacy scan and synthetic test results. Confirm
that no new UI or installer path invokes privileged code. Decide whether the
legacy milestone dialect should remain or become a separately versioned generic
wire format before committing to compatibility. Only then consider a version
bump and release review in a separate authorized step.

## Separate future work, blocked from this patch

| Gate | Required evidence before reconsidering privileged integration |
| --- | --- |
| Evidence authority | A specified independent measurement trust model; fabricated-key-holder rejection tests; no promotion of MAC validity to network truth |
| Generic policy | Strict reusable policy/transaction schemas; no literal deployment inventory/account or prerequisite private transaction |
| Installation | Audited protected installer/launcher, expected executable provenance, safe loader environment and no user-checkout root execution |
| Recovery | Minimal recovery dependencies; durable arm/mutate/commit protocol; boot reconciliation and retryable end-state cleanup |
| Timer integrity | Bound run identity, actual loaded unit/drop-in verification, pending future deadline, stale service/timestamp/reuse handling |
| Filesystem faults | Symlink/hardlink/ancestor races, owner/mode attacks, ENOSPC/EIO/fsync failure and partial-publication fault injection |
| Journal/clock | Exact destination and nonce witness, boot/monotonic binding, cursor identity/coverage, truncation/delay/clock-step cases |
| Operational rehearsal | Disposable VM, isolated IPv4/IPv6 clients, real systemd/UFW behavior, reboot/power cut at every transition and fresh access after restore |
| Approval | Findings reviewed, separate explicit scope/host approval, private enrollment and console recovery established |

Tests must remain synthetic or run in disposable isolated environments. A future
approved live rehearsal must not publish endpoints, keys, journals, receipts,
backups or transaction files. This review does not install dependencies into the
host system or change production settings.
