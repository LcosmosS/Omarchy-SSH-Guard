# SSH-HARDEN-R1 disposable-VM validation protocol

## 0. Enforce scope and record NOT RUN

1. Mark every VM row below **NOT RUN**. Preserve that status until the row is
   executed and its required evidence is independently inspected.
2. Obtain separate authorization for a disposable VM experiment. Do not execute
   these instructions on the development workstation or any production host.
3. Use this file as a future execution procedure. Do not interpret it as an
   implemented VM harness, authorization to deploy, or evidence of a completed run.
4. Obtain a separately reviewed VM-only recovery executable and fault harness.
   Do not use the rejected v2 scripts or install the in-memory reference model as
   a host executor. **Stop here while that reviewed implementation is absent.**
5. Require the future harness interface below; implement/review it separately
   before attempting the later commands. Do not substitute a stub returning
   expected statuses. Verify all observations independently of the harness.

| Future harness operation | Require this behavior |
| --- | --- |
| `prepare --run ID --fixture documentation-dual-stack` | Publish a VM-only baseline/recovery capsule and run-bound service configuration; return before mutation |
| `arm --run ID` | Activate the exact recovery timer and verify loaded configuration and bounded future elapse |
| `restrict --run ID` | Durably publish mutation intent before the actual VM-only firewall change |
| `decide --run ID --review-file FILE` | Consume a separately approved VM experiment decision; do not accept linter/HMAC reports as authority |
| `recover --expected-run ID` | Restore only the matching uncommitted run or reconcile committed cleanup |
| `reconcile --expected-run ID` | Apply the specification's boot/restart decision using surviving records |
| `status --run ID --json` | Report persisted phase separately from actual manager and firewall observations |
| `pause --run ID --boundary NAME` / `resume --run ID` | Stop exactly at the named specification checkpoint; record a private reached-marker |
| `storage-fault --run ID --operation OP --error ERROR` | Inject a real scoped write/sync failure on the dedicated test filesystem; record actual failing syscall and errno |
| `cancel-fault --run ID --mode fail-or-false-ack` | Inject cancellation failure/false return without replacing the independent systemctl observation |
| `quarantine --components LIST` | Make listed optional components unavailable inside the disposable guest; record actual absence, not an invented boolean |
| `collect --run ID --private-dir DIR` | Capture bounded private state, manager properties, filesystem traces and packet/rule observations; never upload them |

## 1. Isolate the experiment and prepare restoration

1. Create three disposable Linux VMs: DUT `r1-dut`, authorized client `r1-allow`,
   unauthorized client `r1-deny`. Use these synthetic fixture names only.
2. Attach them to a dedicated isolated virtual switch with **no physical bridge,
   host interface, forwarding, NAT, default route or upstream network**. Disable
   shared folders, clipboard synchronization and host credential/agent forwarding.
3. Configure only these reserved documentation endpoints on that switch:

   | VM | IPv4 | IPv6 |
   | --- | --- | --- |
   | DUT | 192.0.2.20/24 | 2001:db8:1::20/64 |
   | Authorized | 192.0.2.10/24 | 2001:db8:1::10/64 |
   | Unauthorized | 192.0.2.30/24 | 2001:db8:1::30/64 |

4. Verify from the hypervisor that none of those networks routes to the host's
   management network. Abort on any unexpected interface or route.
5. Keep an independent hypervisor serial/display console and recovery ISO available.
   Verify a console login after disabling SSH temporarily in a throwaway snapshot.
   Do not use an existing SSH connection as out-of-band recovery.
6. Provision disposable guest-only SSH identities and pinned known-hosts privately.
   Use the synthetic fixture account `guardtest`; enable public-key login only.
   Keep keys and fingerprints outside source, CI artifacts, chat and this document.
7. Record guest distribution/kernel/systemd/UFW/Python versions, virtual disk type,
   filesystem/mount options, hypervisor version, cache mode and storage flush policy
   in a private experiment receipt. Keep network and identity records private.
8. Create a clean powered-off snapshot; verify that reverting it restores baseline
   disk bytes and test-client reachability. Use a hypervisor controller, not the DUT:

   ```bash
   virsh shutdown r1-dut
   virsh domstate r1-dut
   # Continue only after independently observing "shut off".
   virsh snapshot-create-as r1-dut r1-clean --atomic
   virsh snapshot-revert r1-dut r1-clean --running
   ```

9. Revert to `r1-clean` before each independent matrix row. Assign a unique run ID
   such as `r1-vm-v01-attempt-01`; increment the attempt component on every retry.
   Never silently reuse a run or remove a pending transaction to make a test pass.
10. Stop if snapshot creation, restoration, console recovery or isolation cannot be
    independently established. Record BLOCKED; do not continue under restriction.

## 2. Establish controlled guest prerequisites

1. In the authorized disposable DUT console only, set a private output directory
   and verify the independently reviewed driver is present. Stop if it is absent:

   ```bash
   set -euo pipefail
   umask 077
   R1_PRIVATE=/run/r1-private
   R1_VM_DRIVER=/opt/r1-vm/recovery-fixture
   R1_RUN=r1-vm-v01-attempt-01
   test -x "$R1_VM_DRIVER" || exit 1
   install -d -m 700 "$R1_PRIVATE"
   ```

2. Before each disruptive test, configure a protected evidence sink on the
   **independent hypervisor**, outside the DUT and its snapshot/revert domain.
   `/run/r1-private` is volatile scratch, never the sole record of pre-fault
   state. Transfer completed pre-fault receipts, checkpoint markers, manifests
   and hashes through a reviewed authenticated guest-to-hypervisor mechanism or
   hypervisor serial capture. Verify receipt bytes, hashes and run identity
   **before** causing reboot, disk fault or `virsh destroy`. Abort and mark BLOCKED
   if host-side preservation fails. After restart, collect independent post-fault
   records and correlate by run/attempt/checkpoint. This is mandatory for
   V24, V26 and the reboot/reachability re-checks. V07 is a process-termination
   test with no reboot and need not use the reboot-specific retention path, but
   its private receipts still require normal preservation. Do not add a recovery
   collector or publish private records to Git.
3. Use an independently verified VM fixture to enable UFW IPv4/IPv6, permit
   baseline TCP/22 from both synthetic clients, preserve console recovery and
   allow the chosen source-bound reachability controls. Configure the restriction
   to permit only the authorized fixture client in each family. Do not introduce
   Docker, QML, CodeQL, a collector or unrelated packages merely to satisfy recovery.
3. Capture UFW persisted files and kernel rules privately. Do not use displayed
   UFW status alone as a packet-path oracle. Capture both families separately.
4. Ensure all DUT storage under test resides on a dedicated expendable virtual
   disk/filesystem. Keep the recovery executable and out-of-band mechanism on a
   separately protected guest image. Never point fault tools at a host disk.
5. Confirm the actual recovery executable's dependency inventory. Verify the
   minimal restore mechanism works from the console before arming any restriction.
6. Run prepare and arm only inside the DUT experiment console:

   ```bash
   set -euo pipefail
   test -x "$R1_VM_DRIVER"
   "$R1_VM_DRIVER" prepare --run "$R1_RUN" --fixture documentation-dual-stack
   "$R1_VM_DRIVER" arm --run "$R1_RUN"
   "$R1_VM_DRIVER" status --run "$R1_RUN" --json > "$R1_PRIVATE/status.json"
   ```

7. Independently inspect the real system manager. Use the exact run-bound unit
   names supplied by the reviewed implementation; reject another run, altered
   fragments or unexpected drop-ins. Capture output privately:

   ```bash
   R1_TIMER="r1-recovery-${R1_RUN}.timer"
   R1_SERVICE="r1-recovery-${R1_RUN}.service"
   systemctl show "$R1_TIMER" \
     -p Id -p LoadState -p FragmentPath -p DropInPaths -p UnitFileState \
     -p ActiveState -p SubState -p Triggers \
     -p NextElapseUSecRealtime -p NextElapseUSecMonotonic \
     > "$R1_PRIVATE/timer-properties.txt"
   systemctl show "$R1_SERVICE" \
     -p Id -p LoadState -p FragmentPath -p DropInPaths -p ExecStart \
     -p ActiveState -p SubState -p InvocationID -p Job -p Result \
     > "$R1_PRIVATE/service-properties.txt"
   systemctl list-jobs --no-pager > "$R1_PRIVATE/jobs.txt"
   ```

8. Compare actual loaded ExecStart arguments, run ID, configuration digest,
   effective drop-ins and enabled state to the durable manifest. Check a nonzero
   future elapse bounded by the recorded deadline and the actual boot/time domain.
   Reject active-but-elapsed timers and already-running recovery services.
9. Trace actual file writes, fsync/fdatasync, rename and directory fsync with a
   separately reviewed syscall tracer. Redirect traces privately. Verify that all
   restoration image bytes, executable/configuration, run binding, enablement intent
   and mutation intent complete their barriers before the first restrictive syscall.
10. Record actual reached-checkpoint markers for every injected fault. Mark a row
    FAIL if the designated checkpoint was never reached, even if the final state
    looks correct. Record a false-ack injection separately from real manager state.

## 3. Measure external IPv4 and IPv6 behavior

1. From **both** independent clients, verify source assignment, direct route and
   fresh baseline TCP/22 reachability to the exact DUT destination in each family.
2. From the authorized client, use a new non-multiplexed key-authenticated session
   with the private pinned fixture identity/known-hosts. Run both commands, redirect
   stdout/stderr to client-private files, and independently record start/end times:

   ```bash
   set -euo pipefail
   # Client-side private fixture files; no identities or fingerprints in Git.
   R1_VM_KNOWN_HOSTS="${R1_VM_KNOWN_HOSTS:-$HOME/.ssh/r1-vm-fixture-known-hosts}"
   R1_VM_FIXTURE_IDENTITY="${R1_VM_FIXTURE_IDENTITY:-$HOME/.ssh/r1-vm-fixture-id}"
   test -r "$R1_VM_KNOWN_HOSTS" && test -f "$R1_VM_KNOWN_HOSTS"
   test -r "$R1_VM_FIXTURE_IDENTITY" && test -f "$R1_VM_FIXTURE_IDENTITY"
   # Keep client results private; preserve both family outcomes even if one fails.
   umask 077
   R1_VM_CLIENT_LOGS="${R1_VM_CLIENT_LOGS:-$HOME/.local/state/omarchy-ssh-guard/vm-tests}"
   mkdir -p -- "$R1_VM_CLIENT_LOGS"
   test -d "$R1_VM_CLIENT_LOGS" && test -w "$R1_VM_CLIENT_LOGS"
   R1_VM_RUN="${R1_VM_RUN:-r1-vm-v01-attempt-01}"
   date -u +%Y-%m-%dT%H:%M:%SZ > "$R1_VM_CLIENT_LOGS/$R1_VM_RUN-ipv4-start.txt"
   if ssh -4 -F /dev/null -p 22 -b 192.0.2.10 \
     -o IdentitiesOnly=yes -o IdentityAgent=none \
     -o ConnectTimeout=8 -o ConnectionAttempts=1 \
     -o ControlMaster=no -o ControlPath=none -o ControlPersist=no \
     -o BatchMode=yes -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no \
     -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$R1_VM_KNOWN_HOSTS" \
     -i "$R1_VM_FIXTURE_IDENTITY" -l guardtest 192.0.2.20 true \
     > "$R1_VM_CLIENT_LOGS/$R1_VM_RUN-ipv4-stdout.txt" \
     2> "$R1_VM_CLIENT_LOGS/$R1_VM_RUN-ipv4-stderr.txt"; then
     R1_V4_EXIT=0
   else
     R1_V4_EXIT=$?
   fi
   date -u +%Y-%m-%dT%H:%M:%SZ > "$R1_VM_CLIENT_LOGS/$R1_VM_RUN-ipv4-end.txt"
   printf '%s\n' "$R1_V4_EXIT" > "$R1_VM_CLIENT_LOGS/$R1_VM_RUN-ipv4-exit.txt"
   date -u +%Y-%m-%dT%H:%M:%SZ > "$R1_VM_CLIENT_LOGS/$R1_VM_RUN-ipv6-start.txt"
   if ssh -6 -F /dev/null -p 22 -b 2001:db8:1::10 \
     -o IdentitiesOnly=yes -o IdentityAgent=none \
     -o ConnectTimeout=8 -o ConnectionAttempts=1 \
     -o ControlMaster=no -o ControlPath=none -o ControlPersist=no \
     -o BatchMode=yes -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no \
     -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$R1_VM_KNOWN_HOSTS" \
     -i "$R1_VM_FIXTURE_IDENTITY" -l guardtest 2001:db8:1::20 true \
     > "$R1_VM_CLIENT_LOGS/$R1_VM_RUN-ipv6-stdout.txt" \
     2> "$R1_VM_CLIENT_LOGS/$R1_VM_RUN-ipv6-stderr.txt"; then
     R1_V6_EXIT=0
   else
     R1_V6_EXIT=$?
   fi
   date -u +%Y-%m-%dT%H:%M:%SZ > "$R1_VM_CLIENT_LOGS/$R1_VM_RUN-ipv6-end.txt"
   printf '%s\n' "$R1_V6_EXIT" > "$R1_VM_CLIENT_LOGS/$R1_VM_RUN-ipv6-exit.txt"
   # Classify the row only after collecting both results. Never publish these logs.
   if (( R1_V4_EXIT != 0 || R1_V6_EXIT != 0 )); then
     printf '%s\n' "One or more authorized-family SSH checks failed (private logs retained)" >&2
     exit 1
   fi
   ```

3. From the unauthorized client, perform source-bound TCP probes to both DUT
   addresses with a bounded timeout and capture independent virtual-switch traffic
   privately. Observe baseline success, restriction rejection and restored baseline
   success. Do not treat failed authentication after TCP success as firewall rejection.
4. Check source-bound ICMP controls before/after rejection tests, but require the
   packet capture and exact flow observations as well. Do not equate ICMP success
   or signed reports with proof of the TCP path or honest measurement.
5. After rollback, require a **fresh** authorized public-key login and unauthorized
   baseline TCP success in both families. Check both kernel and persisted firewall
   images against the original VM-only baseline manifest. Reboot again and repeat
   the checks to detect a live-only restore.
6. After a valid committed test decision, require the specified restriction to
   remain across cleanup/reboot and require no stale timer, running service or
   queued job. Do not classify a committed-cleanup retry as a rollback trial.

## 4. Execute interruption, timer, dependency and storage rows

1. For each table row, restore the clean snapshot, establish the specified initial
   state, arm the named fault, prove its checkpoint was reached, inject the fault,
   then perform boot/restart reconciliation and independent observations.
2. For a **process termination** row, pause at the named checkpoint and kill only
   the fixture process inside the guest. Record that the guest kernel/page cache
   remained alive. Do not label this power-loss validation.
3. For a **VM power interruption** row, pause at the named checkpoint and issue
   `virsh destroy r1-dut` from the hypervisor controller; then `virsh start r1-dut`.
   Do not issue an orderly guest shutdown, reboot or sync before the cut. Record
   whether the hypervisor controller or backing storage may still cache writes.
   Treat this as guest power-loss evidence, not proof against physical host/storage
   power loss. Require stronger storage-specific evidence before any such claim.
4. Enumerate before/after each write, file sync, rename, directory sync and readback
   for lease, capsule, service configuration, mutation intent, commit marker,
   cleanup intent and terminal record. Repeat enough attempts to exercise surviving
   old and new names where permitted. Record unavailable outcomes as untested;
   do not force results to match only the model's dropped-rename branch.
5. For clock rows, isolate time synchronization to the DUT; disable its time-sync
   service, advance/retard only its wall clock through the experiment console,
   and compare real boot/monotonic/wall observations. Restore time services via
   snapshot reversion afterward. Never change the hypervisor/workstation clock.
6. For storage rows, scope ENOSPC and sync/write EIO to the expendable test filesystem.
   Use the reviewed harness plus independent syscall traces to prove the actual
   error occurred. Exercise errors before and after restrictive mutation. Do not
   replace real error injection with a success-returning Python mock.
7. For optional-dependency rows, actually quarantine/remove the designated guest
   components, stop/mask guest journald and its activation sockets where required,
   and prove absence. Do not remove the declared minimal restoration mechanism.
   Test that failure separately and require explicit blocked/OOB behavior.
8. For stale-run rows, complete run A's recovery/cleanup, begin run B, and deliver
   A's previously queued invocation to the run-bound recovery entry. Compare B's
   state/rules/timers before and after; require zero changes.
9. For cancellation rows, compare the returned status with independent manager
   state before retry. Require cleanup to remain pending after failure/false ack.
   Retry after the original deadline and after reboot without requiring fresh
   evidence or reopening a valid committed restriction.

## 5. Record the VM matrix

Keep every row's actual status **NOT RUN** until performed. Append private attempt
receipts; publish only independently reviewed synthetic summaries/booleans later.

| Test_ID | Initial_State | Fault | Expected_Recovery | Required_Observation | Pass_Fail_Rule |
| --- | --- | --- | --- | --- | --- |
| V01 | RESTRICTED_PENDING | Collector unavailable | Restore baseline and clean timer | Dependency absence + both firewall images + fresh dual-family tests | PASS only if recovery runs without collector |
| V02 | RESTRICTED_PENDING | Docker unavailable | Same as V01 | Actual binary/package absence and restore trace | PASS only if no Docker dependency |
| V03 | RESTRICTED_PENDING | Journald unavailable | Same as V01 | Masked service/sockets and independent console traces | PASS only if no journal parser/service needed |
| V04 | RESTRICTED_PENDING | Unrelated packages/QML/CodeQL absent | Same as V01 | Executable dependency closure and restore | PASS only if declared essential set suffices |
| V05 | PREPARED | Cut at each incomplete preparation publication | No restriction; blocked/aborted preparation | Reached marker, surviving objects, kernel rules | FAIL if restriction preceded complete preparation |
| V06 | RECOVERY_DURABLE | Missing/elapsed/disabled timer | No restrictive mutation | Actual loaded config/future elapse + rule syscall trace | FAIL if active status alone permits mutation |
| V07 | MUTATION_INTENT | Kill process immediately before mutation | Restore/reobserve baseline | Process death proof, no guest reboot, rules/access | Never count as power-loss proof |
| V08 | MUTATION_INTENT | Kill after live/persisted mutation | Restore baseline and clean up | Separate kernel/persisted images and fresh flows | PASS only if both images converge |
| V09 | RESTRICTED_PENDING | Power cut before commit marker sync | Reconcile surviving valid old/new decision | Raw storage outcome, marker integrity and loaded recovery | FAIL on guessed retention or ignored valid surviving marker |
| V10 | COMMIT_DECIDED | Power cut before cancel | Retain valid restriction, retry cleanup | Durable marker and manager/flow observations | FAIL if rollback reopens valid committed restriction |
| V11 | CLEANUP_PENDING(COMMIT) | Cancellation syscall failure | Keep cleanup pending | Return error + independent active/enabled/job state | FAIL if reported completed/cancelled |
| V12 | CLEANUP_PENDING(COMMIT) | False successful cancel acknowledgement | Same as V11 | Independent manager still active despite claimed success | FAIL if status trusts return code |
| V13 | CLEANUP_PENDING(COMMIT) | Restart/retry after expiry | Finish cleanup without new evidence | Marker, exact restricted image, inactive/disabled/no jobs | PASS only if cleanup is retryable |
| V14 | RESTRICTED_PENDING | Deadline expires; repeat apply | Restore baseline | Actual deadline/clock and no ordinary pending success | FAIL if deadline is extended or ignored |
| V15 | ROLLBACK_ARMED | Active timer without future occurrence | No mutation/rollback as applicable | Real next-elapse values and running-service state | FAIL if active alone passes |
| V16 | Any owned state | Wrong invocation run ID | No changes | Before/after current run records/rules/manager | FAIL on any current-run effect |
| V17 | Run B pending | Deliver stale run A invocation | Ignore A | B's complete state/rules/timer comparison | FAIL if B changes |
| V18 | ROLLED_BACK | Repeat recovery twice | Remain baseline/clean | Same rule bytes, persisted image and zero duplicate rules | FAIL on new unauthorized mutation |
| V19 | CLEANUP_PENDING(ROLLBACK) | Cancel failure then retry | Baseline retained; cleanup converges | Restore once or idempotent equivalent, retry succeeds | FAIL if ended phase suppresses cleanup |
| V20 | Any publication | Real ENOSPC | Stop advancement; reconcile safely | Actual write/sync errno and durable image | FAIL on unsupported success |
| V21 | MUTATION_INTENT/decision | Real file/directory fsync EIO | Observe uncertain publication; reconcile | Syscall failure plus surviving old/new bytes | FAIL on pretending sync succeeded |
| V22 | State publication | Partial write/rename interruption | Previous/full valid record only | Bytes/integrity, OOB recovery if invalid | FAIL if torn record authorizes mutation/retention |
| V23 | RESTRICTED_PENDING | Wall clock backward/forward jump | Uncommitted rollback | Independent wall/monotonic/boot observations | FAIL on extended window |
| V24 | Uncommitted pending | Orderly reboot/new boot identity | Restore baseline before new transaction | New boot ID, boot-reconciler trace and both families | Keep separate from V26 power tests |
| V25 | Pending/committed | Missing/corrupt essential metadata | Explicit blocked/OOB, no guessed mutation | Binding/integrity error, no false success | Record recovery limitation; do not close a finding from this row alone |
| V26 | Every durable/effect boundary | Abrupt VM destroy/start | Follow surviving marker/capsule decision | Hypervisor cut receipt, reached marker, storage/rules/flows | PASS only per boundary; leave unexecuted cuts NOT RUN |
| V27 | Pending | Recovery service already active/queued | Detect invalid arming; bounded recovery | Actual manager jobs and service state | FAIL on assumed restart at timer expiry |
| V28 | Terminal committed | Timer reactivated or loaded drop-in changed | Retry only owned cleanup or block | Actual effective config, not disk comment alone | FAIL on stale success or unrelated-unit cancellation |

## 6. Require evidence before provisional closure

1. Before considering F02 provisionally addressed in an integrated implementation,
   require V01–V04 and V18–V19 receipts, actual executable/library dependency closure,
   absent-component observations, independent dual-family access after restore,
   and review proving no evidence/Docker/journal/QML/CodeQL path is consulted.
2. Before considering F03 provisionally addressed, require V09–V13, V16–V19 and
   V28 receipts; reach each commit/cancel/terminal boundary; demonstrate both
   uncommitted restoration and committed cleanup retention; reject a deliberately
   false acknowledgement using real independent systemctl observations.
3. Before considering F04 provisionally addressed, require V05–V10, V20–V26 for
   every publication/effect boundary, actual file/directory synchronization traces,
   hypervisor/cache/filesystem assumptions, repeated abrupt guest cuts, both live
   and persisted rule/access checks after another reboot, and evidence for every
   allowed surviving record outcome. Keep physical storage-power claims blocked
   unless separately tested under the applicable storage failure model.
4. Require V06, V14–V19, V23–V24 and V27–V28 for recovery-related F05 review. Keep loaded
   configuration, future elapse, boot binding and stale invocation evidence separate
   from a successful timer start/cancel return value.
5. Keep private receipts, VM disks/snapshots, keys, host identifiers, packet captures,
   journals, rules, timer properties and transaction/backup bytes outside Git and
   CI. Record only test ID, implementation revision, sanitized pass/fail/blocked
   result, covered boundaries and independent reviewer disposition publicly.
6. Require LibertySquared's independent security review of the implementation and
   private receipts. Record missing evidence as BLOCKED. Do not convert any NOT RUN
   row into PASS from a process-restart unit test or a successful model simulation.
7. Restore/delete only the separately authorized disposable experiment resources.
   End with the next decision set to **independent security review**, not deployment.
