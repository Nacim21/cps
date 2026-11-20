"""PLC5 mapping, synthetic model and read-only field node (no Docker required)."""
from pathlib import Path
import pytest
from services.downstream.model import DownstreamFlowModel
from services.downstream.server import FlowContext

ROOT = Path(__file__).resolve().parents[1]


def test_normal_discharge_and_high_release():
    m = DownstreamFlowModel()
    m.observe(65.0, 25)
    assert m.registers()[:4] == [500, 1500, 25, 1]
    m.tick()
    assert m.registers()[4] == 1
    m.observe(65.0, 100)
    assert m.registers()[:2] == [2000, 1500]
    m.mark_source_unavailable()
    assert m.registers()[0] == 0 and m.registers()[3] == 0


def test_synthetic_bias_and_validation():
    m = DownstreamFlowModel(bias_m3s=125)
    m.observe(65, 25)
    assert m.flow_m3s == 175.0
    m.observe(-1, 25)
    assert not m.source_healthy
    with pytest.raises(ValueError):
        DownstreamFlowModel(warning_threshold_m3s=0)
    with pytest.raises(ValueError):
        DownstreamFlowModel(bias_m3s=2000)


def test_field_node_is_modbus_fc04_only():
    ctx = FlowContext(DownstreamFlowModel())
    assert ctx.validate(4, 0, 5)
    for fc in (1, 2, 3, 5, 6, 15, 16):
        assert not ctx.validate(fc, 0, 1)


def test_plc5_is_observational_and_wired():
    st = (ROOT/'plc/downstream.st').read_text()
    cfg = (ROOT/'plc/config/mbconfig-downstream.cfg').read_text()
    compose = (ROOT/'compose.yaml').read_text()
    hmi = (ROOT/'services/hmi/app.py').read_text()
    assert 'PROGRAM DownstreamController' in st
    assert 'AT %QW' not in st and 'AT %QX' not in st
    assert 'FlowAlarmSnapshot AT %MW2' in st
    assert 'Num_Devices = "2"' in cfg
    assert 'device0.address = "172.28.10.23"' in cfg
    assert 'device1.address = "172.28.10.10"' in cfg
    assert 'device0.Input_Registers_Size = "5"' in cfg
    assert 'device1.Holding_Registers_Read_Size = "7"' in cfg
    assert 'device0.Holding_Registers_Size = "0"' in cfg
    assert 'device1.Holding_Registers_Size = "0"' in cfg
    assert 'PLC_ROLE: downstream' in compose
    assert 'ipv4_address: 172.28.10.14' in compose
    assert 'ipv4_address: 172.28.10.23' in compose
    assert '"172.28.10.14": ("downstream", "OPENPLC_DOWNSTREAM")' in hmi
    assert 'Read-only HMI: no write endpoints' in hmi
