"""SSH-HARDEN-R1: pure in-memory protocol model, never a host recovery tool.

No filesystem, process, clock, network, service-manager or evidence APIs are used.
The independent test oracle may inspect MemoryDisk.durable; Controller cannot.
"""
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import re


class Phase(str, Enum):
    PREPARED = "PREPARED"
    RECOVERY_DURABLE = "RECOVERY_DURABLE"
    ROLLBACK_ARMED = "ROLLBACK_ARMED"
    MUTATION_INTENT = "MUTATION_INTENT"
    RESTRICTED_PENDING = "RESTRICTED_PENDING"
    COMMIT_DECIDED = "COMMIT_DECIDED"
    CLEANUP_PENDING = "CLEANUP_PENDING"
    COMPLETED = "COMPLETED"
    ROLLBACK_PENDING = "ROLLBACK_PENDING"
    ROLLED_BACK = "ROLLED_BACK"
    RECOVERY_BLOCKED = "RECOVERY_BLOCKED"


class StorageFault(Exception):
    pass


class MetadataFault(Exception):
    pass


class AdapterFault(Exception):
    pass


class StaleRun(Exception):
    pass


class Terminated(BaseException):
    """Modeled process termination; deliberately bypass ordinary error handling."""


class PowerLoss(BaseException):
    """Modeled volatile-state loss; not a real machine power interruption."""


def require(value):
    if not value:
        raise MetadataFault("Binding or metadata invalid")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sealed(value):
    return canonical({"payload": value, "checksum": digest(value)})


def unseal(raw):
    if raw is None:
        return None
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result)
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=pairs)
        require(type(value) is dict and set(value) == {"payload", "checksum"})
        require(type(value["payload"]) is dict and value["checksum"] == digest(value["payload"]))
        return value["payload"]
    except (ValueError, TypeError, KeyError) as exc:
        raise MetadataFault("Unreadable modeled record") from exc


@dataclass
class Clock:
    boot: str = "synthetic-boot-a"
    wall: int = 1000
    mono: int = 100


@dataclass(frozen=True)
class SyntheticApproval:
    """Injected trusted test input; NOT a real authorization credential."""
    run_id: str
    plan: str
    independent_review: bool = True


@dataclass(frozen=True)
class Result:
    phase: Phase
    code: str
    timer_cancelled: bool = False
    model_commit: bool = False
    persistent_phase: str | None = None
    deployment_authorized: bool = False
    assurance: str = "REFERENCE_MODEL_ONLY"
    vm_validation: str = "NOT_RUN"


@dataclass
class Fault:
    target: str
    mode: str = "terminate"
    action: object = None
    occurrence: int = 1
    hits: int = 0
    matches: int = 0

    def fire(self, world, label):
        if label != self.target:
            return
        self.matches += 1
        if self.matches != self.occurrence or self.hits:
            return
        self.hits += 1
        if self.action:
            self.action(world)
        if self.mode == "terminate":
            raise Terminated(label)
        if self.mode == "power":
            raise PowerLoss(label)
        if self.mode == "storage":
            raise StorageFault(label)
        if self.mode == "partial":
            key = next(reversed(world.disk.temporary))
            world.disk.temporary[key] = b'{"partial":'
            raise StorageFault(label)
        if self.mode == "adapter":
            raise AdapterFault(label)
        require(self.mode == "action")

    def assert_hit(self):
        if self.hits != 1:
            raise AssertionError("Designated fault checkpoint was not executed exactly once: " + self.target)


class MemoryDisk:
    STAGES = ("before_write", "after_write", "before_file_sync", "after_file_sync", "after_replace",
              "before_dir_sync", "after_dir_sync", "after_readback")

    def __init__(self, hook):
        self.hook = hook
        self.visible = {}
        self.durable = {}
        self.temporary = {}
        self.synced = set()
        self.unsynced_renames = {}

    def read(self, key, *, confirmed=False):
        """Read visible or acknowledged modeled bytes; no real fsync assurance."""
        if confirmed and key in self.visible and self.visible.get(key) != self.durable.get(key):
            raise MetadataFault("Visible and acknowledged model bytes disagree")
        return unseal((self.durable if confirmed else self.visible).get(key))

    def unacknowledged(self, key):
        """Whether the visible rename has not crossed a directory-sync barrier."""
        return key in self.unsynced_renames

    def publish(self, key, value, label, exclusive=False):
        raw = sealed(value)
        if exclusive:
            require(key not in self.visible)
        prefix = "publish:" + label + ":"
        self.hook(prefix + "before_write")
        self.temporary[key] = raw
        self.hook(prefix + "after_write")
        self.hook(prefix + "before_file_sync")
        self.synced.add(key)
        self.hook(prefix + "after_file_sync")
        self.visible[key] = self.temporary[key]
        self.unsynced_renames[key] = self.temporary[key]
        self.hook(prefix + "after_replace")
        self.hook(prefix + "before_dir_sync")
        self.durable[key] = self.visible[key]
        self.unsynced_renames.pop(key, None)
        self.hook(prefix + "after_dir_sync")
        require(self.read(key) == value)
        self.hook(prefix + "after_readback")
        self.temporary.pop(key, None)
        self.synced.discard(key)

    def power_loss(self, retain_rename=False):
        # Enumerate both permitted outcomes of file-synced but not dir-synced rename.
        if retain_rename:
            for key, raw in self.unsynced_renames.items():
                if key in self.synced:
                    self.durable[key] = raw
        self.visible = deepcopy(self.durable)
        self.temporary.clear()
        self.synced.clear()
        self.unsynced_renames.clear()


@dataclass
class Timer:
    run_id: str | None = None
    config: str | None = None
    boot: str | None = None
    wall_due: int | None = None
    mono_due: int | None = None
    active: bool = False
    enabled: bool = False
    running: bool = False
    queued: list = field(default_factory=list)
    cancel_mode: str = "normal"
    calls: int = 0

    def snapshot(self):
        return deepcopy(self.__dict__)

    def arm(self, world, capsule, service):
        world.checkpoint("timer:before_arm")
        self.run_id = capsule["run_id"]
        self.config = digest(service)
        self.boot = capsule["boot"]
        self.wall_due = capsule["wall_due"]
        self.mono_due = capsule["mono_due"]
        self.active = self.enabled = True
        world.checkpoint("timer:after_arm")

    def cancel(self, world, run_id, config):
        world.checkpoint("timer:before_cancel")
        if self.run_id not in (None, run_id) or (self.run_id and self.config != config):
            raise AdapterFault("Refuse unrelated loaded timer")
        self.calls += 1
        if self.cancel_mode == "fail":
            raise AdapterFault("Synthetic cancellation failure")
        if self.cancel_mode != "false_ack":
            self.active = self.enabled = False
            # Stopping a timer does not stop the running service or queued jobs.
        world.checkpoint("timer:after_cancel")
        return True  # Deliberately NOT treated as an observation by Controller.


@dataclass
class Firewall:
    live: str = "baseline"
    persisted: str = "baseline"
    restrictions: list = field(default_factory=list)
    restores: int = 0

    def snapshot(self):
        return self.live, self.persisted

    def restrict(self, world, capsule):
        world.checkpoint("firewall:before_restrict")
        require(self.snapshot() == (capsule["baseline"],) * 2)
        # Independent test oracle captures prerequisites at the actual effect.
        self.restrictions.append((deepcopy(world.disk.durable), world.timer.snapshot(), deepcopy(world.clock)))
        self.live = capsule["restricted"]
        world.checkpoint("firewall:after_restrict_live")
        self.persisted = capsule["restricted"]
        world.checkpoint("firewall:after_restrict_persisted")

    def restore(self, world, capsule):
        world.checkpoint("firewall:before_restore")
        require(world.restorer_available)
        require(set(self.snapshot()) <= {capsule["baseline"], capsule["restricted"]})
        self.restores += 1
        self.live = capsule["baseline"]
        world.checkpoint("firewall:after_restore_live")
        self.persisted = capsule["baseline"]
        world.checkpoint("firewall:after_restore_persisted")


class World:
    def __init__(self):
        self.trace = []
        self.fault = None
        self.disk = MemoryDisk(self.checkpoint)
        self.timer = Timer()
        self.firewall = Firewall()
        self.clock = Clock()
        self.optional_services = {name: object() for name in ("collector", "docker", "journald", "unrelated-package")}
        self.restorer_available = True
        self.operation_active = False
        self.last_accepted_clock = None

    def checkpoint(self, label):
        self.trace.append(label)
        if self.fault:
            self.fault.fire(self, label)

    def restart(self, *, power=False, retain_rename=False, reboot=False):
        self.fault = None
        if power:
            self.disk.power_loss(retain_rename)
        if reboot or power:
            self.clock = Clock("synthetic-boot-b", self.clock.wall + 3, 0)
            self.firewall.live = self.firewall.persisted
            self.timer = Timer()
            self.last_accepted_clock = None


class Controller:
    """Pure protocol driver; only injected synthetic effects, no installation API."""
    def __init__(self, world, run_id="synthetic-run-a"):
        require(type(run_id) is str and bool(re.fullmatch(r"synthetic-run-[a-z]", run_id)))
        self.w = world
        self.run_id = run_id
        self.prefix = "runs/" + run_id + "/"

    def _key(self, name):
        return self.prefix + name

    def _record(self, phase, plan, disposition=None):
        value = {"schema": 1, "run_id": self.run_id, "phase": phase.value,
                 "plan": plan, "disposition": disposition}
        self.w.disk.publish(self._key("state"), value, "state." + phase.value)

    @staticmethod
    def _service(capsule):
        return {"schema": 1, "run_id": capsule["run_id"], "plan": digest(capsule),
                "invocation_run_id": capsule["run_id"], "image": "synthetic-recovery-service-v1",
                "boot_reconcile": True, "enablement_intent": True}

    def _load(self):
        lease = self.w.disk.read("lease")
        require(type(lease) is dict and set(lease) == {"schema", "run_id", "plan"}
                and type(lease["schema"]) is int and lease["schema"] == 1)
        if lease["run_id"] != self.run_id:
            raise StaleRun()
        require(not self.w.disk.unacknowledged(self._key("state")))
        state = self.w.disk.read(self._key("state"))
        require(type(state) is dict and set(state) == {"schema", "run_id", "plan", "phase", "disposition"})
        require(type(state["schema"]) is int and state["schema"] == 1
                and state["run_id"] == self.run_id and state["plan"] == lease["plan"])
        require(type(state["phase"]) is str and state["phase"] in {p.value for p in Phase}
                and type(state["disposition"]) in (str, type(None))
                and state["disposition"] in (None, "COMMIT", "ROLLBACK"))
        capsule = self.w.disk.read(self._key("capsule"))
        require(type(capsule) is dict and digest(capsule) == lease["plan"])
        require(set(capsule) == {"schema", "run_id", "baseline", "restricted", "intent", "mechanism",
                                 "boot", "wall_start", "mono_start", "wall_due", "mono_due"})
        require(type(capsule["schema"]) is int and capsule["schema"] == 1 and capsule["run_id"] == self.run_id)
        require(type(capsule["boot"]) is str and bool(capsule["boot"]))
        require(capsule["baseline"] == "baseline" and capsule["restricted"] == "restricted:" + self.run_id)
        require(capsule["intent"] == "restore-baseline" and capsule["mechanism"] == "synthetic-restorer-v1")
        require(all(type(capsule[k]) is int for k in ("wall_start", "mono_start", "wall_due", "mono_due")))
        require(capsule["wall_due"] - capsule["wall_start"] == capsule["mono_due"] - capsule["mono_start"] == 900)
        service = self.w.disk.read(self._key("service"))
        require(canonical(service) == canonical(self._service(capsule)))
        require(not self.w.disk.unacknowledged(self._key("decision")))
        marker = self.w.disk.read(self._key("decision"))
        if marker is not None:
            require(canonical(marker) == canonical({"schema": 1, "run_id": self.run_id, "plan": lease["plan"],
                                                    "approval": "synthetic-independent-review"}))
            require(state["phase"] in (Phase.RESTRICTED_PENDING.value, Phase.COMMIT_DECIDED.value,
                                       Phase.CLEANUP_PENDING.value, Phase.COMPLETED.value))
        if state["phase"] in (Phase.COMMIT_DECIDED.value, Phase.COMPLETED.value) or state["disposition"] == "COMMIT":
            require(marker is not None)
        if state["phase"] in (Phase.COMMIT_DECIDED.value, Phase.COMPLETED.value):
            require(state["disposition"] == "COMMIT")
        if state["phase"] in (Phase.ROLLBACK_PENDING.value, Phase.ROLLED_BACK.value):
            require(state["disposition"] == "ROLLBACK" and marker is None)
        if state["phase"] == Phase.CLEANUP_PENDING.value:
            require(state["disposition"] == ("COMMIT" if marker else "ROLLBACK"))
        if state["phase"] in (Phase.PREPARED.value, Phase.RECOVERY_DURABLE.value, Phase.ROLLBACK_ARMED.value,
                              Phase.MUTATION_INTENT.value, Phase.RESTRICTED_PENDING.value):
            require(state["disposition"] is None)
        require(self.w.restorer_available or marker is not None)
        return state, capsule, service, marker is not None

    def _clock_valid(self, capsule):
        c = self.w.clock
        sample = self.w.last_accepted_clock
        if sample is not None and sample[0] == c.boot and (c.mono < sample[1] or c.wall < sample[2]):
            return False
        return (c.boot == capsule["boot"] and c.mono >= capsule["mono_start"]
                and c.mono < capsule["mono_due"] and c.wall < capsule["wall_due"]
                and abs((c.wall - capsule["wall_start"]) - (c.mono - capsule["mono_start"])) <= 2)

    def _timer_valid(self, capsule, service, context):
        self.w.checkpoint("timer:observe:" + context)
        t = self.w.timer
        valid = (self._clock_valid(capsule) and t.run_id == self.run_id and t.config == digest(service)
                and t.boot == self.w.clock.boot and t.active and t.enabled and not t.running and not t.queued
                and t.mono_due == capsule["mono_due"] and t.wall_due == capsule["wall_due"]
                and t.mono_due > self.w.clock.mono and t.wall_due > self.w.clock.wall)
        if valid:
            c = self.w.clock
            self.w.last_accepted_clock = (c.boot, c.mono, c.wall)
        return valid

    def _timer_clear(self):
        self.w.checkpoint("timer:observe:cleanup")
        t = self.w.timer
        service = self.w.disk.read(self._key("service"))
        require(type(service) is dict)
        matched = ((t.run_id is None and t.config is None)
                   or (t.run_id == self.run_id and t.config == digest(service)))
        return (matched and not t.active and not t.enabled
                and not t.running and not t.queued)

    def _observed_firewall(self, context):
        self.w.checkpoint("firewall:observe:" + context)
        return self.w.firewall.snapshot()

    def _result(self, phase, code, cancelled=False, committed=False):
        state = self.w.disk.read(self._key("state"))
        return Result(phase, code, cancelled, committed, state["phase"] if state else None)

    def _prepare(self):
        old = self.w.disk.read("lease")
        if old is not None:
            require(type(old) is dict and set(old) == {"schema", "run_id", "plan"})
            require(old["run_id"] != self.run_id)
            prior = Controller(self.w, old["run_id"])._status()
            require(prior.phase in (Phase.COMPLETED, Phase.ROLLED_BACK) and prior.timer_cancelled)
        require(self.w.disk.read(self._key("state")) is None)
        require(self.w.firewall.snapshot() == ("baseline", "baseline"))
        c = self.w.clock
        capsule = {"schema": 1, "run_id": self.run_id, "baseline": "baseline", "restricted": "restricted:" + self.run_id,
                   "intent": "restore-baseline", "mechanism": "synthetic-restorer-v1", "boot": c.boot,
                   "wall_start": c.wall, "mono_start": c.mono, "wall_due": c.wall + 900, "mono_due": c.mono + 900}
        plan = digest(capsule)
        self.w.disk.publish("lease", {"schema": 1, "run_id": self.run_id, "plan": plan}, "lease")
        self._record(Phase.PREPARED, plan)
        self.w.disk.publish(self._key("capsule"), capsule, "capsule", exclusive=True)
        self.w.disk.publish(self._key("service"), self._service(capsule), "service", exclusive=True)
        self._load()
        self._record(Phase.RECOVERY_DURABLE, plan)
        return self._result(Phase.RECOVERY_DURABLE, "PREPARATION_ACKNOWLEDGED")

    def _arm(self):
        state, capsule, service, committed = self._load()
        require(state["phase"] == Phase.RECOVERY_DURABLE.value and not committed and self._clock_valid(capsule))
        self.w.timer.arm(self.w, capsule, service)
        require(self._timer_valid(capsule, service, "arm"))
        self._record(Phase.ROLLBACK_ARMED, state["plan"])
        return self._result(Phase.ROLLBACK_ARMED, "ARMED_OBSERVED")

    def _apply(self):
        state, capsule, service, committed = self._load()
        if committed:
            return self._finish()
        if state["phase"] == Phase.RESTRICTED_PENDING.value:
            if not self._timer_valid(capsule, service, "repeat_apply"):
                return self._recover()
            require(self._observed_firewall("repeat_apply") == (capsule["restricted"],) * 2)
            return self._result(Phase.RESTRICTED_PENDING, "PENDING_REOBSERVED")
        require(state["phase"] == Phase.ROLLBACK_ARMED.value)
        if not self._timer_valid(capsule, service, "apply"):
            return self._recover()
        self._record(Phase.MUTATION_INTENT, state["plan"])
        if not self._timer_valid(capsule, service, "before_mutation"):
            return self._recover()
        self._load()  # Recheck restoration mechanism and immutable inputs after observation.
        require(self._observed_firewall("before_mutation") == (capsule["baseline"],) * 2)
        self.w.firewall.restrict(self.w, capsule)
        require(self._observed_firewall("restricted") == (capsule["restricted"],) * 2)
        self._record(Phase.RESTRICTED_PENDING, state["plan"])
        return self._result(Phase.RESTRICTED_PENDING, "RESTRICTED_UNCOMMITTED")

    def _decide(self, approval, evidence):
        state, capsule, service, committed = self._load()
        if committed:
            return self._finish()
        require(state["phase"] == Phase.RESTRICTED_PENDING.value)
        # Evidence is deliberately unused. Nothing in this model authenticates it.
        if (type(approval) is not SyntheticApproval or approval.run_id != self.run_id
                or approval.plan != state["plan"] or approval.independent_review is not True):
            return self._result(Phase.RESTRICTED_PENDING, "AUTHORIZATION_DENIED")
        if not self._timer_valid(capsule, service, "decide"):
            return self._recover()
        require(self._observed_firewall("decide") == (capsule["restricted"],) * 2)
        marker = {"schema": 1, "run_id": self.run_id, "plan": state["plan"], "approval": "synthetic-independent-review"}
        self.w.disk.publish(self._key("decision"), marker, "decision", exclusive=True)
        self._record(Phase.COMMIT_DECIDED, state["plan"], "COMMIT")
        return self._finish()

    def _finish(self):
        state, capsule, service, committed = self._load()
        disposition = "COMMIT" if committed else "ROLLBACK"
        terminal = Phase.COMPLETED if committed else Phase.ROLLED_BACK
        desired = capsule["restricted"] if committed else capsule["baseline"]
        require(self._observed_firewall("cleanup") == (desired,) * 2)
        if state["phase"] == terminal.value and self._timer_clear():
            return self._result(terminal, "COMPLETE_REOBSERVED", True, committed)
        self._record(Phase.CLEANUP_PENDING, state["plan"], disposition)
        try:
            self.w.timer.cancel(self.w, self.run_id, digest(service))
        except AdapterFault:
            return self._result(Phase.CLEANUP_PENDING, "CANCELLATION_PENDING", False, committed)
        if not self._timer_clear():
            return self._result(Phase.CLEANUP_PENDING, "CANCELLATION_UNCONFIRMED", False, committed)
        self._record(terminal, state["plan"], disposition)
        self.w.checkpoint("cleanup:after_terminal")
        if not self._timer_clear():
            return self._result(Phase.CLEANUP_PENDING, "CANCELLATION_UNCONFIRMED", False, committed)
        require(self._observed_firewall("completed") == (desired,) * 2)
        return self._result(terminal, "COMPLETED_OBSERVED" if committed else "ROLLED_BACK_OBSERVED", True, committed)

    def _recover(self):
        self.w.checkpoint("recovery:entry")
        state, capsule, service, committed = self._load()
        if committed:
            return self._finish()
        actual = self._observed_firewall("recovery")
        require(set(actual) <= {capsule["baseline"], capsule["restricted"]})
        if (actual == (capsule["baseline"],) * 2
                and state["phase"] in (Phase.ROLLED_BACK.value, Phase.CLEANUP_PENDING.value)):
            # Already-restored/terminal retry: only reobserve or retry cleanup.
            # No redundant rollback publication or cancellation is permitted.
            return self._finish()
        self._record(Phase.ROLLBACK_PENDING, state["plan"], "ROLLBACK")
        if actual != (capsule["baseline"],) * 2:
            require(self.w.restorer_available)
            self.w.firewall.restore(self.w, capsule)
            require(self._observed_firewall("restored") == (capsule["baseline"],) * 2)
        return self._finish()

    def _status(self):
        state, capsule, service, committed = self._load()
        phase = Phase(state["phase"])
        if phase in (Phase.COMPLETED, Phase.ROLLED_BACK):
            desired = capsule["restricted"] if committed else capsule["baseline"]
            require(self._observed_firewall("status") == (desired,) * 2)
            if self._timer_clear():
                return self._result(phase, "COMPLETE_REOBSERVED", True, committed)
            return self._result(Phase.CLEANUP_PENDING, "CANCELLATION_UNCONFIRMED", False, committed)
        return self._result(phase, "PENDING", False, committed)

    def _execute_unlocked(self, event, *, expected_run=None, approval=None, evidence=None):
        """A model event that assumes the world operation guard is held."""
        try:
            if expected_run is not None and expected_run != self.run_id:
                return Result(Phase.RECOVERY_BLOCKED, "STALE_IGNORED")
            # The prepare event performs its own old-lease validation. All other
            # events MUST reject stale ownership before an injectable checkpoint.
            if event != "prepare":
                lease = self.w.disk.read("lease")
                require(type(lease) is dict)
                if lease.get("run_id") != self.run_id:
                    raise StaleRun()
            self.w.checkpoint("event:" + event + ":entry")
            if event == "prepare":
                return self._prepare()
            if event == "arm":
                return self._arm()
            if event == "apply":
                return self._apply()
            if event == "decide":
                return self._decide(approval, evidence)
            if event in ("recover", "reconcile"):
                return self._recover()
            require(event == "status")
            return self._status()
        except StaleRun:
            return Result(Phase.RECOVERY_BLOCKED, "STALE_IGNORED")
        except (StorageFault, AdapterFault, MetadataFault) as exc:
            # Do not manufacture completion from a readable phase after an error.
            try:
                last = self.w.disk.read(self._key("state"))
                phase = last.get("phase") if last and type(last.get("phase")) is str else None
            except MetadataFault:
                phase = None
            return Result(Phase.RECOVERY_BLOCKED, "IO_UNCERTAIN" if isinstance(exc, StorageFault) else "RECOVERY_BLOCKED",
                          persistent_phase=phase)

    def execute(self, event, *, expected_run=None, approval=None, evidence=None):
        """Reject synthetic concurrent commit/rollback interleaving.

        Not a real interprocess, filesystem, or OS-level lock.
        """
        if self.w.operation_active:
            return Result(Phase.RECOVERY_BLOCKED, "CONCURRENT_EVENT_BLOCKED")
        self.w.operation_active = True
        try:
            return self._execute_unlocked(event, expected_run=expected_run,
                                          approval=approval, evidence=evidence)
        finally:
            self.w.operation_active = False
