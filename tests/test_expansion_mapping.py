"""Static mapping checks for the TWO independent OpenPLC runtimes."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_spillway_owns_gate_not_inlet():
    config = (ROOT / "plc/config/mbconfig.cfg").read_text()
    st = (ROOT / "plc/spillway.st").read_text()
    assert 'Num_Devices = "1"' in config
    assert 'device0.Holding_Registers_Size = "1"' in config
    assert 'device0.address = "172.28.10.20"' in config
    assert 'GateCommand AT %QW100' in st
    assert 'InletCommand' not in st

def test_independent_inlet_owns_only_valve():
    config = (ROOT / "plc/config/mbconfig-inlet.cfg").read_text()
    st = (ROOT / "plc/inlet.st").read_text()
    assert 'Num_Devices = "3"' in config
    assert 'device0.Input_Registers_Size = "1"' in config
    assert 'device0.Holding_Registers_Size = "0"' in config
    assert 'device1.Input_Registers_Size = "2"' in config
    assert 'device1.Holding_Registers_Size = "1"' in config
    assert 'InletCommand AT %QW100' in st
    assert 'GateCommand' not in st

def test_second_runtime_compose_and_read_only_hmi():
    compose = (ROOT / "compose.yaml").read_text()
    assert 'openplc-inlet:' in compose
    assert 'PLC_ROLE: inlet' in compose
    assert 'ipv4_address: 172.28.10.11' in compose
    assert '127.0.0.1:8080:8080' in compose
    app = (ROOT / "services/hmi/app.py").read_text()
    assert 'def do_POST(self):' in app and '405' in app
    assert '"172.28.10.11": ("inlet", "OPENPLC_INLET")' in app
