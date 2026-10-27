PROGRAM SpillwayController
VAR
    WaterLevelRaw AT %IW100 : INT;
    GatePosition AT %IW101 : INT;
    GateCommand AT %QW100 : INT;
    LevelSnapshot AT %MW0 : INT;
    GateSnapshot AT %MW1 : INT;
    DesiredSnapshot AT %MW2 : INT;
    AlarmSnapshot AT %MW3 : INT;
    MismatchSnapshot AT %MW4 : INT;
    MismatchCount AT %MW5 : UINT;
    CycleCount AT %MW6 : UINT;
END_VAR
VAR
    WaterLevel : REAL;
    HighLevelAlarm : BOOL;
    PreviousMismatch : BOOL;
    Mismatch : BOOL;
END_VAR

WaterLevel := INT_TO_REAL(WaterLevelRaw) / 100.0;
HighLevelAlarm := WaterLevel > 90.0;
IF WaterLevel > 90.0 THEN
    GateCommand := 100;
ELSIF WaterLevel > 70.0 THEN
    GateCommand := 75;
ELSIF WaterLevel >= 40.0 THEN
    GateCommand := 25;
ELSE
    GateCommand := 0;
END_IF;
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
