"""状态机：空闲 → 丢球中 → 结果中 → 空闲，带冷却去重。"""
from __future__ import annotations

import time
from enum import Enum

from core.events import Event, EventType, Outcome, StatEvent


class State(Enum):
    IDLE = "idle"
    THROWING = "throwing"
    RESULT = "result"


class StateMachine:
    def __init__(self, throw_timeout_s: float = 5.0, cooldown_s: float = 3.0):
        self.throw_timeout_s = throw_timeout_s
        self.cooldown_s = cooldown_s
        self.state = State.IDLE
        self.entered_at = time.time()
        self.pending_outcome: Outcome | None = None
        self.last_ball_ts: float = 0.0

    @property
    def state_name(self) -> str:
        return self.state.value

    def feed(self, ev: Event) -> list[StatEvent]:
        """输入检测事件，输出用于计数的 StatEvent 列表（可能为空）。"""
        now = ev.ts if ev.ts > 0 else time.time()
        out: list[StatEvent] = []

        if self.state == State.IDLE:
            if ev.type is EventType.BALL_THROWN:
                self.state = State.THROWING
                self.entered_at = now
                self.last_ball_ts = now
                out.append(StatEvent(kind="throw", outcome=None, ts=now,
                                     confidence=ev.confidence, detail=ev.detail))
        elif self.state == State.THROWING:
            if ev.type is EventType.RESULT_DETECTED:
                self.pending_outcome = ev.detail.get("outcome", Outcome.UNKNOWN)
                self.state = State.RESULT
                self.entered_at = now
            elif ev.type is EventType.RESULT_TIMEOUT:
                self.pending_outcome = Outcome.UNKNOWN
                self.state = State.RESULT
                self.entered_at = now
        elif self.state == State.RESULT:
            if ev.type is EventType.COOLDOWN_END:
                if self.pending_outcome is not None:
                    out.append(StatEvent(kind="result", outcome=self.pending_outcome, ts=now,
                                         detail={"enter": self.entered_at}))
                    self.pending_outcome = None
                self.state = State.IDLE
                self.entered_at = now

        return out

    def poll(self, now: float | None = None) -> list[StatEvent]:
        """按时间推进状态：丢球超时、结果冷却结束（主循环每秒调用）。"""
        now = now if now is not None else time.time()
        out: list[StatEvent] = []
        if self.state == State.THROWING and now - self.entered_at >= self.throw_timeout_s:
            out.extend(self.feed(Event(type=EventType.RESULT_TIMEOUT, ts=now)))
        elif self.state == State.RESULT and now - self.entered_at >= self.cooldown_s:
            out.extend(self.feed(Event(type=EventType.COOLDOWN_END, ts=now)))
        return out

    def reset(self) -> None:
        self.state = State.IDLE
        self.entered_at = time.time()
        self.pending_outcome = None
