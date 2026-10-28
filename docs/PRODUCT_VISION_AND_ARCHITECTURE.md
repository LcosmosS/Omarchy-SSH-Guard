# Omarchy SSH Guard — Product Vision and Architecture

**Status: Proposed product requirements and design boundaries. Documentation only.**

**Current release:** v0.1.0 read-only audit CLI and informational Quickshell widget. The capabilities described as future or planned below **do not exist in the installed plugin**. This document does not authorize code execution, firewall changes, privileged integration, key enrollment, VM testing, or production deployment.

## 1. Mission and product principles

**Omarchy SSH Guard** is intended to evolve into a **local-first SSH identity, firewall management, security monitoring, and recovery system**, presented through a CLI and native Omarchy/Quickshell interface. The operator controls which machines are authorized, what a port's actual exposure is, which policy changes may occur, and whether an independently verified transaction is retained or rolled back.

Principles:

1. **Local-first, operator-owned.** No project-operated backend server, cloud account, tracking, telemetry, data harvesting, centralized evidence repository, or automatic upload. Local protected IPC/services and private log storage are permissible **only** when necessary, reviewed, user controlled, and clearly disclosed; they are **not** remote application backends.
2. **Read-only by default.** Auditing and browsing must never implicitly write UFW rules, modify OpenSSH, install credentials, or elevate privileges.
3. **Separate policy, authentication, and observation.** A locally displayed ALLOW rule, successful SSH authentication, and independently verified reachability are different facts.
4. **Explicit human authority.** Every future destructive action requires a reviewed exact plan, deliberate user approval, scoped privilege authorization, and traceable local decision.
5. **Recovery before restriction.** A real, durable, run-bound, independently verified rollback mechanism must be armed before any restrictive firewall mutation. Its continued effectiveness must be measured and tested.
6. **No synthetic security promotion.** A passing reference model, signed client statement, zero exit code, green UI badge or well-formed JSON is not independent evidence of a safe deployed policy.
7. **Honest states.** Use `NOT_VERIFIED`, `UNKNOWN`, `BLOCKED`, `FAILED`, and independently supported status labels, rather than presenting guessed security as guaranteed protection.

### Current versus intended boundaries

| Capability | v0.1.0 now | Future target |
| --- | --- | --- |
| Quickshell bar widget | Static informational text | Live read-only summary and detailed control panel |
| CLI | Unprivileged UFW/SSH/Docker audit and non-executable plan | Operator-facing policy review and user-authorized transaction requests |
| Device/key registry | Not present | Approved-machine identity, public-key fingerprints and revocation |
| Firewall application | Not present | Reviewed, narrowly authorized local transaction executor |
| Event log | Not present in plugin | Local, opt-in bounded firewall/sshd event ingestion and classification |
| External proof | Always `NOT_VERIFIED` | Independently witnessed dual-family network evidence; separate F01 gate |
| Recovery | R1 **synthetic model only** | Real systemd/UFW/storage protocol proven through R2 VM tests |
| Off-device data service | None | **None planned** |

## 2. Logical architecture and trust boundaries

```text
                  Omarchy / Quickshell (user privilege)
  +--------------------------------------------------------------+
  | Bar widget: status / event counters / btop++ launcher        |
  | Control panel: audit, ports, devices, evidence, review        |
  | Unprivileged CLI: audit, explain, diff, recommend             |
  +------------------------------+-------------------------------+
                                 |
                      typed local request + read-only status
                  NO arbitrary shell string or direct sudo
                                 |
  +------------------------------v-------------------------------+
  | Future, separately installed LOCAL authorization boundary    |
  | Explicit per-transaction polkit / OS privilege mediation     |
  | Root-owned validated policy executor and recovery mechanism  |
  | Transaction manifest + minimal dependency-closed restorer    |
  +--------------+------------------------------+----------------+
                 |                              |
       UFW/effective nftables           OpenSSH configuration
       firewall state, IPv4/IPv6        authorized_keys/certificates
                 |                              |
       local kernel/persistent            sshd authentication
       observations                       events and user mapping
                 +---------------+--------------+
                                 |
             Local operator-controlled records and receipts
             no project cloud, collection server or telemetry

 External truth boundary (future experiments only):
 independent IPv4/IPv6 test clients + off-DUT network/hypervisor witness
       -> independent verifier/authorized human review
       -> never inferred from QML, local logs or client signatures
```

The future local privileged helper is **not** an instruction to introduce a root-privileged QML plugin. A user-writable widget/CLI must not be executed through `sudo`; a separately installed, immutable/root-owned helper should accept only a reviewed, structured transaction format and must independently validate path, policy, run ID, requested effect, ownership, deadlines and explicit authorization. Never expose a general `run_command` or arbitrary shell interface to QML.

No component is implemented by this diagram. The current installer copies only the unprivileged audit CLI, and the current widget does not invoke it.

## 3. SSH identity and key-aware access

A firewall at the TCP/IP layer **cannot authenticate an SSH public key from the initial packet**. UFW/nftables filter by packet/network properties; OpenSSH authenticates a key holder after a TCP connection reaches `sshd`. Therefore "recognized keys" must refer to **OpenSSH's identity/access policy**, not claimed L3/L4 packet recognition.

### Access profiles

| Profile | Network reachability | SSH authorization | Intended operator use |
| --- | --- | --- | --- |
| **Key-guarded SSH** | SSH TCP endpoint may be reachable by other sources | Only enrolled public keys/approved SSH certificates, mapped to allowed Unix users and least-privilege options, authenticate | Standard managed remote access |
| **Network-concealed SSH** | SSH endpoint available only through an independently authenticated or allowlisted network path (e.g., a WireGuard tunnel; any single-packet authorization option requires its own threat review) | Same OpenSSH key/certificate authorization remains mandatory | Higher-assurance environments where public TCP/22 exposure is undesirable |

Modes are **future proposals**, not current CLI commands. Neither profile guarantees the absence of malicious traffic or account compromise.

### Planned machine registry

A local, protected record for each approved machine should include:

- User-defined device label, immutable internal device identifier, owner/Unix-account mapping and explicit permitted access scope.
- Public-key type, canonical fingerprint, optional certificate principal/CA trust and validity/revocation state; **never require remote private-key escrow**.
- Enrollment/review provenance, creation/rotation/expiration dates, last *verified* successful SSH authentication when attribution is supported, and verification limitations.
- Device disable/revoke, key removal, rotation and audit trail, with an independent rollback plan for changes that could lock out administrators.

Generate private keys on **the authorized client machine**, preferably in a hardware-backed key store when available; transfer only public keys or appropriately signed certificates to the Omarchy host. If a future key-generation UI is used for the local host or an explicitly authorized client, label where the private key is generated/stored, request consent and never transmit it to a server. Avoid inferring key identity from source IP alone. A dropped firewall packet carries **no authenticated SSH public-key identity**.

### Revocation and threat cases

Plan for key theft, compromised clients, shared-account misuse, lost devices, expired certs, revoked keys, host-key pinning failures, DNS/route drift, and concurrent administrator changes. Revocation must update the actual OpenSSH authorization surface without silently removing the last tested recovery identity.

## 4. Firewall model and truthful per-port status

The future CLI and dashboard should present **distinct** port dimensions, each with its observation source and freshness:

| Dimension | Example values | What it does *not* establish |
| --- | --- | --- |
| Listener | `LISTENING`, `NOT_LISTENING`, `UNKNOWN` | Internet reachability |
| Effective network policy | `ALLOW`, `DENY`, `FILTERED`, `UNKNOWN` per source/family/path | OpenSSH user authorization |
| Authentication posture | `KEY_ONLY`, `PASSWORD_ALLOWED`, `NOT_APPLICABLE`, `UNKNOWN` | Truth of external firewall path |
| Container/forwarded path | `FORWARDED`, `LOCAL_ONLY`, `UNKNOWN` | That UFW `INPUT` captures all traffic |
| Independent access verification | `VERIFIED`, `FAILED`, `NOT_VERIFIED` with time/run and witness | Continuing safety after configuration drift |
| Observed events | Local count, category, source policy, bounded time window | All attempts or identity of rejected TCP clients |

Do not derive a single absolute `GUARDED` badge merely from a local `ufw status` line. If a summary label is offered, it must clearly indicate its scope (e.g., "**Host policy: restrictive; external verification: NOT_VERIFIED**"). The status of TCP/22 must be evaluated separately for IPv4, IPv6, routing/NAT, Docker-published ports, and active interfaces. Docker can publish paths outside ordinary UFW `INPUT` enforcement; do not mutate Docker's own chains blindly.

The **CLI firewall** is a desired user experience, not a currently deployed enforcement capability. Future text commands may support `audit`, `devices`, `ports`, `recommend`, `review`, and `revert` through typed interfaces, but no command name in this document is a runnable production feature.

## 5. Security event collection and retention

The future dashboard should distinguish **source-observed** event classes:

| Class | Origin | Meaning / limitation |
| --- | --- | --- |
| `FIREWALL_BLOCKED` | Kernel/packet-filter counter or bounded logging rule | Blocked network attempt; **not** an SSH public-key identification |
| `SSH_AUTH_FAILED` | Authenticated, validated local sshd logs/journal | SSH-layer authentication failure; may contain claimed identities, not proof of account ownership |
| `SSH_AUTH_SUCCEEDED` | Validated local SSH authentication event | Successful local authentication subject to provenance/race limits |
| `NETWORK_CONNECTION` | Local connection/socket observation | Connection occurred; may not be an authentication attempt |
| `UNOBSERVED/UNKNOWN` | Missing/disabled/error logging path | Never display zero as evidence no attempts happened |

Separate counters by destination port, source family, time window, effective policy state and collector health. Make it obvious when an observation source is missing or incomplete. Avoid indiscriminate packet logging, unbounded journal access, DNS enrichment, remote IP geolocation, or automatic publication. Logs may contain personal/security-sensitive data: default to minimal aggregates and explicit operator controls for retention, encryption where appropriate, redaction, and deletion. The widget should not read raw privileged logs itself.

## 6. Quickshell widget and btop++-adjacent monitoring

Planned bar widget: concise security verdict scoped to the local host, protected/unknown/exposed port counts with provenance, local event-count window, recovery-timer/transaction state, and a visible `NOT_VERIFIED` external-proof indicator until a real F01-qualified verifier has reported.

Planned detail panel tabs:

1. **Overview:** CPU, memory, disk and network resource summary plus a terminal launch action for installed `btop++`. A lightweight panel should obtain resource summaries through a reviewed, bounded unprivileged local interface; `btop++` remains a separate terminal monitor, not a firewall telemetry backend.
2. **Ports:** independently labeled listening, filtering, authentication and reachability dimensions for each port/family; show timestamps and missing coverage.
3. **Attempts:** categories, bounded counts, time range, log completeness and privacy-friendly drill-down.
4. **Devices & keys:** enrollment review, fingerprints, effective Unix account, revocation/rotation and explicit user consent.
5. **Audit & recommendations:** current state, intended vs effective policy, conflict detection and before/after diff.
6. **Deployment & recovery:** policy-specific review, approval, authorization, independently observed timer, deploy/finalize/revert progress; fail-closed error explanations.

**Illustrative UI (not real telemetry):**

| Port | Policy display (illustrative) | Events (illustrative) | External verification |
| --- | --- | ---: | --- |
| 22 / SSH | Key-restricted | 8 | `NOT_VERIFIED` |
| 80 / HTTP | Exposed | 24 | `NOT_VERIFIED` |
| 443 / HTTPS | Filtered | 6 | `NOT_VERIFIED` |

Illustrative resource figures (CPU 37%, memory 54%, network 19%, disk 42%) are *visual mock data*, **not** measurements from a device. Never hardcode them as live UI output.

No automatic privilege escalation, direct root command execution or secret logging may originate from QML. Treat the unsandboxed long-lived shell process as user-trusted but **not privileged**.

## 7. One-click user workflow: one deliberate request, many safety gates

"One-click deployment" means **one operator-initiated guided transaction**, not bypassing evidence collection, authorization, or informed approval:

1. **Audit:** obtain live local configuration read-only; mark denied/unknown observations honestly; capture the relevant port/family/Docker/sshd dimensions.
2. **Recommend:** present a minimal proposed rule/key-policy diff, affected clients, effect on access, and uncertainty.
3. **Review:** user confirms exact operations, run ID, identity mapping, risk, backup and reachable out-of-band recovery path.
4. **Authorize:** request limited OS privilege for this *specific reviewed transaction* using an independently reviewed polkit/local authorization pathway.
5. **Protect:** persist recovery image, confirm its independent executability and arm a run-bound rollback timer **before** first restriction.
6. **Deploy:** perform only the approved atomic, auditable host changes. Block on unexpected concurrent drift.
7. **Verify:** independently controlled external authorized IPv4/IPv6 fresh SSH login and unauthorized IPv4/IPv6 TCP/path rejection; verify genuine F01 witness provenance, run binding, clocks, and loaded firewall/systemd state.
8. **Finalize or revert:** retain only on an independently verified, explicitly authorized completion decision; otherwise restore the exact baseline and independently confirm access, preserving an OOB recovery path.

The user interface must also expose **Revert**, including run binding, status, independently confirmed baseline restoration and history. A button press does not prove revert succeeded. Failure/uncertainty never silently cancels the rollback. Revoking a key must not strand the only administrator.

**Uninstall/disable separation:** removing the visual plugin must **not** implicitly destroy a pending rollback, delete a root-owned transaction or change existing firewall policy. A future separately managed helper requires an explicit, audited decommission process.

## 8. Installation and privilege boundaries

### Stage A — Native Omarchy plugin (current direction)

The documented `omarchy plugin add` mechanism clones/registers the third-party Quickshell plugin; it **does not run plugin install hooks or request sudo**. Omarchy's Setup > Plugins UI can manage enabled/disabled state. Third-party QML runs as user-accessible code in a long-lived desktop process and must be reviewed before enabling.

The current repository's `scripts/install-local.sh` only copies `omarchy-guard` into `~/.local/bin` under ordinary user permissions. It must never be invoked via sudo. Stage A does not install the future root helper, monitor services or any firewall policy.

### Stage B — Optional security-management enrollment (future, separately gated)

The product may eventually present a setup wizard with a **live read-only audit, human-reviewed remediation plan, recovery preflight and specific privilege authorization**. Only then may a separately packaged/root-owned and independently reviewed helper be installed under a controlled, privileged mechanism, potentially via a supported polkit-mediated interaction. Do not assume that the plugin installer itself authorizes sudo execution.

Before enabling any helper, require provenance/signature/pinning of installed bytes, least-privilege polkit rules, independently tested host-specific rollback, an explicit user consent record, and safe upgrade/decommission. The widget cannot supply arbitrary commands, environment-derived shell fragments or user-writable scripts to a root helper.

**No helper, privileged setup wizard or security-management Stage B exists in v0.1.0.**

## 9. Threat model and non-goals

| Threat/failure | Required mitigation or explicit limitation |
| --- | --- |
| Forged HMAC/client claim of a denied SSH attempt | Independent F01 witness; authentic report is not proof of observation; absence of evidence never permits commit |
| Malicious/compromised QML or local unprivileged caller | Typed helper API, strict input checks, root-owned immutable executable, no arbitrary command or blanket polkit authorization |
| Lost/compromised key or wrong Unix account mapping | Least privilege, approval/rotation/revocation, existing recovery path |
| Stale run/second administrator changing UFW concurrently | Real process lock and ownership checks at each effect; drift detection; never overwrite unknown policy |
| Power loss between write/rename/directory sync | Durable publication protocol, independent failure injection and VM evidence; uncertain marker blocks |
| Failed rollback or missing restorer | Independent out-of-band recovery; explicit `BLOCKED` not a false success |
| Journal outage, log gaps, flood/noisy events | Bounded local capture, reliable completeness indicator, no claim that absence means secure |
| Docker/NAT and IPv6 bypass | Check actual forwarding chains, dual-family reachability, route/interface coverage |
| Cloud exfiltration or credentials in Git | No remote service; redact/limit records; private keys and raw receipts remain off public source |
| Root/kernel compromise or malicious independent witness | Beyond automatic guarantees; record trust boundary and require separate adversarial review |

This document is a proposed product specification **not** a proof of full protection, not a replacement for a penetration test, and not an authorization to harden remote machines.

## 10. Milestones and acceptance criteria

| Milestone | Source status | Exit criterion and non-claim |
| --- | --- | --- |
| v0.1 | **Current** | Read-only audit/plan CLI and informational widget; no privileged effects |
| v0.2 evidence (PR #3) | **Merged** | Read-only local schema/linter, always `NOT_VERIFIED` |
| R1 recovery (PR #5) | **Merged** | Deterministic in-memory recovery tests; **not** systemd/UFW/power validation |
| F01-R0 (PR #6) | **Open design PR at authoring** | Independent evidence-authority design; **F01 stays OPEN** |
| R2-D0 (PR #7) | **Open design PR at authoring** | Locked 28-row disposable-VM contract; V01–V28 **NOT RUN** |
| R2-I1/V1 | **Future, gated** | Independently reviewed VM-only recovery executor, isolated testing, real fault and dual-stack witnesses |
| Product UI / inventory | **Future** | Mock vs observed distinguished, privacy-bounded read-only panel and per-port status fidelity |
| Identity registry | **Future** | Device-key-to-Unix-account mapping, enrollment/revoke/rotation with negative tests and user approval |
| Operator-only policy engine | **Future, blocked** | Typed plans and privilege separation; immutable review/rollback contract and no arbitrary root execution |
| Deployment/release | **Not authorized** | Independent F01 and F02–F05 closure, real host-specific recovery/access validation, responsible codeowner security sign-off |

### Phase acceptance checklist for later PRs

- [ ] No UI component claims live port/key status without identifying its data source and freshness.
- [ ] All security states are multidimensional; `UNKNOWN` and `NOT_VERIFIED` cannot masquerade as secure.
- [ ] Unauthorized firewall drops and OpenSSH authentication failures are not conflated or attributed to an unobserved public key.
- [ ] Private key material is generated and stored on the authorized device, never collected centrally.
- [ ] Automatic logging is minimal, bounded, local and user-controlled; no telemetry or backend is introduced.
- [ ] Stage A plugin installation remains unprivileged; privileged Stage B requires separately approved architecture.
- [ ] Any eventual policy mutation has exact operator-reviewed transactions, out-of-band recovery and verified armed rollback beforehand.
- [ ] Independent dual-stack reachability/witness evidence meets F01 and recovery proof gates; 28 VM cases may be marked passed **only after actual execution and independent review**.
- [ ] Removing the plugin cannot disable recovery or alter firewall policies without explicit, separately authorized decommission.

## 11. Normative references and change control

- [Current project README](../README.md) and [security policy](../SECURITY.md)
- [SSH hardening and manual recovery runbook](SSH_HARDENING.md)
- [R1 recovery state machine](RECOVERY_STATE_MACHINE.md) and [28-case VM protocol](RECOVERY_VM_VALIDATION.md)
- [Prior rejected integration security review](SECURITY_REVIEW_01B_V2.md)
- [PR #6 F01 evidence-authority design](https://github.com/LcosmosS/Omarchy-SSH-Guard/pull/6) (separate, unmerged at authoring)
- [PR #7 R2 disposable-VM design](https://github.com/LcosmosS/Omarchy-SSH-Guard/pull/7) (separate, unmerged at authoring)
- [Omarchy Shell Plugins manual](https://omarchy.org/manual/shell-plugins/)
- [OpenSSH sshd configuration](https://man.openbsd.org/sshd_config) and [authorized_keys format](https://man.openbsd.org/sshd.8)
- [Docker/UFW packet-filtering interaction](https://docs.docker.com/engine/network/packet-filtering-firewalls/)

This document expresses product *intent and testable requirements*; the present security policy and actual implementation always determine current operational scope. Any change that introduces privileged code or actual monitoring needs its own PR, negative tests, independent review and authorization. Documentation approval is **not** a security deployment gate.
