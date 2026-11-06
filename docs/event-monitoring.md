# Improvement 2: Event-based PLC monitoring and experiment exports

## Purpose

This adds **read-only observation** for the two-device OpenPLC dam lab. It does not change
Structured Text control logic, Modbus register maps, or the HMI's existing `/api/state` schema.
It is intended to support subsequent controlled fuzzing experiments, not to claim a
vulnerability based solely on a transient alarm or mismatched actuator.

## What changes

`plc/telemetry.cpp` now reads the 12 existing `%MW` state fields once per PLC scan
(approximately every 50 ms) and produces `st_transition` log entries when any of these
sampled signals changes:

- Gate actual position, desired command, mismatch and mismatch count
- High-water alarm
- Inlet desired valve, actual valve, reported flow, mismatch and mismatch count
- Water-level **control band** (below 40%, 40–70%, above 70–90%, above 90%)

The ordinary rising water-level measurements and scan counter are **not** logged every
50 ms. This prevents unnecessary log volume. State changes are still only as precise
as the PLC's input updates: OpenPLC fetches remote Modbus registers approximately once
a second, so some short-lived physical events can remain unobserved. A `st_transition`
record means the PLC **observed** a changed value, not that the change happened at the
exact log timestamp.

The preexisting `st_state` JSON snapshot continues once per second and continues to
be sent by UDP to the HMI. The HMI remains read-only. PLC log timestamps include
`timestamp_epoch_ms` for the observed state transition; the exporter relies on
Docker's UTC timestamps for sorting events from separate containers.

### Example event

```json
{"timestamp_epoch_ms":1793922922430,"component":"OPENPLC","event":"st_transition","signal":"gate_mismatch","previous":0,"current":1,"level_raw":6500,"cycle":13200}
```

## After a reset and an experiment

Reset normally:

```bash
python3 scripts/reset_experiment.py --method baseline --seed 2026
```

Run your authorized experiment, then export **the latest** experiment's timeline:

```bash
python3 scripts/export_experiment_events.py
```

Or choose a particular experiment ID:

```bash
python3 scripts/export_experiment_events.py --experiment-id <experiment-id>
```

The exporter reads `captures/experiments/<id>/baseline.json` to determine when the
reset completed. It then reads Docker's timestamps and structured logs from `openplc`,
`device`, `inlet`, `attacker`, and `hmi` **without issuing Modbus writes or restarting
containers**. It saves:

- `captures/experiments/<id>/events.jsonl`: one normalized event per line in UTC order, each labeled with the experiment ID.
- `captures/experiments/<id>/events_summary.json`: counts and up to 20 review-flag examples.

Existing baseline files and raw packet captures are unchanged. Generated experiment
outputs should remain ignored by Git.

### Review flags versus findings

Only a few events receive review flags, for example a mismatch becoming active,
a high-water alarm, a lost inlet link, or an explicit client failure. These are
**observations**, not automatically confirmed software vulnerabilities.
An `Illegal Data Address` Modbus exception may be correct protocol behavior. The
existing controller routinely corrects unauthorized actuator changes, and even
ordinary startup can increment mismatch counters.

Events across containers are **time-aligned only**. A device may process multiple
requests around the same time, so proximity of timestamps is not proof that a
specific request caused a PLC transition. A future fuzzer should include its own
unique test-case identifiers, request bytes and send timestamps in its results;
those can then be compared against this event timeline.

## Verification steps

```bash
# Run offline tests first
.venv/bin/python -m pytest -q tests/test_export_experiment_events.py

# Rebuild only OpenPLC since telemetry.cpp is compiled into its image
docker compose up -d --build openplc

# Ensure original HMI still receives current PLC snapshots
python3 tests/verify_expansion.py

# Inspect new event and old snapshot logs
docker compose logs --tail=80 openplc

# Save an event timeline for the latest reset
python3 scripts/reset_experiment.py --method baseline --seed 2026
python3 scripts/export_experiment_events.py
```

For stronger evidence, run the existing controlled experiment and then re-export:

```bash
python3 tests/verify_openplc.py
python3 scripts/export_experiment_events.py
```

A gate write may be corrected before a PLC scan observes a mismatch; device command
logs still preserve accepted writes. Do not require a mismatch event on every write.

## Operational boundaries

- Remain within the isolated Docker testbed. The HMI is the only host-published service.
- The exporter is offline and read-only; it does not require a new service or port.
- Do not treat `st_transition` as a continuous 20 Hz trace of physical devices. It
  captures meaningful changes in PLC memory as they become visible to the runtime.
- Docker logs are ephemeral unless exported; run the exporter before deleting
  containers or clearing their logs.
