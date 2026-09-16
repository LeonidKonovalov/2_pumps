TYPE E_ControllerState :
(
    IDLE,
    STARTING,
    RUNNING,
    STOPPING,
    SWITCHING,
    FAULT,
    EMERGENCY
);
END_TYPE


TYPE E_ActivePump :
(
    NONE,
    P1,
    P2
);
END_TYPE


TYPE E_StopReason :
(
    NORMAL_STOP,
    PUMP_FAULT,
    EMERGENCY
);
END_TYPE


FUNCTION_BLOCK FB_PumpController

VAR
    StartTimer : TON;
    StopTimer  : TON;
END_VAR


VAR_INPUT
    AutoMode : BOOL;
    Level : REAL;
    Emergency : BOOL;

    P1_Run : BOOL;
    P1_Fault : BOOL;

    P2_Run : BOOL;
    P2_Fault : BOOL;

    ResetCommand : BOOL;
END_VAR


VAR_OUTPUT
    P1_Start : BOOL;
    P2_Start : BOOL;

    Warning : BOOL;
    Alarm : BOOL;

    ControllerState : E_ControllerState := IDLE;
    ActivePump : E_ActivePump := NONE;
    StopReason : E_StopReason := NORMAL_STOP;
END_VAR


// ==================================================
// DEFAULT OUTPUTS
// ==================================================

P1_Start := FALSE;
P2_Start := FALSE;

Warning := FALSE;
Alarm := FALSE;


// ==================================================
// TIMERS
// ==================================================

StartTimer(
    IN := ControllerState = STARTING,
    PT := T#5s
);

StopTimer(
    IN := (ControllerState = STOPPING)
       OR (ControllerState = EMERGENCY),
    PT := T#5s
);


// ==================================================
// EMERGENCY — HIGHEST PRIORITY
// ==================================================

IF Emergency AND ControllerState <> EMERGENCY THEN

    ControllerState := EMERGENCY;
    StopReason := EMERGENCY;

END_IF;


// ==================================================
// DIAGNOSTICS
// ==================================================

IF P1_Fault OR P2_Fault THEN
    Warning := TRUE;
END_IF;

IF P1_Fault AND P2_Fault THEN
    Alarm := TRUE;
END_IF;


// ==================================================
// STATE MACHINE
// ==================================================

CASE ControllerState OF


    // ==============================================
    // IDLE
    // ==============================================

    IDLE:

        ActivePump := NONE;

        IF Level < 30.0 AND AutoMode THEN

            IF NOT P1_Fault THEN

                ActivePump := P1;
                ControllerState := STARTING;

            ELSIF NOT P2_Fault THEN

                ActivePump := P2;
                ControllerState := STARTING;

            ELSE

                ActivePump := NONE;
                ControllerState := FAULT;

            END_IF;

        END_IF;


    // ==============================================
    // STARTING
    // ==============================================

    STARTING:

        IF ActivePump = P1 THEN

            IF P1_Fault THEN

                StopReason := PUMP_FAULT;
                ControllerState := STOPPING;

            ELSIF P1_Run THEN

                ControllerState := RUNNING;

            ELSIF StartTimer.Q THEN

                StopReason := PUMP_FAULT;

                IF AutoMode THEN
                    ControllerState := STOPPING;
                ELSE
                    ActivePump := NONE;
                    ControllerState := FAULT;
                END_IF;

            END_IF;


        ELSIF ActivePump = P2 THEN

            IF P2_Fault THEN

                StopReason := PUMP_FAULT;
                ControllerState := STOPPING;

            ELSIF P2_Run THEN

                ControllerState := RUNNING;

            ELSIF StartTimer.Q THEN

                StopReason := PUMP_FAULT;

                IF AutoMode THEN
                    ControllerState := STOPPING;
                ELSE
                    ActivePump := NONE;
                    ControllerState := FAULT;
                END_IF;

            END_IF;

        END_IF;


    // ==============================================
    // RUNNING
    // ==============================================

    RUNNING:

        IF ActivePump = P1 THEN

            IF P1_Fault THEN

                StopReason := PUMP_FAULT;
                ControllerState := STOPPING;

            END_IF;


        ELSIF ActivePump = P2 THEN

            IF P2_Fault THEN

                StopReason := PUMP_FAULT;
                ControllerState := STOPPING;

            END_IF;

        END_IF;


        // Normal stop by level

        IF Level > 80.0 THEN

            StopReason := NORMAL_STOP;
            ControllerState := STOPPING;

        END_IF;


    // ==============================================
    // STOPPING
    // ==============================================

    STOPPING:

        IF ActivePump = P1 THEN

            IF NOT P1_Run THEN

                CASE StopReason OF

                    NORMAL_STOP:

                        ActivePump := NONE;
                        ControllerState := IDLE;


                    PUMP_FAULT:

                        IF AutoMode THEN
                            ControllerState := SWITCHING;
                        ELSE
                            ActivePump := NONE;
                            ControllerState := FAULT;
                        END_IF;


                    EMERGENCY:

                        ActivePump := NONE;
                        ControllerState := EMERGENCY;

                END_CASE;


            ELSIF StopTimer.Q THEN

                ActivePump := NONE;
                ControllerState := FAULT;

            END_IF;


        ELSIF ActivePump = P2 THEN

            IF NOT P2_Run THEN

                CASE StopReason OF

                    NORMAL_STOP:

                        ActivePump := NONE;
                        ControllerState := IDLE;


                    PUMP_FAULT:

                        IF AutoMode THEN
                            ControllerState := SWITCHING;
                        ELSE
                            ActivePump := NONE;
                            ControllerState := FAULT;
                        END_IF;


                    EMERGENCY:

                        ActivePump := NONE;
                        ControllerState := EMERGENCY;

                END_CASE;


            ELSIF StopTimer.Q THEN

                ActivePump := NONE;
                ControllerState := FAULT;

            END_IF;

        END_IF;


    // ==============================================
    // SWITCHING
    // ==============================================

    SWITCHING:

        IF NOT AutoMode THEN

            ActivePump := NONE;
            ControllerState := FAULT;

        ELSE

            IF ActivePump = P1 THEN

                IF NOT P1_Run
                   AND NOT P2_Run
                   AND NOT P2_Fault THEN

                    ActivePump := P2;
                    ControllerState := STARTING;

                ELSIF P2_Fault THEN

                    ActivePump := NONE;
                    ControllerState := FAULT;

                END_IF;


            ELSIF ActivePump = P2 THEN

                IF NOT P1_Run
                   AND NOT P2_Run
                   AND NOT P1_Fault THEN

                    ActivePump := P1;
                    ControllerState := STARTING;

                ELSIF P1_Fault THEN

                    ActivePump := NONE;
                    ControllerState := FAULT;

                END_IF;

            END_IF;

        END_IF;


    // ==============================================
    // FAULT
    // ==============================================

    FAULT:

        ActivePump := NONE;

        IF ResetCommand
           AND NOT P1_Run
           AND NOT P2_Run
           AND NOT P1_Fault
           AND NOT P2_Fault THEN

            ControllerState := IDLE;
            StopReason := NORMAL_STOP;

        END_IF;


    // ==============================================
    // EMERGENCY
    // ==============================================

    EMERGENCY:

        P1_Start := FALSE;
        P2_Start := FALSE;

        // Ждем фактической остановки насосов

        IF NOT P1_Run
           AND NOT P2_Run
           AND NOT Emergency THEN

            ActivePump := NONE;
            StopReason := NORMAL_STOP;
            ControllerState := IDLE;

        ELSIF StopTimer.Q THEN

            ActivePump := NONE;
            ControllerState := FAULT;

        END_IF;

END_CASE;


// ==================================================
// OUTPUT COMMANDS
// ==================================================
//
// Выходы формируются ПОСЛЕ state machine.
// Поэтому если внутри цикла произошел переход
// STARTING -> STOPPING, P1_Start уже не включится.
// ==================================================

CASE ControllerState OF

    STARTING,
    RUNNING:

        IF ActivePump = P1 THEN
            P1_Start := TRUE;

        ELSIF ActivePump = P2 THEN
            P2_Start := TRUE;

        END_IF;


    STOPPING,
    SWITCHING,
    IDLE,
    FAULT,
    EMERGENCY:

        P1_Start := FALSE;
        P2_Start := FALSE;

END_CASE;

END_FUNCTION_BLOCK

/* IDLE
 │
 │ Level < 30 AND AutoMode
 ▼
STARTING
 │
 ├── Run → RUNNING
 │
 ├── Fault → STOPPING
 │
 └── Timeout
       ├── Auto → SWITCHING
       └── Manual → FAULT

RUNNING
 │
 ├── Level > 80 → STOPPING
 │
 └── Fault → STOPPING

STOPPING
 │
 ├── Run=0 + NORMAL → IDLE
 │
 ├── Run=0 + PUMP_FAULT
 │      ├── Auto → SWITCHING
 │      └── Manual → FAULT
 │
 └── Timeout → FAULT

SWITCHING
 │
 ├── резерв исправен + Auto → STARTING
 │
 └── резерв Fault → FAULT

FAULT
 │
 └── Reset + оба остановлены + Fault сняты → IDLE

EMERGENCY
 │
 ├── Start=0
 │
 ├── ждём оба Run=0
 │
 ├── Timeout → FAULT
 │
 └── Emergency снят + оба остановлены → IDLE   */