# SSH-HARDEN-01b v2 and proposed patch test report

Review date: 2026-10-27. All executions were unprivileged. No production packet
rules, services, SSH settings, installed scripts or root runtime state were
modified. No test attempted a real network connection. Only source review,
temporary-file storage and mocked candidate operations were used.

## Results and limits

| Check | Result | What it establishes |
| --- | --- | --- |
| Supplied original suite | 23/23 passed | Original implementation behavior under its supplied mocks; private fixtures stayed in the source audit directory |
| Supplied v2 suite, standard Python | 58 passed, 1 skipped | The optional independent meta-schema check was unavailable initially |
| Supplied v2 suite, independent validator installed | 59/59 passed | The skipped meta-schema test also passes; it does not test schema instance semantics |
| Supplied total | 82 discovered; original claim of 81 passes + 1 skip reconciled | There are 23 original + 59 v2 definitions, not 81 total definitions |
| Additional candidate probes | 6 reproduced observations | Fabricated negative reports; schema disagreement; weak journal binding; failed cancellation; rollback cleanup; expired repeat-apply |
| Proposed patch unit suite | 23/23 passed (8 existing + 15 new) | Bounded parsing, diagnostic behavior, privacy, non-attestation, path/descriptor behavior and existing audit behavior |
| Independent proposed schema | Meta-schema, 4 positive + 34 negative instances passed | Real Draft 2020-12 validation with working date/IP/UUID format checkers; no skipped check |
| Candidate schema independently | Meta-schema and challenge/report/bundle positives pass; prefixed nonce also passes unexpectedly | Schema is valid but disagrees with candidate runtime full-string patterns |
| Final syntax / privacy review | Python/JSON/Bash syntax and whitespace checks passed; 14-file allowlist scan found no private endpoints/key blocks/runtime artifacts | Heuristic scan plus manual diff review; not a general secret detector |

The supplied source manifest's five listed digests matched. The sixth deliverable,
the diff, is outside that unsigned manifest. This is consistency checking, not
publisher authentication. Python 3.12.15 was used. The isolated development
environment used jsonschema 4.26.0, rfc3339-validator 0.1.4 and the pinned support
packages in `requirements-schema.txt`; no packages were installed system-wide.
The RFC3339 dependency matters: FormatChecker may otherwise silently lack a
date-time checker. The new independent check asserts all required checkers exist.

## Commands and reproducibility

The original suites were run from the supplied audit directory using Python
`-B -m unittest discover` with each test filename, and v2 rerun in an isolated
`/tmp` environment with jsonschema installed. No deployment shell command from
the source plan was executed. The candidate collector's `--help` subprocess is
the only real candidate subprocess in those tests; mutation and client processes
are mocked. Original tests read their local private policy but no private fixture
was copied into the integration branch.

The final combined supplied suite also passed all 82 tests with the independent
validator installed. Source syntax was compiled without running candidate main
functions; Bash syntax checks included the v2 wrapper. CI is configured but has
not been remotely run. The unchanged plugin's manifest/path validation was run
through the existing local `scripts/check.sh`; no plugin was installed or enabled.

The added local probe script is `/tmp/ssh_guard_candidate_probes.py`, outside Git.
It imports the reviewed synthetic v2 fixture classes and uses no live state or
network helpers. It asserts the following observations against the supplied code:

| Probe | Setup | Observed result and scope |
| --- | --- | --- |
| P1 / F01 | Valid simulated baseline/auth witnesses; construct and MAC both negative reports; make client helper calls raise | `validate_post == []` without a probe; enrolled-key-holder trust gap |
| P2 / F07 | Add a prefix/suffix to a nonce; enable independent format checking | Schema accepts, candidate runtime rejects |
| P3 / F06 | Feed an authorized report a normalized matching event with no destination/boot/nonce | Accepted witness; static representation has no such binding, not proof of a live cross-host attack |
| P4 / F03 | Complete synthetic post evidence; raise in `stop_timer()` after phase save | State verified, timer active, automatic rollback no-op, later verify falsely says cancelled |
| P5 / F05 | Raise in `stop_timer()` after rollback state save | State rolled_back, timer active, repeated rollback skips cleanup |
| P6 / F05 | Pending state with expired deadline; mocked timer active | Repeated apply returns no-op without rejecting expiry |

These probes intentionally demonstrate defects, so their assertions pass when
the candidate exhibits the defect. They are not tests of a corrected executor.
They are excluded from default public CI to avoid executing external untrusted
candidate code or importing private fixtures. A future executor remediation must
turn each defect into a failing-then-fixed regression in its own isolated suite.

To verify the proposed public patch:

```bash
python3 -B -m unittest discover -s tests -v
python3 -B tests/schema_contract.py
```

The second command requires the development dependencies and intentionally fails
if the independent validator/checkers are unavailable. CI installs the pinned
development requirements and runs it without a skip path. The stdlib linter is a
restricted validator, not a general schema implementation; integral float
encodings, noncanonical IP/UUID text and non-UTC timestamps are intentionally
stricter than general JSON Schema. No cryptographic acceptance is implemented.

## Review of all supplied cases

Every definition in both test files was read. The inventory below preserves only
test identifiers and source line numbers, never fixture content. PASS means the
supplied assertion passed against its intended implementation, not that it proves
the broader security property implied by its name.

Coverage qualifications used in the inventory:

- **Legacy parser/gate**: v1 behavior, sometimes private policy fixtures; cannot
  establish v2 provenance, strict input or root installation security.
- **Legacy transaction model**: commands, timer, storage and firewall state are
  mocked; no real systemd/UFW crash or reboot evidence.
- **Collection fixture**: real JSON writes and MAC checks with synthetic secrets,
  constructed reports and synthetic journal/interface/time; root storage checks
  replaced. Does not run clients or establish observation truth.
- **Storage/schema fragment**: tests a narrow failure/property; not a complete
  owner/mode/race/JSON Schema acceptance matrix.
- **Client argv/socket model**: subprocess or socket mocked; validates requested
  options or classification, not client executable/config/route integrity.
- **V2 transaction model**: arm/stop/save/security/gates/commands are replaced;
  misses manager state, power interruption, real filesystem durability and commit
  gaps. Constructed reports in this model are not actual network evidence.
- **Login/journal model**: synthetic text/metadata and mocked effective settings;
  no live journal coverage, event loss or challenge-bound destination witness.

Specific overclaims: the v2 `test_schema_has_no_unknown_fields_and_no_boolean_ports`
only passes an incomplete object, so it does not separately exercise unknown
fields or boolean ports. Its ownership test does not separately exercise a
symlink despite the name. The changed source/destination/path/nonce rejection
tests often fail at stored-challenge equality before reaching the deeper semantic
check. The route-loss collection test changes report fields; a separate client
test covers a mocked bind error. The atomic failure test injects `os.replace`
failure, not power loss, fsync failure or a failed directory flush. The optional
schema test checks only `check_schema`, not valid/invalid document acceptance.

## Threat scenarios still missing from the supplied suites

1. Dishonest enrolled signer and server-held MAC forgery; deliberate free-port
   selection to evade contradiction; authorized-login/nonce witness substitution.
2. Full root boundary matrix: malicious owner/mode for each ancestor, symlink and
   hardlink races, protected installation swap, altered code/schema digest,
   inherited loader variables, executable PATH/config spoofing, client key owner
   and unauthenticated challenge replacement. No root escalation claim is made.
3. Actual systemd elapsed-active timers, disabled enablement, changed loaded
   drop-ins, wrong service, stale queued invocation/run and persistent timestamp,
   service already active, start failures, timeout/retry and lock contention.
4. Process kill/reboot/power cut at every write and transition, including unit
   publication, enablement, mutation, verified save, timer cancellation, rolled-back
   save and cleanup. Disk full, short write, fsync and directory-fsync failure.
5. Recovery with missing collector/schema/Docker/Python package dependencies,
   partially installed units, corrupted transaction, partial restore and external
   UFW changes; both live kernel and persisted-rule restoration, twice.
6. Clock rollback/advance, suspend, new boot, daylight/time sync behavior; journal
   source/destination reuse, wrong boot/invocation, truncated 10,000-record window,
   rotation/rate limits, delayed/duplicate/malformed fields and cursor substitution.
7. Real independent IPv4/IPv6 clients, DHCP/privacy-address rotation, NAT/source
   translation, lost route, VPN/proxy, TCP-specific upstream filtering, spoofed
   ICMP/refusal/banner, blocked ICMP with working TCP and actual host-key policy.
8. Enrollment/begin/issue happy paths with actual protected storage, preserving
   prior state, authenticated provisioning, key revocation/rotation and safe reset.
9. Deep/huge/noncanonical JSON, format-validator divergence, duplicate fields at
   each nesting level, expired post import and interrupted receipt/bundle writes.

Some parsing/privacy scenarios now have public linter tests. That does not fix or
validate the excluded candidate. QML is unchanged; no live Omarchy enable/disable,
privileged prepare, remote login, recovery rehearsal or penetration test was run.

## Complete supplied-case inventory

The following tables are extracted from AST test definitions after manual source
review; definitions are grouped by their original classes.

### `test_ssh_hardening.py` — `SafetyTests`

Qualification: **Legacy parser/gate**.

| Source line | Test | Reviewed result |
| --- | --- | --- |
| 12 | `test_auth_accepts_camelcase_and_lowercase` | PASS |
| 19 | `test_no_complete_auth_on_empty_success` | PASS |
| 22 | `test_rejects_broad_or_local_sources` | PASS |
| 25 | `test_policy_rejects_additional_source_for_this_milestone` | PASS |
| 31 | `test_cannot_stop_an_unowned_timer` | PASS |
| 37 | `test_unverified_access_blocks` | PASS |
| 44 | `test_unreviewed_login_source_blocks` | PASS |
| 55 | `test_login_requires_new_matching_authentication` | PASS |
| 76 | `test_verify_requires_both_families_and_correct_target` | PASS |
| 85 | `test_old_run_and_false_success_cannot_finalize` | PASS |
| 88 | `test_post_test_must_match_the_recorded_baseline_source_and_path` | PASS |
| 93 | `test_baseline_must_be_recent_unauthorized_and_actual_destination` | PASS |
| 101 | `test_user_owned_script_or_policy_is_not_trusted` | PASS |
| 105 | `test_timer_uses_exactly_15_minutes_and_protected_entrypoint` | PASS |

### `test_ssh_hardening.py` — `TransactionTests`

Qualification: **Legacy transaction model**.

| Source line | Test | Reviewed result |
| --- | --- | --- |
| 149 | `test_no_approval_no_mutation` | PASS |
| 152 | `test_gates_before_backup_and_timer` | PASS |
| 156 | `test_timer_first_and_apply_idempotent` | PASS |
| 165 | `test_rollback_restores_broad_before_removing_new_source` | PASS |
| 173 | `test_failure_during_restriction_rolls_back` | PASS |
| 178 | `test_automatic_rollback_does_not_undo_verified_state` | PASS |
| 182 | `test_repeated_apply_rejects_protected_runtime_drift` | PASS |
| 187 | `test_automatic_deadline_restores_access_after_pending_validation` | PASS |
| 193 | `test_failed_validation_cannot_cancel_rollback_timer` | PASS |

### `test_ssh_hardening_v2.py` — `CollectionTests`

Qualification: **Collection fixture**.

| Source line | Test | Reviewed result |
| --- | --- | --- |
| 143 | `test_challenge_client_identifier_cannot_traverse_storage` | PASS |
| 147 | `test_successful_signed_collection_and_new_run` | PASS |
| 154 | `test_missing_ipv6_baseline_blocks_predeployment` | PASS |
| 160 | `test_empty_post_file_is_created_and_never_passes` | PASS |
| 166 | `test_unsigned_or_fabricated_client_report_rejected` | PASS |
| 171 | `test_authorized_login_without_journal_is_rejected` | PASS |
| 176 | `test_baseline_tcp_claim_without_server_witness_is_rejected` | PASS |
| 181 | `test_signed_report_still_requires_operator_attestation` | PASS |
| 184 | `test_replay_and_duplicate_slot_rejected` | PASS |
| 190 | `test_changed_challenge_nonce_cannot_be_signed_into_acceptance` | PASS |
| 195 | `test_missing_source_port_and_wrong_type_fail_closed` | PASS |
| 200 | `test_naive_non_utc_and_invalid_timestamps_rejected` | PASS |
| 205 | `test_timestamp_mismatch_with_journal_rejected` | PASS |
| 210 | `test_future_and_expired_report_rejected` | PASS |
| 217 | `test_stale_complete_baseline_rejected` | PASS |
| 222 | `test_baselines_must_remain_fresh_for_the_full_rollback_window` | PASS |
| 228 | `test_wrong_source_destination_or_network_path_rejected` | PASS |
| 233 | `test_removed_target_address_invalidates_baseline` | PASS |
| 237 | `test_authorized_source_cannot_be_negative_client` | PASS |
| 242 | `test_post_authentication_must_be_after_apply` | PASS |
| 247 | `test_old_deployment_run_cannot_be_reused` | PASS |
| 252 | `test_successful_unauthorized_tcp_is_failure` | PASS |
| 258 | `test_route_loss_bind_error_or_failed_control_is_inconclusive` | PASS |
| 264 | `test_timeout_contradicted_by_server_connection_is_failure` | PASS |
| 271 | `test_rolled_back_transaction_cannot_collect_or_finalize` | PASS |
| 276 | `test_deadline_expired_cannot_finalize` | PASS |
| 281 | `test_bundle_tampering_or_changed_immutable_receipt_rejected` | PASS |
| 286 | `test_post_record_requires_same_client_as_baseline` | PASS |
| 297 | `test_wrong_post_baseline_link_is_rejected` | PASS |
| 306 | `test_crash_after_receipt_write_can_recover_without_fabrication` | PASS |

### `test_ssh_hardening_v2.py` — `StorageAndSchemaTests`

Qualification: **Storage/schema fragment**.

| Source line | Test | Reviewed result |
| --- | --- | --- |
| 313 | `test_json_duplicate_keys_nonfinite_and_symlink_rejected` | PASS |
| 322 | `test_atomic_failure_preserves_previous_complete_file` | PASS |
| 331 | `test_exclusive_receipt_is_never_overwritten` | PASS |
| 337 | `test_unprivileged_storage_and_symlink_rejected` | PASS |
| 342 | `test_schema_has_no_unknown_fields_and_no_boolean_ports` | PASS |
| 345 | `test_json_schema_is_valid_draft202012_when_validator_available` | PASS (initially skipped; later independent run passed) |
| 352 | `test_root_collector_has_no_apply_or_finalize_subcommand` | PASS |

### `test_ssh_hardening_v2.py` — `ClientTests`

Qualification: **Client argv/socket model**.

| Source line | Test | Reviewed result |
| --- | --- | --- |
| 360 | `test_client_ssh_forces_fresh_key_auth_and_host_key_verification` | PASS |
| 374 | `test_client_wrong_server_report_is_inconclusive` | PASS |
| 379 | `test_ping_control_uses_exact_family_source_and_destination` | PASS |
| 386 | `test_route_and_bind_errors_never_become_timeout` | PASS |

### `test_ssh_hardening_v2.py` — `TransactionTests`

Qualification: **V2 transaction model**.

| Source line | Test | Reviewed result |
| --- | --- | --- |
| 450 | `test_prior_approval_does_not_authorize_second_deployment` | PASS |
| 454 | `test_evidence_file_and_timer_precede_firewall_change` | PASS |
| 460 | `test_missing_evidence_cannot_cancel_rollback` | PASS |
| 465 | `test_incomplete_evidence_finalization_fails_with_timer_armed` | PASS |
| 470 | `test_failed_finalization_followed_by_deadline_rollback_restores_access` | PASS |
| 477 | `test_deadline_crossing_during_finalization_keeps_rollback_armed` | PASS |
| 483 | `test_all_three_genuine_reports_then_existing_verify_finalizes` | PASS |
| 491 | `test_missing_finalize_approval_preserves_pending_timer` | PASS |
| 496 | `test_validation_drift_cannot_finalize` | PASS |
| 502 | `test_automatic_rollback_restores_original_rows_and_ends_transaction` | PASS |
| 510 | `test_mutation_failure_restores_access_automatically` | PASS |
| 516 | `test_collector_failure_prevents_timer_and_firewall_changes` | PASS |
| 522 | `test_automatic_rollback_does_not_undo_verified_transaction` | PASS |
| 529 | `test_separate_timer_uses_protected_v2_entrypoint` | PASS |

### `test_ssh_hardening_v2.py` — `LoginAuditTests`

Qualification: **Login/journal model**.

| Source line | Test | Reviewed result |
| --- | --- | --- |
| 538 | `test_password_keyboard_interactive_and_root_password_auth_block_apply` | PASS |
| 562 | `test_original_transaction_and_timer_must_have_ended` | PASS |
| 568 | `test_verified_login_rejects_naive_time_boolean_port_password_and_wrong_journal` | PASS |
| 580 | `test_journal_reader_rejects_forged_user_messages` | PASS |

## Review findings and governance-rebase addendum — 2026-10-27

PR #3's Sourcery review identified two structural-test shortcomings:

- The `source_port` schema constraint was tightened from minimum `0` to `1`, with zero added to the runtime linter's negative unit fixtures and the independent JSON Schema validation fixtures. The revised schema contract expects **4 positive and 35 negative** fixtures; the earlier 4/34 figures above describe the original proposal.
- The filesystem parent-rename test now asserts that the injected replacement actually executed and that the expected moved directory and symlink exist. It fails if implementation changes accidentally bypass the simulated race.

The original negative IPv6 zone-ID example was changed to the reserved documentation prefix with a zone identifier; it remains intentionally invalid for canonical address validation but no longer embeds a real-world link-local address in tracked source. The proposal was reconciled with the merged repository governance files and consolidated into a single reviewable commit based on `main`; the original `8a116bf` / `e63691f` identifiers above remain historical references to the earlier draft, **not hashes of the revised final tree**. GitHub CI and the privacy history check must be rerun after the consolidation; historical test counts are not claims of new independent deployment assurance.
