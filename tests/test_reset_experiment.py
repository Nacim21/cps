"""Pure unit tests for the reset orchestrator, no Docker required."""
from copy import deepcopy
import pytest
from scripts.reset_experiment import baseline_ready, parse_args, wait_for_baseline


@pytest.fixture
def sample():
    return {
        "reservoir": {"online": True, "level_pct": 65.25,
                      "gate_pct": 25, "gate_command_pct": 25},
        "inlet": {"online": True, "valve_pct": 100, "valve_command_pct": 100},
        "plc": {"online": True, "age_seconds": .3,
                "internal": {"event": "st_state", "cycle": 80, "desired": 25,
                             "inlet_desired": 100, "mismatch": 0,
                             "inlet_mismatch": 0}},
    }


def test_healthy_baseline(sample):
    assert baseline_ready(sample)


@pytest.mark.parametrize("part", ("reservoir", "inlet", "plc"))
def test_offline_rejected(sample, part):
    sample[part]["online"] = False
    assert not baseline_ready(sample)


def test_stale_telemetry_rejected(sample):
    sample["plc"]["age_seconds"] = 3.7
    assert not baseline_ready(sample)


def test_wrong_level_rejected(sample):
    sample["reservoir"]["level_pct"] = 50.0
    assert not baseline_ready(sample)


def test_gate_disagreement_rejected(sample):
    sample["reservoir"]["gate_pct"] = 100
    assert not baseline_ready(sample)


def test_inlet_disagreement_rejected(sample):
    sample["inlet"]["valve_command_pct"] = 50
    assert not baseline_ready(sample)


def test_plc_disagreement_rejected(sample):
    sample["plc"]["internal"]["inlet_desired"] = 50
    assert not baseline_ready(sample)


def test_counter_mismatch_rejected(sample):
    sample["plc"]["internal"]["mismatch"] = 1
    assert not baseline_ready(sample)


def test_wait_rejects_stalled_plc(sample):
    calls = iter([deepcopy(sample)] * 4)
    counter = iter([0, 1, 2, 3, 4, 5])
    with pytest.raises(RuntimeError):
        wait_for_baseline(65, 5, 3, fetch=lambda: next(calls),
                          now=lambda: next(counter), pause=lambda _: None)


def test_wait_accepts_advancing_plc(sample):
    first = deepcopy(sample)
    next_one = deepcopy(sample)
    next_one["plc"]["internal"]["cycle"] += 20
    states = iter([first, next_one])
    ticks = iter([0, 0, 1, 1])
    result = wait_for_baseline(65, 5, 5, fetch=lambda: next(states),
                               now=lambda: next(ticks), pause=lambda _: None)
    assert result["plc"]["internal"]["cycle"] == 100


@pytest.mark.parametrize("argv", (["--initial-level", "-1"],
                                   ["--initial-level", "101"],
                                   ["--timeout", "0"],
                                   ["--level-tolerance", "0"]))
def test_invalid_options(argv):
    with pytest.raises(SystemExit):
        parse_args(argv)
