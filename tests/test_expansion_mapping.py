"""Self-contained configuration checks independent of Docker and PyModbus."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_controller_uses_two_field_nodes():
    config = (ROOT / "plc/config/mbconfig.cfg").read_text()
    assert 'Num_Devices = "2"' in config
    assert 'device0.Input_Registers_Size = "2"' in config
    assert 'device1.Input_Registers_Size = "2"' in config
    assert 'device0.Holding_Registers_Size = "1"' in config
    assert 'device1.Holding_Registers_Size = "1"' in config
    assert 'device0.address = "172.28.10.20"' in config
    assert 'device1.address = "172.28.10.21"' in config


def test_state_snapshots_and_outputs_have_distinct_locations():
    st = (ROOT / "plc/spillway.st").read_text()
    assert 'WaterLevelRaw AT %IW100' in st
    assert 'GatePosition AT %IW101' in st
    assert 'GateCommand AT %QW100' in st
    assert 'InletPosition AT %IW102' in st
    assert 'InletFlowRaw AT %IW103' in st
    assert 'InletCommand AT %QW101' in st
    assert 'InletMismatchCount AT %MW11' in st


def test_hmi_has_no_write_endpoint_and_is_only_host_publication():
    app = (ROOT / "services/hmi/app.py").read_text()
    assert 'def do_POST(self):' in app
    assert '405' in app
    compose = (ROOT / "compose.yaml").read_text()
    assert '127.0.0.1:8080:8080' in compose
