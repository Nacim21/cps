"""Static checks for direct OpenPLC-to-OpenPLC Modbus status exchange."""
from pathlib import Path
BASE = Path(__file__).resolve().parents[1]

def test_peer_wiring():
    config = (BASE/'plc/config/mbconfig-inlet.cfg').read_text()
    assert 'Num_Devices = "3"' in config
    assert 'device2.address = "172.28.10.10"' in config
    assert 'device2.IP_Port = "15020"' in config
    assert 'device2.Holding_Registers_Read_Start = "1026"' in config
    assert 'device2.Holding_Registers_Read_Size = "5"' in config
    assert 'device2.Holding_Registers_Size = "0"' in config

def test_peer_health_logic():
    st = (BASE/'plc/inlet.st').read_text()
    assert 'PeerHeartbeat AT %IW107' in st
    assert 'PeerFresh := PeerSeen AND (PeerStaleTicks < 120)' in st
    assert 'IF NOT PeerFresh THEN' in st
    assert 'InletCommand := 0;' in st
    assert 'PeerGateDesired >= 75' in st

def test_native_server_only_enabled_on_spillway():
    entry = (BASE/'plc/entrypoint.sh').read_text()
    server = (BASE/'plc/start_modbus.sh').read_text()
    assert 'PLC_ROLE:-spillway' in entry
    assert 'sh /lab/start_modbus.sh &' in entry
    assert 'start_modbus(15020)' in server
