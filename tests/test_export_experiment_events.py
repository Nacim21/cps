"""Offline tests for the experiment event exporter; Docker not required."""
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from scripts import export_experiment_events as ev


START = datetime(2026, 11, 6, 17, 0, 0, tzinfo=timezone.utc)


def line(value, timestamp="2026-11-06T17:00:01.123456789Z"):
    return f"{timestamp} {json.dumps(value)}"


def test_parse_transition_and_review_flag():
    event = ev.parse_docker_line("openplc", line({"event": "st_transition", "signal": "gate_mismatch",
                                                     "previous": 0, "current": 1}), START)
    assert event["category"] == "plc_transition"
    assert "differs" in event["review_reason"]
    assert event["data"]["current"] == 1
    assert event["timestamp_utc"].startswith("2026-11-06T17:00:01.123456")


def test_expected_command_not_vulnerability():
    event = ev.parse_docker_line("device", line({"event": "gate_command_accepted", "gate": 100}), START)
    assert event["category"] == "actuator_command"
    assert event["review_reason"] is None


@pytest.mark.parametrize("payload", [
    {"event": "st_transition", "signal": "inlet_mismatch", "current": 1},
    {"event": "st_transition", "signal": "high_water_alarm", "current": 1},
    {"event": "inlet_link", "connected": False},
    {"event": "request_failed", "error": "socket timeout"},
])
def test_reviewable_conditions(payload):
    assert ev.classify_event(payload)[1]


@pytest.mark.parametrize("payload", [
    {"event": "st_transition", "signal": "gate_mismatch", "current": 0},
    {"event": "modbus_request", "transaction": 12},
    {"event": "st_state", "cycle": 100},
    {"event": "physics", "actual_level": 65},
    {"event": "inlet_link", "connected": True},
    {"event": "st_transition", "signal": "level_band", "current": 2},
])
def test_normal_events_are_not_review_flags(payload):
    assert ev.classify_event(payload)[1] is None


def test_bad_lines_ignored():
    assert ev.parse_docker_line("openplc", "Not a JSON log line", START) is None
    assert ev.parse_docker_line("openplc", "2026-11-06T17:00:01Z {oops", START) is None
    assert ev.parse_docker_line("openplc", line([1, 2, 3]), START) is None
    assert ev.parse_docker_line("openplc", line({"component": "OPENPLC"}), START) is None
    assert ev.parse_docker_line("openplc", line({"event": "st_state"},
                                                       "2026-11-06T16:59:59Z"), START) is None


def test_datetime_requires_tz():
    with pytest.raises(ValueError):
        ev.utc_datetime("2026-11-06T17:00:01")


def test_find_experiment_latest(tmp_path):
    for name in ("20261106T160000Z-a", "20261106T170000Z-b"):
        path = tmp_path / name / "baseline.json"
        path.parent.mkdir()
        path.write_text("{}")
    assert ev.find_experiment(None, tmp_path).parent.name.endswith("-b")
    assert ev.find_experiment("20261106T160000Z-a", tmp_path).parent.name.endswith("-a")
    with pytest.raises(ValueError):
        ev.find_experiment("../outside", tmp_path)


def test_gather_sorts_across_services():
    def mock_run(command, **kwargs):
        service = command[-1]
        timestamp = "2026-11-06T17:00:02Z" if service == "openplc" else "2026-11-06T17:00:01Z"
        payload = line({"event": "st_state"}, timestamp) if service in ("openplc", "device") else "unstructured"
        return SimpleNamespace(stdout=payload)

    records = ev.gather_events(START, runner=mock_run, experiment_id="trial-123")
    assert [r["service"] for r in records] == ["device", "openplc"]
    assert all(r["experiment_id"] == "trial-123" for r in records)


def test_summary_counts_and_caps_samples():
    baseline = {"experiment_id": "test", "method": "baseline", "seed": 2026}
    events = [ev.parse_docker_line("openplc", line({"event": "st_transition",
                                                    "signal": "gate_mismatch", "current": 1}), START)
              for _ in range(22)]
    summary = ev.make_summary(baseline, events, START)
    assert summary["review_flag_count"] == 22
    assert len(summary["review_flag_samples"]) == 20
    assert summary["counts_by_category"]["plc_transition"] == 22
    assert summary["method"] == "baseline"
