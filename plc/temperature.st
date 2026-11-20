PROGRAM TemperatureController
VAR
    (* Input registers from the independent temperature sensor, units = 0.01 C. *)
    TemperatureRaw AT %IW100 : INT;
    AlarmThresholdRaw AT %IW101 : INT;
    (* PLC1 native Modbus FC03 %MW2..6 copied into this runtime's inputs. *)
    PeerGateDesired AT %IW102 : INT;
    PeerAlarm AT %IW103 : INT;
    PeerHeartbeat AT %IW106 : INT;
    (* Read-only status and advisory, exposed on PLC3's native Modbus server. *)
    TemperatureSnapshot AT %MW0 : INT;
    TemperatureAlarmSnapshot AT %MW1 : INT;
    GateAdvisorySnapshot AT %MW2 : INT;
    PeerFreshSnapshot AT %MW3 : INT;
    PeerStaleTicksSnapshot AT %MW4 : INT;
    CycleCount AT %MW5 : UINT;
    PeerHeartbeatSnapshot AT %MW6 : INT;
END_VAR
VAR
    PeerSeen : BOOL;
    PeerFresh : BOOL;
    PreviousHeartbeat : INT;
    PeerStaleTicks : INT;
    TemperatureAlarm : BOOL;
END_VAR

(* Alarm derives from the sensor-provided temperature and threshold. *)
TemperatureAlarm := TemperatureRaw >= AlarmThresholdRaw;
TemperatureSnapshot := TemperatureRaw;
TemperatureAlarmSnapshot := BOOL_TO_INT(TemperatureAlarm);

(* Advisory ONLY. Neither PLC3 nor the HMI writes the spillway gate. *)
IF TemperatureRaw >= 3500 THEN
    GateAdvisorySnapshot := 100;
ELSIF TemperatureAlarm THEN
    GateAdvisorySnapshot := 75;
ELSE
    GateAdvisorySnapshot := 0;
END_IF;

(* PLC1 heartbeat is polled once/sec; 120 x 50 ms scans = about 6 s timeout. *)
IF PeerHeartbeat <> PreviousHeartbeat THEN
    PeerSeen := TRUE;
    PeerStaleTicks := 0;
ELSIF PeerStaleTicks < 120 THEN
    PeerStaleTicks := PeerStaleTicks + 1;
END_IF;
PreviousHeartbeat := PeerHeartbeat;
PeerFresh := PeerSeen AND (PeerStaleTicks < 120);
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
        PROGRAM Inst0 WITH Main : TemperatureController;
    END_RESOURCE
END_CONFIGURATION
