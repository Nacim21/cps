# Phase 4: Supervisory PLC and safe gate arbitration

All infrastructure in this project is a synthetic and isolated Docker lab.

- PLC1 spillway `.10`: **only** writer of Modbus reservoir gate, using its local water-level policy as the lower bound. Publishes independent local gate request at `%MW12`.
- PLC2 inlet `.11`: remains only writer of inlet valve; exposes read-only state to PLC4 via native Modbus TCP 15020.
- PLC3 temperature `.12`: reads independent synthetic Modbus sensor, publishes advisory and alarm. Exposes read-only state to PLC4.
- PLC4 supervisory `.13`: polls PLC1 `%MW0..12`, PLC2 `%MW0..6`, PLC3 `%MW0..6` using native FC03. Outputs status and a selected gate target at `%MW0..3`. Never writes to any field-device actuator.
- PLC1 consumes PLC4 FC03 `%MW0..3` as read-only input. If valid and fresh, it widens the gate if necessary. If PLC4 fails, PLC1 reverts to its local policy within roughly six seconds after missing heartbeats. High water local logic always dominates any lower supervisor request.

## Priority policy

1. If PLC1 is stale, `decision_valid=0`, `decision_reason=0` and no remote arbitration is trusted.
2. With healthy PLC1, high-water alarm requires 100% gate (`reason=3`).
3. Otherwise, a fresh PLC3 high-temperature advisory may raise (never reduce) PLC1's local request (`reason=2`).
4. Otherwise, use PLC1's local request (`reason=1`).
5. PLC2 availability is observed and reported, but does not change gate priority during Phase 4.

## Verification

```sh
python -m pytest -q
docker compose config --quiet
docker compose up --build -d
docker compose ps
python3 tests/verify_supervisor_plc.py
python3 tests/verify_plc_peer.py
python3 tests/verify_temperature_plc.py
```

Record baseline and controlled 36C scenario only after runtime checks pass. Example:

```sh
INITIAL_WATER_TEMP_C=36 docker compose up -d --no-deps --force-recreate temperature-sensor
sleep 8
curl -s http://127.0.0.1:8080/api/state | python3 -m json.tool
python3 scripts/reset_experiment.py --method baseline --seed 2026
```

At 36C expect the sensor alarm 1, PLC3 advisory 100, PLC4 selected gate 100 with reason 2, and PLC1 applied gate 100. Once reset the sensor returns to 24C, PLC4 selected and PLC1 applied gate return to nominal 25 at 65% reservoir level. These expectations need verification against the user's Docker runtime. This is not a hardware safety controller and does not establish protection for a real dam.
