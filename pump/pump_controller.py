from dataclasses import dataclass, field


IDLE, STARTING, RUNNING, STOPPING, SWITCHING, FAULT, EMERGENCY = (
    "IDLE", "STARTING", "RUNNING", "STOPPING", "SWITCHING", "FAULT", "EMERGENCY"
)
NONE, P1, P2 = "NONE", "P1", "P2"
NORMAL_STOP, PUMP_FAULT, EMERGENCY_STOP = "NORMAL_STOP", "PUMP_FAULT", "EMERGENCY_STOP"


class TON:
    def __init__(self, preset_s: float):
        self.preset = preset_s # PT в секундах
        self.elapsed = 0.0
        self.q = False

    def step(self, in_: bool, dt: float):
        if in_:
            self.elapsed += dt
        else:
            self.elapsed = 0.0
        self.q = self.elapsed >= self.preset
        return self.q


@dataclass
class Inputs:
    auto_mode: bool = False
    level: float = 0.0
    emergency: bool = False
    p1_run: bool = False
    p1_fault: bool = False
    p2_run: bool = False
    p2_fault: bool = False
    reset_command: bool = False


@dataclass
class Outputs:
    p1_start: bool = False
    p2_start: bool = False
    warning: bool = False
    alarm: bool = False
    controller_state: str = IDLE
    active_pump: str = NONE
    stop_reason: str = NORMAL_STOP


class PumpController:
    def __init__(self):
        self.controller_state = IDLE
        self.active_pump = NONE
        self.stop_reason = NORMAL_STOP
        self.start_timer = TON(5.0)
        self.stop_timer = TON(5.0)

    def step(self, i: Inputs, dt: float = 1.0) -> Outputs:
        # DEFAULT OUTPUTS
        p1_start = False
        p2_start = False
        warning = False
        alarm = False

        # TIMERS
        self.start_timer.step(self.controller_state == STARTING, dt)
        self.stop_timer.step(
            self.controller_state in (STOPPING, EMERGENCY), dt
        )

        # EMERGENCY — HIGHEST PRIORITY
        if i.emergency and self.controller_state != EMERGENCY:
            self.controller_state = EMERGENCY
            self.stop_reason = EMERGENCY_STOP

        # DIAGNOSTICS
        if i.p1_fault or i.p2_fault:
            warning = True
        if i.p1_fault and i.p2_fault:
            alarm = True

        # STATE MACHINE
        s = self.controller_state

        if s == IDLE:
            self.active_pump = NONE
            if i.level < 30.0 and i.auto_mode:
                if not i.p1_fault:
                    self.active_pump = P1
                    self.controller_state = STARTING
                elif not i.p2_fault:
                    self.active_pump = P2
                    self.controller_state = STARTING
                else:
                    self.active_pump = NONE
                    self.controller_state = FAULT

        elif s == STARTING:
            if self.active_pump == P1:
                if i.p1_fault:
                    self.stop_reason = PUMP_FAULT
                    self.controller_state = STOPPING
                elif i.p1_run:
                    self.controller_state = RUNNING
                elif self.start_timer.q:
                    self.stop_reason = PUMP_FAULT
                    if i.auto_mode:
                        self.controller_state = STOPPING
                    else:
                        self.active_pump = NONE
                        self.controller_state = FAULT
            elif self.active_pump == P2:
                if i.p2_fault:
                    self.stop_reason = PUMP_FAULT
                    self.controller_state = STOPPING
                elif i.p2_run:
                    self.controller_state = RUNNING
                elif self.start_timer.q:
                    self.stop_reason = PUMP_FAULT
                    if i.auto_mode:
                        self.controller_state = STOPPING
                    else:
                        self.active_pump = NONE
                        self.controller_state = FAULT

        elif s == RUNNING:
            if self.active_pump == P1 and i.p1_fault:
                self.stop_reason = PUMP_FAULT
                self.controller_state = STOPPING
            elif self.active_pump == P2 and i.p2_fault:
                self.stop_reason = PUMP_FAULT
                self.controller_state = STOPPING
            if i.level > 80.0:
                self.stop_reason = NORMAL_STOP
                self.controller_state = STOPPING

        elif s == STOPPING:
            active_run = i.p1_run if self.active_pump == P1 else i.p2_run
            if not active_run:
                if self.stop_reason == NORMAL_STOP:
                    self.active_pump = NONE
                    self.controller_state = IDLE
                elif self.stop_reason == PUMP_FAULT:
                    if i.auto_mode:
                        self.controller_state = SWITCHING
                    else:
                        self.active_pump = NONE
                        self.controller_state = FAULT
                elif self.stop_reason == EMERGENCY_STOP:
                    self.active_pump = NONE
                    self.controller_state = EMERGENCY
            elif self.stop_timer.q:
                self.active_pump = NONE
                self.controller_state = FAULT

        elif s == SWITCHING:
            if not i.auto_mode:
                self.active_pump = NONE
                self.controller_state = FAULT
            else:
                if self.active_pump == P1:
                    if not i.p1_run and not i.p2_run and not i.p2_fault:
                        self.active_pump = P2
                        self.controller_state = STARTING
                    elif i.p2_fault:
                        self.active_pump = NONE
                        self.controller_state = FAULT
                elif self.active_pump == P2:
                    if not i.p1_run and not i.p2_run and not i.p1_fault:
                        self.active_pump = P1
                        self.controller_state = STARTING
                    elif i.p1_fault:
                        self.active_pump = NONE
                        self.controller_state = FAULT

        elif s == FAULT:
            self.active_pump = NONE
            if (i.reset_command and not i.p1_run and not i.p2_run
                    and not i.p1_fault and not i.p2_fault):
                self.controller_state = IDLE
                self.stop_reason = NORMAL_STOP

        elif s == EMERGENCY:
            p1_start = False
            p2_start = False
            if not i.p1_run and not i.p2_run and not i.emergency:
                self.active_pump = NONE
                self.stop_reason = NORMAL_STOP
                self.controller_state = IDLE
            elif self.stop_timer.q:
                self.active_pump = NONE
                self.controller_state = FAULT

        # OUTPUT COMMANDS
        if self.controller_state in (STARTING, RUNNING):
            if self.active_pump == P1:
                p1_start = True
            elif self.active_pump == P2:
                p2_start = True
        else:
            p1_start = False
            p2_start = False

        return Outputs(
            p1_start=p1_start,
            p2_start=p2_start,
            warning=warning,
            alarm=alarm,
            controller_state=self.controller_state,
            active_pump=self.active_pump,
            stop_reason=self.stop_reason,
        )
