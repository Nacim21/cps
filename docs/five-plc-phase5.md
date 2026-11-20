# Phase 5: Independent downstream discharge monitoring

This is a Docker-only, synthetic CPS lab, not a calibrated dam or hardware safety system.

## Architecture

- PLC 1 (.10) remains the only reservoir spillway gate writer.
- PLC 2 (.11) remains the only inlet valve writer.
- PLC 3 (.12) monitors temperature and sends advice to PLC 4.
- PLC 4 (.13) arbitrates, but is read-only with respect to field actuators.
- **PLC 5 (.14)** runs a separate OpenPLC v3 instance. It monitors discharge
  and its source quality and compares actual gate observation against PLC 1.
- **Downstream field sensor (.23)** exposes FC04 input registers at port 5020.
  It reads reservoir FC04 IR0..1 only. It never sends gate writes.

## Model and Modbus map

The discharge estimate, in **m³/s**, is illustrative rather than experimentally
calibrated: `Q = clamp(MAX_DISCHARGE_M3S * gate_pct/100 * sqrt(level_pct/65) + bias, 0,1000)`.
With defaults `MAX_DISCHARGE_M3S=200`, warning=150, and bias=0, at
65% reservoir level, a 25% gate gives ~50 m³/s while a 100% gate gives ~200 m³/s.
Do **not** interpret these as actual hydraulic engineering quantities.

| Sensor FC04 register | Meaning |
|---|---|
| IR0 | Estimated flow, tenths of m³/s |
| IR1 | Configured flow-warning threshold, tenths of m³/s |
| IR2 | Observed spillway gate, percent |
| IR3 | Upstream reservoir Modbus source is healthy (0/1) |
| IR4 | Independent sensor heartbeat (uint16, wraps) |

PLC 5 polls sensor FC04 IR0..4 and PLC 1 native FC03 MW0..6.
PLC 5 exposes a native FC03 register set MW0..13, including flow, threshold,
flow alarm, sensor/PLC1 freshness, gate disagreement, and heartbeats.
A 120-scan timeout (~6 s at 50 ms scan) detects a frozen sensor or PLC1.
If source quality is bad or sensor freshness expires, the alarm is suppressed
and sensor_fresh=0, **not** silently treated as a true safe condition.
PLC 5 has no `%QW`/`%QX` outputs and changes neither the gate nor the inlet.

## Verification

```sh
python -m pytest -q
docker compose config --quiet
docker compose build openplc-downstream downstream-sensor
docker compose up --build -d
docker compose ps
python3 tests/verify_downstream_plc.py
python3 tests/verify_supervisor_plc.py
python3 tests/verify_temperature_plc.py
```

On normal baseline the new sensor reports ~50 m³/s and alarm=0, while
all five PLC telemetry records are online. For a controlled alarm scenario:

```sh
INITIAL_WATER_TEMP_C=36 docker compose up -d --no-deps --force-recreate temperature-sensor
sleep 12
python3 tests/verify_downstream_plc.py --expect-alarm
python3 scripts/reset_experiment.py --method baseline --seed 2026
python3 tests/verify_downstream_plc.py
```

A separate isolated high-flow sensor-bias case, useful for fuzzing without
actuating the gate, is possible using Compose environment overrides:
`DOWNSTREAM_FLOW_BIAS_M3S=125 docker compose up -d --no-deps --force-recreate downstream-sensor`.
Afterwards, reset the experiment to remove the bias and restore comparability.
The HMI remains read-only, on host loopback; Compose keeps field networks isolated.
