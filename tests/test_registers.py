from services.device.physics import Reservoir
from services.device.modbus_server import DeviceContext
import pytest

def test_map():
    ctx = DeviceContext(Reservoir())
    assert ctx.getValues(4, 0, 2) == [6500, 0]
    ctx.setValues(6, 0, [100])
    assert ctx.getValues(3, 0, 1) == [100]
    assert ctx.getValues(4, 1, 1) == [100]
    assert not ctx.validate(4, 2, 1)
    assert ctx.validate(16, 0, 1)
    assert not ctx.validate(16, 0, 2)
    with pytest.raises(ValueError):
        ctx.setValues(6, 0, [101])

    ctx.setValues(16, 0, [25])
    assert list(ctx.history)[-1]["previous"] == 100
    assert list(ctx.history)[-1]["gate"] == 25
    assert list(ctx.history)[-1]["timestamp"]
    assert ctx.getValues(4, 1, 1) == [25]
