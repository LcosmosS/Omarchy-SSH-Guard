"""Adversarial F01 test-only inputs: nothing calls a network or loads keys."""
from dataclasses import replace
import unittest

from support.f01_authority_reference import Challenge, ObserverTrace, evaluate

RUN = "synthetic-f01-run"
POLICY = "f" * 64


def scenario():
    """Build eight synthetic dual-stack witness slots with ordered capture windows."""
    challenges, traces = [], []
    for stage in ("baseline", "post"):
        for role in ("authorized", "unauthorized"):
            for family in (4, 6):
                suffix = f"{role}-{family}"
                cid = f"{stage}-{suffix}"
                pos = len(challenges) + 1
                source = ("192.0.2.10" if role == "authorized" else "192.0.2.30") if family == 4 else (
                    "2001:db8:1::10" if role == "authorized" else "2001:db8:1::30")
                dest = "192.0.2.20" if family == 4 else "2001:db8:1::20"
                c = Challenge(RUN, POLICY, cid, f"{pos:064x}", stage, role, family,
                              source, dest, 22, 100, 200,
                              f"baseline-{suffix}" if stage == "post" else None)
                responses = role == "authorized" or stage == "baseline"
                t = ObserverTrace(cid, RUN, POLICY, c.nonce, stage, role, family,
                                  source, dest, 22, 120 if stage == "baseline" else 150,
                                  115 if stage == "baseline" else 145,
                                  130 if stage == "baseline" else 165,
                                  "independent-vm-monitor",
                                  True, responses, role == "authorized", True, 0, True)
                challenges.append(c); traces.append(t)
    return challenges, traces


class F01AuthorityReferenceTests(unittest.TestCase):
    def check_blocked(self, alter, expected_reason=None):
        """Require fail-closed outcomes for a mutated synthetic evidence matrix."""
        cs, ts = scenario()
        cs, ts, kwargs = alter(cs, ts)
        result = evaluate(cs, ts, run=RUN, policy=POLICY, **kwargs)
        self.assertFalse(result.model_consistent)
        self.assertEqual(result.verdict, "NOT_VERIFIED")
        self.assertFalse(result.deployment_authorized)
        if expected_reason is not None:
            self.assertEqual(result.reason, expected_reason)

    def test_good_synthetic_matrix_still_denies_real_verification(self):
        cs, ts = scenario()
        result = evaluate(cs, ts, run=RUN, policy=POLICY)
        self.assertTrue(result.model_consistent)
        self.assertEqual(result.verdict, "NOT_VERIFIED")
        self.assertFalse(result.deployment_authorized)

    def test_forged_signed_negative_reports_without_probes(self):
        cs, _ = scenario()
        claims = [{"signature": "valid-client-hmac", "result": "timeout"} for _ in cs]
        result = evaluate(cs, (), run=RUN, policy=POLICY, client_claims=claims)
        self.assertFalse(result.model_consistent)
        self.assertEqual(result.verdict, "NOT_VERIFIED")

    def test_missing_one_family_witness(self):
        self.check_blocked(lambda cs, ts: (cs, ts[:-1], {}))

    def test_missing_authorized_login(self):
        self.check_blocked(lambda cs, ts: (cs, [replace(t, ssh_authenticated=False) if t.role == "authorized" else t for t in ts], {}))

    def test_missing_unauthorized_baseline_positive_control(self):
        self.check_blocked(lambda cs, ts: (cs, [replace(t, tcp_response_seen=False) if (t.stage, t.role, t.family) == ("baseline", "unauthorized", 4) else t for t in ts], {}))

    def test_negative_with_return_packet_is_contradicted(self):
        self.check_blocked(lambda cs, ts: (cs, [replace(t, tcp_response_seen=True) if (t.stage, t.role, t.family) == ("post", "unauthorized", 6) else t for t in ts], {}))

    def test_no_actual_syn_observation(self):
        self.check_blocked(lambda cs, ts: (cs, [replace(t, syn_seen=False) for t in ts], {}))

    def test_dropped_capture_is_inconclusive(self):
        self.check_blocked(lambda cs, ts: (cs, [replace(t, capture_drops=1) for t in ts], {}))

    def test_missing_liveness_control(self):
        self.check_blocked(lambda cs, ts: (cs, [replace(t, independent_control_ok=False) for t in ts], {}))

    def test_dut_is_not_an_independent_observer(self):
        self.check_blocked(lambda cs, ts: (cs, [replace(t, observer_domain="dut") for t in ts], {"observer_domain": "dut"}))

    def test_wrong_policy_bound_to_receipt(self):
        self.check_blocked(lambda cs, ts: (cs, [replace(ts[0], policy="a"*64)] + ts[1:], {}))

    def test_wrong_destination_bound_to_receipt(self):
        self.check_blocked(lambda cs, ts: (cs, [replace(ts[0], destination="192.0.2.99")] + ts[1:], {}))

    def test_challenge_replay(self):
        self.check_blocked(lambda cs, ts: (cs, [replace(ts[0], nonce=ts[1].nonce)] + ts[1:], {}))

    def test_expired_capture(self):
        self.check_blocked(lambda cs, ts: (cs, [replace(ts[0], observed_at=201)] + ts[1:], {}))

    def test_reused_nonce(self):
        self.check_blocked(lambda cs, ts: ([replace(cs[0], nonce=cs[1].nonce)] + cs[1:], ts, {}))

    def test_post_flow_must_match_baseline(self):
        self.check_blocked(lambda cs, ts: ([replace(c, destination="192.0.2.99") if (c.stage, c.role, c.family) == ("post", "authorized", 4) else c for c in cs], ts, {}))

    def test_roles_require_distinct_source_addresses(self):
        self.check_blocked(lambda cs, ts: ([replace(c, source="192.0.2.10") if (c.stage, c.role, c.family) == ("baseline", "unauthorized", 4) else c for c in cs], ts, {}))

    def test_wrong_baseline_link(self):
        self.check_blocked(lambda cs, ts: ([replace(c, baseline_id="unrelated") if c.stage == "post" else c for c in cs], ts, {}))

    def test_baseline_capture_must_finish_before_any_post_capture(self):
        """A late IPv6 baseline cannot overlap an IPv4 post attempt."""
        self.check_blocked(
            lambda cs, ts: (cs, [replace(t, window_started_at=145, observed_at=150,
                                         window_ended_at=160)
                                 if (t.stage, t.role, t.family) == ("baseline", "authorized", 6)
                                 else t for t in ts], {}),
            expected_reason="post-observed-before-baseline-complete")

    def test_post_syn_before_baseline_completion_is_rejected(self):
        """A post SYN observed early does not substitute for baseline-before-post."""
        self.check_blocked(
            lambda cs, ts: (cs, [replace(t, window_started_at=110, observed_at=115,
                                         window_ended_at=130)
                                 if (t.stage, t.role, t.family) == ("post", "authorized", 4)
                                 else t for t in ts], {}),
            expected_reason="post-observed-before-baseline-complete")

    def test_baseline_and_post_windows_cannot_touch(self):
        """Equal baseline completion and post capture start is not strictly ordered."""
        self.check_blocked(
            lambda cs, ts: (cs, [replace(t, window_ended_at=145)
                                 if (t.stage, t.role, t.family) == ("baseline", "authorized", 4)
                                 else t for t in ts], {}),
            expected_reason="post-observed-before-baseline-complete")

    def test_negative_probe_must_wait_full_response_window(self):
        """A SYN and a one-second capture cannot establish nonreachability."""
        self.check_blocked(
            lambda cs, ts: (cs, [replace(t, window_ended_at=151)
                                 if (t.stage, t.role, t.family) == ("post", "unauthorized", 4)
                                 else t for t in ts], {}),
            expected_reason="negative-observation-window-incomplete")

    def test_zero_elapsed_negative_probe_is_rejected(self):
        """An immediately completed negative capture is not a negative observation."""
        self.check_blocked(
            lambda cs, ts: (cs, [replace(t, window_ended_at=t.observed_at)
                                 if (t.stage, t.role, t.family) == ("post", "unauthorized", 6)
                                 else t for t in ts], {}),
            expected_reason="negative-observation-window-incomplete")

    def test_negative_capture_outside_challenge_expiry_is_rejected(self):
        """A capture may not extend past the issued challenge's expiry."""
        self.check_blocked(
            lambda cs, ts: (cs, [replace(t, window_started_at=175, observed_at=180,
                                         window_ended_at=201)
                                 if (t.stage, t.role, t.family) == ("post", "unauthorized", 4)
                                 else t for t in ts], {}),
            expected_reason="unreliable-or-unobserved-probe")

    def test_too_long_capture_window_is_rejected(self):
        """Even an allegedly complete capture needs a bounded observation interval."""
        self.check_blocked(
            lambda cs, ts: (cs, [replace(t, window_ended_at=170)
                                 if (t.stage, t.role, t.family) == ("baseline", "authorized", 4)
                                 else t for t in ts], {}),
            expected_reason="unreliable-or-unobserved-probe")

    def test_boolean_capture_timestamp_is_rejected(self):
        """Python bool must not satisfy the synthetic integer time contract."""
        self.check_blocked(
            lambda cs, ts: (cs, [replace(t, window_started_at=True)
                                 if (t.stage, t.role, t.family) == ("baseline", "authorized", 4)
                                 else t for t in ts], {}),
            expected_reason="unreliable-or-unobserved-probe")

    def test_report_replacement_never_changes_model_verdict(self):
        """Unsigned, forged and purportedly signed claims never grant authority."""
        cs, ts = scenario()
        for report in ({"result": "connected", "signature": "forged"}, {"result": "timeout", "signature": "valid"}):
            result = evaluate(cs, ts, run=RUN, policy=POLICY, client_claims=(report,))
            self.assertTrue(result.model_consistent)
            self.assertEqual(result.verdict, "NOT_VERIFIED")
            self.assertFalse(result.deployment_authorized)


if __name__ == "__main__":
    unittest.main()
