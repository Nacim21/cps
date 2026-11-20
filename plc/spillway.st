PROGRAM SpillwayController
VAR
    WaterLevelRaw AT %IW100 : INT;
    GatePosition AT %IW101 : INT;
    GateCommand AT %QW100 : INT;
    (* PLC4 native FC03 MW0..3 maps to input registers 102..105. *)
    SupervisorGate AT %IW102 : INT;
    SupervisorReason AT %IW103 : INT;
    SupervisorValid AT %IW104 : INT;
    SupervisorHeartbeat AT %IW105 : INT;
    LevelSnapshot AT %MW0 : INT;
    GateSnapshot AT %MW1 : INT;
    DesiredSnapshot AT %MW2 : INT;
    AlarmSnapshot AT %MW3 : INT;
    MismatchSnapshot AT %MW4 : INT;
    MismatchCount AT %MW5 : UINT;
    CycleCount AT %MW6 : UINT;
    (* MW7..11 reserved for existing aggregate telemetry. *)
    LocalGateSnapshot AT %MW12 : INT;
    SupervisorFreshSnapshot AT %MW13 : INT;
    SupervisorGateSnapshot AT %MW14 : INT;
    SupervisorReasonSnapshot AT %MW15 : INT;
    SupervisorStaleTicksSnapshot AT %MW16 : INT;
END_VAR
VAR
    WaterLevel : REAL;
    HighLevelAlarm : BOOL;
    PreviousMismatch : BOOL;
    Mismatch : BOOL;
    LocalGate : INT;
    SupervisorSeen : BOOL;
    SupervisorFresh : BOOL;
    SupervisorPreviousHeartbeat : INT;
    SupervisorStaleTicks : INT;
END_VAR

WaterLevel := INT_TO_REAL(WaterLevelRaw) / 100.0;
HighLevelAlarm := WaterLevel > 90.0;
IF WaterLevel > 90.0 THEN
    LocalGate := 100;
ELSIF WaterLevel > 70.0 THEN
    LocalGate := 75;
ELSIF WaterLevel >= 40.0 THEN
    LocalGate := 25;
ELSE
    LocalGate := 0;
END_IF;

(* The supervisory link is optional: loss falls back to local logic. *)
IF SupervisorHeartbeat <> SupervisorPreviousHeartbeat THEN
    SupervisorSeen := TRUE;
    SupervisorStaleTicks := 0;
ELSIF SupervisorStaleTicks < 120 THEN
    SupervisorStaleTicks := SupervisorStaleTicks + 1;
END_IF;
SupervisorPreviousHeartbeat := SupervisorHeartbeat;
SupervisorFresh := SupervisorSeen AND (SupervisorStaleTicks < 120);
GateCommand := LocalGate;
(* No supervisor instruction may reduce local safety opening. *)
IF SupervisorFresh AND (SupervisorValid <> 0)
    AND (SupervisorGate > GateCommand) AND (SupervisorGate <= 100) THEN
    GateCommand := SupervisorGate;
END_IF;
LocalGateSnapshot := LocalGate;
SupervisorFreshSnapshot := BOOL_TO_INT(SupervisorFresh);
SupervisorGateSnapshot := SupervisorGate;
SupervisorReasonSnapshot := SupervisorReason;
SupervisorStaleTicksSnapshot := SupervisorStaleTicks;

Mismatch := GatePosition <> GateCommand;
IF Mismatch AND NOT PreviousMismatch THEN
    IF MismatchCount < 65535 THEN
        MismatchCount := MismatchCount + 1;
    END_IF;
END_IF;
PreviousMismatch := Mismatch;
LevelSnapshot := WaterLevelRaw;
GateSnapshot := GatePosition;
DesiredSnapshot := GateCommand;
AlarmSnapshot := BOOL_TO_INT(HighLevelAlarm);
MismatchSnapshot := BOOL_TO_INT(Mismatch);
IF CycleCount < 65535 THEN
    CycleCount := CycleCount + 1;
ELSE
    CycleCount := 0;
END_IF;
END_PROGRAM

CONFIGURATION Config0
    RESOURCE Res0 ON PLC
        TASK Main(INTERVAL := T#50ms, PRIORITY := 0);
        PROGRAM Inst0 WITH Main : SpillwayController;
    END_RESOURCE
END_CONFIGURATION
