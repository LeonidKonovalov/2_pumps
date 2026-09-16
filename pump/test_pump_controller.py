"""
Прогон сценариев T01-T10
"""
from pump_controller import PumpController, Inputs, STARTING, RUNNING, STOPPING, SWITCHING, IDLE, FAULT, P1, P2


def test_T01_idle_to_starting_p1():
    pc = PumpController()
    i = Inputs(level=20.0, auto_mode=True)
    out = pc.step(i)
    assert out.controller_state == STARTING
    assert out.p1_start is True


def test_T02_starting_to_running():
    pc = PumpController()
    pc.step(Inputs(level=20.0, auto_mode=True))          # T01
    out = pc.step(Inputs(level=20.0, auto_mode=True, p1_run=True))  # T02
    assert out.controller_state == RUNNING
    assert out.p1_start is True


def test_T03_running_to_stopping_on_high_level():
    pc = PumpController()
    pc.step(Inputs(level=20.0, auto_mode=True))
    pc.step(Inputs(level=20.0, auto_mode=True, p1_run=True))
    out = pc.step(Inputs(level=85.0, auto_mode=True, p1_run=True))
    assert out.controller_state == STOPPING
    assert out.p1_start is False and out.p2_start is False


def test_T04_stopping_to_idle():
    pc = PumpController()
    pc.step(Inputs(level=20.0, auto_mode=True))
    pc.step(Inputs(level=20.0, auto_mode=True, p1_run=True))
    pc.step(Inputs(level=85.0, auto_mode=True, p1_run=True))
    out = pc.step(Inputs(level=85.0, auto_mode=True, p1_run=False))
    assert out.controller_state == IDLE


def test_T05_starting_timeout_without_run():
    pc = PumpController()
    pc.step(Inputs(level=20.0, auto_mode=True))  # -> STARTING
    out = None
    # 5 секунд без P1_Run -> таймаут StartTimer, переход в STOPPING
    for _ in range(5):
        out = pc.step(Inputs(level=20.0, auto_mode=True), dt=1.0)
    assert out.controller_state == STOPPING
    assert out.p1_start is False and out.p2_start is False
    out2 = pc.step(Inputs(level=20.0, auto_mode=True), dt=1.0)
    assert out2.controller_state == SWITCHING


def test_T06_stopping_with_fault_to_switching():
    pc = PumpController()
    pc.step(Inputs(level=20.0, auto_mode=True))
    pc.step(Inputs(level=20.0, auto_mode=True, p1_run=True))
    # P1 fault -> STOPPING (stop_reason = PUMP_FAULT)
    pc.step(Inputs(level=20.0, auto_mode=True, p1_run=True, p1_fault=True))
    # насос фактически остановился (Run=0), fault ещё стоит
    out = pc.step(Inputs(level=20.0, auto_mode=True, p1_run=False, p1_fault=True))
    assert out.controller_state == SWITCHING


def test_T07_switching_to_starting_p2():
    pc = PumpController()
    pc.step(Inputs(level=20.0, auto_mode=True))
    pc.step(Inputs(level=20.0, auto_mode=True, p1_run=True))
    pc.step(Inputs(level=20.0, auto_mode=True, p1_run=True, p1_fault=True))
    pc.step(Inputs(level=20.0, auto_mode=True, p1_run=False, p1_fault=True))  # -> SWITCHING
    out = pc.step(Inputs(level=20.0, auto_mode=True, p1_fault=True))  # P2 здоров
    assert out.controller_state == STARTING
    assert out.p2_start is True


def test_T08_starting_p2_to_running():
    pc = PumpController()
    pc.step(Inputs(level=20.0, auto_mode=True))
    pc.step(Inputs(level=20.0, auto_mode=True, p1_run=True))
    pc.step(Inputs(level=20.0, auto_mode=True, p1_run=True, p1_fault=True))
    pc.step(Inputs(level=20.0, auto_mode=True, p1_run=False, p1_fault=True))
    pc.step(Inputs(level=20.0, auto_mode=True, p1_fault=True))  # -> STARTING P2
    out = pc.step(Inputs(level=20.0, auto_mode=True, p1_fault=True, p2_run=True))
    assert out.controller_state == RUNNING
    assert out.p2_start is True


def test_T09_running_p2_fault_to_stopping():
    pc = PumpController()
    pc.step(Inputs(level=20.0, auto_mode=True))
    pc.step(Inputs(level=20.0, auto_mode=True, p1_run=True))
    pc.step(Inputs(level=20.0, auto_mode=True, p1_run=True, p1_fault=True))
    pc.step(Inputs(level=20.0, auto_mode=True, p1_run=False, p1_fault=True))
    pc.step(Inputs(level=20.0, auto_mode=True, p1_fault=True))
    pc.step(Inputs(level=20.0, auto_mode=True, p1_fault=True, p2_run=True))
    out = pc.step(Inputs(level=20.0, auto_mode=True, p1_fault=True, p2_run=True, p2_fault=True))
    assert out.controller_state == STOPPING
    assert out.p1_start is False and out.p2_start is False


def test_T10_stopping_p2_to_switching():
    pc = PumpController()
    pc.step(Inputs(level=20.0, auto_mode=True))
    pc.step(Inputs(level=20.0, auto_mode=True, p1_run=True))
    pc.step(Inputs(level=20.0, auto_mode=True, p1_run=True, p1_fault=True))
    pc.step(Inputs(level=20.0, auto_mode=True, p1_run=False, p1_fault=True))
    pc.step(Inputs(level=20.0, auto_mode=True, p1_fault=True))
    pc.step(Inputs(level=20.0, auto_mode=True, p1_fault=True, p2_run=True))
    pc.step(Inputs(level=20.0, auto_mode=True, p1_fault=True, p2_run=True, p2_fault=True))
    out = pc.step(Inputs(level=20.0, auto_mode=True, p1_fault=True, p2_run=False, p2_fault=True))
    assert out.controller_state == SWITCHING
