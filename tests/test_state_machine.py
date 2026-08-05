"""状态机逻辑自测：模拟 丢球→成功 / 丢球→失败 / 丢球→超时 / 冷却去重。

设计约定：结果统计事件在「冷却结束进入 IDLE」时产出（RESULT_TIMEOUT 只迁移状态）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.events import Event, EventType, Outcome
from core.state_machine import StateMachine


def sim(name, events, expect):
    sm = StateMachine(throw_timeout_s=2.0, cooldown_s=1.0)
    stats = []
    for ev in events:
        stats += sm.feed(ev)
        stats += sm.poll(ev.ts)
    got = [(s.kind, s.outcome.value if s.outcome else None) for s in stats]
    assert got == expect, f"{name}: 期望 {expect} 实际 {got}"
    print(f"[PASS] {name}: {got}")


sim("丢球→成功",
    [Event(EventType.BALL_THROWN, 1.0, 0.9),
     Event(EventType.RESULT_DETECTED, 1.0, 0.9, {"outcome": Outcome.SUCCESS}),
     Event(EventType.IDLE, 2.5)],
    [("throw", None), ("result", "success")])

sim("丢球→失败",
    [Event(EventType.BALL_THROWN, 1.0, 0.9),
     Event(EventType.RESULT_DETECTED, 1.0, 0.85, {"outcome": Outcome.FAIL}),
     Event(EventType.IDLE, 2.5)],
    [("throw", None), ("result", "fail")])

sim("丢球→超时未知",
    [Event(EventType.BALL_THROWN, 1.0, 0.9),
     Event(EventType.IDLE, 3.5),
     Event(EventType.IDLE, 4.5)],
    [("throw", None), ("result", "unknown")])

sim("重复丢球去重(THROWING 中再命中被忽略)",
    [Event(EventType.BALL_THROWN, 1.0, 0.9),
     Event(EventType.BALL_THROWN, 1.3, 0.95),
     Event(EventType.BALL_THROWN, 1.6, 0.9),
     Event(EventType.IDLE, 3.5),
     Event(EventType.IDLE, 4.5)],
    [("throw", None), ("result", "unknown")])

sim("连续两球各计一次",
    [Event(EventType.BALL_THROWN, 1.0, 0.9),
     Event(EventType.RESULT_DETECTED, 1.0, 0.9, {"outcome": Outcome.SUCCESS}),
     Event(EventType.IDLE, 2.5),
     Event(EventType.BALL_THROWN, 3.0, 0.9),
     Event(EventType.RESULT_DETECTED, 4.0, 0.9, {"outcome": Outcome.FAIL}),
     Event(EventType.IDLE, 6.0)],
    [("throw", None), ("result", "success"), ("throw", None), ("result", "fail")])

sim("丢球后立刻冷却内新丢球被忽略，冷却后才可再丢",
    [Event(EventType.BALL_THROWN, 1.0, 0.9),
     Event(EventType.RESULT_DETECTED, 1.0, 0.9, {"outcome": Outcome.SUCCESS}),
     Event(EventType.BALL_THROWN, 2.0, 0.9),
     Event(EventType.IDLE, 2.5),
     Event(EventType.BALL_THROWN, 3.0, 0.9),
     Event(EventType.RESULT_DETECTED, 4.0, 0.9, {"outcome": Outcome.FAIL}),
     Event(EventType.IDLE, 6.0)],
    [("throw", None), ("result", "success"), ("throw", None), ("result", "fail")])

print("全部通过")

