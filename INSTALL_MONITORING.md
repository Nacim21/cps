# CPS Improvement 2: installation and verification

This is an incremental patch for `Nacim21/cps` on `derek-environment-expansion`,
**after** the previously installed two-device/HMI expansion and reset utility.
The archive intentionally contains only one modified file (`plc/telemetry.cpp`)
and three new files. It does not replace the HMI, Compose configuration,
Structured Text controller, or existing reset script.

## 1. Apply to your existing working branch

From Terminal on the Mac:

```bash
cd ~/cps
git branch --show-current
unzip -o ~/Downloads/cps_improvement2_monitoring_patch.zip -d .
```

The branch should be `derek-environment-expansion`.

## 2. Run offline tests

```bash
.venv/bin/python -m pytest -q tests/test_export_experiment_events.py
```

The package passed **17 offline exporter tests** and a separate C++ telemetry smoke test
in the preparation environment. Neither verifies a real OpenPLC Docker runtime.

## 3. Rebuild the updated PLC telemetry image

```bash
docker compose up -d --build openplc
docker compose ps
python3 tests/verify_expansion.py
```

The image rebuild will recompile the OpenPLC program but does not change the
controller's Structured Text. The HMI should still work at `http://127.0.0.1:8080`.

## 4. Record and export a trial

```bash
python3 scripts/reset_experiment.py --method baseline --seed 2026
python3 tests/verify_openplc.py
python3 scripts/export_experiment_events.py
```

The exporter reads logs *since the latest reset completed*. It creates
`captures/experiments/<id>/events.jsonl` and `events_summary.json` in the same
folder as `baseline.json`. The prior captures are not deleted.

For a quick check that event logging is enabled, run:

```bash
docker compose logs --tail=100 openplc
```

Look for JSON `"event":"st_state"` and `"event":"st_transition"` records.
There may be no `st_transition` in an idle, steady-state system; that is normal.

## 5. Run regression tests before committing

```bash
.venv/bin/python -m pytest -q
python3 tests/verify_openplc.py
```

When all checks pass:

```bash
git add plc/telemetry.cpp scripts/export_experiment_events.py tests/test_export_experiment_events.py docs/event-monitoring.md INSTALL_MONITORING.md
git commit -m "Add event-based PLC monitoring and experiment event exports"
git push origin derek-environment-expansion
```

Do not add the `captures/experiments/` folder to Git. Keep `main` untouched until
Nacim has reviewed the branch.

## Break / shutdown

```bash
docker compose stop
```

Later, after reopening Docker Desktop, `docker compose start` resumes the lab.
For **clean experiment baselines**, use `scripts/reset_experiment.py` instead of
assuming an ordinary restart resets the experiment.
