#!/usr/bin/env python3
"""Recreate the isolated CPS lab and record a verified pre-experiment baseline.

Run on the Docker host from any directory. Uses the existing images and Compose
configuration, including compose.override.yaml if present. The script never
sends actuator write commands and does not remove saved capture files.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
HMI = "http://127.0.0.1:8080/api/state"
SERVICES = ("inlet", "device", "openplc", "hmi", "attacker")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Reset the authorized isolated dam lab and save its baseline.")
    parser.add_argument("--method", choices=("baseline", "adaptive", "manual"),
                        default="manual", help="Experimental method label")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed used by the upcoming fuzzer (metadata only)")
    parser.add_argument("--initial-level", type=float, default=65.0,
                        help="Requested initial reservoir percentage (0..100)")
    parser.add_argument("--timeout", type=float, default=55.0,
                        help="Maximum number of seconds to wait for the baseline")
    parser.add_argument("--level-tolerance", type=float, default=5.0,
                        help="Maximum allowed drift from the initial level, percentage points")
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "captures" / "experiments")
    args = parser.parse_args(argv)
    if not 0 <= args.initial_level <= 100:
        parser.error("--initial-level must be within 0..100")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if not 0 < args.level_tolerance <= 100:
        parser.error("--level-tolerance must be within (0, 100]")
    return args


def fetch_snapshot():
    with urlopen(HMI, timeout=3) as response:
        if response.status != 200:
            raise ValueError(f"HMI returned HTTP {response.status}")
        return json.load(response)


def baseline_ready(data, requested_level=65.0, tolerance=5.0):
    """Validate a fresh, healthy, settled OpenPLC + two-node observation.

    Check coherence rather than requiring a fixed output at thresholds, since
    the controller may legitimately change commands as water level evolves.
    """
    try:
        reservoir, inlet, plc = data["reservoir"], data["inlet"], data["plc"]
        if not (reservoir["online"] and inlet["online"] and plc["online"]):
            return False
        if plc["age_seconds"] is None or plc["age_seconds"] > 3.5:
            return False
        internal = plc["internal"]
        if not internal or internal["event"] != "st_state":
            return False
        level = reservoir["level_pct"]
        if not isinstance(level, (int, float)) or abs(level - requested_level) > tolerance:
            return False
        if not (0 <= level <= 100):
            return False
        if reservoir["gate_pct"] != reservoir["gate_command_pct"]:
            return False
        if inlet["valve_pct"] != inlet["valve_command_pct"]:
            return False
        if reservoir["gate_command_pct"] != internal["desired"]:
            return False
        if inlet["valve_command_pct"] != internal["inlet_desired"]:
            return False
        if internal["mismatch"] != 0 or internal["inlet_mismatch"] != 0:
            return False
        return isinstance(internal["cycle"], int)
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def wait_for_baseline(requested_level, tolerance, timeout, fetch=fetch_snapshot,
                      now=time.monotonic, pause=time.sleep):
    deadline = now() + timeout
    previous = None
    last = None
    last_error = None
    while now() < deadline:
        try:
            last = fetch()
            if baseline_ready(last, requested_level, tolerance):
                cycle = last["plc"]["internal"]["cycle"]
                # A second fresh telemetry sample confirms PLC progress, rather
                # than accepting an apparently healthy but stalled controller.
                if previous is not None and cycle != previous:
                    return last
                previous = cycle
            else:
                previous = None
        except (HTTPError, URLError, OSError, ValueError, KeyError, TimeoutError) as exc:
            last_error = str(exc)
            previous = None
        pause(1.0)
    raise RuntimeError(
        "Clean baseline not reached. "
        f"Last HMI state: {json.dumps(last)[:1000] if last else 'unavailable'}. "
        f"Last connection error: {last_error}. "
        "Check `docker compose ps` and `docker compose logs --tail=40 hmi openplc device inlet`."
    )


def commit_hash():
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def uncommitted_changes():
    result = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                            cwd=ROOT, capture_output=True, text=True, check=False)
    return bool(result.stdout.strip()) if result.returncode == 0 else None


def main(argv=None):
    args = parse_args(argv)
    environment = os.environ.copy()
    # Environment override applies to Compose at container creation only.
    environment["INITIAL_WATER_LEVEL"] = str(args.initial_level)
    print("Validating the current Docker Compose configuration...", flush=True)
    subprocess.run(["docker", "compose", "config", "--quiet"], cwd=ROOT,
                   env=environment, check=True)

    # All five services must be newly created: this resets PLC counters, field
    # device memory, and HMI's cached UDP telemetry, not just reservoir physics.
    # `--no-build` prevents an expensive rebuild and keeps the software version
    # identical across repeated trials. Existing images must already exist.
    command = ["docker", "compose", "up", "-d", "--no-build",
               "--force-recreate", *SERVICES]
    print("Recreating isolated lab services without deleting captures...", flush=True)
    subprocess.run(command, cwd=ROOT, env=environment, check=True)
    print("Checking both Modbus devices and PLC progress via HMI...", flush=True)
    baseline = wait_for_baseline(args.initial_level, args.level_tolerance,
                                 args.timeout)

    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid4().hex[:8]
    run_dir = args.output_dir.resolve() / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    details = {
        "experiment_id": run_id,
        "reset_completed_at_utc": now.isoformat(),
        "method": args.method,
        "seed": args.seed,
        "requested_initial_water_level_pct": args.initial_level,
        "observed_water_level_pct": baseline["reservoir"]["level_pct"],
        "level_tolerance_pct_points": args.level_tolerance,
        "git_head": commit_hash(),
        "tracked_code_has_uncommitted_changes": uncommitted_changes(),
        "compose_services": list(SERVICES),
        "baseline": baseline,
        "caveat": (
            "Containers and in-memory state were reset. The PLC and physical "
            "process continue running, so exact request timing and subsequent "
            "states are not deterministic; record fuzzer results promptly."
        ),
    }
    output = run_dir / "baseline.json"
    output.write_text(json.dumps(details, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PASS: healthy dual-device PLC baseline at {baseline['reservoir']['level_pct']}%")
    print(f"Experiment ID: {run_id}")
    print(f"Saved baseline: {output}")
    print("Run your next experiment now; repeat this reset before the next trial.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (subprocess.CalledProcessError, FileNotFoundError, RuntimeError) as exc:
        print(f"RESET FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
