# SSH-HARDEN-R2 — Disposable-VM Recovery Validation: architecture and contract

**Status:** `R2_DESIGN_ONLY` — proposed architecture, offline contract checks only.  
**Source:** merged R1 / PR #5, especially `docs/RECOVERY_STATE_MACHINE.md` and `docs/RECOVERY_VM_VALIDATION.md`.  
**Separation:** F01 is being addressed independently in PR #6; this PR neither imports its code nor assumes its acceptance.  
**Authorization:** No permission to execute tests, provision VMs, change firewall/SSH/systemd, run as root, merge, or deploy is provided by this design.

## Objective and success boundary

Translate the R1 non-production reference model into an *independently reviewable plan* for measuring actual Linux/systemd/UFW behavior in **three disposable, isolated VMs**. R2 must determine whether real boot, deadline, durability, rollback, timer and external network observations satisfy the R1 invariants. R1 simulated 106 passing tests are prerequisites and useful comparisons, never VM evidence. No claim of verified recovery is allowed until an independently reviewed VM-only implementation exists and **all 28 R1 VM rows** and every required interruption subcase have been executed, independently observed and dispositioned.

The initial R2 PR intentionally adds **no VM executor or fault injector**: it locks the interface, trust boundaries, plan and evidence requirements first. Phase I1 will be a separately reviewed, VM-only implementation PR. Phase V1 requires explicit experiment authorization and a disposable host environment. The design-only plan will always report `NOT_RUN` and `deployment_authorized=false`.

## Topology and trust isolation

```text
 Independent hypervisor/controller (trusted test administrator)
   |-- protected external evidence sink (outside DUT snapshot domain)
   |-- independent serial/display recovery console
   |-- read-only observer for virtual switch + VM lifecycle
   |
   +---- isolated virtual switch (no host bridge/NAT/uplink/default route)
           |-- DUT VM: disposable SSH daemon, UFW, systemd, private fixture
           |-- authorized client VM: fresh IPv4 and IPv6 SSH key authentication
           |-- unauthorized client VM: controlled TCP-path observation
```

Guest names, identities, addresses and credentials are **synthetic fixture values** defined privately at test time. Use the reserved documentation address plan from R1 only on the isolated virtual switch; verify there is no route to the host or upstream. The host/hypervisor is not a DUT; fail closed if a selected target, storage device, bridge or executor can affect any non-disposable system. Source-controlled tests may use synthetic names but must never publish real addresses, keys, routes, snapshots, logs or packet captures.

The DUT and its evidence reporter are **not trusted to attest their own recovery**. The hypervisor (power-cut witness, console, external storage sink), independently controlled client VMs (fresh SSH/packet observations), and a reviewer inspecting original private receipts supply separate observations. Distinct instruments may share a fault or be misconfigured; document observer independence, trust and failure limits. A hash detects changed bytes; it does **not** prove an observation occurred or that a witness is independent.

## R2 component interfaces — requirements for the *future* VM-only PR

| Adapter | Allowed VM-only scope | Prohibited assumption |
| --- | --- | --- |
| Guest transaction runner | Expose `prepare`, `arm`, `restrict`, `decide`, `recover`, `reconcile`, `status` with run-bound IDs and typed failures | Never copy rejected privileged v2 code or promote the R1 in-memory model into a host executor |
| Recovery executor | Minimal, root-owned **guest-only** restore path without collector, Docker, journald or arbitrary Python packages | No remote backend or central orchestration dependency |
| systemd adapter | Record actual effective unit/drop-ins, run binding, active/enabled state, next elapse, queued/running jobs and cancel result | `systemctl` success does not prove quiescence |
| Firewall adapter | Independent live kernel and on-disk UFW image verification for IPv4 *and* IPv6 | Displayed UFW status is not packet-path truth |
| Storage adapter | Durable write/flush/rename + directory sync, errno injection confined to disposable guest filesystem, independent syscall trace | Simulated `fsync` or VM process restart is not physical durability |
| Fault/VM driver | Pause at named checkpoint and prove reach; separately inject process kill, guest reboot, abrupt hypervisor VM destruction and storage errors | No test counts as reached just because a requested hook name exists |
| Observation clients | Non-multiplexed, source-bound dual-stack SSH and unauthorized TCP probes with isolated identities, captured by an independent switch observer | Failed authentication is not proof of firewall rejection |
| Evidence sink | Protected off-DUT, off-snapshot private receipts, pre/post correlation and checksum confirmation *before* destructive fault | No storage exclusively under volatile guest directories |
| Review interface | Human decision tied to exact run, manifest hashes, covered boundaries and residual risk | No automatic `PASS`, security certificate or deployment authorization from a receipt parser |

**Non-authority of F01:** PR #6 is a parallel evidence-authority design, not a dependency to silently import into R2. For tests of the *committed* branch, any synthetic experiment decision must be documented as a disposable-VM authorization to explore transaction cleanup, **not a production retain decision** and **not proof of real external evidence authority**. Do not treat an HMAC, self-reported rejection, `model_consistent`, or signed local report as independent observation. R2 results must not claim F01 closed.

## Mandatory transaction and crash invariants

1. **No restrictive effect without recoverability:** recovery image + restorer bytes/config, run ID, pre-scheduled rollback and persisted `MUTATION_INTENT` must be independently verified before the first firewall mutation.
2. **Commit survives cleanup failure:** only a valid durably committed marker controls retention; an uncertain marker must block until outcome resolution. Cancellation success alone is never proof.
3. **Uncommitted outcomes restore baseline:** both live and persistent firewall image must match, with fresh authorized and unauthorized observations in *both* address families after rollback and after reboot.
4. **Ownership isolation:** a stale run A cannot alter B's storage, timer, firewall, queue or service. Future VM harness must use a real interprocess/OS lock and recheck ownership before side effects.
5. **Deadlines and boot:** a clock discontinuity, expired/invalid next elapse or new boot cannot extend an uncommitted restriction; preserve wall, monotonic and boot identity evidence independently.
6. **Timer/service cleanup:** inspect loaded unit identity, configuration and drop-ins; require inactive/disabled state, no running service and no queued work. Reconcile terminal state when reactivated.
7. **Recovery isolation:** optional collector/journal/Docker/QML/CodeQL loss does not remove the minimal restoration capability. Missing essential metadata/restorer is **BLOCKED/OOB**, never a silently passed test.
8. **Fault proof:** every injected fault must produce an independently observable reached-checkpoint receipt, actual syscall/manager result where applicable, and an expected *negative* control. No coverage is inferred from dry-run checks.

## Experiment progression (nonparallel)

```text
R2-D0 design PR (this PR)
   -> independent codeowner review + repository CI
   -> R2-I1 separately reviewed VM-only implementation
   -> disposable topology and OOB recovery acceptance test
   -> R2-V1 explicit authorization of private real-VM experiments
   -> V01..V28 + each R1 V26 durability/effect boundary
   -> independent private evidence review; recorded failures/unknowns
   -> possible provisional F02/F03/F04/F05 decisions (not F01)
   -> no direct route to production deployment
```

At each transition, missing prerequisites yield `BLOCKED`, not `PASS`. Do not parallel-activate F01 or R2 privileged features while review is pending.

## Non-goals

No new production command, QML mutation, installer, systemd service, firewall rule, network daemon, public upload/telemetry, remote API, central backend, key enrollment, or automatic deployment is authorized. This PR changes only docs, synthetic machine-readable planning data and a standard-library offline contract verifier/tests. Existing privacy, CODEOWNERS and CI protections must remain intact.

## Reference and coverage

- Canonical transaction specification: [RECOVERY_STATE_MACHINE.md](RECOVERY_STATE_MACHINE.md)
- Canonical full 28-row experiment matrix: [RECOVERY_VM_VALIDATION.md](RECOVERY_VM_VALIDATION.md)
- R1 implementation and limitations: [RECOVERY_R1_REPORT.md](RECOVERY_R1_REPORT.md)
- R2 row-for-row locked plan: [../r2/validation_plan.json](../r2/validation_plan.json)
- Evidence and independent review: [RECOVERY_R2_EVIDENCE_CONTRACT.md](RECOVERY_R2_EVIDENCE_CONTRACT.md)
- Release/activation boundaries: [RECOVERY_R2_GATES.md](RECOVERY_R2_GATES.md)
