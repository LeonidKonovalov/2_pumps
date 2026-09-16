
from pump_controller import PumpController, Inputs, STARTING, RUNNING, STOPPING, SWITCHING, IDLE, FAULT, P1, P2

def test_T05_starting_timeout_without_run():
    pc = PumpController()
    out0 = pc.step(Inputs(level=20.0, auto_mode=True))  # -> STARTING
    print(f"\nscan 0: state={out0.controller_state} active={out0.active_pump} "
          f"p1_start={out0.p1_start} elapsed={pc.start_timer.elapsed:.1f}")
    out = None
    # 5 секунд без P1_Run -> таймаут StartTimer, переход в STOPPING
    for n in range(1, 6):
        out = pc.step(Inputs(level=20.0, auto_mode=True), dt=1.0)
        print(f"scan {n}: state={out.controller_state} active={out.active_pump} "
              f"stop_reason={out.stop_reason} p1_start={out.p1_start} "
              f"elapsed={pc.start_timer.elapsed:.1f} q={pc.start_timer.q}")
    assert out.controller_state == STOPPING
    assert out.p1_start is False and out.p2_start is False
    # P1_Run еще не был TRUE, поэтому условие выхода из
    # STOPPING (NOT P1_Run) выполняется сразу же -> уже на следующем
    # скане контроллер провалится дальше, в SWITCHING (AutoMode=TRUE).
    out2 = pc.step(Inputs(level=20.0, auto_mode=True), dt=1.0)
    print(f"scan 6: state={out2.controller_state} active={out2.active_pump} "
          f"stop_reason={out2.stop_reason} p1_start={out2.p1_start}")
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
