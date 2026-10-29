# F01 — independent network evidence authority (design candidate)

**Status: F01 OPEN / INTEGRATION BLOCKED / VM VALIDATION NOT RUN.**

This is a review proposal for the distinct F01 problem identified in
`SECURITY_REVIEW_01B_V2.md`, not a substitute for that finding or for the
28-case recovery VM plan. The current read-only CLI, optional evidence linter,
repository governance and approved R1 recovery reference model remain unchanged.
No privileged executor, SSH/UFW mutation, signer, probe collector, daemon or
production trust anchor is supplied by this proposal.

## Failure being fixed

The rejected 01b candidate used a shared HMAC to authenticate client reports.
An enrolled key holder or the DUT (which also had the key) could fabricate a
post-change timeout/refusal, matching ICMP controls and unused source port; the
validator accepted this as a negative SSH reachability test although no TCP
attempt occurred. This is **not** fixed by changing HMAC to Ed25519 alone:
an authenticated liar is still a liar. Missing sshd journal entries and an
operator checkbox are not independent negative proof.

**Non-negotiable rule:** client-originated reports, MACs, signatures, journal
silence, operator attestations and on-host status output may be supporting
context, but **none may independently satisfy negative reachability**. Any
missing, contradictory, stale, replayed, or unverifiable observer evidence
must return `NOT_VERIFIED` and must not cancel recovery or authorize retention.

## Trust boundaries and intended future implementation

1. **DUT:** the Omarchy guest being inspected; untrusted as a source of external
   access facts. Its UFW files, kernel rules, local journal and state may be
   privately collected for comparison but cannot self-certify reachability.
2. **Client fixtures:** an authorized and unauthorized disposable client, each
   independently controlled on a completely isolated virtual switch. Do not
   assume client possession of a signing key proves an actual probe occurred.
3. **Witness:** an independently administered hypervisor or capture appliance
   outside the DUT and client trust/storage domains. It must observe outbound
   attempts and the relevant packets on the VM switch (with tested packet
   coverage), not merely echo client RPC results. The witness controller and
   its signing keys must never reside on the DUT, client or shared HMAC store.
4. **Challenge authority:** a distinct, independently administered verifier
   issues fresh unpredictable, single-use run/challenge nonces and an approved
   exact policy digest, checks receipt freshness and single use, and pins
   expected witness identity and public key *out of band*. DUT-controlled
   enrollment, on-path key substitution and optional CI variables are not a
   trust anchor. Challenge issuance and state ledger must survive verifier
   crashes without accepting replay or recycling accepted decisions.
5. **Human decision:** an independent reviewer inspects private raw receipts,
   capture/controller bounds, traffic controls and exact scope. Only a future,
   separately reviewed policy engine can decide what an independently validated
   observation authorizes. This proposal grants **no** deployment authority.

A signature authenticates the origin/integrity of the witness receipt only.
Before trusting the signed body, separately validate the installed witness
binary/image and key custody, capture interface, isolated topology, clock/boot
identity, dropped-packet counters, control traffic and provenance of the
recorded syscall/packet observation. Do not make the witness or challenge
authority accessible for a DUT or client to mint arbitrary receipts.

## Required evidence sequence (all IPv4 and IPv6)

At least eight **distinct** run-bound challenges are needed: baseline and post,
for authorized and unauthorized roles, in both families. Each must include:

- Run and one-time challenge IDs; cryptographically random nonce; policy digest;
  fixed stage, role and client identity; source/destination/family/port;
  expected target SSH host identity; trust-domain, boot and monotonic/wall-clock
  windows; and linkage from post to its exact baseline challenge.
- Direct route/topology and link observations. No bridge, NAT, forwarding,
  upstream path or host SSH agent; dedicated test credentials remain private.
- Independent witness receipt binding the precise challenge, attempted TCP/22
  flow, observed SYN timestamp, capture **start and end** times, interface and
  capture-loss counters. The witness must demonstrate the SYN left the expected
  source and was seen at the monitored DUT-side path. All baseline capture
  windows must **finish strictly before any post-change capture begins** in
  either IP family or client role. Challenge issue times alone do not establish
  this ordering. A client-signed `timeout` alone is not proof.
- Authorized positive control: fresh non-multiplexed key-authenticated SSH
  login in **both** families, with server identity pinned by the client and
  independent flow observations. Baseline unauthorized source must also be
  proven capable of reaching TCP/22 before restriction.
- Post negative outcome: on each unauthorized family, independently observe
  a test SYN and the absence of an established TCP connection through the **full
  bounded negative-observation window**. The model demands at least 8 elapsed
  seconds after the observed SYN, a positive capture interval of no more than
  45 seconds, and a capture end no later than challenge expiry. These limits
  are synthetic protocol checks, **not** verification of actual wall-clock
  elapsed time; a future real harness must independently calibrate and test
  the timeout and packet-capture interval. Require packet capture completeness
  and positive liveness/control traffic. A refused handshake is not equivalent
  to a firewall drop; record the observed result rather than inventing its cause.
- Post authorized fresh login must continue to succeed. A timeout caused by
  routing, downed service, wrong destination, key failure or packet-capture
  loss is `INCONCLUSIVE`, not proof of safely restrictive UFW policy.
- Confirm independently observed *actual* kernel and persistent rule images,
  the correct host/boot/service and continued out-of-band console recovery.
  A privileged operator or off-path network administrator can invalidate the
  captured assumptions; use explicit, bounded lock/TOCTOU and drift checks.

The witness must preserve immutable, content-addressed, authenticated private
receipts outside DUT snapshots. Cross-check receipt identifiers/sequence with
an append-only or replay-resistant verifier ledger and reject old, duplicate,
unknown, late and contradictory reports. Keep raw captures, host addresses,
identities, private signing keys, serial numbers and credentials **out of Git,
CI artifacts, logs, and chat**. Publish only sanitized test IDs and outcomes.

## Deterministic reference model in this PR

`tests/support/f01_authority_reference.py` is a **pure in-memory logic model**.
Its `ObserverTrace` is a synthetic *assumption* that an independent authenticated
observer supplied a measured trace. The model deliberately **does not validate
cryptography, provenance, packet truth or independent administration**. All
results, including a fully consistent synthetic matrix, retain
`verdict=NOT_VERIFIED` and `deployment_authorized=False`. The
`model_consistent=True` diagnostic must never be wired to an actual hardener,
evidence verifier, recovery cancellation or deployment gate.

`tests/test_f01_authority.py` tests fabricated enrolled-client claims without
witnesses; missing families, missing authorized login, failed baseline controls,
contradictory negative packets, nonexistent SYNs, lost captures, missing control
traffic, untrusted DUT witness domain, wrong policy/source/destination, expired
or replayed challenge, reused nonce, incorrect baseline linkage, overlapping
baseline/post captures and prematurely finished negative observation windows. All
fixtures use reserved documentation addresses and synthetic identifiers.

No current application imports the model; no new runtime dependencies or
workflow permissions are needed. The original offline evidence schema/linter
continue to return `NOT_VERIFIED` regardless of report signatures.

## F01 closure acceptance — separate milestone, not satisfied here

- [ ] Separately review a real isolated witness implementation and challenge
      authority, including pinned asymmetric key lifecycle, access control,
      replay-resistant ledger and adversarial enrollment/key-compromise cases.
- [ ] Independently verify real probes and raw packet captures from distinct
      IPv4/IPv6 clients; prove the unsafe fabricated-claim reproduction is
      rejected even when an enrolled client key holder signs every field.
- [ ] Demonstrate capture coverage, loss/clock/route/SSH-server controls and
      mismatch handling; differentiate TCP success, authentication failure,
      refusal, timeout and firewall causality without conflation.
- [ ] Exercise client/DUT/report key compromise and witness outage: fail
      closed; never allow the compromised party to manufacture a trusted
      witness receipt or turn missing evidence into positive authorization.
- [ ] Validate out-of-band console recovery, pre/post UFW live/persisted
      images and concurrent-external-change behavior in authorized disposable
      VMs without touching production hosts.
- [ ] Perform an independent security review of implementation, raw private
      evidence and threat assumptions; do not auto-close F01 on a model or CI
      result. Retain F02–F05 integration/VM gates and separate F01 authority.

**Decision for this proposal:** accept or reject the non-production design and
negative-control tests on their own merits. **Do not close F01, declare
external reachability `VERIFIED`, or ship a privileged deployment component.**
