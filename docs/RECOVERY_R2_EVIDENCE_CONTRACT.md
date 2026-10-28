# R2 private evidence and public status contract

**All V01–V28: NOT RUN.** This file is a design and audit contract, not test results. The public `r2/validation_plan.json` contains a row-for-row copy of the R1 matrix and is intentionally immutable until a separately reviewed protocol amendment.

## Two distinct records

**Public controlled plan and status:** versioned, synthetic `r2/validation_plan.json`. This design-stage artifact may only declare `R2_DESIGN_ONLY`, `vm_executed=false`, `deployment_authorized=false`, and `NOT_RUN` for every row. The offline verifier validates structure, preservation of the R1 row text and refusal of invented PASS results. It does not inspect a VM or certify evidence.

**Private runtime receipt index (future):** retain off-DUT, off-snapshot with owner-only permissions in a user-controlled test environment. An independent reviewer receives controlled access outside Git. Per attempt, record these fields; never source-control their *values*:

| Field | Required meaning |
| --- | --- |
| `test_id`, `attempt_id`, `run_id` | Bound to one row and unique attempt/transaction |
| `source_revision`, `vm_driver_revision`, `config_digest` | Exact reviewed implementation and immutable fixture |
| `dut_snapshot_digest`, `guest_boot_id`, `storage_profile` | Confirm reset/boot/storage identity |
| `fault_label`, `fault_occurrence`, `fault_reached` | Exact boundary and external proof it actually fired |
| `pre_fault_receipt_sha256`, `pre_fault_export_confirmed` | Checksum of immutable receipt verified outside DUT **before** fault |
| `post_fault_receipt_sha256`, `post_fault_capture_source` | Independently retained post-fault observations |
| `manager_receipt_sha256`, `firewall_live_sha256`, `firewall_persisted_sha256` | Separate actual timer/service and dual-family firewall images |
| `client_v4_sha256`, `client_v6_sha256`, `unauthorized_tcp_sha256` | Fresh, source-bound independent client/switch observations |
| `hypervisor_event_sha256`, `storage_syscall_sha256` | Guest-cut and file/directory sync/error proof where relevant |
| `outcome`, `limitation`, `reviewer`, `review_time` | Human disposition, missing evidence, traceable review |

The receipt index must use canonical JSON/UTF-8, non-reused IDs, checksum verification of the original private bytes, and explicit timestamps/clock domain. Do not confuse SHA-256 with provenance or witness independence. Verify and preserve private receipts outside both Git and the DUT snapshot domain. An immutable pre-fault receipt must be exported and independently matched before process/VM power tests; never use a directory under the DUT volatile memory filesystem as the only store.

## Decision states

- **NOT_RUN:** no VM execution occurred; the default for all 28 rows.
- **BLOCKED:** a prerequisite or observation unavailable; no fault claimed executed.
- **FAIL:** a required effect/observation contradicts the locked pass/fail rule, including an unmet checkpoint or safety invariant.
- **INCOMPLETE:** execution may have occurred but private receipts, complete family observations, independence or correlation are insufficient.
- **PASS_CANDIDATE:** all required evidence appears present to a reviewer, but has not been adjudicated independently.
- **INDEPENDENTLY_REVIEWED_PASS:** only a human reviewer, using private original receipts and the locked rule, can issue this outcome; **never emitted by the offline verifier**.

A reviewer must not mark `PASS` merely because a test driver printed `OK`, because an exit code was zero, or because receipts are correctly formatted. Report completeness and independent observation truth are different properties. Unknowns cannot be converted to PASS to meet a count.

## Execution evidence sequence for each row

1. Confirm design/implementation reviews, hypervisor isolation, console/OOB access, independent clients and correct snapshot from protected host observations.
2. Assign fresh run/attempt; restore the clean snapshot, pin implementation and fixture SHA-256.
3. Observe baseline TCP reachability and fresh SSH login for both families, plus separate kernel/persistent firewall state.
4. Arm one named checkpoint; capture and **verify the off-DUT pre-fault receipt** before fault. Require an independent reached marker.
5. Inject exactly the specified fault within the disposable guest or hypervisor; capture the actual effect, errno, exit status or power action through an independent channel.
6. Reconcile; collect fresh after-fault manager, firewall and independent client records (both families). Reboot again where required, and compare original baseline/retained restriction.
7. Preserve and hash the original records in the protected sink. Compare receipts to expected invariant, including explicit unsafe/blocked conditions.
8. Record FAIL / INCOMPLETE / PASS_CANDIDATE. Only then request independent human review; do not auto-edit the public NOT_RUN plan based on synthetic data.

## Special coverage and separation

**V01–V04:** prove optional dependencies are actually absent, with a guest dependency inventory.  
**V09–V13, V28:** distinguish durable committed retention from timer cancellation/queued-work cleanup.  
**V16–V19:** run A versus B isolation, idempotence and retry.  
**V20–V22, V26:** actual file/directory sync tracing, ENOSPC/EIO, old/new rename survival and *each* specified interruption boundary.  
**V23–V24:** wall/monotonic/boot discontinuity evidence, process restart versus orderly reboot distinguished.  
**V25:** missing essential metadata is blocked/OOB; never falsely counted as recovery success.  
**V26:** abrupt **guest** VM cut differs from physical host/storage power failure; the latter remains a separate claim.

F01 PR #6 cannot be treated as closed by successful R2 receipts; F01 authority requires its own independently reviewed protocol and evidence.

## Privacy and reproducibility

Keep all private source/destination addresses, hostnames, credentials, SSH keys/fingerprints, journal exports, traffic captures, firewall/backup images, metadata containing host IDs and VM disk snapshots out of commits, CI, PR comments, public artifacts and chat. Public summaries may contain sanitized row ID, code revision, reviewed outcome classification, covered checkpoint IDs (synthetic labels), and residual limits. No backend server, telemetry pipeline, automatic remote transfer or centralized evidence collection is required or introduced by this design. Host-side private capture is controlled by the operator and is **not** an application runtime backend.

## Offline contract versus real validation

The standard-library `tests/support/r2_contract.py` checker accepts **only the locked, all-NOT_RUN design plan** and checks its row text against R1. Tests deliberately reject an invented `PASS`, missing rows, duplicate JSON fields and altered security rules. A passing CI check establishes only **plan consistency**; it does not imply R2-VM validation or deployment authorization.
