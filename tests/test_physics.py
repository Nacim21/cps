import pytest
from services.device.physics import Reservoir
from shared.register_map import encode_level

@pytest.mark.parametrize("level,encoded", [(0,0),(65,6500),(100,10000),(12.34,1234)])
def test_encoding(level, encoded):
    assert encode_level(level) == encoded

def test_bounds_and_reproducibility():
    a, b = Reservoir(), Reservoir()
    for gate in [25,100,0] * 20:
        a.gate = b.gate = gate
        a.step(1); b.step(1)
        assert a == b
    a.gate = 100
    a.step(10000)
    assert a.actual_level == 0
    a.gate = 0
    a.step(10000)
    assert a.actual_level == 100
    with pytest.raises(ValueError):
        encode_level(101)

def test_attack_changes_physics():
    normal, attacked = Reservoir(gate=25), Reservoir(gate=100)
    normal.step(10); attacked.step(10)
    assert normal.actual_level == 65
    assert attacked.actual_level == 57.5
