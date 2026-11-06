"""Unit tests for the expanded environment; do not require Docker."""
import pytest
from services.inlet.state import InletState
from services.device.inlet_link import pct_to_inflow
from services.device.physics import Reservoir

@pytest.mark.parametrize("opening,expected", [(0,0.0),(25,0.0625),(50,0.125),(100,0.25)])
def test_inlet_valve_flow(opening,expected):
    inlet = InletState()
    inlet.set_valve(opening)
    assert inlet.flow_percent_per_second == pytest.approx(expected)
    assert inlet.flow_milli_percent_per_second == round(expected * 1000)
    assert pct_to_inflow(opening) == pytest.approx(expected)

@pytest.mark.parametrize("opening", [-1,101,1.5,True,"100"])
def test_inlet_rejects_bad_commands(opening):
    with pytest.raises(ValueError):
        InletState().set_valve(opening)


def test_shared_reservoir_physics_changes_with_valve():
    normal = Reservoir(gate=25)
    shut = Reservoir(gate=25)
    normal.inflow = pct_to_inflow(100)
    shut.inflow = pct_to_inflow(0)
    normal.step(10)
    shut.step(10)
    assert normal.actual_level == pytest.approx(65)
    assert shut.actual_level == pytest.approx(62.5)


def test_inlet_initial_value_preserves_old_reservoir_baseline():
    assert InletState().valve_percent == 100
    assert pct_to_inflow(InletState().valve_percent) == Reservoir().inflow
