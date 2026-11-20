# Phase 2: Native PLC-to-PLC Modbus TCP dependency

PLC1 (`openplc`, 172.28.10.10) starts OpenPLC v3's native server on TCP 15020 via its localhost-only interactive control socket 43628. **This server is internal to Docker only**, not published to the host. The TCP server is unprotected by Modbus authentication, as in the existing isolated testbed.

PLC2 (`openplc-inlet`, 172.28.10.11) remains a Modbus master of the inlet valve, but additionally acts as a Modbus client to PLC1, polling the native PLC1 server each second. PLC1 remains Modbus client of the reservoir. This is genuine PLC-to-PLC communications, not an HMI proxy.

## Register contract (zero-based PDU addresses)

| PLC1 internal variable | Native Modbus holding address | PLC2 mapped input |
| --- | --- | --- |
| `%MW2` Gate desired | 1026 | `%IW103` |
| `%MW3` High-level alarm | 1027 | `%IW104` |
| `%MW4` Gate mismatch | 1028 | `%IW105` (reserved) |
| `%MW5` Mismatch count | 1029 | `%IW106` (reserved) |
| `%MW6` Scan counter (heartbeat) | 1030 | `%IW107` |

`%IW100` is the independent reservoir reading; `%IW101..102` are inlet status.

## Control policy for simulated dam

- Below 70% water level, PLC2 requests 100% inlet if the peer is fresh.
- Over 70% water level and PLC1 requests at least 75% gate opening, PLC2 limits inlet to 25% (model-only coordination behavior).
- If PLC1 announces high-water alarm, inlet command is 0%.
- If PLC1's heartbeat does not advance for 120 PLC2 scans (nominally 6s at 50ms), PLC2 requests 0% inlet and reports `peer_fresh=0`.
- Once the heartbeat advances, PLC2 returns to normal coordinated control.

The heartbeat distinguishes an advancing peer from stale Modbus buffers, including cases where the Modbus master silently keeps the last valid input value after a timeout. The peer server is reachable only inside the isolated Docker network, but *all PLC1 Modbus holding registers remain writable by clients on that network*. Do not connect this educational lab to real equipment.

## Verify after installing

```bash
source .venv/bin/activate
python -m pytest -q
deactivate
docker compose config --quiet
docker compose up --build -d
docker compose ps
python3 tests/verify_plc_peer.py
python3 tests/verify_two_plcs.py
python3 scripts/reset_experiment.py --method baseline --seed 2026
```

To inspect the peer's observed status:

```bash
curl -s http://127.0.0.1:8080/api/state | python3 -m json.tool
```

Look at `plcs.inlet.internal.peer_fresh`, `peer_gate_desired`, `peer_alarm`, `peer_stale_ticks`. The remote server logs should contain `modbus_server_started`. In a future controlled failure trial, stop PLC1, observe PLC2's fallback response, restart PLC1, and reset before subsequent experiments. Do not interpret an initial mismatch count as attack evidence.
