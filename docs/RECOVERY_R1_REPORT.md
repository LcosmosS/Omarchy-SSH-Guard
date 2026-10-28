# SSH-HARDEN-R1 reference-model validation report

Classification: **R1_REFERENCE_MODEL_VALIDATED**.

Branch: `security/recovery-gate-r1`. Baseline: `de42d91` from current `origin/main`.
Identify the completed artifact revision by this report's containing local Git
commit; the final handoff supplies that SHA. The branch was subsequently
published for review as PR #5 (`security/recovery-gate-r1`). Publication
does not authorize merge, release, or deployment.
Next decision: **independent security review by LibertySquared**.

## Delivered files and scope

The following six files were added for the R1 reference model:

- `docs/RECOVERY_STATE_MACHINE.md` — fault model written before the tests,
  transition table, publication barriers, interruption policy and invariants.
- `tests/support/__init__.py` — explicit non-production test package.
- `tests/support/recovery_model.py` — in-memory storage, clock, timer, firewall,
  fault injector and protocol controller; no host-effect adapters.
- `tests/test_recovery_fault_matrix.py` — deterministic conformance, fault matrix,
  independent observation/durability oracles and mutation-detection tests.
- `docs/RECOVERY_VM_VALIDATION.md` — future disposable-VM execution procedure,
  harness prerequisites, 28-row matrix and exact evidence gates; all NOT RUN.
- `docs/RECOVERY_R1_REPORT.md` — this report and independent-review checklist.

After the original local R1 milestone, this public PR also modified `README.md`,
`scripts/privacy_guard.py` and `tests/test_privacy_guard.py`, and added the
self-contained artwork `assets/omarchy-ssh-guard-shield.svg`,
`assets/omarchy-ssh-guard-badge.svg` and
`assets/omarchy-ssh-guard-overview.webp`.
The privacy guard changes allow only the digest-pinned public artwork; they are
subject to the privacy workflow and regression tests.

The read-only plugin, audit CLI, evidence linter/schema, installer, SECURITY.md,
CODEOWNERS and all three workflows match the inspected baseline. The privacy
scanner and its tests **did change** in this PR.
No governance settings or branch protections were changed. Existing CI discovers
the new tests without workflow changes. The initial worktree was clean; no local
changes were discarded. Fetching current `main` and creating the local branch
updated Git metadata only.

## Recovery protocol

Preparation publishes a run lease, capsule, service image and durable preparation
record. Arming requires a structured observation of the exact loaded run/config,
boot and bounded future deadline. Restriction follows a durable `MUTATION_INTENT`
and another arming/mechanism check. Live and persisted firewall images are distinct.

Uncommitted reconciliation restores the exact baseline, then retries cleanup.
An immutable synthetic commit marker is authoritative even if the cached phase
lags behind it. Committed reconciliation retains the expected restriction and
retries cleanup after restart/expiry. Cancellation return codes never suffice:
completion requires observed inactive/disabled timer, idle service and empty
queue. A terminal record is reobserved rather than trusted indefinitely. Missing
essential metadata or committed-firewall drift reports `RECOVERY_BLOCKED` without
guessing a restore or claiming successful finalization.

The controller cannot access the test-only durable-image oracle. Test code
independently inspects the acknowledged bytes captured at every restrictive effect.
The storage model exercises temporary bytes, file sync, rename, directory sync and
readback as separate boundaries. After an interrupted unsynced rename, both old
and fully file-synced new publication outcomes are modeled. This does not establish
actual storage durability.

The only positive commit input is an explicitly injected `SyntheticApproval`
bound to run/plan/review. It is a test assumption, not a credential or implemented
authorization policy. Structurally valid, attested or MAC-shaped evidence does not
authorize retention. Every result denies deployment authority and carries
`REFERENCE_MODEL_ONLY` / VM `NOT_RUN`.

## Exact offline results

| Validation | Result | Interpretation |
| --- | --- | --- |
| Initial local R1 suite (historical) | **92 passed** at initial submission | 44 existing + 48 initial R1 methods; not current PR acceptance count |
| Initial R1 methods (historical) | **48 passed** | New T49–T58 are listed below; use final CI for current count |
| Initial grouped cases (historical) | **500 passed** | Initial 464 modeled power cases + 36 other grouped cases, not current PR results |
| Initial power-model matrix (historical) | **464 passed** | Historical commit/rollback checkpoint counts; final-PR count is generated dynamically and must be read from CI |
| False-cancellation negative control | **Expected rejection observed** | Mutated controller caused ordinary T12 to fail once |
| Missing-intent negative control | **Expected rejection observed** | Mutated controller caused both ordinary T08 subcases to fail |
| Built-in mutation guards | **T36/T37 passed** | Independent oracles reject each bad implementation; mutations scoped to tests only |
| Unused-fault guard | **T38 passed** | A designated but unreached hook raises an assertion |
| Independent schema | **Meta-schema + 4 positives + 35 negatives passed** | Current CI contract; FormatChecker dependencies enabled |
| Python syntax | **PASS** | New model and fault suite compile; no new runtime imports |
| AST host-effect/oracle boundary | **PASS (T39)** | Model imports only copy/dataclasses/enum/hashlib/json/re; Controller never reads durable oracle |
| Privacy working tree / introduced history | **PASS on initial local R1 baseline** | The public PR later changed the scanner and its tests for digest-pinned artwork; check current-head Privacy CI independently |
| Protected baseline comparison | **13 files identical** | Runtime/UI/schema/installer/security/governance paths checked byte-for-byte |
| Whitespace check | **PASS** | No diff whitespace errors |
| Ruff | **NOT RUN — unavailable** | Stdlib compilation and the explicit AST boundary test ran |
| CodeQL / remote CI | **PASS on initial head** | Runs 40612902769 (CodeQL), 40612902838 (unit/schema), 40612902693 (privacy) passed on `fec92ab`. Repeat after review fixes |
| VM tests V01–V28 | **NOT RUN / BLOCKED on reviewed VM-only implementation and separate authorization** | No live systemd, UFW, SSH, reboot or guest power-cut result |
| Physical storage/power loss | **NOT RUN** | Memory-model success does not establish this property |

The existing privacy test file emits two Python SyntaxWarnings about its existing
backtick escape on import. Its tests pass; the file is unchanged. These are
baseline warnings, not skipped checks or suppressed scanner findings.

Run the ordinary suite with:

```bash
python3 -B -m unittest discover -s tests -v
python3 -B -m unittest discover -s tests -p 'test_recovery_fault_matrix.py' -v
python3 -m py_compile tests/support/recovery_model.py tests/test_recovery_fault_matrix.py
```

Run `tests/schema_contract.py` in the development environment established by
current CI's `requirements-schema.txt` procedure. Run the current, reviewed
`scripts/privacy_guard.py` with trusted baseline/head revision inputs after the
local commit. Do not run the VM protocol on the current workstation.

## Finding → invariant → test → result → remaining limitation

Use `Tnn` for the matching `test_nn_...` method in the inventory below.

| Finding_ID | Invariant | Test_ID | Test_Result | Remaining_Limitation |
| --- | --- | --- | --- | --- |
| F02 | R1 recovery independence | T01–T04, T30, T39, T43, T46, T53–T54 | PASS; poisoned optional registry never consulted | Actual recovery executable/library dependency closure and V01–V04 NOT RUN; essential mechanism still required |
| F04 | R2 durable preparation | T05–T08, T20–T22, T26, T37, T43, T47, T50 | PASS; missing-intent mutant rejected | Real file/directory sync, durable code/unit enablement and firewall persistence require V05–V08/V20–V26 |
| F03 | R3 truthful finalization | T10–T13, T28, T36, T41, T45, T56–T57 | PASS; false-ack mutant rejected | Actual loaded manager config, queue observations and cancellation atomicity require V09–V13/V28 |
| F03/F04 | R4 crash consistency | T05, T07–T10, T20–T27, T33–T35, T41, T45–T46, T48–T52, T58 | PASS for enumerated model outcomes; explicit blocked results for corruption | Single-fault nominal path enumeration plus targeted retries is not a proof for all concurrent/multiple hardware faults; real cuts NOT RUN |
| F05 recovery | R5 run isolation | T16–T17, T32, T40, T48, T51 | PASS; stale calls do not change current run | No real process locks, privilege boundaries or loaded stale-job execution tested; V16–V17 required |
| F05 recovery | R6 idempotent recovery | T18–T19, T33, T46, T52–T54, T58 | PASS; interrupted restore/cleanup converges | Actual dual-family rule bytes/access and retry lifecycle require V18–V19 |
| F05 recovery | R7 deadline enforcement | T14–T15, T23–T24, T29, T44, T47, T55 | PASS; expired/invalid clock/timer rolls back or blocks | Kernel clocks, suspend, real next-elapse/service state and boot ordering require V06/V14–V15/V23–V24/V27 |
| F01 boundary, excluded | R8 fail-closed authorization | T31–T32 and fixed denial in every Result | PASS for evidence rejection and explicit synthetic decision assumption | F01 is not remediated; no real independent authority implemented; production retention remains unauthorized |
| Cross-cutting | R9 no misleading assurance | T26–T27, T39, T49, Result assurance checks and VM ledger | PASS for model labels/claims | All live/physical gates remain NOT RUN; independent review required |

## Provisional disposition

Treat F02's dependency separation, F03's commit/cleanup protocol, F04's publication
ordering and the recovery portions of F05 as **addressed in this reference design
and its bounded offline model only**. Keep their implementation/integration/VM
validation gates BLOCKED. Do not close the original findings from this report.

Keep F01 and other excluded security findings outside this milestone. Do not infer
host reachability, evidence honesty, a secure privilege boundary, package integrity
or readiness for production from a test-approved synthetic decision.

## Known limitations and blocked validation entries

- Assume serialized operations, trusted numeric clock samples, honest structured
  adapter observations and a functioning minimal restoration mechanism. Test the
  actual interprocess locking/ownership/TOCTOU boundary independently later.
- Model only specified atomic file publication and permitted old/new rename
  outcomes. Do not infer real filesystem/controller/cache/flush behavior from
  MemoryDisk. Keep F04 blocked until storage-specific VM evidence exists.
- Use symbolic baseline/restricted image identifiers, not real rule evaluation.
  Keep real kernel/UFW persisted-state equivalence and external dual-family SSH
  behavior blocked until independent VM observations exist.
- Treat damaged essential metadata and absent restoration mechanism as explicit
  blocked recovery. This is a limitation requiring OOB intervention, not successful
  restoration or an invariant waived to obtain a passing classification.
- Treat timer properties as injected observations. Reject false cancellation
  acknowledgement against those observations, but require real independent
  systemctl/unit/drop-in/queue inspection before any systemd assurance claim.
- Keep all 28 VM rows NOT RUN. The future VM-only privileged harness is intentionally
  absent and requires its own review and authorization. A process restart is not a
  VM power cut; a VM destroy/start is not physical host/storage power-loss proof.
- Keep raw VM/host evidence outside Git. This patch contains only synthetic data
  and source/specification. No real keys, endpoints, accounts, snapshots, journals,
  backups, transaction records or operational evidence were imported.

## LibertySquared independent-review checklist

- [ ] Confirm the clean-worktree start and `de42d91` baseline, the
  published PR #5 tree against the reviewed local commit, and that no
  merge, tag, release or production deployment occurred.
- [ ] Review the independently rechecked F02–F05 source facts without treating
  historical assertions as live evidence; do not execute rejected scripts.
- [ ] Compare the transition table with every Controller event and blocked outcome;
  verify commit-marker authority when cached phase lags.
- [ ] Verify no restrictive effect can precede durable intent, restoration image,
  run/service binding and a correct future timer observation.
- [ ] Inspect storage stage ordering, both unsynced-rename outcomes and per-occurrence
  checkpoint coverage; distinguish process/reboot/power-model faults.
- [ ] Verify recovery never consults collector/Docker/journald/QML/CodeQL or unrelated
  packages; inspect the explicit essential-mechanism failure outcome.
- [ ] Verify terminal phase cannot substitute for independent cancellation or rule
  observation; exercise false ack, cleanup retries after expiry and timer reactivation.
- [ ] Verify stale A cannot alter B, and corrupt old-run state cannot be silently
  overwritten by a new preparation.
- [ ] Rerun the **complete suite, R1 method inventory and power-case count on
  the final PR head**; compare with the actual current-head CI logs (do not use
  the historical 92-test / 464-case totals as acceptance criteria). Confirm
  zero skips and actual fault-hook hits; reproduce both negative controls.
- [ ] Verify the controller does not consult the durability oracle and the oracles
  do not simply reuse the controller's timer-validation functions.
- [ ] Confirm `SyntheticApproval` is only a test assumption, no evidence authorizes
  retention, and every result denies deployment authority.
- [ ] Rerun independent schema/privacy/history/static checks without weakening the
  scanner, CODEOWNERS, CodeQL or branch protections.
- [ ] Review all VM prerequisites, isolation, OOB access, actual adapter observations,
  storage/cut evidence and closure criteria; leave every unexecuted row NOT RUN.
- [ ] Record findings and the next independent review decision. Do not approve a
  production deployment from this milestone classification.

## Complete R1 method inventory

Each row denotes one R1 unittest method in the current PR proposal. Verify
its passing status against current-head CI; grouped cases are additional
assertion contexts, not extra method counts. All injected
faults use an explicit label/occurrence and an exactly-once hit assertion.

| Test_ID | Method | Result |
| --- | --- | --- |
| T01 | `test_01_missing_collector_during_rollback` | PASS |
| T02 | `test_02_missing_docker_during_rollback` | PASS |
| T03 | `test_03_missing_journald_during_rollback` | PASS |
| T04 | `test_04_missing_unrelated_python_package` | PASS |
| T05 | `test_05_interrupted_recovery_preparation` | PASS |
| T06 | `test_06_no_mutation_without_durable_arming_and_intent` | PASS |
| T07 | `test_07_failure_immediately_before_restrictive_effect` | PASS |
| T08 | `test_08_failure_after_live_or_persisted_mutation` | PASS |
| T09 | `test_09_crash_before_commit_marker_publication` | PASS |
| T10 | `test_10_crash_after_durable_marker_before_cancellation` | PASS |
| T11 | `test_11_timer_cancellation_failure` | PASS |
| T12 | `test_12_false_cancellation_acknowledgement` | PASS |
| T13 | `test_13_repeated_decision_retries_interrupted_cleanup` | PASS |
| T14 | `test_14_expired_repeated_apply_rolls_back` | PASS |
| T15 | `test_15_active_timer_without_future_elapse` | PASS |
| T16 | `test_16_mismatched_expected_transaction_id` | PASS |
| T17 | `test_17_stale_invocation_cannot_touch_next_run` | PASS |
| T18 | `test_18_repeated_rollback_converges_without_extra_effect` | PASS |
| T19 | `test_19_rollback_cleanup_failure_then_retry` | PASS |
| T20 | `test_20_disk_full_during_state_publication` | PASS |
| T21 | `test_21_file_and_directory_fsync_failure` | PASS |
| T22 | `test_22_partial_record_never_becomes_authoritative` | PASS |
| T23 | `test_23_wall_clock_rollback_and_forward_jump` | PASS |
| T24 | `test_24_reboot_changes_boot_identity_and_rolls_back_uncommitted` | PASS |
| T25 | `test_25_missing_or_corrupted_recovery_metadata_blocks` | PASS |
| T26 | `test_26_power_loss_at_every_named_transition_boundary` | PASS |
| T27 | `test_27_process_restart_and_unsynced_power_outcomes_differ` | PASS |
| T28 | `test_28_terminal_phase_cannot_hide_reactivated_timer` | PASS |
| T29 | `test_29_loaded_config_service_or_queue_mismatch_blocks_restriction` | PASS |
| T30 | `test_30_missing_essential_restorer_is_explicitly_blocked` | PASS |
| T31 | `test_31_self_reported_evidence_never_authorizes_commit` | PASS |
| T32 | `test_32_synthetic_approval_requires_run_plan_and_review_binding` | PASS |
| T33 | `test_33_partial_restore_is_idempotently_retried` | PASS |
| T34 | `test_34_corrupt_commit_marker_is_not_reinterpreted_as_uncommitted` | PASS |
| T35 | `test_35_committed_firewall_drift_is_blocked_not_overwritten` | PASS |
| T36 | `test_36_mutant_false_cancellation_is_detected` | PASS |
| T37 | `test_37_mutant_missing_durable_intent_is_detected` | PASS |
| T38 | `test_38_unused_fault_hook_is_a_test_failure` | PASS |
| T39 | `test_39_model_has_no_host_effect_or_durability_oracle_imports` | PASS |
| T40 | `test_40_capsule_transaction_mismatch_is_blocked` | PASS |
| T41 | `test_41_firewall_drift_after_terminal_write_is_not_success` | PASS |
| T42 | `test_42_malformed_phase_metadata_is_blocked` | PASS |
| T43 | `test_43_restorer_disappearing_at_last_observation_blocks_mutation` | PASS |
| T44 | `test_44_backward_monotonic_clock_is_not_a_valid_pending_run` | PASS |
| T45 | `test_45_error_after_commit_flush_reconciles_surviving_decision` | PASS |
| T46 | `test_46_restore_error_preserves_pending_work_and_retries` | PASS |
| T47 | `test_47_timer_arm_error_never_allows_restriction` | PASS |
| T48 | `test_48_corrupt_previous_run_cannot_be_overwritten_by_prepare` | PASS |

| T49 | `test_49_unhashable_phase_returns_blocked` | PASS |
| T50 | `test_50_unsynced_commit_blocks_until_power_outcome` | PASS |
| T51 | `test_51_concurrent_commit_and_rollback_cannot_interleave` | PASS |
| T52 | `test_52_external_firewall_drift_blocks_first_restriction` | PASS |
| T53 | `test_53_restorer_lost_at_restore_effect_blocks` | PASS |
| T54 | `test_54_commit_cleanup_does_not_need_restorer` | PASS |
| T55 | `test_55_clock_regression_after_accepted_sample` | PASS |
| T56 | `test_56_timer_config_drift_is_not_terminal` | PASS |
| T57 | `test_57_queued_and_running_work_survives_timer_cancel` | PASS |
| T58 | `test_58_baseline_noop_recovery_records_rollback_pending` | PASS |

## Post-publication security-review amendments

The original offline totals above describe the initial R1 commit. Subsequent
Sourcery/CodeRabbit findings motivated modeled durability uncertainty, a
synthetic concurrency guard, foreign-firewall drift checks, restorer effect
rechecks, committed cleanup, clock regression, loaded timer identity, and
running/queued-job separation. The VM plan now requires private host-side
pre-fault receipts, fail-fast commands and explicit client credential paths.
New regression cases were added; use the current PR CI results for revised
counts. No real VM tests have run (V01–V28 NOT RUN). F01 and real F02–F05
remain unclosed and privileged integration remains prohibited.
