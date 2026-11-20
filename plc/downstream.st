PROGRAM DownstreamController
VAR
    (* Independent field sensor FC04 IR0..4 -> IW100..104. *)
    FlowRaw AT %IW100 : INT;
    WarningLimitRaw AT %IW101 : INT;
    GateObserved AT %IW102 : INT;
    SourceHealthy AT %IW103 : INT;
    SensorHeartbeat AT %IW104 : INT;
    (* PLC1 FC03 MW0..6 -> IW105..111. *)
    P1GateDesired AT %IW107 : INT;
    P1Heartbeat AT %IW111 : INT;
    (* PLC5 native FC03 MW0..13, starting address 1024. *)
    FlowSnapshot AT %MW0 : INT;
    WarningLimitSnapshot AT %MW1 : INT;
    FlowAlarmSnapshot AT %MW2 : INT;
    SensorFreshSnapshot AT %MW3 : INT;
    SensorStaleTicksSnapshot AT %MW4 : INT;
    CycleCount AT %MW5 : UINT;
    P1FreshSnapshot AT %MW6 : INT;
    P1StaleTicksSnapshot AT %MW7 : INT;
    P1DesiredSnapshot AT %MW8 : INT;
    GateObservedSnapshot AT %MW9 : INT;
    SourceHealthySnapshot AT %MW10 : INT;
    GateMismatchSnapshot AT %MW11 : INT;
    SensorHeartbeatSnapshot AT %MW12 : INT;
    P1HeartbeatSnapshot AT %MW13 : INT;
END_VAR
VAR
    SensorSeen : BOOL;
    SensorFresh : BOOL;
    P1Seen : BOOL;
    P1Fresh : BOOL;
    PreviousSensorHeartbeat : INT;
    PreviousP1Heartbeat : INT;
    SensorStaleTicks : INT;
    P1StaleTicks : INT;
    FlowAlarm : BOOL;
END_VAR

(* Each heartbeat advances independently of this controller. *)
(* Allow ~6 s for a missing heartbeat before declaring it stale. *)
IF SensorHeartbeat <> PreviousSensorHeartbeat THEN
    SensorSeen := TRUE;
    SensorStaleTicks := 0;
ELSIF SensorStaleTicks < 120 THEN
    SensorStaleTicks := SensorStaleTicks + 1;
END_IF;
PreviousSensorHeartbeat := SensorHeartbeat;
IF P1Heartbeat <> PreviousP1Heartbeat THEN
    P1Seen := TRUE;
    P1StaleTicks := 0;
ELSIF P1StaleTicks < 120 THEN
    P1StaleTicks := P1StaleTicks + 1;
END_IF;
PreviousP1Heartbeat := P1Heartbeat;
SensorFresh := SensorSeen AND (SensorStaleTicks < 120)
               AND (SourceHealthy <> 0);
P1Fresh := P1Seen AND (P1StaleTicks < 120);

(* Suppress alarms on missing upstream data, report bad quality separately. *)
FlowAlarm := SensorFresh AND (WarningLimitRaw > 0)
             AND (FlowRaw >= WarningLimitRaw);
FlowSnapshot := FlowRaw;
WarningLimitSnapshot := WarningLimitRaw;
FlowAlarmSnapshot := BOOL_TO_INT(FlowAlarm);
SensorFreshSnapshot := BOOL_TO_INT(SensorFresh);
SensorStaleTicksSnapshot := SensorStaleTicks;
P1FreshSnapshot := BOOL_TO_INT(P1Fresh);
P1StaleTicksSnapshot := P1StaleTicks;
P1DesiredSnapshot := P1GateDesired;
GateObservedSnapshot := GateObserved;
SourceHealthySnapshot := SourceHealthy;
GateMismatchSnapshot := BOOL_TO_INT(SensorFresh AND P1Fresh
                        AND (GateObserved <> P1GateDesired));
SensorHeartbeatSnapshot := SensorHeartbeat;
P1HeartbeatSnapshot := P1Heartbeat;

(* Advisory monitoring only: no outputs and no control-side writes. *)
IF CycleCount < 65535 THEN CycleCount := CycleCount + 1;
ELSE CycleCount := 0; END_IF;
END_PROGRAM

CONFIGURATION Config0
    RESOURCE Res0 ON PLC
        TASK Main(INTERVAL := T#50ms, PRIORITY := 0);
        PROGRAM Inst0 WITH Main : DownstreamController;
    END_RESOURCE
END_CONFIGURATION
