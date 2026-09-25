"""Automatic resume while the router is running.

The resumer re-checks queued work on a bounded backoff schedule. Every attempt
goes through ``Coordinator.wake``: fresh eligibility (auth, account, usage,
spend, model, tools), the per-process turn lock, the cross-process dispatch
lease, compare-and-swap dispatch phases and reconciliation, all on the same
pinned model. A reported reset time only schedules an earlier *check*; it
never proves availability.

It runs only while a router process is open (``chat`` or ``serve``). Nothing
runs while the app is closed or the Mac is asleep. After a detected sleep (the
wall clock jumped past the monotonic clock) or at start, it reconciles first.
"""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from .contracts import JobState, parse_utc, utc_now
from .store import dumps

MIN_INTERVAL = 30.0
MAX_INTERVAL = 900.0
SLEEP_JUMP_SECONDS = 120.0
PROGRESS_STATES = {JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED, JobState.PAUSED, JobState.RUNNING}


@dataclass
class TickResult:
    ran: bool
    resumed: list[tuple[str, str]] = field(default_factory=list)
    reconciled_after_sleep: bool = False
    next_delay: float = MAX_INTERVAL
    waiting: int = 0


class AutoResumer:
    def __init__(
        self,
        coordinator,
        *,
        min_interval: float = MIN_INTERVAL,
        max_interval: float = MAX_INTERVAL,
        sleep_jump: float = SLEEP_JUMP_SECONDS,
        monotonic: Callable[[], float] = time.monotonic,
        wall: Callable[[], float] = time.time,
        jitter: float = 0.1,
        rng: random.Random | None = None,
    ) -> None:
        if not 0 < min_interval <= max_interval:
            raise ValueError("need 0 < min_interval <= max_interval")
        self.coordinator = coordinator
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.sleep_jump = sleep_jump
        self._monotonic = monotonic
        self._wall = wall
        self._jitter = jitter
        self._rng = rng or random.Random()
        self._backoff = min_interval
        self._stop = threading.Event()
        self._nudge = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_mono = monotonic()
        self._last_wall = wall()

    # -- control -------------------------------------------------------------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="model-router-resumer", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 10.0) -> None:
        self._stop.set()
        self._nudge.set()
        if self._thread:
            self._thread.join(timeout)

    def reset_backoff(self) -> None:
        """New work was queued: start again from the shortest interval."""
        self._backoff = self.min_interval

    def nudge(self) -> None:
        """Check soon (e.g. the owner queued new work or typed /wake)."""
        self._backoff = self.min_interval
        self._nudge.set()

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # -- loop ----------------------------------------------------------------

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                delay = self.tick().next_delay
            except Exception as exc:  # the resumer must never die silently
                self.coordinator.store.event("scheduler.error", {"error": repr(exc)})
                delay = self.max_interval
            self._nudge.clear()
            self._nudge.wait(delay)

    def detect_sleep(self) -> bool:
        mono, wall = self._monotonic(), self._wall()
        jumped = (wall - self._last_wall) - (mono - self._last_mono) > self.sleep_jump
        self._last_mono, self._last_wall = mono, wall
        return jumped

    def tick(self) -> TickResult:
        result = TickResult(ran=True)
        if self.detect_sleep():
            # The machine slept: connections may be gone and turns uncertain.
            self.coordinator.store.event("scheduler.woke_from_sleep", {})
            self.coordinator.recover()
            result.reconciled_after_sleep = True
        waiting = self.coordinator.waiting_jobs()
        result.waiting = len(waiting)
        if not waiting:
            self._backoff = self.min_interval
            result.next_delay = self.max_interval
            self._record(result)
            return result
        results = self.coordinator.wake(blocking=False)
        result.resumed = [(job_id, state.value) for job_id, state in results]
        progressed = any(state in PROGRESS_STATES for _, state in results)
        if progressed:
            self._backoff = self.min_interval
        else:
            self._backoff = min(self._backoff * 2, self.max_interval)
        delay = self._backoff
        soonest = self._soonest_reset()
        if soonest is not None:
            delay = max(self.min_interval, min(delay, soonest))
        result.next_delay = self._with_jitter(delay)
        self._record(result)
        return result

    def _soonest_reset(self) -> float | None:
        now = parse_utc(utc_now())
        best = None
        for job in self.coordinator.waiting_jobs():
            if not job.get("next_check_at"):
                continue
            try:
                seconds = (parse_utc(job["next_check_at"]) - now).total_seconds()
            except ValueError:
                continue
            seconds = max(0.0, seconds) + 5.0  # a little after the reported reset
            best = seconds if best is None else min(best, seconds)
        return best

    def _with_jitter(self, delay: float) -> float:
        spread = delay * self._jitter
        return max(self.min_interval, min(self.max_interval, delay + self._rng.uniform(-spread, spread)))

    def _record(self, result: TickResult) -> None:
        payload = {
            "last_tick": utc_now(),
            "next_check_in_s": round(result.next_delay, 1),
            "waiting": result.waiting,
            "resumed": result.resumed,
            "note": "runs only while a router process is open",
        }
        self.coordinator.store.execute(
            "INSERT INTO meta(key, value) VALUES('auto_resume', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (dumps(payload),),
        )
        if result.resumed:
            self.coordinator.store.event("scheduler.tick", payload)
