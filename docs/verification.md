# Verification record

## Docker Desktop: verified, Linux arm64

- `docker compose --progress plain build openplc`: succeeded. The real OpenPLC runtime and generated ST harness both compile; the harness prints PASS.
- `docker compose up --build -d`: succeeded for openplc, device and attacker. `docker compose ps` reports all three running, with no published ports.
- `docker compose config --quiet`: passed.
- `python3 tests/verify_openplc.py`: passed before and after restarting the field device, and while packet capture was running.
- Native ST telemetry advances 20 scans per second, receives water level through `%IW100`, reports actual gate through `%IW101`, and calculates desired output 25% through `%QW100` at the baseline level.
- Device logs show native OpenPLC FC04 input reads and FC16 gate writes. The explicitly triggered attacker FC04 reads succeed; its FC06 write changes the gate from 25 to 100. The subsequent OpenPLC FC16 write restores 25.
- Runtime telemetry recorded `gate:100, desired:25, mismatch:1` and an incremented mismatch counter following the injected command.
- Device stop/start succeeds; OpenPLC logs disconnection and successful reconnection, then resumes real Modbus operation. Initial startup also logged connection refused followed by a successful retry.
- The documented NET_RAW-only capture helper in the device network namespace captured 80 packets, zero kernel drops. `captures/modbus.pcap` is 7185 bytes. Scapy inspection confirmed source .10 FC04/FC16 requests and source .30 FC04/FC06 requests, including gate value 100.
- Exported device and runtime logs are in `captures/experiment.log`. The stopped capture helper was removed. Application services remain running for inspection.

## Build failure and fix

The initial Docker reproduction successfully built MatIEC and linked the complete native runtime. Its separate standalone generated-code harness then failed under GCC with undefined references to `connect_to_tcp_server`, `send_tcp_message` and `receive_tcp_message`.

At the default optimization level, GCC emits unused inline standard IEC TCP block code which refers to helpers provided by the runtime's full core. Those helpers are not linked into the standalone harness. Building the harness with `-O2` removes those unused inline blocks and preserves all asserted controller tests. This change applies to both `plc/build-runtime.sh` and `tests/verify_st.py`; the deployed ST control logic and actual runtime link are unchanged. The full Docker rebuild and live acceptance checks pass after this fix. The Automake/configure warnings in the initial output were not the fatal error.

## Other executed checks

- Inspected OpenPLC v3 source at commit `b5d41356dab4aeadca0dd7ca64ba542f870b595d` for Docker, compilation, master configuration and I/O mapping before implementation.
- Built its actual MatIEC compiler on macOS arm64 and compiled `plc/spillway.st` with upstream flags. Fixed a compiler requirement to separate located and local variable declaration blocks.
- Executed generated Config0/Res0 code in `tests/st_harness.cpp`, on the host and during the Linux Docker build. Tested 0%, 39.99%, 40%, 65%, 70%, 70.01%, 90%, 90.01%, 100%; asserted mapped output, alarm, snapshots, cyclic execution and mismatch rising-edge counter.
- Python protocol/physics suite: **15 passed** using PyModbus 3.6.9, Scapy 2.6.1, pytest 8.3.5. Real localhost TCP tests exercise FC04/FC06/FC16, accepted unauthorized writes, physical drainage, invalid-value exception 03 without mutation, invalid-address exception 02, restoration, repeated startup, target restrictions and DNS rejection. Host Python: 3.9.6; the running device and attacker containers use Python 3.12.7.
- Shell syntax, Python source compilation, telemetry C++ syntax and Compose structure/isolation checks pass.

## Remaining platform limits

Native Linux Engine host-bridge capture and Linux amd64 builds have not been separately tested. Wireshark GUI inspection has not been performed; the produced PCAP was inspected programmatically. This is an educational non-real-time simulation: cyclic correction may occur before a physics step, and a gate change between PLC samples can be missed by mismatch telemetry. Device command logs and PCAP retain accepted writes regardless of subsequent correction.

To reproduce:

```sh
docker compose up --build -d
python3 tests/verify_openplc.py
```

Follow `wireshark.md` to capture a new experiment. The acceptance script deliberately triggers one read and one write; it is never run at service startup.
