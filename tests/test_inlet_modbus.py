"""Unit tests for the second Modbus node (requires requirements-test.txt)."""
from services.inlet.server import InletContext
from services.inlet.state import InletState
import pytest


def test_inlet_registers_and_commands():
    context = InletContext(InletState())
    assert context.getValues(4, 0, 2) == [100, 250]
    assert context.getValues(3, 0, 1) == [100]
    assert context.validate(16, 0, 1)
    assert not context.validate(16, 0, 2)
    context.setValues(16, 0, [50])
    assert context.getValues(4, 0, 2) == [50, 125]
    assert context.getValues(3, 0, 1) == [50]
    assert context.history[-1]["function"] == 16
    context.setValues(6, 0, [0])
    assert context.getValues(4, 0, 2) == [0, 0]
    assert context.history[-1]["previous"] == 50


def test_inlet_rejects_out_of_range_mutation():
    context = InletContext()
    with pytest.raises(ValueError):
        context.setValues(6, 0, [101])
    assert context.getValues(3, 0, 1) == [100]
    assert not context.validate(4, 2, 1)
