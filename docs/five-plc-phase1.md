# Five-PLC environment expansion: Phase 1 (two independent runtimes)

This phase separates the original single OpenPLC program into two independently
compiled and independently running IEC 61131-3 controllers.

- `openplc` at `172.28.10.10`: spillway PLC. Reads reservoir IR0..1 and writes
  only reservoir gate HR0 (FC16).
- `openplc-inlet` at `172.28.10.11`: inlet PLC. Reads reservoir IR0 and inlet
  IR0..1, and writes only inlet valve HR0 (FC16).
- The reservoir and inlet remain separate **simulated field devices**; they are
  not PLCs. The HMI receives independent best-effort UDP telemetry from both PLCs.
- Normal control has a single writer per field actuator. Both PLCs use the
  same reservoir sensor, creating a shared physical-process dependency.

## Important limitation

The controllers are now independent, but **direct PLC-to-PLC Modbus messaging
is not yet implemented**. Both currently read the common reservoir sensor.
That explicit PLC-to-PLC dependency is the next phase, followed by additional
controllers for temperature, supervisory coordination, and downstream flow.
The IP layer/network impairment experiments are future phases too.

## Run and verify

From a clean five-PLC development branch after installing the phase:

```bash
source .venv/bin/activate
python -m pytest -q
deactivate
docker compose config --quiet
docker compose up --build -d
docker compose ps
python3 tests/verify_expansion.py
curl -s http://127.0.0.1:8080/api/state
```

Expected `docker compose ps`: six services (`openplc`, `openplc-inlet`,
`device`, `inlet`, `hmi`, `attacker`). The HMI API keeps legacy `plc` combined
fields and adds `plcs.spillway` and `plcs.inlet`, each with an independent
online status and scan counter.

```bash
docker compose logs --tail=30 openplc openplc-inlet
python3 scripts/reset_experiment.py --method baseline --seed 2026
```

Stop if the independent inlet controller fails compilation, the HMI reports
`plcs.inlet.online=false`, or the reset script cannot reach a good baseline.
Do not merge to main until runtime tests pass. This lab must remain isolated
and must not be connected to production industrial control networks.
