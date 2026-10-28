"""Deterministic R1 reference-model tests. Synthetic memory only; no host adapters."""
import ast
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from support.recovery_model import (
    Controller, Fault, Phase, PowerLoss, SyntheticApproval, Terminated, World, digest, sealed,
)

POWER_CASES_EXECUTED = 0


def approval(controller):
    state = controller.w.disk.read(controller._key("state"))
    return SyntheticApproval(controller.run_id, state["plan"])


def drive(world, path):
    controller = Controller(world)
    for event in ("prepare", "arm", "apply"):
        result = controller.execute(event)
        if result.phase == Phase.RECOVERY_BLOCKED:
            raise AssertionError("Nominal setup unexpectedly blocked")
    return controller.execute("decide", approval=approval(controller)) if path == "commit" else controller.execute("recover")


def power_cases():
    cases = []
    for path in ("commit", "rollback"):
        world = World(); drive(world, path)
        occurrences = {}
        for boundary in world.trace:
            occurrences[boundary] = occurrences.get(boundary, 0) + 1
            for retain in (False, True):
                cases.append((path, boundary, occurrences[boundary], retain))
    return cases


@contextmanager
def injected(world, boundary, mode="action", action=None, occurrence=1):
    fault = Fault(boundary, mode, action, occurrence)
    world.fault = fault
    try:
        yield fault
    finally:
        fault.assert_hit()
        world.fault = None


class PoisonServices:
    def __getattribute__(self, name):
        raise AssertionError("Recovery consulted an unrelated dependency")


class RecoveryFaultMatrix(unittest.TestCase):
    def pending(self):
        world = World(); controller = Controller(world)
        for event in ("prepare", "arm", "apply"):
            self.assertNotEqual(controller.execute(event).phase, Phase.RECOVERY_BLOCKED)
        self.assertEqual(world.firewall.snapshot(), ("restricted:synthetic-run-a",) * 2)
        return world, controller

    def assert_truth(self, world, result):
        # This oracle deliberately does not call Controller._timer_clear/_timer_valid.
        t = world.timer
        clear = not (t.active or t.enabled or t.running or t.queued)
        if result.timer_cancelled:
            self.assertTrue(clear, "Claimed cancellation contradicts external observation")
            lease = world.disk.read("lease")
            self.assertIn(t.run_id, (None, lease["run_id"]))
        if result.phase in (Phase.COMPLETED, Phase.ROLLED_BACK):
            self.assertTrue(result.timer_cancelled)
            self.assertTrue(clear)
            desired = "restricted:" + world.disk.read("lease")["run_id"] if result.model_commit else "baseline"
            self.assertEqual(world.firewall.snapshot(), (desired,) * 2)
        self.assertFalse(result.deployment_authorized)
        self.assertEqual(result.assurance, "REFERENCE_MODEL_ONLY")
        self.assertEqual(result.vm_validation, "NOT_RUN")

    def assert_preparation(self, world):
        # Inspect durable bytes captured at each actual restrictive effect.
        for durable, timer, clock in world.firewall.restrictions:
            lease = json.loads(durable["lease"])["payload"]
            prefix = "runs/" + lease["run_id"] + "/"
            state = json.loads(durable[prefix + "state"])["payload"]
            capsule = json.loads(durable[prefix + "capsule"])["payload"]
            service = json.loads(durable[prefix + "service"])["payload"]
            self.assertEqual(state["phase"], "MUTATION_INTENT", "Restriction preceded durable write-ahead intent")
            self.assertEqual(state["plan"], digest(capsule))
            self.assertEqual(lease["plan"], state["plan"])
            self.assertEqual(capsule["run_id"], lease["run_id"])
            self.assertEqual(service["invocation_run_id"], lease["run_id"])
            self.assertEqual(timer["run_id"], lease["run_id"])
            self.assertEqual(timer["config"], digest(service))
            self.assertEqual(timer["boot"], clock.boot)
            self.assertTrue(timer["active"] and timer["enabled"])
            self.assertFalse(timer["running"] or timer["queued"])
            self.assertGreater(timer["mono_due"], clock.mono)
            self.assertGreater(timer["wall_due"], clock.wall)
            self.assertEqual(timer["mono_due"], capsule["mono_due"])

    def assert_rolled_back(self, world, result):
        self.assertEqual(result.phase, Phase.ROLLED_BACK)
        self.assertFalse(result.model_commit)
        self.assertEqual(world.firewall.snapshot(), ("baseline",) * 2)
        self.assert_truth(world, result)
        self.assert_preparation(world)

    def dependency_absent(self, name):
        world, controller = self.pending()
        removed = []
        def remove(w):
            removed.append(w.optional_services.pop(name))
            w.optional_services = PoisonServices()
        with injected(world, "recovery:entry", action=remove):
            result = controller.execute("recover")
        self.assertEqual(len(removed), 1)
        self.assert_rolled_back(world, result)

    def test_01_missing_collector_during_rollback(self):
        self.dependency_absent("collector")

    def test_02_missing_docker_during_rollback(self):
        self.dependency_absent("docker")

    def test_03_missing_journald_during_rollback(self):
        self.dependency_absent("journald")

    def test_04_missing_unrelated_python_package(self):
        self.dependency_absent("unrelated-package")

    def test_05_interrupted_recovery_preparation(self):
        world = World(); controller = Controller(world)
        with injected(world, "publish:capsule:after_file_sync", "terminate"):
            with self.assertRaises(Terminated): controller.execute("prepare")
        world.restart()
        result = Controller(world).execute("reconcile")
        self.assertEqual(result.phase, Phase.RECOVERY_BLOCKED)
        self.assertEqual(world.firewall.snapshot(), ("baseline",) * 2)
        self.assertFalse(world.firewall.restrictions)
        self.assert_truth(world, result)

    def test_06_no_mutation_without_durable_arming_and_intent(self):
        world = World(); controller = Controller(world); controller.execute("prepare")
        with injected(world, "event:apply:entry"):
            result = controller.execute("apply")
        self.assertEqual(result.phase, Phase.RECOVERY_BLOCKED)
        self.assertFalse(world.firewall.restrictions)
        controller.execute("arm")
        with injected(world, "publish:state.MUTATION_INTENT:before_dir_sync", "storage"):
            result = controller.execute("apply")
        self.assertEqual(result.code, "IO_UNCERTAIN")
        self.assertFalse(world.firewall.restrictions)
        self.assertEqual(world.firewall.snapshot(), ("baseline",) * 2)

    def test_07_failure_immediately_before_restrictive_effect(self):
        world = World(); controller = Controller(world)
        controller.execute("prepare"); controller.execute("arm")
        with injected(world, "firewall:before_restrict", "terminate"):
            with self.assertRaises(Terminated): controller.execute("apply")
        self.assertFalse(world.firewall.restrictions)
        world.restart()
        self.assert_rolled_back(world, Controller(world).execute("reconcile"))

    def test_08_failure_after_live_or_persisted_mutation(self):
        for boundary in ("firewall:after_restrict_live", "firewall:after_restrict_persisted"):
            with self.subTest(boundary=boundary):
                world = World(); controller = Controller(world)
                controller.execute("prepare"); controller.execute("arm")
                with injected(world, boundary, "terminate"):
                    with self.assertRaises(Terminated): controller.execute("apply")
                self.assertEqual(world.firewall.live, "restricted:synthetic-run-a")
                world.restart()
                self.assert_rolled_back(world, Controller(world).execute("reconcile"))

    def test_09_crash_before_commit_marker_publication(self):
        world, controller = self.pending()
        with injected(world, "publish:decision:after_write", "terminate"):
            with self.assertRaises(Terminated): controller.execute("decide", approval=approval(controller))
        self.assertIsNone(world.disk.read(controller._key("decision")))
        world.restart()
        self.assert_rolled_back(world, Controller(world).execute("reconcile"))

    def test_10_crash_after_durable_marker_before_cancellation(self):
        world, controller = self.pending()
        with injected(world, "publish:decision:after_dir_sync", "terminate"):
            with self.assertRaises(Terminated): controller.execute("decide", approval=approval(controller))
        self.assertTrue(world.timer.active)
        self.assertEqual(world.disk.read(controller._key("state"))["phase"], "RESTRICTED_PENDING")
        world.restart(); world.clock.wall += 1000
        result = Controller(world).execute("reconcile")
        self.assertEqual(result.phase, Phase.COMPLETED)
        self.assertTrue(result.model_commit)
        self.assertEqual(world.firewall.restores, 0)
        self.assert_truth(world, result)

    def test_11_timer_cancellation_failure(self):
        world, controller = self.pending()
        with injected(world, "timer:before_cancel", action=lambda w: setattr(w.timer, "cancel_mode", "fail")):
            result = controller.execute("decide", approval=approval(controller))
        self.assertEqual(result.phase, Phase.CLEANUP_PENDING)
        self.assertEqual(result.code, "CANCELLATION_PENDING")
        self.assertFalse(result.timer_cancelled)
        self.assertTrue(world.timer.active and result.model_commit)
        self.assert_truth(world, result)

    def test_12_false_cancellation_acknowledgement(self):
        world, controller = self.pending()
        with injected(world, "timer:before_cancel", action=lambda w: setattr(w.timer, "cancel_mode", "false_ack")):
            result = controller.execute("decide", approval=approval(controller))
        self.assertEqual(world.timer.calls, 1)
        self.assertEqual(result.phase, Phase.CLEANUP_PENDING)
        self.assertEqual(result.code, "CANCELLATION_UNCONFIRMED")
        self.assertFalse(result.timer_cancelled)
        self.assert_truth(world, result)

    def test_13_repeated_decision_retries_interrupted_cleanup(self):
        world, controller = self.pending()
        with injected(world, "timer:before_cancel", "terminate"):
            with self.assertRaises(Terminated): controller.execute("decide", approval=approval(controller))
        world.restart(); world.clock.wall += 1000
        result = Controller(world).execute("decide")
        self.assertEqual(result.phase, Phase.COMPLETED)
        self.assertTrue(result.model_commit)
        self.assertEqual(world.firewall.restores, 0)
        self.assert_truth(world, result)

    def test_14_expired_repeated_apply_rolls_back(self):
        world, controller = self.pending()
        def expire(w):
            w.clock.wall += 901; w.clock.mono += 901
        with injected(world, "timer:observe:repeat_apply", action=expire):
            result = controller.execute("apply")
        self.assertNotEqual(result.code, "PENDING_REOBSERVED")
        self.assert_rolled_back(world, result)

    def test_15_active_timer_without_future_elapse(self):
        for deadline in (None, 0, 99):
            with self.subTest(deadline=deadline):
                world, controller = self.pending()
                with injected(world, "timer:observe:repeat_apply", action=lambda w: setattr(w.timer, "mono_due", deadline)):
                    result = controller.execute("apply")
                self.assert_rolled_back(world, result)

    def test_16_mismatched_expected_transaction_id(self):
        world, controller = self.pending()
        before = deepcopy((world.disk.visible, world.timer.snapshot(), world.firewall.snapshot()))
        hook = Fault("event:recover:entry", action=lambda w: setattr(w.timer, "active", False))
        world.fault = hook
        try:
            result = controller.execute("recover", expected_run="synthetic-run-b")
        finally:
            world.fault = None
        self.assertEqual(hook.hits, 0, "Stale expected ID must fail before the entry checkpoint")
        self.assertEqual(result.code, "STALE_IGNORED")
        self.assertEqual(before, (world.disk.visible, world.timer.snapshot(), world.firewall.snapshot()))
        self.assertFalse(result.timer_cancelled)

    def test_17_stale_invocation_cannot_touch_next_run(self):
        world, old = self.pending(); old.execute("recover")
        current = Controller(world, "synthetic-run-b")
        for event in ("prepare", "arm", "apply"):
            self.assertNotEqual(current.execute(event).phase, Phase.RECOVERY_BLOCKED)
        before = deepcopy((world.disk.visible, world.timer.snapshot(), world.firewall.snapshot()))
        # A stale run must never execute any event-entry callback. Every hook
        # would damage the new run if the ownership check were ordered too late.
        for event in ("arm", "apply", "decide", "recover", "reconcile", "status"):
            with self.subTest(event=event):
                def corrupt_current(w):
                    w.timer.active = False
                    w.firewall.live = "stale-injected-drift"
                hook = Fault("event:" + event + ":entry", mode="action",
                             action=corrupt_current)
                world.fault = hook
                try:
                    result = old.execute(event)
                finally:
                    world.fault = None
                self.assertEqual(result.code, "STALE_IGNORED")
                self.assertEqual(hook.hits, 0, "Stale run reached a mutating entry hook")
                self.assertEqual(before, (world.disk.visible, world.timer.snapshot(),
                                          world.firewall.snapshot()))

    def test_18_repeated_rollback_converges_without_extra_effect(self):
        world, controller = self.pending()
        with injected(world, "recovery:entry"):
            first = controller.execute("recover")
        before = deepcopy((world.disk.visible, world.timer.snapshot()))
        second = controller.execute("recover")
        self.assertEqual(world.firewall.restores, 1)
        self.assertEqual(before, (world.disk.visible, world.timer.snapshot()))
        self.assert_rolled_back(world, first); self.assert_rolled_back(world, second)

    def test_19_rollback_cleanup_failure_then_retry(self):
        world, controller = self.pending()
        with injected(world, "timer:before_cancel", action=lambda w: setattr(w.timer, "cancel_mode", "fail")):
            result = controller.execute("recover")
        self.assertEqual(result.phase, Phase.CLEANUP_PENDING)
        self.assertEqual(world.firewall.snapshot(), ("baseline",) * 2)
        self.assertFalse(result.timer_cancelled)
        world.timer.cancel_mode = "normal"
        self.assert_rolled_back(world, controller.execute("recover"))
        self.assertEqual(world.firewall.restores, 1)

    def test_20_disk_full_during_state_publication(self):
        world = World(); controller = Controller(world)
        controller.execute("prepare"); controller.execute("arm")
        with injected(world, "publish:state.RESTRICTED_PENDING:before_write", "storage"):
            result = controller.execute("apply")
        self.assertEqual(result.code, "IO_UNCERTAIN")
        self.assertFalse(result.timer_cancelled)
        self.assertEqual(result.persistent_phase, "MUTATION_INTENT")
        self.assert_rolled_back(world, controller.execute("reconcile"))

    def test_21_file_and_directory_fsync_failure(self):
        for stage in ("before_file_sync", "before_dir_sync"):
            with self.subTest(stage=stage):
                world = World(); controller = Controller(world)
                controller.execute("prepare"); controller.execute("arm")
                with injected(world, "publish:state.MUTATION_INTENT:" + stage, "storage"):
                    result = controller.execute("apply")
                self.assertEqual(result.code, "IO_UNCERTAIN")
                self.assertFalse(world.firewall.restrictions)
                if stage == "before_dir_sync":
                    # The unsynced rename may have two permitted outcomes after a cut;
                    # it is not yet safe to claim durable recovery without one.
                    self.assertEqual(controller.execute("reconcile").phase, Phase.RECOVERY_BLOCKED)
                    world.restart(power=True, retain_rename=False)
                self.assert_rolled_back(world, controller.execute("reconcile"))

    def test_22_partial_record_never_becomes_authoritative(self):
        world = World(); controller = Controller(world)
        controller.execute("prepare"); controller.execute("arm")
        before = world.disk.visible[controller._key("state")]
        with injected(world, "publish:state.MUTATION_INTENT:after_write", "partial"):
            result = controller.execute("apply")
        self.assertEqual(result.code, "IO_UNCERTAIN")
        self.assertEqual(before, world.disk.visible[controller._key("state")])
        self.assertIn(b'{"partial":', world.disk.temporary.values())
        self.assertFalse(world.firewall.restrictions)
        self.assert_rolled_back(world, controller.execute("reconcile"))

    def test_23_wall_clock_rollback_and_forward_jump(self):
        for delta in (-100, 100):
            with self.subTest(delta=delta):
                world, controller = self.pending()
                with injected(world, "timer:observe:repeat_apply", action=lambda w: setattr(w.clock, "wall", w.clock.wall + delta)):
                    result = controller.execute("apply")
                self.assert_rolled_back(world, result)

    def test_24_reboot_changes_boot_identity_and_rolls_back_uncommitted(self):
        world, controller = self.pending()
        original_boot = world.clock.boot
        with injected(world, "event:apply:entry", action=lambda w: w.restart(reboot=True)):
            result = controller.execute("apply")
        self.assertNotEqual(original_boot, world.clock.boot)
        self.assert_rolled_back(world, result)

    def test_25_missing_or_corrupted_recovery_metadata_blocks(self):
        for artifact in ("capsule", "service", "state"):
            for missing in (False, True):
                with self.subTest(artifact=artifact, missing=missing):
                    world, controller = self.pending()
                    def damage(w):
                        key = controller._key(artifact)
                        if missing: w.disk.visible.pop(key)
                        else: w.disk.visible[key] = b'{"corrupt":'
                    with injected(world, "recovery:entry", action=damage):
                        result = controller.execute("recover")
                    self.assertEqual(result.phase, Phase.RECOVERY_BLOCKED)
                    self.assertFalse(result.timer_cancelled)
                    self.assertTrue(world.timer.active)
                    self.assertEqual(world.firewall.restores, 0)
                    self.assertEqual(world.firewall.live, "restricted:synthetic-run-a")
                    self.assert_truth(world, result)

    def test_26_power_loss_at_every_named_transition_boundary(self):
        global POWER_CASES_EXECUTED
        POWER_CASES_EXECUTED = 0
        cases = power_cases()
        self.assertGreater(len(cases), 100)
        for path, boundary, occurrence, retain in cases:
            with self.subTest(path=path, boundary=boundary, occurrence=occurrence, retain_rename=retain):
                world = World()
                with injected(world, boundary, "power", occurrence=occurrence):
                    with self.assertRaises(PowerLoss): drive(world, path)
                world.restart(power=True, retain_rename=retain)
                prefix = "runs/synthetic-run-a/"
                # Decision oracle consults surviving bytes, not the Controller phase.
                full = all(key in world.disk.visible for key in ("lease", prefix + "state", prefix + "capsule", prefix + "service"))
                committed = prefix + "decision" in world.disk.visible
                result = Controller(world).execute("reconcile")
                if not full:
                    self.assertEqual(result.phase, Phase.RECOVERY_BLOCKED)
                    self.assertEqual(world.firewall.snapshot(), ("baseline",) * 2)
                    self.assertFalse(world.firewall.restrictions)
                elif committed:
                    self.assertEqual(result.phase, Phase.COMPLETED)
                    self.assertTrue(result.model_commit)
                    self.assertEqual(world.firewall.snapshot(), ("restricted:synthetic-run-a",) * 2)
                    self.assertEqual(world.firewall.restores, 0)
                else:
                    self.assert_rolled_back(world, result)
                self.assert_truth(world, result)
                self.assert_preparation(world)
                POWER_CASES_EXECUTED += 1
        self.assertEqual(POWER_CASES_EXECUTED, len(cases))

    def test_27_process_restart_and_unsynced_power_outcomes_differ(self):
        for power, retain, terminal in ((False, False, Phase.RECOVERY_BLOCKED), (True, False, Phase.ROLLED_BACK), (True, True, Phase.COMPLETED)):
            with self.subTest(power=power, retain=retain):
                world, controller = self.pending()
                with injected(world, "publish:decision:after_replace", "terminate"):
                    with self.assertRaises(Terminated): controller.execute("decide", approval=approval(controller))
                world.restart(power=power, retain_rename=retain)
                result = Controller(world).execute("reconcile")
                self.assertEqual(result.phase, terminal)
                if not power:
                    self.assertFalse(result.timer_cancelled)
                self.assert_truth(world, result)

    def test_28_terminal_phase_cannot_hide_reactivated_timer(self):
        world, controller = self.pending()
        with injected(world, "cleanup:after_terminal", action=lambda w: setattr(w.timer, "active", True)):
            result = controller.execute("decide", approval=approval(controller))
        self.assertEqual(result.phase, Phase.CLEANUP_PENDING)
        self.assertEqual(result.persistent_phase, "COMPLETED")
        self.assertFalse(result.timer_cancelled)
        self.assertEqual(controller.execute("status").phase, Phase.CLEANUP_PENDING)
        self.assertEqual(controller.execute("reconcile").phase, Phase.COMPLETED)

    def test_29_loaded_config_service_or_queue_mismatch_blocks_restriction(self):
        for field, bad in (("config", "synthetic-wrong-config"), ("running", True), ("queued", ["synthetic-run-b"]), ("enabled", False)):
            with self.subTest(field=field):
                world = World(); controller = Controller(world)
                controller.execute("prepare"); controller.execute("arm")
                with injected(world, "timer:observe:before_mutation", action=lambda w: setattr(w.timer, field, bad)):
                    result = controller.execute("apply")
                self.assertFalse(world.firewall.restrictions)
                self.assertEqual(world.firewall.snapshot(), ("baseline",) * 2)
                self.assertNotEqual(result.phase, Phase.RESTRICTED_PENDING)
                self.assert_truth(world, result)

    def test_30_missing_essential_restorer_is_explicitly_blocked(self):
        world, controller = self.pending()
        with injected(world, "recovery:entry", action=lambda w: setattr(w, "restorer_available", False)):
            result = controller.execute("recover")
        self.assertEqual(result.phase, Phase.RECOVERY_BLOCKED)
        self.assertFalse(result.timer_cancelled)
        self.assertTrue(world.timer.active)
        self.assertEqual(world.firewall.restores, 0)

    def test_31_self_reported_evidence_never_authorizes_commit(self):
        for evidence in ({"structure": "VALID"}, {"operator_attestation": True}, {"signature": "0" * 64}):
            with self.subTest(evidence_kind=next(iter(evidence))):
                world, controller = self.pending()
                with injected(world, "event:decide:entry"):
                    result = controller.execute("decide", evidence=evidence)
                self.assertEqual(result.code, "AUTHORIZATION_DENIED")
                self.assertIsNone(world.disk.read(controller._key("decision")))
                self.assertTrue(world.timer.active)
                self.assertFalse(result.timer_cancelled or result.deployment_authorized)

    def test_32_synthetic_approval_requires_run_plan_and_review_binding(self):
        for field, bad in (("run_id", "synthetic-run-b"), ("plan", "synthetic-wrong-plan"), ("independent_review", False)):
            with self.subTest(field=field):
                world, controller = self.pending()
                fields = dict(approval(controller).__dict__); fields[field] = bad
                with injected(world, "event:decide:entry"):
                    result = controller.execute("decide", approval=SyntheticApproval(**fields))
                self.assertEqual(result.code, "AUTHORIZATION_DENIED")
                self.assertFalse(result.timer_cancelled)
                self.assertIsNone(world.disk.read(controller._key("decision")))

    def test_33_partial_restore_is_idempotently_retried(self):
        world, controller = self.pending()
        with injected(world, "firewall:after_restore_live", "terminate"):
            with self.assertRaises(Terminated): controller.execute("recover")
        self.assertNotEqual(world.firewall.live, world.firewall.persisted)
        world.restart()
        self.assert_rolled_back(world, Controller(world).execute("recover"))
        self.assertEqual(world.firewall.restores, 2)

    def test_34_corrupt_commit_marker_is_not_reinterpreted_as_uncommitted(self):
        world, controller = self.pending()
        controller.execute("decide", approval=approval(controller))
        with injected(world, "recovery:entry", action=lambda w: w.disk.visible.__setitem__(controller._key("decision"), b'broken')):
            result = controller.execute("reconcile")
        self.assertEqual(result.phase, Phase.RECOVERY_BLOCKED)
        self.assertEqual(world.firewall.restores, 0)
        self.assertFalse(result.timer_cancelled)

    def test_35_committed_firewall_drift_is_blocked_not_overwritten(self):
        world, controller = self.pending()
        controller.execute("decide", approval=approval(controller))
        with injected(world, "recovery:entry", action=lambda w: setattr(w.firewall, "live", "synthetic-external-change")):
            result = controller.execute("reconcile")
        self.assertEqual(result.phase, Phase.RECOVERY_BLOCKED)
        self.assertEqual(world.firewall.live, "synthetic-external-change")
        self.assertEqual(world.firewall.restores, 0)

    def test_36_mutant_false_cancellation_is_detected(self):
        world, controller = self.pending()
        with injected(world, "timer:before_cancel", action=lambda w: setattr(w.timer, "cancel_mode", "false_ack")):
            with patch.object(Controller, "_timer_clear", return_value=True):
                result = controller.execute("decide", approval=approval(controller))
        self.assertEqual(result.phase, Phase.COMPLETED)
        with self.assertRaisesRegex(AssertionError, "Claimed cancellation"):
            self.assert_truth(world, result)

    def test_37_mutant_missing_durable_intent_is_detected(self):
        world = World(); controller = Controller(world)
        controller.execute("prepare"); controller.execute("arm")
        original = Controller._record
        def omit_intent(instance, phase, plan, disposition=None):
            if phase != Phase.MUTATION_INTENT:
                return original(instance, phase, plan, disposition)
        with injected(world, "firewall:before_restrict"):
            with patch.object(Controller, "_record", omit_intent):
                controller.execute("apply")
        self.assertEqual(len(world.firewall.restrictions), 1)
        with self.assertRaisesRegex(AssertionError, "durable write-ahead intent"):
            self.assert_preparation(world)

    def test_38_unused_fault_hook_is_a_test_failure(self):
        world, controller = self.pending()
        with self.assertRaisesRegex(AssertionError, "not executed exactly once"):
            with injected(world, "synthetic-unreachable-checkpoint"):
                controller.execute("status")

    def test_39_model_has_no_host_effect_or_durability_oracle_imports(self):
        path = Path(__file__).parent / "support/recovery_model.py"
        tree = ast.parse(path.read_text())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import): imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom): imports.add(node.module)
        self.assertEqual(imports, {"copy", "dataclasses", "enum", "hashlib", "json", "re"})
        controller = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Controller")
        self.assertFalse(any(isinstance(n, ast.Attribute) and n.attr == "durable" for n in ast.walk(controller)))
        self.assertFalse(any(
            isinstance(n, ast.keyword) and n.arg == "confirmed"
            for n in ast.walk(controller)
        ), "Controller must read visible records, not the test-only durable image")

    def test_40_capsule_transaction_mismatch_is_blocked(self):
        world, controller = self.pending()
        capsule = world.disk.read(controller._key("capsule")); capsule["run_id"] = "synthetic-run-b"
        with injected(world, "recovery:entry", action=lambda w: w.disk.visible.__setitem__(controller._key("capsule"), sealed(capsule))):
            result = controller.execute("recover")
        self.assertEqual(result.phase, Phase.RECOVERY_BLOCKED)
        self.assertEqual(world.firewall.restores, 0)
        self.assertFalse(result.timer_cancelled)

    def test_41_firewall_drift_after_terminal_write_is_not_success(self):
        world, controller = self.pending()
        with injected(world, "cleanup:after_terminal", action=lambda w: setattr(w.firewall, "live", "synthetic-external-change")):
            result = controller.execute("decide", approval=approval(controller))
        self.assertEqual(result.phase, Phase.RECOVERY_BLOCKED)
        self.assertEqual(result.persistent_phase, "COMPLETED")
        self.assertFalse(result.timer_cancelled)
        self.assertEqual(world.firewall.restores, 0)

    def test_42_malformed_phase_metadata_is_blocked(self):
        for field, value in (("schema", True), ("disposition", "COMMIT"), ("unexpected", True)):
            with self.subTest(field=field):
                world, controller = self.pending()
                state = world.disk.read(controller._key("state")); state[field] = value
                with injected(world, "recovery:entry", action=lambda w: w.disk.visible.__setitem__(controller._key("state"), sealed(state))):
                    result = controller.execute("recover")
                self.assertEqual(result.phase, Phase.RECOVERY_BLOCKED)
                self.assertEqual(world.firewall.restores, 0)
                self.assertFalse(result.timer_cancelled)

    def test_43_restorer_disappearing_at_last_observation_blocks_mutation(self):
        world = World(); controller = Controller(world)
        controller.execute("prepare"); controller.execute("arm")
        with injected(world, "timer:observe:before_mutation", action=lambda w: setattr(w, "restorer_available", False)):
            result = controller.execute("apply")
        self.assertEqual(result.phase, Phase.RECOVERY_BLOCKED)
        self.assertFalse(world.firewall.restrictions)
        self.assertEqual(world.firewall.snapshot(), ("baseline",) * 2)

    def test_44_backward_monotonic_clock_is_not_a_valid_pending_run(self):
        world, controller = self.pending()
        with injected(world, "timer:observe:repeat_apply", action=lambda w: setattr(w.clock, "mono", 99)):
            result = controller.execute("apply")
        self.assert_rolled_back(world, result)

    def test_45_error_after_commit_flush_reconciles_surviving_decision(self):
        world, controller = self.pending()
        with injected(world, "publish:decision:after_dir_sync", "storage"):
            result = controller.execute("decide", approval=approval(controller))
        self.assertEqual(result.code, "IO_UNCERTAIN")
        self.assertFalse(result.timer_cancelled)
        self.assertIsNotNone(world.disk.read(controller._key("decision")))
        result = controller.execute("reconcile")
        self.assertEqual(result.phase, Phase.COMPLETED)
        self.assertEqual(world.firewall.restores, 0)
        self.assert_truth(world, result)

    def test_46_restore_error_preserves_pending_work_and_retries(self):
        for boundary in ("firewall:before_restore", "firewall:after_restore_live"):
            with self.subTest(boundary=boundary):
                world, controller = self.pending()
                with injected(world, boundary, "adapter"):
                    result = controller.execute("recover")
                self.assertEqual(result.phase, Phase.RECOVERY_BLOCKED)
                self.assertEqual(result.persistent_phase, "ROLLBACK_PENDING")
                self.assertFalse(result.timer_cancelled)
                self.assertTrue(world.timer.active)
                self.assert_rolled_back(world, controller.execute("recover"))

    def test_47_timer_arm_error_never_allows_restriction(self):
        world = World(); controller = Controller(world)
        controller.execute("prepare")
        with injected(world, "timer:before_arm", "adapter"):
            result = controller.execute("arm")
        self.assertEqual(result.phase, Phase.RECOVERY_BLOCKED)
        self.assertEqual(result.persistent_phase, "RECOVERY_DURABLE")
        result = controller.execute("apply")
        self.assertEqual(result.phase, Phase.RECOVERY_BLOCKED)
        self.assertFalse(world.firewall.restrictions)
        self.assert_rolled_back(world, controller.execute("reconcile"))

    def test_48_corrupt_previous_run_cannot_be_overwritten_by_prepare(self):
        for damage in ("lease-fields", "lease-type", "previous-state"):
            with self.subTest(damage=damage):
                world, old = self.pending(); old.execute("recover")
                current = Controller(world, "synthetic-run-b")
                def corrupt(w):
                    if damage == "lease-fields": w.disk.visible["lease"] = sealed({"run_id": old.run_id})
                    elif damage == "lease-type": w.disk.visible["lease"] = sealed({"schema": 1, "run_id": [], "plan": "synthetic-invalid"})
                    else: w.disk.visible[old._key("state")] = b'broken'
                with injected(world, "event:prepare:entry", action=corrupt):
                    result = current.execute("prepare")
                self.assertEqual(result.phase, Phase.RECOVERY_BLOCKED)
                self.assertIsNone(world.disk.read(current._key("state")))
                self.assertFalse(result.timer_cancelled)
                self.assertEqual(world.firewall.snapshot(), ("baseline",) * 2)


    def test_49_unhashable_phase_returns_blocked(self):
        for bad in ([], {"invalid": "object"}):
            with self.subTest(bad=repr(bad)):
                world, controller = self.pending()
                state = world.disk.read(controller._key("state"))
                state["phase"] = bad
                world.disk.visible[controller._key("state")] = sealed(state)
                self.assertEqual(controller.execute("reconcile").phase, Phase.RECOVERY_BLOCKED)

    def test_50_unsynced_commit_blocks_until_power_outcome(self):
        world, controller = self.pending()
        with injected(world, "publish:decision:after_replace", "terminate"):
            with self.assertRaises(Terminated):
                controller.execute("decide", approval=approval(controller))
        world.restart()
        uncertain = controller.execute("reconcile")
        self.assertEqual(uncertain.phase, Phase.RECOVERY_BLOCKED)
        self.assertFalse(uncertain.timer_cancelled)
        self.assertEqual(world.firewall.restores, 0)
        self.assertEqual(world.firewall.snapshot(), ("restricted:synthetic-run-a",) * 2)
        for retain, terminal in ((False, Phase.ROLLED_BACK), (True, Phase.COMPLETED)):
            with self.subTest(retain=retain):
                # Rebuild identical unsynced publication in each independent world.
                w, c = self.pending()
                with injected(w, "publish:decision:after_replace", "terminate"):
                    with self.assertRaises(Terminated):
                        c.execute("decide", approval=approval(c))
                w.restart(power=True, retain_rename=retain)
                self.assertEqual(c.execute("reconcile").phase, terminal)

    def test_51_concurrent_commit_and_rollback_cannot_interleave(self):
        world, controller = self.pending()
        responses = []
        with injected(world, "publish:decision:before_write",
                      action=lambda w: responses.append(Controller(w).execute("recover"))):
            result = controller.execute("decide", approval=approval(controller))
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0].code, "CONCURRENT_EVENT_BLOCKED")
        self.assertEqual(result.phase, Phase.COMPLETED)
        self.assertEqual(world.firewall.restores, 0)

    def test_52_external_firewall_drift_blocks_first_restriction(self):
        for boundary in ("timer:observe:before_mutation", "firewall:before_restrict"):
            for image in ("live", "persisted"):
                with self.subTest(boundary=boundary, image=image):
                    world = World(); controller = Controller(world)
                    controller.execute("prepare"); controller.execute("arm")
                    with injected(world, boundary, action=lambda w: setattr(w.firewall, image, "external-drift")):
                        result = controller.execute("apply")
                    self.assertEqual(result.phase, Phase.RECOVERY_BLOCKED)
                    self.assertFalse(world.firewall.restrictions)
                    self.assertEqual(world.firewall.restores, 0)
                    self.assertEqual(controller.execute("recover").phase, Phase.RECOVERY_BLOCKED)

    def test_53_restorer_lost_at_restore_effect_blocks(self):
        world, controller = self.pending()
        with injected(world, "firewall:before_restore",
                      action=lambda w: setattr(w, "restorer_available", False)):
            result = controller.execute("recover")
        self.assertEqual(result.phase, Phase.RECOVERY_BLOCKED)
        self.assertEqual(world.firewall.restores, 0)
        self.assertEqual(world.firewall.snapshot(), ("restricted:synthetic-run-a",) * 2)

    def test_54_commit_cleanup_does_not_need_restorer(self):
        world, controller = self.pending()
        with injected(world, "publish:decision:after_dir_sync", "storage"):
            controller.execute("decide", approval=approval(controller))
        world.restorer_available = False
        result = controller.execute("reconcile")
        self.assertEqual(result.phase, Phase.COMPLETED)
        self.assertTrue(result.timer_cancelled)
        self.assertEqual(world.firewall.restores, 0)

    def test_55_clock_regression_after_accepted_sample(self):
        world, controller = self.pending()
        world.clock.wall += 30; world.clock.mono += 30
        self.assertEqual(controller.execute("apply").phase, Phase.RESTRICTED_PENDING)
        world.clock.wall -= 8; world.clock.mono -= 8
        self.assert_rolled_back(world, controller.execute("apply"))

    def test_56_timer_config_drift_is_not_terminal(self):
        world, controller = self.pending()
        self.assertEqual(controller.execute("recover").phase, Phase.ROLLED_BACK)
        world.timer.config = "different-service-digest"
        result = controller.execute("status")
        self.assertEqual(result.phase, Phase.CLEANUP_PENDING)
        self.assertFalse(result.timer_cancelled)

    def test_57_queued_and_running_work_survives_timer_cancel(self):
        for kind in ("queued", "running"):
            with self.subTest(kind=kind):
                world, controller = self.pending()
                if kind == "queued":
                    world.timer.queued.append("synthetic-recovery-job")
                else:
                    world.timer.running = True
                result = controller.execute("recover")
                self.assertEqual(result.phase, Phase.CLEANUP_PENDING)
                self.assertFalse(result.timer_cancelled)
                self.assertFalse(world.timer.active)
                self.assertFalse(world.timer.enabled)
                if kind == "queued":
                    self.assertEqual(world.timer.queued, ["synthetic-recovery-job"])
                    world.timer.queued.clear()  # Independently observed quiescence.
                else:
                    self.assertTrue(world.timer.running)
                    world.timer.running = False
                self.assert_rolled_back(world, controller.execute("recover"))


    def test_58_baseline_noop_recovery_records_rollback_pending(self):
        world = World(); controller = Controller(world)
        self.assertEqual(controller.execute("prepare").phase, Phase.RECOVERY_DURABLE)
        self.assertEqual(controller.execute("arm").phase, Phase.ROLLBACK_ARMED)
        self.assertEqual(world.firewall.snapshot(), ("baseline", "baseline"))
        result = controller.execute("recover")
        self.assertEqual(result.phase, Phase.ROLLED_BACK)
        self.assertIn("publish:state.ROLLBACK_PENDING:after_dir_sync", world.trace)
        self.assertEqual(world.firewall.restores, 0)
        self.assert_rolled_back(world, result)



if __name__ == "__main__":
    unittest.main()
