# CPS environment expansion: ready-to-apply overlay

This archive contains working source for a second Modbus TCP inlet node, a read-only live web HMI, and new OpenPLC state snapshots. It is an **overlay for `https://github.com/Nacim21/cps`**, not a standalone replacement for that repository.

## Fastest installation on your Mac

Open Terminal. From a clean, up-to-date checkout of Nacim's repository:

```bash
cd ~/cps
git switch main
git pull --ff-only
git switch -c derek-environment-expansion
unzip -o ~/Downloads/cps_environment_expansion_patch.zip -d .
git diff --stat
test -f .env || cp .env.example .env
docker compose config --quiet
docker compose up --build -d
docker compose ps
python3 tests/verify_expansion.py
python3 tests/verify_openplc.py
```

The `cd ~/cps` path is an example. Use your actual cloned repository folder. The ZIP must be in `~/Downloads` for the unzip command to match; use the actual ZIP path otherwise. The first OpenPLC image build recompiles the pinned upstream compiler/runtime and may take a while.

Open the live HMI at **http://127.0.0.1:8080**. Its JSON endpoint is `http://127.0.0.1:8080/api/state`.

If the original branch contains uncommitted work or has moved since the review, do not overwrite it. Start with a clean branch and review `git diff` before committing. This patch intentionally changes `compose.yaml`, `plc/config/mbconfig.cfg`, `plc/entrypoint.sh`, `plc/spillway.st`, `plc/telemetry.cpp`, `services/device/modbus_server.py`, and `tests/st_harness.cpp`.

## Tests

The existing requirements-test file includes PyModbus 3.6.9 and pytest. Install dependencies into a virtual environment if needed:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-test.txt
.venv/bin/python -m pytest -q
```

A separate read-only smoke test checks both Modbus nodes, live PLC state data, command values and advancing scan counter:

```bash
python3 tests/verify_expansion.py
```

To inspect source events:

```bash
docker compose logs -f openplc device inlet hmi
```

## Rollback

Switch back to `main` to use the prior implementation without merging this branch. Do not merge until the Docker smoke test and existing suite pass and Nacim has reviewed the changes.

## What's implemented versus unverified

- Implemented: second PyModbus valve node; inlet-to-reservoir coupling; dual-device OpenPLC mapping; extended ST control/mismatch counters; UDP PLC telemetry; read-only HMI; tests and documentation.
- Locally verified: Python syntax, YAML structure, C++ telemetry syntax, inlet physics unit tests, HMI endpoint behavior with simulated Modbus responses.
- **Not yet verified:** actual full Docker build, compiled Structured Text against pinned MatIEC, multi-node network acceptance, and HMI with live PLC telemetry. Run the smoke tests above before merging.

See `docs/expansion.md` for topology, Modbus registers, PLC memory addresses, physics, assumptions, and limitations.
