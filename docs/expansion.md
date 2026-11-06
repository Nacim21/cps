# Two-node dam expansion and read-only HMI

This expansion preserves the existing compiled OpenPLC v3 dam control logic and adds:

1. A second Modbus TCP field node at `inlet:5020` (`172.28.10.21`) with a controllable inlet valve.
2. A physical coupling: the reservoir device reads the inlet valve position over Modbus and calculates the authoritative inflow. It **does not** run a second reservoir model.
3. A read-only web HMI at `http://127.0.0.1:8080` showing both field devices and PLC internal telemetry.
4. New memory snapshots and mismatch counters in the actual Structured Text program.

## Topology

```text
                    +-------------------+
                    |  OpenPLC v3       |
                    |  (172.28.10.10)   |
                    |  ST every 50 ms   |
                    +----------+--------+
                  FC04/FC16    |       +-----------------+
                 +------------+-------|--| UDP telemetry   |
                 |                    |  | to HMI :10555   |
    +------------v---+           +----v---+             |
    | reservoir node |           | inlet  |             |
    | .20:5020       |           | .21:5020             |
    | gate + physics |<-- FC04 --| valve % |             |
    +----------+-----+           +--------+             |
               |                                          |
               +------ Modbus reads -----+                |
                                        |                |
                                +-------v---------------v-+
                                | read-only HMI .40:8080   |
                                | host loopback 127.0.0.1 |
                                +--------------------------+
```

All Modbus device communication remains on the existing `internal: true` Docker bridge. HMI is the *only* published port, bound to the Docker host's loopback interface. The HMI does not expose write endpoints.

## Device register map (zero-based PDU offsets, unit ID 1)

| Node | Modbus function | Address | Meaning | Encoding |
|---|---|---:|---|---|
| reservoir .20 | FC04 read | IR0 | water level | 0..10000 representing 0..100% |
| reservoir .20 | FC04 read | IR1 | actual gate | 0..100% |
| reservoir .20 | FC03 read / FC06,FC16 write | HR0 | gate command | 0..100% |
| inlet .21 | FC04 read | IR0 | actual valve | 0..100% |
| inlet .21 | FC04 read | IR1 | incoming flow | thousandths of reservoir %/s, max 250 |
| inlet .21 | FC03 read / FC06,FC16 write | HR0 | valve command | 0..100% |

Invalid commands outside 0..100 must return Modbus exception 03; unknown registers should return exception 02.

## OpenPLC remote-device memory allocation

OpenPLC's pinned v3 Modbus master assigns input registers sequentially, starting at `%IW100`, and output holding registers starting at `%QW100`, *across* devices in `mbconfig.cfg` order. The first device's two input registers and one output register remain unchanged.

| PLC address | Meaning |
|---|---|
| `%IW100`, `%IW101` | reservoir level and gate feedback |
| `%QW100` | reservoir gate command |
| `%IW102`, `%IW103` | inlet valve feedback and reported flow |
| `%QW101` | inlet valve command |
| `%MW0` .. `%MW6` | original PLC snapshots and cycle / gate mismatch counters |
| `%MW7` | desired inlet valve percentage |
| `%MW8` | actual inlet valve percentage sampled by PLC |
| `%MW9` | sampled inlet flow units (0.001 reservoir %/s) |
| `%MW10` | inlet mismatch flag |
| `%MW11` | inlet mismatch rising-edge counter |

The original gate thresholds are unchanged. The new inlet thresholds are: water above 90% -> valve 0%; above 70% -> valve 50%; otherwise 100%. At the default 65% water level, the expected gate is 25% and inlet is 100%, preserving the original equilibrium.

## Physics

The reservoir remains the authoritative physics simulator. Every physics step it obtains the inlet's *actual* reported position using an internal Modbus read. `inflow = 0.25 * valve_pct / 100` reservoir percentage points/s; outflow is unchanged at `gate_pct / 100` percentage points/s. If the inlet service cannot be reached while INLET_HOST is configured, inlet flow fails closed to zero and a connection-loss event is logged. Without INLET_HOST, the old standalone device remains compatible with the original tests.

The controller executes the ST scan every 50 ms but polls Modbus devices every ~1 second. A transient modified command may be overwritten before the physics step. Modbus history and PCAP remain essential for short-lived events. UDP telemetry is sampled once a second and is best-effort, so it is **not** a complete 20 Hz control trace.

## Run and verify

```sh
cp .env.example .env
# if already present, keep your existing .env
docker compose config --quiet
docker compose up --build -d
docker compose ps
python3 tests/verify_expansion.py
python3 tests/verify_openplc.py
```

Then open `http://127.0.0.1:8080` on the same computer running Docker Desktop. HMI JSON is available from `http://127.0.0.1:8080/api/state` for future read-only fuzzing observations.

The initial OpenPLC build compiles its pinned upstream runtime and can be lengthy; rebuild only changed services after the first build.

Run the standard test suite to catch regressions:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-test.txt
.venv/bin/python -m pytest -q
```

Capture logs: `docker compose logs --no-color --timestamps openplc device inlet hmi > captures/expansion.log`.

Reset: `docker compose down` followed by `docker compose up -d`. The services currently keep process state in memory and reset to default values when containers are recreated. An existing `docker compose up -d` without recreate does not reset state.

## Limitations

- Deployment has been code-reviewed and syntax/unit-tested; the expanded Docker integration must be verified on a machine with Docker. The pinned OpenPLC native build is not available in this patch-generation environment.
- This is a training and research simulation, not a real industrial process model or production HMI.
- Internal Modbus is intentionally unauthenticated for controlled lab evaluation. Do not publish its ports or connect it to live industrial networks.
- The HMI is read-only. It does not implement alarm acknowledgment, historical storage, authentication, or operator controls.
- For rigorous experiments, log individual fuzzer inputs and PLC/network events. The 1 Hz UDP snapshots alone will miss some transient state changes.
