# OpenPLC Modbus dam lab

An isolated educational reservoir simulation with a **real OpenPLC v3 runtime** executing `plc/spillway.st`, a PyModbus field device, and an idle Scapy attacker. No industrial hardware or credentials are involved. Modbus is intentionally unauthenticated.

## Verification status

Verified on Docker Desktop (Linux arm64): all images build, all three services start, OpenPLC executes compiled ST and exchanges mapped I/O through Modbus, explicit unauthorized reads/writes succeed, and cyclic control restores the injected gate command. Device restart/reconnection and an 80-packet PCAP were also verified. The Python protocol suite passes 15 tests. See `docs/verification.md` for evidence, the Linux harness linker fix, and remaining platform limits.

## Build and run

Requirements: Docker Engine with Compose v2, or Docker Desktop, and network access during builds to fetch pinned source and packages. Reserve subnet `172.28.10.0/24`; adjust all mapping and target restrictions together if it conflicts with another network. From this folder:

```sh
cp .env.example .env
docker compose config
docker compose up --build -d
docker compose ps
docker compose logs -f openplc device
```

The first build compiles bundled MatIEC and native OpenPLC dependencies, then compiles the ST program into the actual `core/openplc` executable. Compilation errors fail the image build. Startup automatically loads the fixed remote-device configuration and executes that binary, which runs its ST task every 50 ms and polls the device every second. There is no web UI, manual upload, Python controller, or host port publication. The upstream optional real-time scheduling attempt may warn under dropped capabilities; this simulation uses normal scheduling. `memlock: 0` prevents partial memory locking from starving runtime threads.

At the default 65% level, expect device `gate_command_accepted` events with `function:16, gate:25`, OpenPLC `st_state` telemetry with `level_raw` near 6500 and `desired:25`, and device physics logs. `%MW6` is a scan counter. The initial startup gate can be 0 until the first input exchange. OpenPLC's native remote-device loop retries failed connections.

## Explicit experiments

Start capture first (see `docs/wireshark.md`), then run:

```sh
docker compose exec attacker python unauthorized_read.py
docker compose exec attacker python unauthorized_write.py --target device --port 5020 --gate 100
docker compose logs --since 30s device openplc
```

The write uses its own TCP connection, FC06, unit 1, address 0, value 100. A successful attack prints the matching server echo. The device logs every accepted command, including previous/new values and function code, and retains the last 1000 commands in its in-process history. Export durable experiment evidence with:

```sh
docker compose logs --no-color --timestamps device openplc > captures/experiment.log
```

OpenPLC continues cyclic FC16 writes and normally restores 25% within approximately one polling interval. An injected command may have little or no physical effect between discrete simulation steps. Its accepted transition and subsequent restoration remain in device logs and PCAP. ST mismatch telemetry can detect sampled discrepancies; it cannot guarantee detection of a change between input samples. Startup or threshold transitions also produce mismatches, so the counter alone is not proof of an attack. No controller logic is disabled to preserve an injected value.

The attacker rejects every destination except `device` / `172.28.10.20` on port 5020, checks DNS results, and connects to the checked numeric IP. It has no raw-socket capabilities. No attacks run at startup.

## Tests

The actual `spillway.st` has also been compiled with the pinned source's MatIEC compiler and its generated C code executed in a native harness. That verifies thresholds, mapped input/output variables, alarm behavior, continuing cyclic output and mismatch counting. The image build runs the same harness. To reproduce separately with a checkout whose MatIEC compiler is already built:

```sh
python3 tests/verify_st.py --openplc-source /path/to/OpenPLC_v3
```

This harness supplies test input images; it does not verify the runtime's network mapping or replace the deployed PLC.

Portable device/protocol tests (Python 3.12 recommended; also executed on the available Python 3.9.6 host):

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-test.txt
.venv/bin/python -m pytest -q
```

The tests intentionally use ephemeral localhost ports; the public attacker CLI still restricts destinations to the Docker device. They do not substitute for ST execution. With Compose running, explicitly run the OpenPLC acceptance experiment:

```sh
python3 tests/verify_openplc.py
```

This triggers one authorized lab experiment (read and write), checks advancing ST telemetry and legitimate FC16 writes, then verifies an FC06 acceptance and subsequent FC16 restoration. It fails if those events are absent. For connection recovery:

```sh
docker compose stop device
sleep 3
docker compose start device
docker compose logs --since 30s openplc device
python3 tests/verify_openplc.py
```

Stop and reset volatile reservoir state:

```sh
docker compose down
docker compose up -d
```

Remove containers and network after the experiment with `docker compose down --remove-orphans`. Captures remain on the host. No volumes are required for PLC deployment; change ST and rebuild `openplc` to deploy a new program.

See `plc/README.md`, `docs/register-map.md`, `docs/architecture.md`, `docs/threat-model.md`, and `docs/wireshark.md` for implementation details.
