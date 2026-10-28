# SSH-HARDEN-R1 recovery transaction specification

Scope: research specification and **test-only reference model**. No executor,
installer, systemd unit or firewall adapter is delivered. The existing plugin,
audit CLI, schema and evidence linter retain their authority limits. R1 cannot
authorize deployment or close a production security finding.

## Baseline and independent verification

Baseline: `de42d91` on current `origin/main`, inspected from a clean worktree before
creating `security/recovery-gate-r1`. CODEOWNERS, privacy CI, CodeQL and ordinary
CI were inspected and are preserved. Historical review text was not accepted as
proof. An AST-only examination of the rejected shell wrapper's embedded Python
independently established the following control-flow facts; none of that code
was imported, executed or copied into the reference model:

| Finding | Independent observation | Limit |
| --- | --- | --- |
| F02 | Root dispatch calls the full dependency audit before rollback; that audit loads the collector and requires Docker | Static control flow, not a dependency-removal trial |
| F03 | Verification saves `verified` before stopping the timer and computes cancellation from the phase | Static ordering, not a real interruption trial |
| F04 | Unit/backup publication functions contain no file/directory fsync; timer activation is checked with active status | Missing explicit synchronization is verified; actual loss is not measured |
| F05 recovery | Repeated apply has no deadline check in its existing-transaction branch; ended rollback skips cleanup | Static paths; actual systemd manager behavior remains untested |

The examined historical source SHA-256 is
`92a5d7165a33d395ebb6ed2ea8927d5646c3c995e7d330af12396a792579b960`.
It identifies source bytes, not authentic operational evidence. No historical
policy, endpoint, journal, backup, transaction or executable enters this patch.

## Fault model — specified before implementation

Each injected fault must name one checkpoint and record that it fired. A test
with zero hits fails. Fault classes are deliberately distinct:

| Class | Reference semantics | Claim excluded |
| --- | --- | --- |
| Controlled exception | Raise a storage/adapter exception at a named checkpoint; caller returns uncertain/pending, never success | Does not emulate process death |
| Process termination | Raise a BaseException checkpoint signal; discard the controller, retain kernel-visible model state | Does not flush or discard a disk cache |
| Missing optional dependency | Remove/poison collector, Docker, journald or unrelated package registry at recovery entry | Does not prove a real executable has a minimal dependency graph |
| Storage error | Fail write, file sync or directory sync at its named boundary | Real EIO/ENOSPC semantics require VM validation |
| Interrupted publication | Partial bytes exist only in a temporary object before rename; previous published record survives | Relies on atomic replacement and honest sync/reads |
| Clock discontinuity | Change injected wall/boot/monotonic clock; never consult workstation time | Does not test kernel clocks or time synchronization |
| Reboot | Change boot identity, reset modeled monotonic clock and timer manager | Does not boot an OS |
| Power loss | Drop volatile state, or retain a fully file-synced rename that lacked directory-sync acknowledgement; enumerate both outcomes | A memory simulation is not a physical power cut |
| Inconsistent external state | Independently change loaded timer config, future elapse, cancellation effect, queues or live/persistent firewall observations | Observation adapters are assumed honest; real manager/kernel queries require VM evidence |
| Stale/malicious input | Wrong run ID, malformed bytes, missing capsule or invented evidence | Root compromise and hostile storage firmware remain outside the model |

The storage model distinguishes temporary bytes, file-synced bytes, a visible
renamed directory entry and acknowledged durable entries. Readers see visible
entries, **not a durability oracle**. Tests may inspect the durable image to
check ordering independently. Before directory-sync acknowledgement, a power
interruption may yield the old record or a fully synced new record. Tests must
exercise both. Torn temporary data must never become the authoritative record.
These are explicit filesystem assumptions, not facts established by naming a
state or calling a simulated sync method.

Assume serialized controller/recovery actions and an exclusive active-run lease.
Real interprocess locking, hostile path replacement, disk/controller honesty,
barrier ordering across filesystems and kernel/firewall persistence are VM or
future implementation gates. Arbitrary media corruption is detectable only where
the model's schema/digest checks cover it; unrecoverable metadata produces
`RECOVERY_BLOCKED` and requires independent out-of-band intervention.

## Records, binding and authority

All reference records are synthetic, canonical JSON with a schema version,
transaction identifier and integrity checksum. Checksums detect modeled accidental
corruption; they do not authenticate an adversarial administrator. Identifiers
are never reused. A durable active lease names one run; every service invocation
must carry that exact expected run ID before any effect. A different ID returns
`STALE_IGNORED` without changing files, firewall or timers.

The immutable recovery capsule specifies the exact baseline image identifier,
restriction image identifier, rollback intent and minimal restoration mechanism
identifier. A separately published service image specifies a run-bound recovery
invocation and expected timer configuration. Neither contains real rules, commands,
keys or endpoints in R1. Capsule/service checksums and the plan identity bind
state, lease, timer observations and the commit marker to one transaction.

The commit marker is a separate immutable record. It is written only for an
explicitly injected `SyntheticApproval` bound to the run and plan. This is a
**test assumption for exercising the commit protocol**, not an authorization
implementation. Evidence, including structurally valid or MAC-shaped input,
cannot create that approval. Every result has `deployment_authorized=false`
and assurance `REFERENCE_MODEL_ONLY`. F01 remains excluded and unresolved.

A surviving valid commit marker dominates a lagging phase record: a process may
die between marker publication and phase publication. A phase claiming commitment
without the marker is inconsistent metadata, not authority. No marker, no inferred
permission to retain a restriction. Uncommitted reboot/restart reconciliation
restores the capsule's baseline. A valid committed transaction retains its exact
restriction and retries cleanup; it does not reopen access simply because cleanup
was interrupted. Drift in a committed firewall produces `RECOVERY_BLOCKED`.

## State meanings

| State | Meaning and required postcondition |
| --- | --- |
| PREPARED | Run reserved and initial record published; no permission to restrict |
| RECOVERY_DURABLE | Capsule, rollback intent, service image, lease and state have completed the publication protocol and readback |
| ROLLBACK_ARMED | Manager observation independently matches run/config/boot, enabled/active state and a bounded future elapse; state published |
| MUTATION_INTENT | Write-ahead record durably states restriction may be partial; all preparation/arming checks still hold |
| RESTRICTED_PENDING | Both modeled live and persisted firewall images match restriction; no commit marker |
| COMMIT_DECIDED | Valid immutable synthetic commit marker exists; phase cache published; cleanup not yet established |
| CLEANUP_PENDING | Disposition COMMIT or ROLLBACK is explicit; retry cancellation and inspect actual effects |
| COMPLETED | Valid marker, expected restriction and observed timer/service/queue cleanup; completion record published |
| ROLLBACK_PENDING | Durable rollback intent precedes restoration; repeated restore converges to baseline |
| ROLLED_BACK | Exact live/persisted baseline observed, timer cleanup observed, terminal record published |
| RECOVERY_BLOCKED | Binding/metadata/observation cannot support a safe automatic action; never success or permission |

`RECOVERY_BLOCKED` is a diagnostic state when metadata cannot safely be rewritten.
The result reports it without manufacturing a trusted persistent record. Likewise,
a storage failure reports `IO_UNCERTAIN`; the last readable phase is not presented
as evidence of a completed action. Persistent phase and observed timer/firewall
state are separate values. Terminal results must be reobserved on every query.

## Publication and external effects

For each object, the publication sequence is: validate/bound payload; create a
private same-directory temporary object; write complete bytes; synchronize the
file; atomically publish the name; synchronize its parent directory; reread and
validate the exact bytes and identity. Immutable objects require exclusive
publication. Any failure stops advancement and must be reconciled before retry.
New directories and parent entries must also be synchronized in a real executor.
Do not assume that a successful readback implies durability.

Before restriction, durably publish: active run lease, exact restoration image
and manifest, rollback intent, minimal recovery mechanism/version, service/timer
configuration with expected invocation run ID, clock/deadline binding and
transaction record. Verify the mechanism is available independently of evidence
services. Verify loaded manager configuration and future trigger. Then publish
`MUTATION_INTENT` and recheck clock/timer before changing the firewall. The model
checks separate live and persisted firewall observations; neither substitutes for
the other. A partial mutation is restored on reconciliation.

Commit order: independent synthetic decision -> immutable commit marker publication
-> `COMMIT_DECIDED` publication -> `CLEANUP_PENDING(COMMIT)` publication -> request
cancellation -> independently observe inactive/disabled/no running service/no
queued invocation -> publish `COMPLETED` -> report completed. A cancellation return
code alone is insufficient. Failed or false acknowledgement retains cleanup work.
Reordering phase persistence after cancellation alone does not solve crash safety.

Rollback order: verify expected run/lease/capsule -> publish `ROLLBACK_PENDING` ->
restore exact baseline -> observe both firewall images -> publish
`CLEANUP_PENDING(ROLLBACK)` -> cancel/observe cleanup -> publish `ROLLED_BACK`.
Missing collector, Docker, journal parser, QML, CodeQL or unrelated packages must
not be consulted on this path. Minimal restoration dependencies are still required;
their absence is `RECOVERY_BLOCKED`, never successful recovery.

## Deadline and timer rules

Capture synthetic wall and monotonic issue/deadline values plus boot identity.
Use a 900-unit maximum window. Within one boot, require monotonic progress and
agreement of wall/monotonic deltas within two units. Expiry, backward monotonic
movement, wall jump in either direction or a different boot invalidates an
uncommitted pending run and triggers rollback; it never extends the deadline.
Reboot policy is deliberately conservative: restore every uncommitted run,
including one that had not yet expired. A committed run may retry cleanup after
expiry or a boot change, because the marker, not the old timer, controls retention.

An armed observation must include exact transaction ID, expected loaded config
digest, boot identity, active and enabled state, idle service, empty stale queue,
and exact future wall/monotonic deadline no later than the transaction's deadline.
Active with zero/past/unknown next elapse is invalid. There is no production
systemd adapter here: the model tests these fields, not the truth of a real query.
The boot reconciler is a required independent mechanism, not an assumption that
`Persistent=true` recovers every failure. It must run before ordinary administration
can begin another transaction and must not depend on evidence validation.

## Transition table

| Current_State | Event | Preconditions | Durable_Write | Side_Effect | Next_State | Failure_Action |
| --- | --- | --- | --- | --- | --- | --- |
| Absent/terminal old run | prepare(new ID) | Serialized lease; ID never reused; prior run clean | Lease, PREPARED | None | PREPARED | Refuse busy/reused ID; uncertain writes require reconciliation |
| PREPARED | prepare recovery | Correct lease/plan | Capsule, service image, RECOVERY_DURABLE | None | RECOVERY_DURABLE | No restriction; incomplete metadata blocked |
| RECOVERY_DURABLE | arm | Images readback valid; clock current | ROLLBACK_ARMED after manager verification | Arm run-bound timer | ROLLBACK_ARMED | Do not mutate; reconcile/restore baseline |
| ROLLBACK_ARMED | apply | All durable preparation acknowledged; valid observed future timer | MUTATION_INTENT | Restrict live/persisted images; observe | RESTRICTED_PENDING after publication | Any interruption reconciles as uncommitted rollback |
| RESTRICTED_PENDING | repeated apply | No marker; current clock and correct future timer | None | Observe only | RESTRICTED_PENDING | Expired/invalid timer -> rollback, never ordinary no-op |
| RESTRICTED_PENDING | decide | Explicit matching synthetic approval; correct images/timer/deadline | Immutable decision, COMMIT_DECIDED | None | COMMIT_DECIDED | Evidence alone denied; uncertain publication reconciled from surviving marker |
| COMMIT_DECIDED | finish | Valid marker and exact restricted images | CLEANUP_PENDING(COMMIT) | Cancel and independently observe | COMPLETED after terminal publication | Keep commit; retry cleanup; never claim cancellation from phase |
| Any uncommitted phase | recover/boot/expiry | Matching lease and valid capsule | ROLLBACK_PENDING | Restore and observe baseline | CLEANUP_PENDING(ROLLBACK) | Retry restore; block if metadata/mechanism unavailable |
| CLEANUP_PENDING(ROLLBACK) | retry | Valid capsule, baseline or safe repeat restoration | ROLLED_BACK only after cleanup | Retry cancel/observe | ROLLED_BACK | Remain pending, do not suppress cleanup because restore already ran |
| CLEANUP_PENDING(COMMIT) | retry | Valid marker and exact restricted images | COMPLETED only after cleanup | Retry cancel/observe | COMPLETED | Remain pending; committed firewall drift is blocked |
| COMPLETED/ROLLED_BACK | repeat/reconcile | Revalidate record, disposition and observations | Repair cleanup record if needed | Only owned cleanup, or idempotent baseline restoration for rollback | Same terminal state | No stale success claim; block inconsistency |
| Any | stale expected ID | Expected ID differs from active lease | None | None | Unchanged | STALE_IGNORED |
| Any | corrupt/missing binding | Cannot establish ownership/restoration/decision | None if unsafe to write | None | RECOVERY_BLOCKED diagnostic | Out-of-band recovery and independent review |

## Interruption and reconciliation contract

Every publication has named checkpoints `before_write`, `after_write`,
`before_file_sync`, `after_file_sync`, `after_replace`, `before_dir_sync`,
`after_dir_sync`, `after_readback`. Phase is
part of each state publication checkpoint name. Effect checkpoints surround arm,
live restriction, persisted restriction, restoration, cancellation and observation.
Repeated checkpoint labels carry an occurrence ordinal; the matrix injects each
occurrence separately rather than silently deduplicating repeated observations.

| Surviving data after interruption | Reconciliation decision |
| --- | --- |
| No lease/partial initial preparation | No restriction permitted; report blocked/absent preparation; no guessed restore |
| Lease/state but missing/corrupt capsule or service binding | RECOVERY_BLOCKED; no unauthorized mutation |
| Valid uncommitted capsule, any nonterminal phase including MUTATION_INTENT | Restore exact baseline even if mutation may not have happened |
| Valid marker with lagging pending phase | Treat as committed; publish commit/cleanup phase and retry cleanup |
| Valid marker and incomplete cancellation | Retain exact restriction, retry owned cleanup, report cancellation only from observation |
| Baseline restored but cleanup interrupted | Reobserve baseline and retry cleanup; repeat restore only if needed |
| Terminal phase with timer reactivated | Reconcile and retry owned cleanup; do not report stale cancellation |
| Unexpected owner/run or irreversible metadata corruption | Stale no-op or RECOVERY_BLOCKED as appropriate |

For pre-directory-sync power loss, apply this table separately to each permitted
surviving old/new record. A new valid commit marker that actually survives is a
commit decision; lack of acknowledgement alone cannot justify ignoring it.
The model does not assume all unsynced renames are always lost.

## Independently checkable invariants and validation gates

| Invariant | Required check | Model evidence / remaining gate |
| --- | --- | --- |
| R1 | Rollback never consults optional-service registry | Dependency-removal/poison tests; actual executable dependency closure requires VM |
| R2 | At each restrictive effect, durable lease/capsule/service/intent exist and timer/clock meet contract | Independent durable-image oracle in tests; actual synchronization requires VM |
| R3 | Any claimed cancellation equals current independent timer/service/queue observation | False-ack/failure/terminal-reobserve tests; real manager observation requires VM |
| R4 | Each checkpoint has deterministic recovery for each permitted surviving image | Exhaustive enumerated checkpoint matrix; not a physical durability proof |
| R5 | Wrong expected ID causes zero changes to current run | Stale/mismatched invocation tests; real concurrency/locking requires VM |
| R6 | Repeat restoration/cleanup converges, including interrupted cleanup | Repeat and partial-restore tests; actual rule restoration requires VM |
| R7 | Expired or clock-invalid repeated apply never returns ordinary pending success | Expiry, empty-elapse, clock and boot tests |
| R8 | Evidence alone cannot create a commit; every result denies deployment authority | Fake-evidence/approval-binding tests; real independent authorization remains blocked |
| R9 | Model results never claim live/physical validation | Result assurance fields and NOT RUN VM ledger; independent review required |

Run results, exact test counts, mutation detection and the finding-to-test matrix
are recorded in `RECOVERY_R1_REPORT.md` after validation. No VM result is inferred
from these tests. See `RECOVERY_VM_VALIDATION.md` for the future isolated procedure.

## Source semantics supporting the specification

File sync does not by itself synchronize a containing directory; see
[fsync(2)](https://man7.org/linux/man-pages/man2/fsync.2.html). Atomic name replacement
does not describe durability of several objects; see
[rename(2)](https://man7.org/linux/man-pages/man2/rename.2.html). Persistent calendar
timers catch up missed activations but do not restart an already active service;
see [systemd.timer](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html).
The application-level reconciliation policy above is a design choice derived
from these constraints, not a guarantee made by those documents.
