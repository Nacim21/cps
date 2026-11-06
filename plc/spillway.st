PROGRAM SpillwayController
VAR
    (* Device 0: existing reservoir. Keep its current memory mapping. *)
    WaterLevelRaw AT %IW100 : INT;
    GatePosition AT %IW101 : INT;
    GateCommand AT %QW100 : INT;
    (* Device 1: independent inlet Modbus node. *)
    InletPosition AT %IW102 : INT;
    InletFlowRaw AT %IW103 : INT;
    InletCommand AT %QW101 : INT;
    (* Existing internal snapshots and counters. *)
    LevelSnapshot AT %MW0 : INT;
    GateSnapshot AT %MW1 : INT;
    DesiredSnapshot AT %MW2 : INT;
    AlarmSnapshot AT %MW3 : INT;
    MismatchSnapshot AT %MW4 : INT;
    MismatchCount AT %MW5 : UINT;
    CycleCount AT %MW6 : UINT;
    (* New inlet snapshots and mismatch tracking. *)
    InletDesiredSnapshot AT %MW7 : INT;
    InletPositionSnapshot AT %MW8 : INT;
    InletFlowSnapshot AT %MW9 : INT;
    InletMismatchSnapshot AT %MW10 : INT;
    InletMismatchCount AT %MW11 : UINT;
END_VAR
VAR
    WaterLevel : REAL;
    HighLevelAlarm : BOOL;
    PreviousMismatch : BOOL;
    Mismatch : BOOL;
    PreviousInletMismatch : BOOL;
    InletMismatch : BOOL;
END_VAR

WaterLevel := INT_TO_REAL(WaterLevelRaw) / 100.0;
HighLevelAlarm := WaterLevel > 90.0;
(* Preserve the original spillway control thresholds. *)
IF WaterLevel > 90.0 THEN
    GateCommand := 100;
ELSIF WaterLevel > 70.0 THEN
    GateCommand := 75;
ELSIF WaterLevel >= 40.0 THEN
    GateCommand := 25;
ELSE
    GateCommand := 0;
END_IF;
(* Restrict incoming water when the reservoir becomes high. *)
IF WaterLevel > 90.0 THEN
    InletCommand := 0;
ELSIF WaterLevel > 70.0 THEN
    InletCommand := 50;
ELSE
    InletCommand := 100;
END_IF;

Mismatch := GatePosition <> GateCommand;
IF Mismatch AND NOT PreviousMismatch THEN
    IF MismatchCount < 65535 THEN
        MismatchCount := MismatchCount + 1;
    END_IF;
END_IF;
PreviousMismatch := Mismatch;
InletMismatch := InletPosition <> InletCommand;
IF InletMismatch AND NOT PreviousInletMismatch THEN
    IF InletMismatchCount < 65535 THEN
        InletMismatchCount := InletMismatchCount + 1;
    END_IF;
END_IF;
PreviousInletMismatch := InletMismatch;
LevelSnapshot := WaterLevelRaw;
GateSnapshot := GatePosition;
DesiredSnapshot := GateCommand;
AlarmSnapshot := BOOL_TO_INT(HighLevelAlarm);
MismatchSnapshot := BOOL_TO_INT(Mismatch);
InletDesiredSnapshot := InletCommand;
InletPositionSnapshot := InletPosition;
InletFlowSnapshot := InletFlowRaw;
InletMismatchSnapshot := BOOL_TO_INT(InletMismatch);
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
