PROGRAM SupervisoryController
VAR
    (* PLC1 FC03 MW0..12 -> local input registers 100..112. *)
    P1Level AT %IW100 : INT;
    P1GateDesired AT %IW102 : INT;
    P1HighWater AT %IW103 : INT;
    P1Heartbeat AT %IW106 : INT;
    P1LocalGate AT %IW112 : INT;
    (* PLC2 FC03 MW0..6 -> 113..119. *)
    P2InletDesired AT %IW114 : INT;
    P2Heartbeat AT %IW119 : INT;
    (* PLC3 FC03 MW0..6 -> 120..126. *)
    P3TemperatureRaw AT %IW120 : INT;
    P3TemperatureAlarm AT %IW121 : INT;
    P3GateAdvisory AT %IW122 : INT;
    P3PeerFresh AT %IW123 : INT;
    P3Heartbeat AT %IW125 : INT;
    (* Native PLC4 holding register snapshots, FC03 starting at 1024. *)
    SelectedGate AT %MW0 : INT;
    DecisionReason AT %MW1 : INT;
    DecisionValid AT %MW2 : INT;
    CycleCount AT %MW3 : UINT;
    P1FreshSnapshot AT %MW4 : INT;
    P2FreshSnapshot AT %MW5 : INT;
    P3FreshSnapshot AT %MW6 : INT;
    TemperatureAlarmSnapshot AT %MW7 : INT;
    TemperatureAdvisorySnapshot AT %MW8 : INT;
    LocalGateSnapshot AT %MW9 : INT;
    InletCommandSnapshot AT %MW10 : INT;
    HealthyPeerCount AT %MW11 : INT;
END_VAR
VAR
    P1Seen : BOOL;
    P2Seen : BOOL;
    P3Seen : BOOL;
    P1Fresh : BOOL;
    P2Fresh : BOOL;
    P3Fresh : BOOL;
    LastP1 : INT;
    LastP2 : INT;
    LastP3 : INT;
    StaleP1 : INT;
    StaleP2 : INT;
    StaleP3 : INT;
END_VAR

(* Every PLC has its own independent heartbeat; 120 scans x 50ms ~= 6s. *)
IF P1Heartbeat <> LastP1 THEN P1Seen := TRUE; StaleP1 := 0;
ELSIF StaleP1 < 120 THEN StaleP1 := StaleP1 + 1; END_IF;
IF P2Heartbeat <> LastP2 THEN P2Seen := TRUE; StaleP2 := 0;
ELSIF StaleP2 < 120 THEN StaleP2 := StaleP2 + 1; END_IF;
IF P3Heartbeat <> LastP3 THEN P3Seen := TRUE; StaleP3 := 0;
ELSIF StaleP3 < 120 THEN StaleP3 := StaleP3 + 1; END_IF;
LastP1 := P1Heartbeat;
LastP2 := P2Heartbeat;
LastP3 := P3Heartbeat;
P1Fresh := P1Seen AND (StaleP1 < 120);
P2Fresh := P2Seen AND (StaleP2 < 120);
P3Fresh := P3Seen AND (StaleP3 < 120);
P1FreshSnapshot := BOOL_TO_INT(P1Fresh);
P2FreshSnapshot := BOOL_TO_INT(P2Fresh);
P3FreshSnapshot := BOOL_TO_INT(P3Fresh);
HealthyPeerCount := BOOL_TO_INT(P1Fresh) + BOOL_TO_INT(P2Fresh) + BOOL_TO_INT(P3Fresh);
TemperatureAlarmSnapshot := P3TemperatureAlarm;
TemperatureAdvisorySnapshot := P3GateAdvisory;
LocalGateSnapshot := P1LocalGate;
InletCommandSnapshot := P2InletDesired;

(* Priority: valid high-water alarm > temperature advisory > local gate. *)
(* PLC1 remains the only gate writer. PLC4 only provides an FC03 decision. *)
DecisionValid := 0;
DecisionReason := 0;  (* 0=missing PLC1, 1=local, 2=temp, 3=high-water *)
SelectedGate := 0;
IF P1Fresh AND (P1LocalGate >= 0) AND (P1LocalGate <= 100) THEN
    DecisionValid := 1;
    SelectedGate := P1LocalGate;
    DecisionReason := 1;
    IF P1HighWater <> 0 THEN
        SelectedGate := 100;
        DecisionReason := 3;
    ELSIF P3Fresh AND (P3PeerFresh <> 0) AND (P3TemperatureAlarm <> 0)
        AND (P3GateAdvisory >= 0) AND (P3GateAdvisory <= 100)
        AND (P3GateAdvisory > SelectedGate) THEN
        SelectedGate := P3GateAdvisory;
        DecisionReason := 2;
    END_IF;
END_IF;

IF CycleCount < 65535 THEN CycleCount := CycleCount + 1;
ELSE CycleCount := 0; END_IF;
END_PROGRAM

CONFIGURATION Config0
    RESOURCE Res0 ON PLC
        TASK Main(INTERVAL := T#50ms, PRIORITY := 0);
        PROGRAM Inst0 WITH Main : SupervisoryController;
    END_RESOURCE
END_CONFIGURATION
