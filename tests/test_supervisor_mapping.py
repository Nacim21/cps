"""Static checks: all controller crosslinks are native FC03 and the HMI stays read-only."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_supervisor_role():
    c=(ROOT/'plc/config/mbconfig-supervisor.cfg').read_text()
    assert 'Num_Devices = "3"' in c
    for i,ip,count in [(0,'172.28.10.10',13),(1,'172.28.10.11',7),(2,'172.28.10.12',7)]:
        assert f'device{i}.address = "{ip}"' in c
        assert f'device{i}.Holding_Registers_Read_Size = "{count}"' in c
        assert f'device{i}.Holding_Registers_Size = "0"' in c
    assert 'PLC_ROLE: supervisor' in (ROOT/'compose.yaml').read_text()

def test_single_spillway_writer_and_fallback():
    p1=(ROOT/'plc/spillway.st').read_text()
    sup=(ROOT/'plc/supervisor.st').read_text()
    assert 'GateCommand AT %QW100' in p1
    assert 'AT %QW' not in sup
    assert 'GateCommand := LocalGate;' in p1
    assert 'SupervisorFresh AND (SupervisorValid <> 0)' in p1
    assert 'LocalGateSnapshot AT %MW12' in p1
    assert 'IF P1HighWater <> 0' in sup
    assert 'P3Fresh AND (P3PeerFresh <> 0)' in sup

def test_hmi_four_roles():
    hmi=(ROOT/'services/hmi/app.py').read_text()
    assert '("supervisor", "OPENPLC_SUPERVISOR")' in hmi
    assert 'def do_POST' in hmi
    assert 'Read-only HMI: no write endpoints' in hmi
