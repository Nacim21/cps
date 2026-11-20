# Phase 3: Third independent PLC for temperature monitoring

A new `temperature-sensor` field device is available at `172.28.10.22:5020`,
Modbus unit 1. It accepts **FC04 read-only input registers**, where IR0 is
water temperature in centi-degrees Celsius and IR1 is the alarm threshold in
the same units. This is a synthetic model, not a validated dam thermodynamics
simulation. Its initial temperature, threshold, and optional drift are Compose
variables: `INITIAL_WATER_TEMP_C` (default 24), `WATER_TEMP_ALARM_C` (32), and
`WATER_TEMP_DRIFT_C_PER_S` (0).

`openplc-temp` (`172.28.10.12`) is a separately built native OpenPLC v3 runtime.
It reads both the temperature sensor and PLC1's native status server on port
15020. It tracks PLC1 heartbeat freshness independently of PLC2 and publishes
its own temperature alarm and **advisory** gate setting (0 = none, 75 or 100 =
request). **It never writes the spillway gate or inlet valve.** PLC1 remains
the single spillway actuator writer. Supervisor PLC4 can later arbitrate the
advisory and the spillway control policy.

The HMI adds `temperature` and `plcs.temperature` to the JSON API; old `plc`
combined state remains for compatibility with previous tests and clients. The
experiment reset and structured log exporter now cover eight Compose services.

## Verify

```sh
python -m pytest -q
docker compose config --quiet
docker compose up --build -d
docker compose ps
python3 tests/verify_plc_peer.py
python3 tests/verify_two_plcs.py
python3 tests/verify_temperature_plc.py
curl -s http://127.0.0.1:8080/api/state | python3 -m json.tool
```

Do NOT merge the branch into main until both previous PLCs and PLC3 are verified.
Do not treat an advisory as an actual physical gate command. Only run this
lab on the isolated Docker bridge, never connected to production ICS.
