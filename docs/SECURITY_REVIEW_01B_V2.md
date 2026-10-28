# SSH-HARDEN-01b v2 security review — 2026-10-27

**Decision: do not integrate or deploy the privileged candidate. Support a limited,
read-only v0.2 proposal consisting of an evidence interchange schema, an offline
linter, synthetic tests and this review. Findings require human review before any
merge, push, release or deployment.** This is a source review and synthetic test
exercise, not a security certification or a fresh audit of this host's firewall.

## Scope and handling

All six v2 deliverables were read as untrusted material from the supplied local
audit directory: `ssh_hardening_v2.sh`, `ssh_evidence_collector.py`,
`ssh_evidence_schema.json`, `test_ssh_hardening_v2.py`,
`ssh_hardening_v2_plan.md`, and `ssh_hardening_v2.diff`. The release manifest lists
the first five, not the diff; their SHA-256 values matched the supplied manifest.
That manifest is co-located and unsigned: matching it identifies reviewed bytes,
not a trusted publisher. The original script and 23 original test definitions
were also reviewed to understand inherited behavior. No instruction in those
files was treated as authorization to deploy.

The supplied tests ran unprivileged, after inspecting their execution paths.
They exercise mocks and temporary files; no candidate deployment entry point was
invoked. The original tests read the original private policy locally; neither
those private fixtures nor the original tests were imported into this repository.
No production UFW, SSH, systemd or installed security script was changed. No real
evidence, journal, backup, transaction, endpoint list or key was copied into Git.
The source plan's account of a previous rollback remains an unverified historical
assertion for this review; it is not evidence for a new run.

Source references below are filenames and line numbers in the supplied candidate,
not line numbers in the proposed evidence-only patch.

## Prioritized findings

| ID | Priority | Disposition |
| --- | --- | --- |
| F01 | P1 — integration blocker | An enrolled HMAC holder can fabricate accepted negative observations |
| F02 | P1 — recovery blocker | Emergency rollback depends on the full evidence/dependency audit |
| F03 | P1 — lifecycle blocker | Interrupted finalization commits `verified` before timer cancellation |
| F04 | P1 — recovery assurance blocker | Power-loss durability and actual timer activation are unproved |
| F05 | P2 | Timer identity/deadline and ended-state cleanup are incomplete |
| F06 | P2 | Journal correlation lacks destination, boot and on-wire challenge binding |
| F07 | P2 | Published schema and runtime validation disagree |
| F08 | P2 | Client execution and key/challenge provisioning rely on ambient trust |
| F09 | P2 | File and executable integrity claims exceed what is checked |
| F10 | P2 | Host-specific policy and operational material are not reusable source |

### F01 — authenticated claims can still be invented (reproduced)

`ssh_evidence_collector.py:203-205,255-306,411-473` authenticates the whole report
with HMAC-SHA256, compares the stored challenge and policy, and requires operator
attestation. For post-change negative tests, it then trusts signed booleans for
ICMP controls and a signed `timeout`/`connection_refused`, provided it finds no
matching sshd event. There is no independent witness that a TCP attempt occurred.
A key holder can choose an unused source port, invent times and controls, sign
the report, and import it. The protected host also holds every HMAC secret and
can generate the same reports. These are MACs, not asymmetric signatures or
nonrepudiable client attestations.

A synthetic probe supplied valid simulated baseline and authorized-login
witnesses, constructed both post-change negative reports without calling either
client helper, and obtained `validate_post(...) == []`. No network probe ran.
The source documentation acknowledges dishonest clients as out of scope; that
assumption does **not** satisfy a requirement that signing self-reported results
cannot attest to reachability. The root collector has no finalize command, but
its accepted result is used by the hardener to cancel recovery.

Fix: retain `NOT_VERIFIED` for this evidence class. Any future stronger assurance
needs a separately trusted measurement service/device and an explicit threat
model, with policy-bound client identities, independently authenticated results
and independently administered observation. Asymmetric keys improve separation
and provenance, but do not make a dishonest client truthful. ICMP success does not
prove the TCP/22 path worked, or attribute a drop to this firewall.

### F02 — unrelated failures can disable emergency recovery (static control flow)

`ssh_hardening_v2.sh:75-123,574-575,597-615` calls `executable_security()` before
dispatching **every** root operation, including automatic rollback. That gate
requires the collector, schema, Docker, systemd-analyze, a UFW Python package,
all enumerated standard-library files and shared-library inspections. Missing or
unreadable evidence code, Docker removal, package layout changes or a failed
inspection prevents the broad SSH restoration at `449-461`. The same code bundle
must remain executable throughout the pending transaction. Restart-on-failure
cannot fix a persistent missing dependency.

Fix: a separately reviewed, minimal recovery executable must depend only on its
protected transaction/recovery data and the actual restore mechanism. It must
work with evidence, Docker, journald and the collector unavailable. Validate
recoverability in an isolated VM before authorizing restriction. This review
does not claim an unprivileged attacker can remove root-owned dependencies.

### F03 — finalization has a durable-state/cleanup gap (reproduced)

`ssh_hardening_v2.sh:522-538` saves `phase=verified` before `stop_timer()`.
If cancellation fails or power is lost between those operations, automatic
rollback explicitly returns `NO_OP` for `verified` (`449-452`). A subsequent
successful `verify` before expiry returns `timer_cancelled=true` based solely on
that phase, even if the timer is still armed. After expiry, evidence verification
rejects a retry, so finalization cannot complete its cleanup through that path.

The injected stop failure reproduced all three facts: durable verified state,
an active simulated timer, and a false cancellation report. Evidence had passed
before the failure; this is an ambiguous lifecycle/result problem, not proof
that incomplete evidence passes the normal verifier.

Fix: define a durable commit and cleanup protocol with explicit recovery of each
intermediate state. Report observed cancellation, never infer it from a phase.
Boot recovery must distinguish a valid committed restriction from an incomplete
commit and act deterministically. Simply moving the save after cancellation
creates a different unsafe crash window and is not a complete fix.

### F04 — persistent timers do not establish crash safety (static + untested)

`ssh_hardening_v2.sh:398-438` uses an absolute `OnCalendar` deadline and
`Persistent=true`; it enables the timer and checks `is-active` before UFW changes.
This is a useful timer-first order. However, the two unit files are written
sequentially with `open('x')` and chmod, without atomic replacement, file fsync or
parent-directory fsync. There is no explicit transaction establishing durable
unit contents, enablement and rollback state before a persistent firewall edit.
The firewall backup at `377-396` is checked by reading it but is also not fsynced.
A same-boot readback is not a power-cut test.

Systemd documents that persistent calendar timers catch up after inactivity;
that presupposes the units/enablement survive and the service can execute. It
does not make several filesystem writes atomic. No VM reboot, forced power cut,
disk-full/fsync failure or crash at each write boundary was tested. Clock steps,
suspend and service timeout/retry behavior also remain untested.

Fix: durable publication and readback, a boot reconciler for unfinished runs,
bounded recovery dependencies and real power-cut fault injection. Validate both
live packet rules and UFW's persisted configuration after recovery. See
[systemd.timer](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html).

### F05 — active is insufficient, cleanup is not idempotent (partly reproduced)

`ssh_hardening_v2.sh:473-483` accepts repeated pending apply when `is-active`
returns success, without rechecking the deadline, next elapse, loaded service
command, drop-ins, timer marker or enabled state. An expired deadline plus a
simulated active timer returned `NO_OP`. An active calendar timer can have no
future occurrence; active status alone is not a recovery guarantee.

`stop_timer()` checks marker comments in files but not the loaded manager
configuration. `arm_timer()` rejects existing files/name, which usefully blocks
ordinary stale-unit reuse, but does not check the service name separately. The
service command has no expected run ID argument; its marker is only a comment.
This is insufficient defense against stale queued work in a future reuse design;
the current candidate generally refuses reuse rather than providing one.

Rollback saves `rolled_back` before stopping the timer. An injected stop failure
left the timer active; repeated rollback returned `NO_OP` and did not retry
cleanup. Partial unit installation can likewise leave manual cleanup necessary.
Rule restoration itself is ordered broad-first and is repeatable while pending,
but full lifecycle idempotence is incomplete. Manual rollback of `verified` is
allowed and intentionally reopens broad access; automatic rollback skips it.
The verification failure response also says the timer remains armed even when
the collected errors explicitly include an inactive timer (`531-533`). That
message is not an observation of available recovery.

Fix: bind service invocations to the expected run, verify the loaded timer/service
and a future bounded trigger, and make end-state cleanup retryable without
reopening a valid committed firewall. Exercise both already-running service and
stale persistent-timestamp cases. Systemd does not restart a target service that
is already active when a timer fires; see the timer documentation linked above.

### F06 — journal evidence is useful but incompletely bound (static + synthetic)

`ssh_evidence_collector.py:212-231,284-305` requires trusted `_UID`, `_EXE` and
`_SYSTEMD_UNIT` fields. That excludes a normal user's `logger` text and is an
improvement over matching a message alone. However, normalized events contain
source, source port and wall time, but no local destination/port, boot ID,
monotonic time, service invocation ID or challenge nonce. A suitable unrelated
login from the same source/port/time can serve as the witness; the challenge is
not echoed through an authenticated server-side operation. A synthetic witness
with no destination information was accepted. The stored receipt's
`journal_cursor` is not compared to the reselected event on revalidation.

Only the latest 10,000 records in 24 hours are read. Truncation, dropped events,
rotation, disabled log levels and delayed delivery are not distinguished from an
absence of contradictory events. A received banner hash is a client assertion
and does not authenticate a particular server host key. Clock synchronization
within five seconds is assumed, not measured. Post report times are bounded by
apply/deadline, but the actual journal event's upper bound can extend five seconds
beyond the report window; event boot/time provenance needs an explicit contract.

Fix: capture a server-side challenge witness and exact flow/destination plus boot
and monotonic bounds; retain and validate exact witness identity and coverage.
Missing evidence must remain inconclusive. Even complete journal silence cannot
prove an unobserved remote attempt. Trusted-field semantics and boot/monotonic
fields are described in
[systemd.journal-fields](https://www.freedesktop.org/software/systemd/man/latest/systemd.journal-fields.html).

### F07 — schema validity is not runtime equivalence (reproduced)

The original schema is a **valid Draft 2020-12 schema**. Valid synthetic challenge,
report and bundle objects pass an independent validator with format checking.
There is no timestamp-escaping bug; an initial display-based suspicion was
disproved by running both validators.

Patterns for nonce, hashes, identifiers, user names and timestamps are unanchored
in `ssh_evidence_schema.json`; JSON Schema uses substring matching while the
runtime uses `re.fullmatch` (`135-200`). A prefixed/suffixed 64-character nonce
passes the published schema but fails the runtime. The optional supplied schema
test (`test_ssh_hardening_v2.py:345-350`) checks only the meta-schema, not any
instances or agreement. Formats require an enabled checker and its dependencies;
without format enforcement the IPv4/IPv6 `oneOf` branches can both match.
Standard JSON Schema also accepts integral numeric encodings such as `41000.0`,
while the candidate requires a Python `int`.

Fix in this proposal: explicitly anchor patterns, independently test positive and
negative instances, require working date/IP/UUID checkers in CI, and document the
linter's stricter canonical encodings. Structural validity still allows empty
collections, contradictory claims and fake signatures by design; it is never
deployment authorization. See the
[JSON Schema validation specification](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.3.3).

### F08 — client trust and provisioning are operational assumptions (static)

Enrollment generates independent 256-bit HMAC secrets and protects the server
copy. Client `client_setup()` (`520-532`) checks a private regular file and key
length, but not its owner or ancestor permissions. Challenges are not authenticated
to the client; private authenticated transfer is assumed. There is no key
rotation/revocation or authorized client enrollment identity beyond the private
role file. `Store.key()` does not independently check key length/profile integrity.

`ssh_client()` (`586-613`) disables multiplexing, password/interactive auth,
proxies and forwarding and requires strict host-key checking. However it resolves
`ssh` through client PATH, inherits environment/config, omits an explicit TCP port,
and does not isolate arbitrary `Match exec`, `Hostname`, known-hosts or other SSH
configuration. Ping is an arbitrary absolute path chosen by the operator and also
inherits environment. Fixed argv does not mean reviewed executable/configuration.
These are client-integrity gaps, not a demonstrated root escalation on the server.

Fix: reviewed absolute client tools, controlled environment/config with explicit
port/target/known-hosts, authenticated challenge transport, per-user key ownership,
and a documented enrollment, revocation and rotation procedure. Client integrity
remains an assumption unless independently attested. OpenSSH configuration can
execute `Match exec` commands; see
[ssh_config](https://man.openbsd.org/ssh_config).

### F09 — privilege-boundary checks have limits (static)

Positive controls: absolute root subprocess paths and a fixed child environment;
Bash privileged mode and isolated Python; root-owned non-writable ancestors;
0700 state directories and private collector files; bounded regular JSON input,
duplicate-key/nonfinite rejection and leaf `O_NOFOLLOW`; same-directory temporary
JSON writes, file/directory fsync and exclusive receipt publication; a shared
flock for the main mutating operations.

Limits: the hardener's `trusted_path()` (`61-73`) permits root-owned symlinks and
does not require private modes, despite its docstring saying it rejects symlinks.
It hashes current files but has no independently authenticated expected digest.
Its interpreter/imports execute before their checks, and the collector is imported
before the full dependency walk. `-I -S` and Bash `-p` do not sanitize dynamic-loader
variables before process startup; a trusted, sanitized launcher/sudo configuration
is assumed. Checks by pathname followed by reopen are not descriptor-based and
do not resist a concurrent privileged replacement. Trusted, non-writable parents
substantially constrain an ordinary user's ability to exploit those races; no
unprivileged write-to-root exploit is established here.

The hardener reads saved transaction JSON without a private-file `Store.read`
check or transaction schema. Backup reads follow source symlinks, use a final
archive name before completion, and are not a generic safe restore implementation.
The collector refuses leaf input symlinks but does not pin untrusted input
ancestors. Deep JSON, malformed journal field shapes and large journal output
lack comprehensive resource bounds. The main hardener enriches evidence before
taking its lock (`580-598`); collector directory creation also precedes its lock.
External UFW administrators do not participate in that flock. These races require
explicit treatment; the shared lock alone does not serialize the whole system.

Fix: a protected launcher and immutable reviewed code version, fd-relative
no-follow access, validated transaction schema, declared privilege model,
bounded parsing/output, versioned locked transitions and explicit concurrency
rules for external firewall administration. Do not claim malicious-root resistance.

### F10 — deployment specialization and private state must be separated (verified)

The hardener contains literal deployment addresses/account, fixed DNS/Docker rule
inventories, an old transaction prerequisite and milestone-specific source checks
(`16-17,178-192,464-470`). Its plan embeds operational history and deployment
instructions. Original tests use a private policy. Replacing a few addresses is
not enough to create a portable root executor. None of these artifacts belongs
in the public integration patch.

The schema contains no endpoint examples or keys and can be retained after
correction and scope clarification. All proposed test addresses are documentation
ranges. Public/runtime storage boundaries and future acceptance gates are in
[ARCHITECTURE.md](ARCHITECTURE.md) and
[V0_2_INTEGRATION_PLAN.md](V0_2_INTEGRATION_PLAN.md).

## Verified properties, assumptions and incomplete validation

| Area | Verified by source/tests | Assumed or incomplete |
| --- | --- | --- |
| MAC | Canonical sorted JSON excluding signature; HMAC-SHA256; constant-time comparison; role/key selection | Truthful client, secure transfer, protected root; no asymmetric provenance |
| Replay | Exact stored challenge/nonce/policy/run; exclusive receipts; one slot/family; baseline linkage; ended-run rejection | No on-wire nonce witness, boot binding, robust clock discontinuity handling or key lifecycle |
| Time | UTC parser, narrow test interval, expiry, baseline age, apply/deadline checks | Actual synchronized clocks; power/clock-step testing; monotonic recovery deadline |
| IPv4/IPv6 | Exactly one authorized IPv4 and unauthorized tests for both families; matching baseline endpoints; controls and contradictory-event checks | Actual independent vantage, stable routing, ICMP/TCP equivalence; no physical path proof |
| Journal | Trusted root sshd metadata, source/port/user/method/window | Complete coverage, exact destination, current boot, exact receipt cursor, negative causality |
| Root storage | Stronger collector ownership/mode checks and durable JSON publication | Full no-follow behavior, installer/executable attestation, all crash boundaries |
| Recovery | Timer-first order and broad-first rollback in the modeled paths | Power-loss recovery, minimal dependencies, stale manager state, cleanup retry, real restore |

The supplied passing suite is evidence about these modeled paths only. The full
case inventory, added probes, schema results and untested threats are recorded in
[TEST_REPORT_01B_V2.md](TEST_REPORT_01B_V2.md).
