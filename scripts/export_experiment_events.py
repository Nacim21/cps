#!/usr/bin/env python3
"""Export a time-ordered, read-only CPS experiment event timeline.

Run after scripts/reset_experiment.py and the experiment. Never issues Modbus
commands or changes device/PLC/HMI state. Docker is only asked for its logs.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "captures" / "experiments"
SERVICES = ("openplc", "device", "inlet", "attacker", "hmi")


def utc_datetime(value: str) -> datetime:
    """Accept Docker's RFC3339 timestamps (including nanoseconds)."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def parse_docker_line(service: str, line: str, since: datetime):
    """Parse one --timestamps --no-log-prefix line; ignore non-JSON chatter."""
    timestamp_string, delimiter, payload = line.strip().partition(" ")
    if not delimiter or not payload.lstrip().startswith("{"):
        return None
    try:
        timestamp = utc_datetime(timestamp_string)
        if timestamp < since:
            return None
        item = json.loads(payload)
    except (ValueError, TypeError):
        return None
    if not isinstance(item, dict) or not isinstance(item.get("event"), str):
        return None
    category, review = classify_event(item)
    return {
        "timestamp_utc": timestamp.isoformat(),
        "service": service,
        "category": category,
        "review_reason": review,
        "data": item,
    }


def classify_event(item: dict) -> tuple[str, str | None]:
    """Tag observations for review, NOT confirmed vulnerabilities."""
    event = item.get("event")
    if event == "st_transition":
        signal = item.get("signal")
        current = item.get("current")
        if signal in ("gate_mismatch", "inlet_mismatch") and current == 1:
            return "plc_transition", "Actuator feedback differs from the desired PLC command"
        if signal == "high_water_alarm" and current == 1:
            return "plc_transition", "High-water alarm activated"
        return "plc_transition", None
    if event == "plc_monitor_started":
        return "monitoring", None
    if event == "st_state":
        return "plc_snapshot", None
    if event in ("gate_command_accepted", "valve_command_accepted"):
        return "actuator_command", None
    if event == "modbus_request":
        return "modbus_request", None
    if event == "physics":
        return "physics_snapshot", None
    if event == "inlet_link":
        return "connectivity", ("Inlet connection lost" if item.get("connected") is False else None)
    if event in ("request_failed", "unauthorized_write_failed"):
        return "client_failure", "Modbus client failure; check expected error conditions"
    if event and (event.startswith("unauthorized_") or event.startswith("fuzz_")):
        return "test_action", None
    return "other", None


def find_experiment(experiment_id: str | None, base_dir: Path = EXPERIMENTS) -> Path:
    if experiment_id:
        if Path(experiment_id).name != experiment_id or experiment_id in (".", ".."):
            raise ValueError("Invalid experiment ID")
        path = base_dir / experiment_id / "baseline.json"
    else:
        candidates = sorted(base_dir.glob("*/baseline.json"))
        if not candidates:
            raise FileNotFoundError("No experiment baseline found; run scripts/reset_experiment.py first")
        path = candidates[-1]
    if not path.is_file():
        raise FileNotFoundError(f"Baseline not found: {path}")
    return path


def gather_events(since: datetime, runner=subprocess.run, experiment_id: str | None = None) -> list[dict]:
    results = []
    for service in SERVICES:
        command = ["docker", "compose", "logs", "--no-color", "--no-log-prefix",
                   "--timestamps", "--since", since.isoformat(), service]
        response = runner(command, cwd=ROOT, capture_output=True, text=True, check=True)
        for line in response.stdout.splitlines():
            parsed = parse_docker_line(service, line, since)
            if parsed is not None:
                if experiment_id is not None:
                    parsed["experiment_id"] = experiment_id
                results.append(parsed)
    # Timestamps from the Docker logging driver give an approximate cross-
    # service ordering; they are not a request/response correlation identifier.
    results.sort(key=lambda item: (item["timestamp_utc"], item["service"]))
    return results


def make_summary(baseline: dict, events: list[dict], since: datetime) -> dict:
    by_service = Counter(e["service"] for e in events)
    by_category = Counter(e["category"] for e in events)
    flagged = [e for e in events if e["review_reason"]]
    return {
        "experiment_id": baseline["experiment_id"],
        "method": baseline.get("method"),
        "seed": baseline.get("seed"),
        "since_utc": since.isoformat(),
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "event_count": len(events),
        "counts_by_service": dict(sorted(by_service.items())),
        "counts_by_category": dict(sorted(by_category.items())),
        "review_flag_count": len(flagged),
        "review_flag_samples": [
            {"timestamp_utc": e["timestamp_utc"], "service": e["service"],
             "reason": e["review_reason"], "data": e["data"]}
            for e in flagged[:20]
        ],
        "interpretation": (
            "Review flags identify observations requiring human analysis; they are not "
            "proof of vulnerabilities. Expected PLC corrections, startup conditions, "
            "and valid Modbus exceptions must be distinguished from anomalies."
        ),
        "correlation_limit": (
            "Events are approximately ordered by Docker timestamps. They are not "
            "cryptographically or transaction-ID linked across PLC and field devices. "
            "A fast transition between PLC scans or truncated Docker logs may be missed."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Export read-only CPS event log for the latest reset")
    parser.add_argument("--experiment-id", help="Export a specific baseline's experiment ID (default: latest)")
    args = parser.parse_args(argv)
    baseline_path = find_experiment(args.experiment_id)
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if not isinstance(baseline, dict) or "reset_completed_at_utc" not in baseline or "experiment_id" not in baseline:
        raise ValueError("Invalid baseline.json format")
    since = utc_datetime(baseline["reset_completed_at_utc"])
    events = gather_events(since, experiment_id=baseline["experiment_id"])
    run_dir = baseline_path.parent
    timeline = run_dir / "events.jsonl"
    timeline.write_text("".join(json.dumps(event, sort_keys=True) + "\n" for event in events),
                        encoding="utf-8")
    summary = make_summary(baseline, events, since)
    summary_path = run_dir / "events_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    print(f"Exported {len(events)} events for {baseline['experiment_id']}")
    print(f"Review flags (not verified vulnerabilities): {summary['review_flag_count']}")
    print(f"Timeline: {timeline}")
    print(f"Summary:  {summary_path}")
    if not events:
        print("No structured events found since reset. Check Docker status and container logs.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"EXPORT FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)
