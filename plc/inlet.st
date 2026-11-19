PROGRAM InletController
VAR
    WaterLevelRaw AT %IW100 : INT;
    InletPosition AT %IW101 : INT;
    InletFlowRaw AT %IW102 : INT;
    InletCommand AT %QW100 : INT;
    LevelSnapshot AT %MW0 : INT;
    InletDesiredSnapshot AT %MW1 : INT;
    InletPositionSnapshot AT %MW2 : INT;
    InletFlowSnapshot AT %MW3 : INT;
    InletMismatchSnapshot AT %MW4 : INT;
    InletMismatchCount AT %MW5 : UINT;
    CycleCount AT %MW6 : UINT;
END_VAR
VAR
    WaterLevel : REAL;
    Mismatch : BOOL;
    PreviousMismatch : BOOL;
END_VAR

WaterLevel := INT_TO_REAL(WaterLevelRaw) / 100.0;
IF WaterLevel > 90.0 THEN
    InletCommand := 0;
ELSIF WaterLevel > 70.0 THEN
    InletCommand := 50;
ELSE
    InletCommand := 100;
END_IF;

Mismatch := InletPosition <> InletCommand;
IF Mismatch AND NOT PreviousMismatch THEN
    IF InletMismatchCount < 65535 THEN
        InletMismatchCount := InletMismatchCount + 1;
    END_IF;
END_IF;
PreviousMismatch := Mismatch;
LevelSnapshot := WaterLevelRaw;
InletDesiredSnapshot := InletCommand;
InletPositionSnapshot := InletPosition;
InletFlowSnapshot := InletFlowRaw;
InletMismatchSnapshot := BOOL_TO_INT(Mismatch);
IF CycleCount < 65535 THEN
    CycleCount := CycleCount + 1;
ELSE
    CycleCount := 0;
END_IF;
END_PROGRAM

CONFIGURATION Config0
    RESOURCE Res0 ON PLC
        TASK Main(INTERVAL := T#50ms, PRIORITY := 0);
        PROGRAM Inst0 WITH Main : InletController;
    END_RESOURCE
END_CONFIGURATION
