"""Non-production F01 authority gate model; NOT a signature or packet verifier.

Only an external verifier, separately controlled from DUT/client, could supply
real authenticated observations. This model receives synthetic oracle inputs;
client claims and client-held HMACs are intentionally not proof.
"""
from dataclasses import dataclass
import ipaddress
import re


@dataclass(frozen=True)
class Challenge:
    run: str
    policy: str
    challenge_id: str
    nonce: str
    stage: str
    role: str
    family: int
    source: str
    destination: str
    port: int
    issued: int
    expires: int
    baseline_id: str | None = None


@dataclass(frozen=True)
class ObserverTrace:
    """Synthetic, externally verified packet observation *assumption*.

    The model has no key/trust-store, capture device or proof of honest execution.
    This object MUST NOT be accepted as deployment evidence by runtime code.
    """
    challenge_id: str
    run: str
    policy: str
    nonce: str
    stage: str
    role: str
    family: int
    source: str
    destination: str
    port: int
    observed_at: int
    observer_domain: str
    syn_seen: bool
    tcp_response_seen: bool
    ssh_authenticated: bool
    capture_complete: bool
    capture_drops: int
    independent_control_ok: bool


@dataclass(frozen=True)
class Decision:
    model_consistent: bool
    reason: str
    verdict: str = "NOT_VERIFIED"
    deployment_authorized: bool = False


def evaluate(challenges, traces, *, run, policy, observer_domain="independent-vm-monitor", client_claims=()):
    """Check an injected synthetic observation matrix without trusting reports.

    Client reports (including correctly signed HMAC claims) have no authority.
    The returned model_consistent flag is NOT real-world reachability evidence.
    """
    # Deliberately never inspect client_claims: they cannot create a probe witness.
    _ = client_claims
    blocked = lambda reason: Decision(False, reason)
    slots = {(stage, role, family) for stage in ("baseline", "post")
             for role in ("authorized", "unauthorized") for family in (4, 6)}
    if len(challenges) != len(slots) or len(traces) != len(slots):
        return blocked("incomplete-or-duplicate-matrix")
    if observer_domain in ("dut", "client", "operator", ""):
        return blocked("no-independent-observer")
    indexed = {}
    for c in challenges:
        slot = (c.stage, c.role, c.family)
        if slot not in slots or slot in indexed:
            return blocked("unexpected-or-duplicate-challenge")
        if (c.run != run or c.policy != policy or c.port != 22
                or not isinstance(c.challenge_id, str) or not c.challenge_id
                or not isinstance(c.nonce, str) or not re.fullmatch(r"[0-9a-f]{64}", c.nonce)
                or type(c.issued) is not int or type(c.expires) is not int
                or not 0 < c.expires - c.issued <= 900):
            return blocked("invalid-challenge-binding")
        try:
            src, dst = ipaddress.ip_address(c.source), ipaddress.ip_address(c.destination)
            if src.version != c.family or dst.version != c.family or str(src) != c.source or str(dst) != c.destination:
                return blocked("invalid-address-family")
        except ValueError:
            return blocked("invalid-address-family")
        indexed[slot] = c
    if len({c.challenge_id for c in challenges}) != len(slots) or len({c.nonce for c in challenges}) != len(slots):
        return blocked("reused-challenge")
    for family in (4, 6):
        if indexed[("baseline", "authorized", family)].source == indexed[("baseline", "unauthorized", family)].source:
            return blocked("roles-share-source")
        if indexed[("baseline", "authorized", family)].destination != indexed[("baseline", "unauthorized", family)].destination:
            return blocked("clients-target-different-servers")
    for (stage, role, family), c in indexed.items():
        base = indexed.get(("baseline", role, family))
        if (stage == "baseline" and c.baseline_id is not None) or (stage == "post" and c.baseline_id != base.challenge_id):
            return blocked("incorrect-baseline-link")
        if stage == "post" and (c.source, c.destination, c.port) != (base.source, base.destination, base.port):
            return blocked("post-flow-differs-from-baseline")
        if stage == "post" and c.issued < base.issued:
            return blocked("post-issued-before-baseline")
        matching = [t for t in traces if t.challenge_id == c.challenge_id]
        if len(matching) != 1:
            return blocked("missing-or-duplicate-witness")
        t = matching[0]
        if (t.run, t.policy, t.nonce, t.stage, t.role, t.family, t.source,
                t.destination, t.port) != (c.run, c.policy, c.nonce, c.stage,
                                          c.role, c.family, c.source, c.destination, c.port):
            return blocked("witness-not-bound-to-challenge")
        if (t.observer_domain != observer_domain or type(t.observed_at) is not int
                or not c.issued <= t.observed_at <= c.expires
                or not t.capture_complete or type(t.capture_drops) is not int
                or t.capture_drops != 0 or not t.independent_control_ok or not t.syn_seen):
            return blocked("unreliable-or-unobserved-probe")
        if role == "authorized":
            if not t.tcp_response_seen or not t.ssh_authenticated:
                return blocked("authorized-fresh-ssh-not-proven-in-model")
        elif stage == "baseline":
            if not t.tcp_response_seen:
                return blocked("unauthorized-baseline-tcp-not-seen")
        elif t.tcp_response_seen or t.ssh_authenticated:
            return blocked("negative-probe-contradicted")
    # This result does NOT indicate authentic attestations or packet truth.
    return Decision(True, "synthetic-witness-matrix-consistent")
