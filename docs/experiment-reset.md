# Repeatable experiment resets

The `scripts/reset_experiment.py` command recreates **all five lab containers** from their existing images and verifies that:

- Reservoir Modbus, inlet Modbus, and PLC telemetry are online.
- The sampled PLC cycle counter is advancing.
- Actual and commanded gate/valve values match.
- PLC mismatch flags are clear (historical mismatch counters may increase during startup).
- The reported reservoir level is within a configurable tolerance of the requested starting level.

It saves an individual `captures/experiments/<experiment-id>/baseline.json` containing the initial state, method, seed, and code commit. This path is under the repository's ignored `captures/` directory. Existing captures are **not removed**.

## Before the first run

Make sure Docker Desktop is running, the existing expanded environment has already been built, and your existing `compose.override.yaml` still makes the HMI available at `127.0.0.1:8080`.

```sh
docker compose ps
```

If the images have never been built, build the environment once:

```sh
docker compose up --build -d
```

## Reset for a baseline trial

From the repository root:

```sh
python3 scripts/reset_experiment.py --method baseline --seed 2026
```

Expect a `PASS` confirmation and the saved baseline JSON path. Run the fuzzer immediately afterward, and save its results with the same experiment ID.

## Reset for an adaptive trial

```sh
python3 scripts/reset_experiment.py --method adaptive --seed 2026
```

Use the **same** method-independent test budget, initial water level and seed across compared trials. Only the selection policy should differ.

## Different starting water levels

For example, initialize the reservoir at 85%:

```sh
python3 scripts/reset_experiment.py --initial-level 85 --method baseline --seed 2026
```

The controller is continuously operating, so the observed initial level may differ slightly from the requested level by the time the HMI sees it. The default readiness tolerance is 5 percentage points. For experiments close to PLC thresholds, inspect the saved `baseline.json` and do not equate a *requested* starting value with an identical *observed* starting value.

## Everyday Docker management

- `docker compose stop` stops all containers, retaining their filesystem and images.
- `docker compose start` resumes services, but does **not** guarantee the same baseline or clear the Docker logs.
- `python3 scripts/reset_experiment.py` is the controlled reset operation.
- `docker compose down` removes service containers and the Compose network; it does **not** delete the `captures/` directory. Avoid `docker compose down -v` unless you intentionally want to remove volumes.

## Important reproducibility limits

This tool resets **in-memory simulation state**, not physics time: once OpenPLC starts, the reservoir continues to evolve. Network scheduling, PLC polling and fuzzing request timing are not bit-for-bit deterministic. Always compare the *observed* baseline in the JSON record and run repeated trials. The script does not delete old logs/captures or open a Modbus write path; it simply recreates the isolated simulation. Run the reset only when no fuzzing job is active.

On failure, check:

```sh
docker compose ps
docker compose logs --tail=40 hmi openplc device inlet
curl -i http://127.0.0.1:8080/api/state
```
