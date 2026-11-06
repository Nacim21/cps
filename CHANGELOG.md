# Expansion change list

- Added second Modbus TCP node (`inlet`) at 172.28.10.21:5020, unit 1, with valve command and feedback.
- Coupled inlet node to original reservoir via internal Modbus polling; kept one authoritative physics model.
- Extended pinned OpenPLC v3 Modbus master configuration from one to two devices.
- Extended existing Structured Text with inlet control logic and additional memory snapshots.
- Extended native telemetry logger to report the new PLC state, plus best-effort internal UDP snapshots to the HMI.
- Added read-only HMI, Modbus reads, dashboard and localhost-only Docker port publication.
- Extended native ST generated-code harness and added inlet physics tests and live integration smoke test.
- Preserved the existing attacker container and existing gate map to minimize regressions.
