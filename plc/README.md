# OpenPLC v3 deployment

Selected source: upstream `thiagoralves/OpenPLC_v3`, immutable commit `b5d41356dab4aeadca0dd7ca64ba542f870b595d`. This archived v3 source is used specifically for its native remote-device Modbus master. This configuration is not for v4.

Before implementation, the following source paths were inspected at this commit:

- `Dockerfile` and `background_installer.sh`: Debian Docker deployment and native dependency/compiler workflow.
- `webserver/scripts/compile_program.sh`: MatIEC invocation, generated Config0/Res0 code and native link steps.
- `webserver/core/main.cpp`: config initialization, 50 ms generated task execution, remote Modbus startup.
- `webserver/core/modbus_master.cpp`: quoted `mbconfig.cfg` syntax, remote I/O offset 100, FC04 reads and FC16 writes, connection retry loop.
- `utils/libmodbus_src/src/modbus-tcp.c`: `modbus_new_tcp` uses a numeric IPv4 address.

Source: https://github.com/thiagoralves/OpenPLC_v3/tree/b5d41356dab4aeadca0dd7ca64ba542f870b595d

## Build and initialization

The Dockerfile builds the native runtime using bundled MatIEC, libmodbus and Snap7, following the compiler workflow in the upstream installer. It uses the upstream DNP3 dummy implementation and removes its unused DNP3 link flags. This avoids the upstream full installer's swap setup, which would otherwise require privileges during image build. EtherCAT and physical I/O are not used. A blank hardware driver adds read-only telemetry; it never supplies inputs or calculates outputs.

`build-runtime.sh` invokes the upstream `compile_program.sh spillway.st`, checks for the executable and generated program type, runs a harness against the generated ST task, and fails on errors. `entrypoint.sh` resolves Docker hostname `device`, verifies the static lab address, writes the v3 master configuration and directly executes the resulting native binary in `/opt/openplc/webserver`. The binary initializes and runs the compiled program without the Python web manager. No web management DB is needed and no manual deployment is required.

The runtime runs as UID 10001 with all capabilities dropped. Its optional real-time scheduling/memory-lock warnings do not require granting capabilities for this simulation. Snap7 is linked as an upstream dependency; no host ports are published. This is an isolated lab runtime, not a hardened production PLC.

## I/O and telemetry

Remote device 0: numeric IP resolved from `device`, port 5020, unit 1, poll period 1000 ms.

| ST variable | Location | Network mapping |
|---|---|---|
| WaterLevelRaw | `%IW100` | FC04 device input register 0, hundredths of percent |
| GatePosition | `%IW101` | FC04 device input register 1, percent |
| GateCommand | `%QW100` | FC16 device holding register 0, percent |

Only this one remote device is configured. v3 appends remote registers beginning at index 100; adding earlier devices or register blocks changes allocation.

The ST thresholds preserve the original specification: below 40 → 0, 40 through 70 → 25, above 70 through 90 → 75, above 90 → 100 with alarm. Task period: 50 ms. `HighLevelAlarm` is computed in ST from the network sensor input. Device DI0 independently reports actual high water.

`%MW0..6` expose level raw, sampled gate, desired gate, alarm (0/1), current mismatch (0/1), saturating mismatch rising-edge counter and wrapping scan counter. The telemetry driver prints these values once a second. No runtime Modbus server is started for telemetry. A transient mismatch may be missed by input sampling, or by 1 Hz logging; the ST counter preserves detected rising edges. Startup mismatches are expected.

To deploy edits: `docker compose up -d --build openplc`. Inspect compiler output during the build and `docker compose logs openplc` afterward. The complete Docker runtime workflow has been verified on Docker Desktop with Linux arm64 containers; see `../docs/verification.md`.

The standalone generated-code harness uses `-O2` to omit unused inline IEC TCP blocks. Without optimization, GCC emitted those unused blocks and failed to link their runtime network helpers. The actual runtime links its complete core and compiled successfully before this harness fix; its controller and network code are unchanged.
