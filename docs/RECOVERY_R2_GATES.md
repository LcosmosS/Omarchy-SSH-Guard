# SSH-HARDEN-R2 — Prerequisites, review gates and decision ledger

R2 validation cannot begin merely because PR #5 is merged. The only result of this initial PR is a **design-stage contract**. It has no privileges and performs no networking.

| Gate | Entry conditions | Required exit artifact | State in this PR |
| --- | --- | --- | --- |
| R2-D0 DESIGN | R1 merged; 28-row protocol selected; F01 separated | Reviewed architecture, locked JSON matrix, synthetic validator/tests, reviewer checklist | **PROPOSED; not independently approved** |
| R2-I1 VM IMPLEMENTATION | D0 approved, no code from rejected v2 imported, fixed VM-only scope | Independently reviewed VM-only recovery executable, scoped fault harness, OOB preflight and negative tests | **NOT IMPLEMENTED** |
| R2-P0 PREFLIGHT | I1 approved; separately authorized disposable VM experiment | Independent isolation/console/snapshot checks, 3-guest inventory, dependency closure, protected evidence sink verified | **NOT RUN** |
| R2-V1 EXECUTION | P0 passed; correct run/revision/clock/syscall/fault schedule; F01 non-authority recorded | Private V01–V28 receipts, each boundary reached, both-family observations, immutable run ledger | **NOT RUN (28/28)** |
| R2-V2 INDEPENDENT VALIDATION | Complete private receipts and qualified independent reviewer | Findings F02–F05 provisional dispositions tied to evidence, blocked/failed cases retained | **NOT RUN** |
| R2-PRODUCTION | Separate independent F01, integration, security, recovery and release approvals | New production-specific protocol and explicitly authorized deployment | **NOT AUTHORIZED** |

## Phased implementation PR: required acceptance checklist

- [ ] VM-only target enforced at build/runtime and repository path; refuse non-disposable/host execution. No production installer integration, default automatic execution, or access to real workstation settings.
- [ ] True root-owned minimal restore path exists inside expendable DUT and has an independent dependency inventory.
- [ ] Real interprocess run lock, lease identity check before any hook, stale-job isolation and separate boot reconciler are implemented and fault-injected.
- [ ] Atomic publication + actual file/fsync/rename/directory fsync ordering recorded before mutation. Unknown commits block; valid commit markers preserve intended retention.
- [ ] VM-only fault harness can pause exactly before/after each canonical checkpoint and *prove* checkpoint execution.
- [ ] Independent systemd loaded unit, queued job and running recovery service observations distinguish failed cancel/false ack.
- [ ] Driver only mutates named guest firewall state and has negative tests ensuring non-guest paths/storage/host operations are impossible.
- [ ] Independent physical network/console observation channels remain outside the DUT and the suspect evidence publisher.
- [ ] Three disposable VMs are isolated, snapshots and manual OOB recovery tested, storage failure confined to expendable guest filesystem.
- [ ] No fixture credentials, packet traces, private host paths, operational rules or personal identifiers enter Git or CI.
- [ ] All implementation tests and existing repository privacy, plugin, schema and CodeQL checks pass before requesting independent code-owner review.
- [ ] Explicit human approval and separately authorized disposable execution before any real guest restriction or fault.

## Locked 28-row matrix

`r2/validation_plan.json` copies the six R1 columns exactly, adds `NOT_RUN`, and MUST remain locked. Any changed row requires a dedicated protocol amendment and independent review. A passing synthetic plan linter must never turn a row into executed or validated evidence. R1 `docs/RECOVERY_VM_VALIDATION.md` remains normative.

F02: V01–V04, V18–V19 and dependency-closure evidence.  
F03: V09–V13, V16–V19 and V28.  
F04: V05–V10, V20–V26 at **all** publication/effect boundaries; keep host physical-power claims out of scope.  
Recovery F05: V06, V14–V19, V23–V24, V27–V28.  
F01: parallel PR #6 only; no R2 inference.

## Independent review questions

1. Does any path allow a positive security/deployment status from modeled or self-reported evidence?
2. Is a stale run's ID checked **before** every privileged mutation, injectable checkpoint, timer/unit operation and dispatcher?
3. Can a new run change an old run's lease, executor or timer or vice versa? What ensures real OS locking?
4. Can a missing collector, Docker, journald or unrelated runtime dependency disable emergency restoration?
5. What happens when the guest is cut after file sync but before directory sync? How are old/new outcomes independently distinguished?
6. Does a false timer-cancellation acknowledgement leave pending cleanup, not a fabricated terminal state?
7. Are authorized and unauthorized IPv4 and IPv6 client observations separately recorded on each restoration and next reboot?
8. Are pre-cut receipts preserved outside the DUT's power/snapshot domain, with independent verifiable hashes **before** the cut?
9. Are missing coverage, unexpected host exposure and failed OOB access immediate STOP/BLOCKED conditions?
10. Is the outcome limited to disposable VM validation and independent review, without releasing an executor?

## Stop/abort conditions

Stop and mark **BLOCKED** if no independently reviewed executable, no protected host evidence sink, no out-of-band console, no clean snapshot, network leakage, unbound run identity, missing fault proof, untrusted current systemd configuration, unexpected storage target, absent essential metadata/restorer or loss of operator control. An observed broken recovery invariant is **FAIL**, not blocked-away. An empty or unexecuted case stays **NOT_RUN**.

**Current closure ledger:** R2 design under review; 0/28 VM cases executed, 28/28 NOT_RUN; no finding closed; no production effect; F01 separately open.
