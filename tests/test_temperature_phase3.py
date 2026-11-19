"""No Docker required: verify safe PLC3 wiring and synthetic field model."""
from pathlib import Path
import pytest
from services.temperature.model import TemperatureModel
from services.temperature.server import TemperatureContext

ROOT = Path(__file__).resolve().parents[1]


def test_model_registers_and_drift():
    model = TemperatureModel(24.0, 32.0, 0.05)
    assert model.registers() == [2400, 3200]
    model.step(2)
    assert model.registers() == [2410, 3200]
    ctx = TemperatureContext(model)
    assert ctx.validate(4, 0, 2)
    assert not ctx.validate(6, 0, 1)
    assert not ctx.validate(16, 0, 1)


def test_bad_model_rejected():
    with pytest.raises(ValueError):
        TemperatureModel(temperature_c=-1)
    with pytest.raises(ValueError):
        TemperatureModel(drift_c_per_s=0.5)


def test_third_controller_is_read_only_to_actuators():
    st = (ROOT / "plc/temperature.st").read_text()
    assert "PROGRAM TemperatureController" in st
    assert "GateAdvisorySnapshot AT %MW2" in st
    assert "%QW" not in st
    cfg = (ROOT / "plc/config/mbconfig-temperature.cfg").read_text()
    assert 'Num_Devices = "2"' in cfg
    assert 'device0.address = "172.28.10.22"' in cfg
    assert 'device1.address = "172.28.10.10"' in cfg
    assert 'device1.IP_Port = "15020"' in cfg
    assert 'device0.Holding_Registers_Size = "0"' in cfg
    assert 'device1.Holding_Registers_Size = "0"' in cfg


def test_compose_and_hmi_wiring():
    compose = (ROOT / "compose.yaml").read_text()
    assert 'openplc-temp:' in compose and 'temperature-sensor:' in compose
    assert 'ipv4_address: 172.28.10.12' in compose
    assert 'ipv4_address: 172.28.10.22' in compose
    hmi = (ROOT / "services/hmi/app.py").read_text()
    assert '"172.28.10.12": ("temperature", "OPENPLC_TEMP")' in hmi
    assert 'client.read_input_registers(0, count=2, slave=1)' in hmi
