"""事件定义：状态机输入/输出的事件类型与结果枚举。"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EventType(Enum):
    IDLE = "idle"
    BALL_THROWN = "ball_thrown"
    RESULT_DETECTED = "result_detected"
    RESULT_TIMEOUT = "result_timeout"
    COOLDOWN_END = "cooldown_end"


class Outcome(Enum):
    SUCCESS = "success"
    FAIL = "fail"
    UNKNOWN = "unknown"


@dataclass
class Event:
    type: EventType
    ts: float
    confidence: float = 0.0
    detail: dict = field(default_factory=dict)


@dataclass
class StatEvent:
    """状态机产出、用于计数的完成事件。"""
    kind: str  # throw | result
    outcome: Outcome | None
    ts: float
    confidence: float = 0.0
    detail: dict = field(default_factory=dict)
