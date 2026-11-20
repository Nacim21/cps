PROGRAM InletController
VAR
    WaterLevelRaw AT %IW100 : INT;
    InletPosition AT %IW101 : INT;
    InletFlowRaw AT %IW102 : INT;
    InletCommand AT %QW100 : INT;
    (* Remote PLC1 %MW2..6, read through Modbus FC03 at 1026..1030. *)
    PeerGateDesired AT %IW103 : INT;
    PeerAlarm AT %IW104 : INT;
    PeerHeartbeat AT %IW107 : INT;
    LevelSnapshot AT %MW0 : INT;
    InletDesiredSnapshot AT %MW1 : INT;
    InletPositionSnapshot AT %MW2 : INT;
    InletFlowSnapshot AT %MW3 : INT;
    InletMismatchSnapshot AT %MW4 : INT;
    InletMismatchCount AT %MW5 : UINT;
    CycleCount AT %MW6 : UINT;
    PeerGateSnapshot AT %MW7 : INT;
    PeerAlarmSnapshot AT %MW8 : INT;
    PeerFreshSnapshot AT %MW9 : INT;
    PeerStaleTicksSnapshot AT %MW10 : INT;
    PeerHeartbeatSnapshot AT %MW11 : INT;
END_VAR
VAR
    WaterLevel : REAL;
    Mismatch : BOOL;
    PreviousMismatch : BOOL;
    PeerSeen : BOOL;
    PeerFresh : BOOL;
    PreviousHeartbeat : INT;
    PeerStaleTicks : INT;
END_VAR

WaterLevel := INT_TO_REAL(WaterLevelRaw) / 100.0;
IF WaterLevel > 90.0 THEN
    InletCommand := 0;
ELSIF WaterLevel > 70.0 THEN
    InletCommand := 50;
ELSE
    InletCommand := 100;
END_IF;

(* The peer scan counter changes once a second via FC03 polling. *)
(* A frozen heartbeat can indicate a stopped PLC or broken network link. *)
IF PeerHeartbeat <> PreviousHeartbeat THEN
    PeerSeen := TRUE;
    PeerStaleTicks := 0;
ELSIF PeerStaleTicks < 120 THEN
    PeerStaleTicks := PeerStaleTicks + 1;
END_IF;
PreviousHeartbeat := PeerHeartbeat;
PeerFresh := PeerSeen AND (PeerStaleTicks < 120);

(* Model-only coordination policy: if PLC1 requests a wide gate opening,
   limit inlet flow further. Missing PLC1 heartbeat closes the inlet. *)
IF NOT PeerFresh THEN
    InletCommand := 0;
ELSIF PeerAlarm <> 0 THEN
    InletCommand := 0;
ELSIF PeerGateDesired >= 75 AND InletCommand > 25 THEN
    InletCommand := 25;
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
PeerGateSnapshot := PeerGateDesired;
PeerAlarmSnapshot := PeerAlarm;
PeerFreshSnapshot := BOOL_TO_INT(PeerFresh);
PeerStaleTicksSnapshot := PeerStaleTicks;
PeerHeartbeatSnapshot := PeerHeartbeat;
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
